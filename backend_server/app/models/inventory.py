from datetime import datetime
import uuid
from app import db

class ProductionBatch(db.Model):
    __tablename__ = 'production_batches'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), nullable=False)
    recorded_by = db.Column(db.String(36), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='in_progress')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "farmer_id": self.farmer_id,
            "recorded_by": self.recorded_by,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
