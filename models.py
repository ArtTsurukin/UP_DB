from setup_db import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(255))
    password = db.Column(db.String(255))


class PartImage(db.Model):
    __tablename__ = "part_images"

    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    is_main = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    part = db.relationship('Part', backref=db.backref('images', cascade='all, delete-orphan'))

class Part(db.Model):
    __tablename__ = "parts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    car = db.Column(db.String(255))
    part_number = db.Column(db.String(255))
    description = db.Column(db.String(255))
    price_in = db.Column(db.Integer)
    price_out = db.Column(db.Integer)



