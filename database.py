import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass

# Create a separate Flask app just for database operations
flask_app = Flask(__name__)

# Get database URL from environment or use a default SQLite for development
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # Fallback to SQLite for development if PostgreSQL is not configured
    database_url = "sqlite:///development.db"

flask_app.config["SQLALCHEMY_DATABASE_URI"] = database_url
flask_app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db = SQLAlchemy(model_class=Base)
db.init_app(flask_app)

# Define models based on CSV structure
class Article(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    pk = db.Column(db.String(255), unique=True, nullable=False)
    article_id = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    search_term = db.Column(db.String(255))
    title = db.Column(db.String(1000), nullable=False)
    published_at = db.Column(db.DateTime, nullable=False)
    modified_at = db.Column(db.DateTime)
    country_code = db.Column(db.String(10))
    isic_name = db.Column(db.String(500))
    isic_code = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Article {self.title}>'

class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    pk = db.Column(db.String(255), nullable=False)
    company_name = db.Column(db.String(500), nullable=False)
    litigation_reason = db.Column(db.String(1000))
    litigation_reason_reference = db.Column(db.Text)
    claim_category = db.Column(db.String(500))
    claim_category_reference = db.Column(db.Text)
    source_of_pfas = db.Column(db.String(500))
    source_of_pfas_reference = db.Column(db.Text)
    settlement_finalized = db.Column(db.Boolean, default=False)
    settlement_currency = db.Column(db.String(10))
    settlement_amount = db.Column(db.Float)
    settlement_paid_date = db.Column(db.String(255))
    settlement_reference = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Company {self.company_name}>'