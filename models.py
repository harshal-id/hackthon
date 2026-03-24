from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'warden' or 'student'

class Pass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    room = db.Column(db.String(10))
    status = db.Column(db.String(20))

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    num = db.Column(db.String(10))
    status = db.Column(db.String(20))
    student = db.Column(db.String(100))

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    status = db.Column(db.String(20))
    author = db.Column(db.String(100))