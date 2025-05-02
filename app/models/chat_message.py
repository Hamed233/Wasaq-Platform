from app import db
from datetime import datetime
import uuid

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), index=True)  # To group conversations
    content = db.Column(db.Text, nullable=False)
    is_bot = db.Column(db.Boolean, default=False)  # True if message is from bot, False if from user
    
    # Foreign keys (optional - if user is authenticated)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # AI processing data
    intent = db.Column(db.String(100), nullable=True)  # Detected intent
    confidence = db.Column(db.Float, nullable=True)  # Confidence score
    entities = db.Column(db.Text, nullable=True)  # JSON of detected entities
    sentiment = db.Column(db.Float, nullable=True)  # Sentiment score (-1 to 1)
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'session_id': self.session_id,
            'content': self.content,
            'is_bot': self.is_bot,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'intent': self.intent,
            'confidence': self.confidence,
            'entities': self.entities,
            'sentiment': self.sentiment
        }
    
    def __repr__(self):
        return f'<ChatMessage {self.id}>'
