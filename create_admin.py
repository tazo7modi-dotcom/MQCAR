from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # 1. Create the tables if they don't exist yet
    db.create_all()
    
    # 2. Now we can safely check for the admin
    existing_admin = User.query.filter_by(email="admin@dropi.com").first()
    
    if not existing_admin:
        admin = User(username="Boss", email="admin@dropi.com", is_admin=True)
        admin.set_password("DropiAa1223Aa") 
        db.session.add(admin)
        db.session.commit()
        print("✅ Success! Admin account created.")
        print("Email: admin@dropi.com")
        print("Password: DropiAa1223Aa")
    else:
        print("⚠️ Admin already exists.")