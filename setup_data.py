from app import create_app, db
from app.models import User

# Initialize the Flask app
app = create_app()

def create_admin_user():
    """Creates the main admin user if not exists"""
    print("\n👤 Checking Admin User...")
    
    email = "tazo@tazo.com"
    password = "Hamod88"


    admin = User.query.filter_by(email=email).first()
    
    if admin:
        print(f"   ✅ Admin already exists: {email}")
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()
            print("   🔧 Fixed admin permissions.")
    else:
       
        print("   ⚠️ Admin not found. Resetting DB and creating new admin...")
        
        db.drop_all()    
        db.create_all()  
        
        new_admin = User(email=email, username="Tazo", is_admin=True)
        new_admin.set_password(password)
        
        db.session.add(new_admin)
        db.session.commit()
        print(f"   ✨ Created Admin: {email} / {password}")

if __name__ == "__main__":
    with app.app_context():
     
        db.create_all()
        create_admin_user()