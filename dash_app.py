
import os
import logging
import dash
from dash import dcc, html, Input, Output, dash_table, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import numpy as np
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Import database setup
from database import flask_app, db, Article, Company

# Create Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

def get_articles(company_filter=None):
    """Get filtered articles from database"""
    try:
        with flask_app.app_context():
            query = db.session.query(Article)
            
            if company_filter:
                # Find companies that match the filter and get their associated articles by pk
                company_pks = db.session.query(Company.pk).filter(
                    Company.company_name.ilike(f'%{company_filter}%')
                ).all()
                company_pk_list = [pk[0] for pk in company_pks]
                if company_pk_list:
                    query = query.filter(Article.pk.in_(company_pk_list))
                else:
                    return pd.DataFrame()  # No matching companies found
            
            articles = query.order_by(Article.published_at.desc()).all()
            
            data = []
            for article in articles:
                data.append({
                    'PK': article.pk,
                    'Article ID': article.article_id,
                    'Title': article.title,
                    'URL': article.url,
                    'Published Date': article.published_at.strftime('%Y-%m-%d %H:%M') if article.published_at else '',
                    'Country': article.country_code,
                    'Industry': article.isic_name,
                    'Search Term': article.search_term
                })
            
            return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Error fetching articles: {str(e)}")
        return pd.DataFrame()

def get_companies(article_filter=None):
    """Get filtered companies from database"""
    try:
        with flask_app.app_context():
            query = db.session.query(Company)
            
            if article_filter:
                # Filter companies based on article pk
                query = query.filter(Company.pk == article_filter)
            
            companies = query.order_by(Company.company_name).all()
            
            data = []
            for company in companies:
                data.append({
                    'PK': company.pk,
                    'Company Name': company.company_name,
                    'Litigation Reason': company.litigation_reason,
                    'Claim Category': company.claim_category,
                    'Source of PFAS': company.source_of_pfas,
                    'Settlement Finalized': 'Yes' if company.settlement_finalized else 'No',
                    'Settlement Amount': f"{company.settlement_currency} {company.settlement_amount:,.0f}" if company.settlement_amount else '',
                    'Settlement Date': company.settlement_paid_date or ''
                })
            
            return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Error fetching companies: {str(e)}")
        return pd.DataFrame()

def get_scatter_plot_data(company_filter=None, article_filter=None):
    """Get data for scatter plot showing articles published per week"""
    try:
        with flask_app.app_context():
            query = db.session.query(Article)
            
            if company_filter:
                company_pks = db.session.query(Company.pk).filter(
                    Company.company_name.ilike(f'%{company_filter}%')
                ).all()
                company_pk_list = [pk[0] for pk in company_pks]
                if company_pk_list:
                    query = query.filter(Article.pk.in_(company_pk_list))
                else:
                    return pd.DataFrame()
            
            if article_filter:
                query = query.filter(Article.pk == article_filter)
            
            articles = query.all()
            
            data = []
            for article in articles:
                if article.published_at:
                    # Get the start of the week (Monday)
                    week_start = article.published_at - pd.Timedelta(days=article.published_at.weekday())
                    data.append({
                        'week': week_start.strftime('%Y-%m-%d'),
                        'title': article.title,
                        'published_date': article.published_at,
                        'pk': article.pk
                    })
            
            df = pd.DataFrame(data)
            if not df.empty:
                # Group by week and add vertical positioning for dots
                df_grouped = df.groupby('week').apply(lambda x: x.assign(
                    y_position=range(len(x))
                )).reset_index(drop=True)
                return df_grouped
            
            return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error fetching scatter plot data: {str(e)}")
        return pd.DataFrame()

