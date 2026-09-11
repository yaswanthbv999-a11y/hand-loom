from datetime import datetime
import uuid
from app import db

SHIFT_STATUSES = ['pending', 'confirmed', 'cancelled']

class Availability(db.Model):
    __tablename__ = 'volunteer_availabilities'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    volunteer_id = db.Column(db.String(36), nullable=False)
    event_id = db.Column(db.String(36), nullable=False)
    preferred_slots = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "volunteer_id": self.volunteer_id,
            "event_id": self.event_id,
            "preferred_slots": self.preferred_slots,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Shift(db.Model):
    __tablename__ = 'volunteer_shifts'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    volunteer_id = db.Column(db.String(36), nullable=False)
    event_id = db.Column(db.String(36), nullable=False)
    time_slot = db.Column(db.String(100), nullable=False)
    availability_id = db.Column(db.String(36), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='pending')
    confirmed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "volunteer_id": self.volunteer_id,
            "event_id": self.event_id,
            "time_slot": self.time_slot,
            "availability_id": self.availability_id,
            "status": self.status,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
