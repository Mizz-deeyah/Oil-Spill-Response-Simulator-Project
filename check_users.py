from main import app, db, User

with app.app_context():
    users = User.query.all()
    for u in users:
        print(u.id, u.email, u.role)