# App layout
app.layout = dbc.Container([
    dbc.Row([
        # Sidebar
        dbc.Col([
            html.Div([
                html.H4([
                    html.I(className="fas fa-filter me-2"),
                    "Filters"
                ], className="mb-4"),
                
                # Company Filter
                html.Div([
                    dbc.Label([
                        html.I(className="fas fa-building me-1"),
                        "Company Filter"
                    ]),
                    dcc.Input(
                        id='company-filter',
                        type='text',
                        placeholder="Enter company name...",
                        className="form-control"
                    )
                ], className="mb-4"),
                
                # Clear Filters Button
                dbc.Button([
                    html.I(className="fas fa-eraser me-1"),
                    "Clear Filters"
                ], id="clear-filters", color="outline-secondary", className="w-100 mb-3"),
                
                # Filter Status
                html.Div(id="filter-status", className="text-muted small")
            ], className="p-3 bg-light")
        ], width=3, className="vh-100 position-fixed"),
        
        # Main Content
        dbc.Col([
            # Header
            html.Div([
                html.H1([
                    html.I(className="fas fa-newspaper me-2"),
                    "PFAS Articles & Companies Dashboard"
                ], className="display-6"),
                html.P("Monitor and analyze PFAS-related articles and company involvement", 
                      className="text-muted")
            ], className="mb-4"),
            
            # Scatter Plot Chart
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-chart-scatter me-2"),
                        "Articles Published by Week"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dcc.Graph(id="scatter-plot-chart")
                ])
            ], className="mb-4"),
            
            # Articles Table
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        html.H5([
                            html.I(className="fas fa-newspaper me-2"),
                            "Articles"
                        ], className="mb-0"),
                        dbc.Badge(id="article-count", color="primary")
                    ], className="d-flex justify-content-between align-items-center")
                ]),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='articles-table',
                        columns=[
                            {'name': 'Title', 'id': 'Title', 'type': 'text'},
                            {'name': 'Published Date', 'id': 'Published Date', 'type': 'datetime'},
                            {'name': 'Country', 'id': 'Country', 'type': 'text'},
                            {'name': 'Industry', 'id': 'Industry', 'type': 'text'},
                            {'name': 'Search Term', 'id': 'Search Term', 'type': 'text'},
                            {'name': 'PK', 'id': 'PK', 'type': 'text'}
                        ],
                        data=[],
                        sort_action="native",
                        filter_action="native",
                        page_action="native",
                        page_current=0,
                        page_size=10,
                        row_selectable="single",
                        selected_rows=[],
                        style_cell={
                            'textAlign': 'left',
                            'padding': '10px',
                            'fontFamily': 'Arial'
                        },
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(248, 248, 248)'
                            }
                        ],
                        style_cell_conditional=[
                            {
                                'if': {'column_id': 'Title'},
                                'width': '30%',
                                'whiteSpace': 'normal',
                                'height': 'auto',
                            },
                            {
                                'if': {'column_id': 'PK'},
                                'width': '0%',
                                'display': 'none'
                            }
                        ]
                    )
                ])
            ], className="mb-4"),
            
            # Companies Table
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        html.H5([
                            html.I(className="fas fa-building me-2"),
                            "Related Companies"
                        ], className="mb-0"),
                        dbc.Badge(id="company-count", color="secondary")
                    ], className="d-flex justify-content-between align-items-center")
                ]),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='companies-table',
                        columns=[
                            {'name': 'Company Name', 'id': 'Company Name', 'type': 'text'},
                            {'name': 'Litigation Reason', 'id': 'Litigation Reason', 'type': 'text'},
                            {'name': 'Claim Category', 'id': 'Claim Category', 'type': 'text'},
                            {'name': 'Source of PFAS', 'id': 'Source of PFAS', 'type': 'text'},
                            {'name': 'Settlement Finalized', 'id': 'Settlement Finalized', 'type': 'text'},
                            {'name': 'Settlement Amount', 'id': 'Settlement Amount', 'type': 'text'},
                            {'name': 'PK', 'id': 'PK', 'type': 'text'}
                        ],
                        data=[],
                        sort_action="native",
                        filter_action="native",
                        page_action="native",
                        page_current=0,
                        page_size=10,
                        row_selectable="single",
                        selected_rows=[],
                        style_cell={
                            'textAlign': 'left',
                            'padding': '10px',
                            'fontFamily': 'Arial'
                        },
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(248, 248, 248)'
                            }
                        ],
                        style_cell_conditional=[
                            {
                                'if': {'column_id': 'Company Name'},
                                'width': '20%',
                            },
                            {
                                'if': {'column_id': 'PK'},
                                'width': '0%',
                                'display': 'none'
                            }
                        ]
                    )
                ])
            ])
        ], width=9, className="ms-auto")
    ]),
    
    # Hidden div to store selected article PK
    html.Div(id="selected-article-pk", style={'display': 'none'}),
    html.Div(id="selected-company-pk", style={'display': 'none'})
], fluid=True)

