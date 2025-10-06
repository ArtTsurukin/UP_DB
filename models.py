from setup_db import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(255))
    password = db.Column(db.String(255))

class Part(db.Model):
    __tablename__ = "parts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    part_number = db.Column(db.String(255))
    description = db.Column(db.String(255))
    price_in = db.Column(db.Integer)
    price_out = db.Column(db.Integer)





