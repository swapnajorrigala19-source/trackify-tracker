import os
from app import app, db, User, bcrypt

with app.app_context():
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
        new_admin = User(username='AdminUser', email='admin@trackify.com', password_hash=hashed_pw, role='admin')
        db.session.add(new_admin)
        db.session.commit()
        print("Admin user created successfully!")
    else:
        print("Admin user already exists!")
