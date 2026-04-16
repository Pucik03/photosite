from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    preview_image = db.Column(db.String(200))
    is_published = db.Column(db.Boolean, default=False)

    groups = db.relationship(
        "PhotoGroup",
        backref="event",
        cascade="all, delete-orphan",
        lazy=True
    )


class PhotoGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("event.id"),
        nullable=False
    )

    photos = db.relationship(
        "Photo",
        backref="group",
        cascade="all, delete-orphan",
        lazy=True
    )


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    preview_filename = db.Column(db.String(200), nullable=False)
    thumb_filename = db.Column(db.String(200), nullable=False)

    price = db.Column(db.Float, nullable=False, default=0.0)

    group_id = db.Column(
        db.Integer,
        db.ForeignKey("photo_group.id"),
        nullable=False
    )


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    customer_name = db.Column(db.String(120))
    customer_phone = db.Column(db.String(50))
    customer_email = db.Column(db.String(120))

    status = db.Column(db.String(20), default="awaiting_payment")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship(
        "OrderItem",
        backref="order",
        cascade="all, delete-orphan"
    )


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))
    photo_id = db.Column(db.Integer, db.ForeignKey("photo.id"))

    photo = db.relationship("Photo")


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)