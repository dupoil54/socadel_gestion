import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "CHANGE-ME")
uri = os.getenv("DATABASE_URL", "sqlite:///socadel.db")
if uri.startswith("postgres://"): uri = uri.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Base(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    code=db.Column(db.String(30), unique=True, nullable=False)
    name=db.Column(db.String(120), nullable=False)
    region=db.Column(db.String(100), nullable=False)
    department=db.Column(db.String(100), default="")
    localities=db.Column(db.Text, default="")

class User(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True, nullable=False)
    full_name=db.Column(db.String(150), nullable=False)
    password_hash=db.Column(db.String(255), nullable=False)
    role=db.Column(db.String(30), nullable=False)
    base_id=db.Column(db.Integer, db.ForeignKey("base.id"))
    active=db.Column(db.Boolean, default=True)
    def set_password(self,p): self.password_hash=generate_password_hash(p)
    def check_password(self,p): return check_password_hash(self.password_hash,p)

class Complaint(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    reference=db.Column(db.String(50), unique=True, nullable=False)
    customer=db.Column(db.String(150), nullable=False)
    phone=db.Column(db.String(40), nullable=False)
    region=db.Column(db.String(100), nullable=False)
    locality=db.Column(db.String(150), nullable=False)
    fault=db.Column(db.String(120), nullable=False)
    description=db.Column(db.Text, nullable=False)
    status=db.Column(db.String(40), default="Nouvelle")
    base_id=db.Column(db.Integer, db.ForeignKey("base.id"))
    created_at=db.Column(db.DateTime, default=datetime.utcnow)

class Intervention(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    complaint_id=db.Column(db.Integer, db.ForeignKey("complaint.id"), nullable=False)
    base_id=db.Column(db.Integer, db.ForeignKey("base.id"), nullable=False)
    technician_id=db.Column(db.Integer, db.ForeignKey("user.id"))
    status=db.Column(db.String(50), default="À planifier")
    notes=db.Column(db.Text, default="")
    jasa_complete=db.Column(db.Boolean, default=False)
    technician_signed=db.Column(db.Boolean, default=False)
    supervisor_signed=db.Column(db.Boolean, default=False)
    chef_signed=db.Column(db.Boolean, default=False)

def user():
    return db.session.get(User, session.get("uid")) if session.get("uid") else None
def required(fn):
    @wraps(fn)
    def wrap(*a,**k):
        if not user(): return redirect(url_for("login"))
        return fn(*a,**k)
    return wrap
def allow(*roles):
    def deco(fn):
        @required
        @wraps(fn)
        def wrap(*a,**k):
            if user().role not in roles: return "Accès refusé",403
            return fn(*a,**k)
        return wrap
    return deco
def scoped(q, model):
    u=user()
    if u.role=="chef_base": q=q.filter(model.base_id==u.base_id)
    if u.role=="technicien" and model==Intervention: q=q.filter(Intervention.technician_id==u.id)
    return q

@app.route("/")
def home(): return redirect(url_for("dashboard") if user() else url_for("login"))
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=User.query.filter_by(username=request.form["username"],active=True).first()
        if u and u.check_password(request.form["password"]):
            session.clear(); session["uid"]=u.id
            return redirect(url_for("dashboard"))
        flash("Identifiants incorrects.")
    return render_template("login.html")
@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("login"))
@app.route("/dashboard")
@required
def dashboard():
    cs=scoped(Complaint.query,Complaint).all()
    ins=scoped(Intervention.query,Intervention).all()
    return render_template("dashboard.html",u=user(),nc=len(cs),ni=len(ins),np=sum(c.status!="Clôturée" for c in cs))
@app.route("/bases",methods=["GET","POST"])
@allow("admin","direction")
def bases():
    if request.method=="POST":
        db.session.add(Base(code=request.form["code"],name=request.form["name"],region=request.form["region"],department=request.form.get("department",""),localities=request.form.get("localities","")))
        db.session.commit(); flash("Base créée.")
    return render_template("bases.html",bases=Base.query.all())
@app.route("/plaintes",methods=["GET","POST"])
@required
def plaintes():
    if request.method=="POST":
        c=Complaint(reference="SOC-"+datetime.utcnow().strftime("%Y%m%d%H%M%S"),customer=request.form["customer"],phone=request.form["phone"],region=request.form["region"],locality=request.form["locality"],fault=request.form["fault"],description=request.form["description"])
        matches=Base.query.filter_by(region=c.region).all()
        if len(matches)==1: c.base_id=matches[0].id
        db.session.add(c); db.session.commit(); flash("Plainte enregistrée : "+c.reference)
    return render_template("plaintes.html",rows=scoped(Complaint.query,Complaint).order_by(Complaint.created_at.desc()).all(),bases=Base.query.all(),can_assign=user().role in ["admin","direction","service_clientele"])
@app.route("/plaintes/<int:cid>/affecter",methods=["POST"])
@allow("admin","direction","service_clientele")
def affecter(cid):
    c=Complaint.query.get_or_404(cid); b=db.session.get(Base,int(request.form["base_id"]))
    if b and b.region==c.region: c.base_id=b.id; c.status="Affectée"; db.session.commit(); flash("Plainte affectée.")
    else: flash("Base invalide pour cette région.")
    return redirect(url_for("plaintes"))
@app.route("/interventions",methods=["GET","POST"])
@required
def interventions():
    if request.method=="POST":
        c=db.session.get(Complaint,int(request.form["complaint_id"]))
        if not c or not c.base_id: flash("La plainte doit d'abord être affectée.")
        elif user().role=="chef_base" and c.base_id!=user().base_id: return "Accès refusé",403
        else: db.session.add(Intervention(complaint_id=c.id,base_id=c.base_id)); c.status="Intervention planifiée"; db.session.commit()
    return render_template("interventions.html",rows=scoped(Intervention.query,Intervention).all(),complaints=scoped(Complaint.query.filter(Complaint.base_id.isnot(None)),Complaint).all(),u=user())
@app.route("/interventions/<int:iid>",methods=["POST"])
@required
def update_intervention(iid):
    i=scoped(Intervention.query,Intervention).filter_by(id=iid).first_or_404(); u=user()
    if u.role=="technicien":
        i.technician_id=u.id; i.notes=request.form.get("notes",""); i.jasa_complete=bool(request.form.get("jasa")); i.technician_signed=bool(request.form.get("techsign")); i.status="Travaux réalisés"
    elif u.role=="superviseur":
        i.supervisor_signed=bool(request.form.get("supsign")); i.status="En revue"
    elif u.role in ("chef_base","admin"):
        if not (i.jasa_complete and i.technician_signed and i.supervisor_signed): flash("JASA et signatures technicien/superviseur obligatoires."); return redirect(url_for("interventions"))
        i.chef_signed=True; i.status="Validée"; db.session.get(Complaint,i.complaint_id).status="Clôturée"
    else: return "Accès refusé",403
    db.session.commit(); flash("Intervention mise à jour."); return redirect(url_for("interventions"))
@app.route("/jasa")
@required
def jasa(): return render_template("jasa.html")
@app.route("/rapports")
@allow("admin","direction","chef_base")
def rapports(): return render_template("rapports.html",cs=scoped(Complaint.query,Complaint).all(),ins=scoped(Intervention.query,Intervention).all())
@app.route("/health")
def health(): return {"status":"ok"}
with app.app_context():
    db.create_all()
    name=os.getenv("INITIAL_ADMIN_USER","admin")
    if not User.query.filter_by(username=name).first():
        a=User(username=name,full_name="Administrateur SOCAD’EL",role="admin")
        a.set_password(os.getenv("INITIAL_ADMIN_PASSWORD","ChangeMe123!"))
        db.session.add(a); db.session.commit()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)))
