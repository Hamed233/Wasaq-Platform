from app import db
from datetime import datetime
import uuid

class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    report_type = db.Column(db.String(50))  # status, project update, maintenance, etc.
    status = db.Column(db.String(50))  # draft, published, archived
    
    # Foreign keys
    land_id = db.Column(db.Integer, db.ForeignKey('lands.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)
    
    # Additional attributes
    attachments = db.Column(db.Text)  # JSON list of attachment URLs
    tags = db.Column(db.String(200))  # Comma-separated tags
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'content': self.content,
            'report_type': self.report_type,
            'status': self.status,
            'land_id': self.land_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'attachments': self.attachments,
            'tags': self.tags
        }
    
    def __repr__(self):
        return f'<Report {self.title}>'
