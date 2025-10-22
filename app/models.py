from flask_sqlalchemy import SQLAlchemy
from .extensions import db
from datetime import datetime


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


class PartVideo(db.Model):
    __tablename__ = "part_videos"

    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    part = db.relationship('Part', backref=db.backref('videos', cascade='all, delete-orphan'))


class Part(db.Model):
    __tablename__ = "parts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    car = db.Column(db.String(255))
    part_number = db.Column(db.String(255))
    description = db.Column(db.String(255))
    price_in = db.Column(db.Integer)
    price_out = db.Column(db.Integer)
    quantity = db.Column(db.Integer, default=1)


class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    discount_type = db.Column(db.String(10))  # 'percent' или 'fixed'
    discount_value = db.Column(db.Integer)  # значение скидки
    total_amount = db.Column(db.Integer)  # общая сумма
    final_amount = db.Column(db.Integer)  # итоговая сумма после скидки
    transport_company = db.Column(db.String(255))  # название ТК
    tracking_number = db.Column(db.String(255))  # трек номер

    items = db.relationship('SaleItem', backref='sale', cascade='all, delete-orphan')


class SaleItem(db.Model):
    __tablename__ = "sale_items"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id', ondelete='CASCADE'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Integer)  # цена на момент продажи
    total_price = db.Column(db.Integer)  # quantity * unit_price

    # Сохраняем основные данные о детали на момент продажи
    part_name = db.Column(db.String(255))
    part_car = db.Column(db.String(255))
    part_number = db.Column(db.String(255))

    part = db.relationship('Part')