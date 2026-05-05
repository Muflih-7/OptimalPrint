from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    history = db.relationship('PrintHistory', backref='user', lazy=True)
    saved = db.relationship('SavedSetting', backref='user', lazy=True)

class PrintHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    filament = db.Column(db.String(50))
    printer = db.Column(db.String(50))
    purpose = db.Column(db.String(50))
    nozzle = db.Column(db.String(10))
    size = db.Column(db.String(20))
    priority = db.Column(db.String(20))
    quality_level = db.Column(db.Integer)
    layer_height = db.Column(db.Float)
    speed = db.Column(db.Integer)
    infill = db.Column(db.Integer)
    print_time = db.Column(db.String(20))
    weight_grams = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SavedSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100))
    filament = db.Column(db.String(50))
    printer = db.Column(db.String(50))
    purpose = db.Column(db.String(50))
    nozzle = db.Column(db.String(10))
    size = db.Column(db.String(20))
    priority = db.Column(db.String(20))
    quality_level = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)