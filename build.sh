
set -o errexit


pip install -r requirements.txt


python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"


flask db stamp head
flask db migrate 2>/dev/null || true 
flask db upgrade


python setup_data.py