# models.py
from extensions import db
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()


class User(db.Model):
    username = db.Column(db.String(100), unique=True, nullable=False, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    gender = db.Column(db.Enum('M', 'F'), nullable=False)
    birthdate = db.Column(db.Date, nullable=False)
    country = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

    def check_password(self, _password):
        return bcrypt.check_password_hash(self.password, _password)
