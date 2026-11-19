# SOCAD’EL — socle initial

## Installation locale
Python 3.11+ recommandé.
1. `python -m venv .venv`
2. Activez l'environnement virtuel.
3. `pip install -r requirements.txt`
4. Définissez `SECRET_KEY` et `INITIAL_ADMIN_PASSWORD`.
5. `python main.py`
6. Ouvrez http://127.0.0.1:5000

Compte initial par défaut : admin / ChangeMe123! — changez-le impérativement.

## Publication GitHub + Render
1. Créez un dépôt GitHub et téléversez le contenu de ce dossier.
2. Dans Render, choisissez New > Blueprint, puis connectez ce dépôt.
3. Render détectera `render.yaml` et créera le service et PostgreSQL.
4. Renseignez `INITIAL_ADMIN_PASSWORD` avec un mot de passe fort, puis déployez.

## Important
Ceci est un socle de démarrage, pas une version de production prête pour des données opérationnelles sensibles.
À compléter : administration des utilisateurs, affectations détaillées par localité/arrondissement, JASA officiel recto-verso et PDF, signatures électroniques, PWA hors ligne et synchronisation sécurisée, prestataire SMS, exports Excel/PDF, journal d'audit, sauvegardes testées, protection anti-bruteforce et tests de sécurité.
Le routage actuel ne fait qu'une correspondance exacte sur la région ; toute ambiguïté doit être vérifiée manuellement. Le logo est un emplacement réservé.
