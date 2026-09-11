from datetime import datetime
import uuid
from app import db

WORKSHOP_TYPES = ['spinning', 'weaving', 'dyeing']

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(150), nullable=False)
    event_type = db.Column(db.String(50), nullable=False, default='Exhibition')
    city = db.Column(db.String(100), nullable=True)
    date = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "event_type": self.event_type,
            "city": self.city,
            "date": self.date,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Workshop(db.Model):
    __tablename__ = 'workshops'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_by = db.Column(db.String(36), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    workshop_type = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=20)
    enrolled_count = db.Column(db.Integer, nullable=False, default=0)
    fee = db.Column(db.Float, nullable=False, default=0.0)
    venue = db.Column(db.String(150), nullable=True)
    date = db.Column(db.String(50), nullable=True)
    event_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "created_by": self.created_by,
            "title": self.title,
            "workshop_type": self.workshop_type,
            "capacity": self.capacity,
            "enrolled_count": self.enrolled_count,
            "fee": self.fee,
            "venue": self.venue,
            "date": self.date,
            "event_id": self.event_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Registration(db.Model):
    __tablename__ = 'workshop_registrations'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workshop_id = db.Column(db.String(36), db.ForeignKey('workshops.id'), nullable=False)
    customer_id = db.Column(db.String(36), nullable=False)
    confirmation_sent = db.Column(db.Boolean, default=True)
    payment_status = db.Column(db.String(50), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "workshop_id": self.workshop_id,
            "customer_id": self.customer_id,
            "confirmation_sent": self.confirmation_sent,
            "payment_status": self.payment_status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
