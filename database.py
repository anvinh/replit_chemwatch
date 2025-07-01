import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass

# Create a separate Flask app just for database operations
flask_app = Flask(__name__)
flask_app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
flask_app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db = SQLAlchemy(model_class=Base)
db.init_app(flask_app)

# Define models directly here to avoid circular imports
class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Company {self.name}>'

class Industry(db.Model):
    __tablename__ = 'industries'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Industry {self.name}>'

class LegalAction(db.Model):
    __tablename__ = 'legal_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    action_date = db.Column(db.Date, nullable=False)
    article_url = db.Column(db.String(1000))
    status = db.Column(db.String(100))
    
    # Foreign keys
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    industry_id = db.Column(db.Integer, db.ForeignKey('industries.id'), nullable=False)
    
    # Relationships
    company = db.relationship('Company', backref='legal_actions')
    industry = db.relationship('Industry', backref='legal_actions')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<LegalAction {self.title}>'
    
    def to_dict(self):
        """Convert the legal action to a dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'action_date': self.action_date.isoformat() if self.action_date else None,
            'article_url': self.article_url,
            'status': self.status,
            'company': self.company.name if self.company else None,
            'industry': self.industry.name if self.industry else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }