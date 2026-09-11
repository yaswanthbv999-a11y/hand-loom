from datetime import datetime
import uuid
from app import db

PAYEE_TYPES = ['farmer', 'artisan']
PAYMENT_MODES = ['bank_transfer', 'upi', 'cash']
PAYMENT_STATUSES = ['pending', 'completed', 'failed']

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payee_id = db.Column(db.String(36), nullable=False)
    payee_type = db.Column(db.String(50), nullable=False)
    batch_id = db.Column(db.String(36), nullable=True)
    recorded_by = db.Column(db.String(36), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    mode = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='pending')
    notes = db.Column(db.String(255), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "payee_id": self.payee_id,
            "payee_type": self.payee_type,
            "batch_id": self.batch_id,
            "recorded_by": self.recorded_by,
            "amount": self.amount,
            "mode": self.mode,
            "status": self.status,
            "notes": self.notes,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
