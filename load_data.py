
import pandas as pd
from datetime import datetime
import os
from database import flask_app, db, Article, Company

def load_articles_from_csv():
    """Load articles data from CSV file"""
    try:
        df = pd.read_csv('attached_assets/temp_article_df_1751374177682.csv')
        
        with flask_app.app_context():
            # Clear existing data
            db.session.query(Article).delete()
            
            for _, row in df.iterrows():
                # Parse published_at date
                published_at = None
                if pd.notna(row['published_at']):
                    try:
                        published_at = pd.to_datetime(row['published_at'])
                    except:
                        pass
                
                # Parse modified_at date
                modified_at = None
                if pd.notna(row['modified_at']):
                    try:
                        modified_at = pd.to_datetime(row['modified_at'])
                    except:
                        pass
                
                article = Article(
                    pk=str(row['pk']) if pd.notna(row['pk']) else f"row_{_}",
                    article_id=str(row['article_id']) if pd.notna(row['article_id']) else '',
                    url=str(row['url']) if pd.notna(row['url']) else '',
                    search_term=str(row['search_term']) if pd.notna(row['search_term']) else '',
                    title=str(row['title']) if pd.notna(row['title']) else '',
                    published_at=published_at,
                    modified_at=modified_at,
                    country_code=str(row['country_code']) if pd.notna(row['country_code']) else '',
                    isic_name=str(row['isic_name']) if pd.notna(row['isic_name']) else '',
                    isic_code=str(row['isic_code']) if pd.notna(row['isic_code']) else ''
                )
                db.session.add(article)
            
            db.session.commit()
            print(f"Loaded {len(df)} articles into database")
            
    except Exception as e:
        print(f"Error loading articles: {str(e)}")
        db.session.rollback()

def load_companies_from_csv():
    """Load companies data from CSV file"""
    try:
        df = pd.read_csv('attached_assets/temp_company_level_df_1751374177683.csv')
        
        with flask_app.app_context():
            # Clear existing data
            db.session.query(Company).delete()
            
            for _, row in df.iterrows():
                # Handle settlement amount
                settlement_amount = None
                if pd.notna(row['settlement_amount']):
                    try:
                        settlement_amount = float(row['settlement_amount'])
                    except:
                        pass
                
                company = Company(
                    pk=str(row['pk']) if pd.notna(row['pk']) else f"row_{_}",
                    company_name=str(row['company_name']) if pd.notna(row['company_name']) else '',
                    litigation_reason=str(row['litigation_reason']) if pd.notna(row['litigation_reason']) else '',
                    litigation_reason_reference=str(row['litigation_reason_reference']) if pd.notna(row['litigation_reason_reference']) else '',
                    claim_category=str(row['claim_category']) if pd.notna(row['claim_category']) else '',
                    claim_category_reference=str(row['claim_category_reference']) if pd.notna(row['claim_category_reference']) else '',
                    source_of_pfas=str(row['source_of_pfas']) if pd.notna(row['source_of_pfas']) else '',
                    source_of_pfas_reference=str(row['source_of_pfas_reference']) if pd.notna(row['source_of_pfas_reference']) else '',
                    settlement_finalized=bool(row['settlement_finalized']) if pd.notna(row['settlement_finalized']) else False,
                    settlement_currency=str(row['settlement_currency']) if pd.notna(row['settlement_currency']) else '',
                    settlement_amount=settlement_amount,
                    settlement_paid_date=str(row['settlement_paid_date']) if pd.notna(row['settlement_paid_date']) else '',
                    settlement_reference=str(row['settlement_reference']) if pd.notna(row['settlement_reference']) else ''
                )
                db.session.add(company)
            
            db.session.commit()
            print(f"Loaded {len(df)} companies into database")
            
    except Exception as e:
        print(f"Error loading companies: {str(e)}")
        db.session.rollback()

def create_tables_and_load_data():
    """Create database tables and load data"""
    with flask_app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created")
        
        # Load data
        load_articles_from_csv()
        load_companies_from_csv()
        print("Data loading completed")

if __name__ == '__main__':
    create_tables_and_load_data()
