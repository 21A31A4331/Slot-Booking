from datetime import datetime, date, time, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='client')  # 'client' or 'admin'
    created_at = db.Column(db.DateTime, default=utc_now)

    bookings = db.relationship('Booking', backref='customer', lazy=True, cascade='all, delete-orphan')

    @property
    def is_admin(self):
        return self.role == 'admin'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    category = db.Column(db.String(50), default='General')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    slots = db.relationship('Slot', backref='service', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Service {self.name}>'


class Slot(db.Model):
    __tablename__ = 'slots'

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=1)
    is_available = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    bookings = db.relationship('Booking', backref='slot', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('service_id', 'date', 'start_time', name='uq_service_date_time'),
    )

    @property
    def formatted_time_range(self):
        return f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"

    @property
    def is_past(self):
        now = datetime.now()
        slot_datetime = datetime.combine(self.date, self.start_time)
        return slot_datetime < now

    def __repr__(self):
        return f'<Slot {self.service_id} {self.date} {self.start_time}>'


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(30), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slots.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='CONFIRMED')  # 'CONFIRMED', 'CANCELLED', 'COMPLETED'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    def __repr__(self):
        return f'<Booking {self.booking_reference} ({self.status})>'
