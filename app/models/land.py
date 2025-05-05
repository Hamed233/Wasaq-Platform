from app import db
from datetime import datetime
import uuid

class Land(db.Model):
    __tablename__ = 'lands'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    region = db.Column(db.String(50), index=True)  # Northern, Southern, Eastern, Western, Central
    city = db.Column(db.String(50))
    district = db.Column(db.String(100))
    address = db.Column(db.String(200))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    area = db.Column(db.Float)  # in square meters
    land_type = db.Column(db.String(50))  # residential, commercial, agricultural, etc.
    status = db.Column(db.String(50))  # available, under development, invested, etc.
    annual_return = db.Column(db.Float)  # annual return percentage
    occupancy_rate = db.Column(db.Float)  # occupancy rate percentage
    water_usage = db.Column(db.Float)  # water usage in cubic meters
    yearly_income = db.Column(db.Float)  # yearly income in SAR
    
    # Contact information
    contact_name = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(100))
    contact_position = db.Column(db.String(100))
    contact_notes = db.Column(db.Text)
    
    # GIS data
    geom = db.Column(db.Text)  # GeoJSON representation of the land geometry
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reports = db.relationship('Report', backref='land', lazy='dynamic')
    recommendations = db.relationship('Recommendation', backref='land', lazy='dynamic')
    statistics = db.relationship('Statistic', backref='land', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'description': self.description,
            'region': self.region,
            'city': self.city,
            'district': self.district,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'area': self.area,
            'land_type': self.land_type,
            'status': self.status,
            'annual_return': self.annual_return,
            'occupancy_rate': self.occupancy_rate,
            'water_usage': self.water_usage,
            'yearly_income': self.yearly_income,
            'contact_name': self.contact_name,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'contact_position': self.contact_position,
            'contact_notes': self.contact_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Land {self.name}>'
