from app import app, db, User, bcrypt

with app.app_context():
    admins = User.query.filter_by(role='admin').all()
    if not admins:
        print("No admin users found.")
    else:
        for a in admins:
            print(f"Found Admin - ID: {a.id}, Username: {a.username}, Email: {a.email}")
            a.password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
            print(f"Reset password for {a.email} to 'admin123'")
        db.session.commit()
        print("Database commit successful.")
