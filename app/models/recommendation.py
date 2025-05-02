from app import db
from datetime import datetime
import uuid

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    recommendation_type = db.Column(db.String(50))  # development, investment, maintenance, etc.
    priority = db.Column(db.String(20))  # high, medium, low
    status = db.Column(db.String(50))  # pending, approved, rejected, implemented
    
    # AI-generated confidence score (0-1)
    confidence_score = db.Column(db.Float, default=0.0)
    
    # Estimated metrics
    estimated_cost = db.Column(db.Float)  # in SAR
    estimated_return = db.Column(db.Float)  # percentage
    estimated_timeframe = db.Column(db.Integer)  # in months
    
    # Foreign keys
    land_id = db.Column(db.Integer, db.ForeignKey('lands.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    implemented_at = db.Column(db.DateTime, nullable=True)
    
    # Additional data
    supporting_data = db.Column(db.Text)  # JSON with supporting data points
    ai_model_version = db.Column(db.String(50))  # Version of the AI model that generated this
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'description': self.description,
            'recommendation_type': self.recommendation_type,
            'priority': self.priority,
            'status': self.status,
            'confidence_score': self.confidence_score,
            'estimated_cost': self.estimated_cost,
            'estimated_return': self.estimated_return,
            'estimated_timeframe': self.estimated_timeframe,
            'land_id': self.land_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'implemented_at': self.implemented_at.isoformat() if self.implemented_at else None,
            'supporting_data': self.supporting_data,
            'ai_model_version': self.ai_model_version
        }
    
    def __repr__(self):
        return f'<Recommendation {self.title}>'