# Callbacks
@app.callback(
    [Output('articles-table', 'data'),
     Output('companies-table', 'data'),
     Output('scatter-plot-chart', 'figure'),
     Output('article-count', 'children'),
     Output('company-count', 'children'),
     Output('filter-status', 'children'),
     Output('selected-article-pk', 'children'),
     Output('selected-company-pk', 'children')],
    [Input('company-filter', 'value'),
     Input('articles-table', 'selected_rows'),
     Input('companies-table', 'selected_rows'),
     Input('clear-filters', 'n_clicks')],
    prevent_initial_call=False
)
def update_dashboard(company_filter, selected_article_rows, selected_company_rows, clear_clicks):
    ctx = callback_context
    
    # Handle clear filters
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'clear-filters.n_clicks' and clear_clicks:
        company_filter = None
        selected_article_rows = []
        selected_company_rows = []
    
    # Get selected article PK
    selected_article_pk = None
    if selected_article_rows:
        articles_df = get_articles(company_filter)
        if not articles_df.empty and selected_article_rows[0] < len(articles_df):
            selected_article_pk = articles_df.iloc[selected_article_rows[0]]['PK']
    
    # Get selected company PK  
    selected_company_pk = None
    if selected_company_rows:
        companies_df = get_companies(selected_article_pk)
        if not companies_df.empty and selected_company_rows[0] < len(companies_df):
            selected_company_pk = companies_df.iloc[selected_company_rows[0]]['Company Name']
    
    # Get filtered data
    articles_df = get_articles(selected_company_pk if selected_company_pk else company_filter)
    companies_df = get_companies(selected_article_pk)
    scatter_df = get_scatter_plot_data(selected_company_pk if selected_company_pk else company_filter, selected_article_pk)
    
    # Update articles table
    articles_data = articles_df.to_dict('records') if not articles_df.empty else []
    
    # Update companies table
    companies_data = companies_df.to_dict('records') if not companies_df.empty else []
    
    # Update scatter plot
    if not scatter_df.empty:
        fig = px.scatter(
            scatter_df, 
            x='week', 
            y='y_position',
            hover_data=['title', 'published_date'],
            title='Articles Published by Week (Each dot represents one article)'
        )
        fig.update_traces(
            marker=dict(size=8, opacity=0.7),
            hovertemplate='<b>%{customdata[0]}</b><br>Published: %{customdata[1]}<br>Week: %{x}<extra></extra>'
        )
        fig.update_layout(
            xaxis_title="Week Starting",
            yaxis_title="Articles in Week",
            yaxis=dict(tickmode='linear', dtick=1),
            hovermode='closest'
        )
    else:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for the selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16, color="gray")
        )
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
    
    # Update counts
    article_count = f"{len(articles_df)} articles"
    company_count = f"{len(companies_df)} companies"
    
    # Update filter status
    filters = []
    if company_filter:
        filters.append(f"Company: {company_filter}")
    if selected_article_pk:
        filters.append(f"Article selected")
    if selected_company_pk:
        filters.append(f"Company: {selected_company_pk}")
    
    if filters:
        filter_status = f"Active filters: {', '.join(filters)}"
    else:
        filter_status = "No filters applied"
    
    return (articles_data, companies_data, fig, article_count, company_count, 
            filter_status, selected_article_pk or '', selected_company_pk or '')

@app.callback(
    [Output('company-filter', 'value')],
    [Input('clear-filters', 'n_clicks')]
)
def clear_company_filter(n_clicks):
    ctx = callback_context
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'clear-filters.n_clicks' and n_clicks:
        return ['']
    return [dash.no_update]

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=5000, debug=True)
