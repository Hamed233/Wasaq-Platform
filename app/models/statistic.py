from app import db
from datetime import datetime
import uuid

class Statistic(db.Model):
    __tablename__ = 'statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # financial, usage, demographic, etc.
    value = db.Column(db.Float)
    unit = db.Column(db.String(20))  # percentage, SAR, count, etc.
    time_period = db.Column(db.String(50))  # daily, monthly, quarterly, yearly
    
    # Foreign keys
    land_id = db.Column(db.Integer, db.ForeignKey('lands.id'))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)  # When the statistic was recorded
    
    # Additional data
    raw_data = db.Column(db.Text)  # JSON with raw data points
    data_source = db.Column(db.String(100))  # Source of the data
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'value': self.value,
            'unit': self.unit,
            'time_period': self.time_period,
            'land_id': self.land_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'raw_data': self.raw_data,
            'data_source': self.data_source
        }
    
    def __repr__(self):
        return f'<Statistic {self.name}>'
