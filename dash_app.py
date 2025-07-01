import os
import logging
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Import database setup
from database import flask_app, db, Company, Industry, LegalAction

# Create Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

def get_companies():
    """Get all companies from database"""
    try:
        with flask_app.app_context():
            companies = db.session.query(Company).order_by(Company.name).all()
            return [{'label': c.name, 'value': c.id} for c in companies]
    except Exception as e:
        logging.error(f"Error fetching companies: {str(e)}")
        return []

def get_industries():
    """Get all industries from database"""
    try:
        with flask_app.app_context():
            industries = db.session.query(Industry).order_by(Industry.name).all()
            return [{'label': i.name, 'value': i.id} for i in industries]
    except Exception as e:
        logging.error(f"Error fetching industries: {str(e)}")
        return []

def get_legal_actions(company_id=None, industry_id=None):
    """Get filtered legal actions from database"""
    try:
        with flask_app.app_context():
            query = db.session.query(LegalAction).join(Company).join(Industry)
            
            if company_id:
                query = query.filter(LegalAction.company_id == company_id)
            if industry_id:
                query = query.filter(LegalAction.industry_id == industry_id)
            
            legal_actions = query.order_by(LegalAction.action_date.desc()).all()
            
            data = []
            for action in legal_actions:
                data.append({
                    'Title': action.title,
                    'Company': action.company.name,
                    'Industry': action.industry.name,
                    'Action Date': action.action_date.strftime('%Y-%m-%d') if action.action_date else '',
                    'Status': action.status or '',
                    'Description': action.description or ''
                })
            
            return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Error fetching legal actions: {str(e)}")
        return pd.DataFrame()

def get_time_series_data(company_id=None, industry_id=None):
    """Get time series data for chart"""
    try:
        with flask_app.app_context():
            query = db.session.query(
                func.date_trunc('month', LegalAction.action_date).label('month'),
                func.count(LegalAction.id).label('count')
            ).join(Company).join(Industry)
            
            if company_id:
                query = query.filter(LegalAction.company_id == company_id)
            if industry_id:
                query = query.filter(LegalAction.industry_id == industry_id)
            
            results = query.group_by(func.date_trunc('month', LegalAction.action_date)).order_by(func.date_trunc('month', LegalAction.action_date)).all()
            
            data = []
            for result in results:
                if result.month:
                    data.append({
                        'Month': result.month.strftime('%Y-%m'),
                        'Count': result.count
                    })
            
            return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Error fetching time series data: {str(e)}")
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
                        "Company"
                    ]),
                    dcc.Dropdown(
                        id='company-filter',
                        options=[{'label': 'All Companies', 'value': ''}] + get_companies(),
                        value='',
                        placeholder="Select a company"
                    )
                ], className="mb-4"),
                
                # Industry Filter
                html.Div([
                    dbc.Label([
                        html.I(className="fas fa-industry me-1"),
                        "Industry"
                    ]),
                    dcc.Dropdown(
                        id='industry-filter',
                        options=[{'label': 'All Industries', 'value': ''}] + get_industries(),
                        value='',
                        placeholder="Select an industry"
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
                    html.I(className="fas fa-gavel me-2"),
                    "Legal Actions Dashboard"
                ], className="display-6"),
                html.P("Monitor and analyze legal actions across companies and industries", 
                      className="text-muted")
            ], className="mb-4"),
            
            # Time Series Chart
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-chart-line me-2"),
                        "Legal Actions Over Time"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dcc.Graph(id="time-series-chart")
                ])
            ], className="mb-4"),
            
            # Data Table
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        html.H5([
                            html.I(className="fas fa-table me-2"),
                            "Legal Actions Data"
                        ], className="mb-0"),
                        dbc.Badge(id="record-count", color="secondary")
                    ], className="d-flex justify-content-between align-items-center")
                ]),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='legal-actions-table',
                        columns=[
                            {'name': 'Title', 'id': 'Title', 'type': 'text'},
                            {'name': 'Company', 'id': 'Company', 'type': 'text'},
                            {'name': 'Industry', 'id': 'Industry', 'type': 'text'},
                            {'name': 'Action Date', 'id': 'Action Date', 'type': 'datetime'},
                            {'name': 'Status', 'id': 'Status', 'type': 'text'},
                            {'name': 'Description', 'id': 'Description', 'type': 'text'}
                        ],
                        data=[],
                        sort_action="native",
                        filter_action="native",
                        page_action="native",
                        page_current=0,
                        page_size=20,
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
                                'if': {'column_id': 'Description'},
                                'width': '30%',
                                'whiteSpace': 'normal',
                                'height': 'auto',
                            },
                            {
                                'if': {'column_id': 'Title'},
                                'width': '25%',
                                'whiteSpace': 'normal',
                                'height': 'auto',
                            }
                        ]
                    )
                ])
            ])
        ], width=9, className="ms-auto")
    ])
], fluid=True)

# Callbacks
@app.callback(
    [Output('legal-actions-table', 'data'),
     Output('time-series-chart', 'figure'),
     Output('record-count', 'children'),
     Output('filter-status', 'children')],
    [Input('company-filter', 'value'),
     Input('industry-filter', 'value')]
)
def update_dashboard(company_id, industry_id):
    # Get filtered data
    df = get_legal_actions(company_id, industry_id)
    time_series_df = get_time_series_data(company_id, industry_id)
    
    # Update table data
    table_data = df.to_dict('records') if not df.empty else []
    
    # Update time series chart
    if not time_series_df.empty:
        fig = px.line(time_series_df, x='Month', y='Count', 
                     title='Legal Actions Over Time',
                     markers=True)
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Number of Legal Actions",
            hovermode='x unified'
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
            yaxis=dict(visible=False),
            annotations=[dict(text="No data available", x=0.5, y=0.5)]
        )
    
    # Update record count
    record_count = f"{len(df)} records"
    
    # Update filter status
    filters = []
    if company_id:
        company_options = get_companies()
        company_name = next((opt['label'] for opt in company_options if opt['value'] == company_id), '')
        if company_name:
            filters.append(f"Company: {company_name}")
    
    if industry_id:
        industry_options = get_industries()
        industry_name = next((opt['label'] for opt in industry_options if opt['value'] == industry_id), '')
        if industry_name:
            filters.append(f"Industry: {industry_name}")
    
    if filters:
        filter_status = f"Filters: {', '.join(filters)}"
    else:
        filter_status = "No filters applied"
    
    return table_data, fig, record_count, filter_status

@app.callback(
    [Output('company-filter', 'value'),
     Output('industry-filter', 'value')],
    [Input('clear-filters', 'n_clicks')]
)
def clear_filters(n_clicks):
    if n_clicks:
        return '', ''
    return dash.no_update, dash.no_update

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=5000, debug=True)