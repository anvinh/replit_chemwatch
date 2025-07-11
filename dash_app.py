# Refactored scatter plot data processing and updated plot to display individual articles stacked vertically.
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

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load data from CSV files
articles_df = pd.read_csv('attached_assets/temp_article_df_1751374177682.csv')
companies_df = pd.read_csv('attached_assets/temp_company_level_df_1751374177683.csv')

# Parse date columns
articles_df['published_at'] = pd.to_datetime(articles_df['published_at'], errors='coerce')
articles_df['modified_at'] = pd.to_datetime(articles_df['modified_at'], errors='coerce')

# Create Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

def get_articles(company_filter=None, industry_filter=None):
    """Get filtered articles from CSV data"""
    try:
        df = articles_df.copy()

        if company_filter:
            # Find companies that match the filter and get their associated articles by pk
            company_pks = companies_df[
                companies_df['company_name'].str.contains(company_filter, case=False, na=False)
            ]['pk'].tolist()

            if company_pks:
                df = df[df['pk'].isin(company_pks)]
            else:
                return pd.DataFrame()  # No matching companies found

        if industry_filter:
            df = df[df['isic_name'] == industry_filter]

        # Sort by published date descending
        df = df.sort_values('published_at', ascending=False, na_position='last')

        # Format data for display
        data = []
        for _, article in df.iterrows():
            data.append({
                'PK': str(article['pk']),
                'Article ID': str(article['article_id']) if pd.notna(article['article_id']) else '',
                'Title': str(article['title']) if pd.notna(article['title']) else '',
                'URL': str(article['url']) if pd.notna(article['url']) else '',
                'Published Date': article['published_at'].strftime('%Y-%m-%d %H:%M') if pd.notna(article['published_at']) else '',
                'Country': str(article['country_code']) if pd.notna(article['country_code']) else '',
                'Industry': str(article['isic_name']) if pd.notna(article['isic_name']) else '',
                'Search Term': str(article['search_term']) if pd.notna(article['search_term']) else ''
            })

        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Error fetching articles: {str(e)}")
        return pd.DataFrame()

def get_companies(article_filter=None):
    """Get filtered companies from CSV data"""
    try:
        df = companies_df.copy()

        if article_filter:
            # Filter companies based on article pk
            df = df[df['pk'] == article_filter]

        # Sort by company name
        df = df.sort_values('company_name', na_position='last')

        # Format data for display
        data = []
        for _, company in df.iterrows():
            settlement_amount = ''
            if pd.notna(company['settlement_amount']):
                currency = str(company['settlement_currency']) if pd.notna(company['settlement_currency']) else ''
                settlement_amount = f"{currency} {company['settlement_amount']:,.0f}".strip()

            data.append({
                'PK': str(company['pk']),
                'Company Name': str(company['company_name']) if pd.notna(company['company_name']) else '',
                'Litigation Reason': str(company['litigation_reason']) if pd.notna(company['litigation_reason']) else '',
                'Claim Category': str(company['claim_category']) if pd.notna(company['claim_category']) else '',
                'Source of PFAS': str(company['source_of_pfas']) if pd.notna(company['source_of_pfas']) else '',
                'Settlement Finalized': 'Yes' if company['settlement_finalized'] else 'No',
                'Settlement Amount': settlement_amount,
                'Settlement Date': str(company['settlement_paid_date']) if pd.notna(company['settlement_paid_date']) else ''
            })

        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Error fetching companies: {str(e)}")
        return pd.DataFrame()

def get_scatter_plot_data(company_filter=None, industry_filter=None, article_filter=None, aggregation_type="weekly"):
    """Get data for scatter plot showing articles published per week or month"""
    try:
        df = articles_df.copy()

        if company_filter:
            company_pks = companies_df[
                companies_df['company_name'].str.contains(company_filter, case=False, na=False)
            ]['pk'].tolist()

            if company_pks:
                df = df[df['pk'].isin(company_pks)]
            else:
                return pd.DataFrame()

        if industry_filter:
            df = df[df['isic_name'] == industry_filter]

        if article_filter:
            df = df[df['pk'] == article_filter]

        # Filter out rows with null published_at
        df = df[pd.notna(df['published_at'])]

        data = []
        for _, article in df.iterrows():
            if aggregation_type == "weekly":
                # Get the start of the week (Monday)
                period_start = article['published_at'] - pd.Timedelta(days=article['published_at'].weekday())
                period_key = period_start.strftime('%Y-%m-%d')
            else:  # monthly
                # Get the start of the month
                period_start = article['published_at'].replace(day=1)
                period_key = period_start.strftime('%Y-%m-%d')

            data.append({
                'period': period_key,
                'title': str(article['title']) if pd.notna(article['title']) else '',
                'published_date': article['published_at'],
                'pk': str(article['pk'])
            })

        plot_df = pd.DataFrame(data)
        if not plot_df.empty:
            # Group by period and add vertical positioning for dots (starting from 0)
            plot_df_grouped = plot_df.groupby('period').apply(lambda x: x.sort_values('published_date').assign(
                y_position=range(len(x))
            ), include_groups=False).reset_index()
            return plot_df_grouped

        return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error fetching scatter plot data: {str(e)}")
        return pd.DataFrame()

def get_company_options():
    """Get options for company dropdown"""
    company_names = companies_df['company_name'].unique()
    options = [{'label': company, 'value': company} for company in company_names]
    return options

def get_industry_options():
    """Get options for industry dropdown"""
    industry_names = articles_df['isic_name'].unique()
    options = [{'label': industry, 'value': industry} for industry in industry_names]
    return options

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
                    dcc.Dropdown(
                        id='company-filter',
                        placeholder="Select company...",
                        style={
                            'border': '1',
                            'padding': '0',
                            'outline': 'none'
                        }
                    )
                ], className="mb-4"),

                # Industry Filter
                html.Div([
                    dbc.Label([
                        html.I(className="fas fa-industry me-1"),
                        "Industry Filter"
                    ]),
                    dcc.Dropdown(
                        id='industry-filter',
                        placeholder="Select industry...",
                        style={
                            'border': '1',
                            'padding': '0',
                            'outline': 'none'
                        }
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
                        "Articles Published by Time Period"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dcc.Graph(id="scatter-plot-chart"),
                    html.Div([
                        dbc.ButtonGroup([
                            dbc.Button("Weekly", id="weekly-btn", color="primary", className="me-2"),
                            dbc.Button("Monthly", id="monthly-btn", color="outline-primary")
                        ], className="d-flex justify-content-center mt-3")
                    ])
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
    html.Div(id="selected-company-pk", style={'display': 'none'}),
    # Hidden div to store aggregation type
    html.Div(id="aggregation-type", children="monthly", style={'display': 'none'})
], fluid=True)

# Define a decorator for logging callback trigger
def log_callback_trigger(func):
    def wrapper(*args, **kwargs):
        ctx = callback_context
        if ctx.triggered:
            logging.debug(f"Callback triggered by: {ctx.triggered[0]['prop_id']}")
        else:
            logging.debug("Callback triggered without explicit input")
        return func(*args, **kwargs)
    return wrapper

# Callback for aggregation buttons
@app.callback(
    [Output('aggregation-type', 'children'),
     Output('weekly-btn', 'color'),
     Output('monthly-btn', 'color')],
    [Input('weekly-btn', 'n_clicks'),
     Input('monthly-btn', 'n_clicks')],
    prevent_initial_call=False
)
def update_aggregation_type(weekly_clicks, monthly_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return "monthly", "outline-primary", "primary"

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'weekly-btn':
        return "weekly", "primary", "outline-primary"
    elif button_id == 'monthly-btn':
        return "monthly", "outline-primary", "primary"

    return "monthly", "outline-primary", "primary"

# Main dashboard callback
@app.callback(
    [Output('articles-table', 'data'),
     Output('companies-table', 'data'),
     Output('scatter-plot-chart', 'figure'),
     Output('article-count', 'children'),
     Output('company-count', 'children'),
     Output('filter-status', 'children'),
     Output('selected-article-pk', 'children'),
     Output('selected-company-pk', 'children'),
     Output('company-filter', 'options'),
     Output('industry-filter', 'options')],

    [Input('company-filter', 'value'),
     Input('industry-filter', 'value'),
     Input('articles-table', 'selected_rows'),
     Input('companies-table', 'selected_rows'),
     Input('clear-filters', 'n_clicks'),
     Input('aggregation-type', 'children')],
    prevent_initial_call=False
)
@log_callback_trigger
def update_dashboard(company_filter, industry_filter, selected_article_rows, selected_company_rows, clear_clicks, aggregation_type):
    ctx = callback_context

    # Handle clear filters: when only the button "clear filters" is clicked
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'clear-filters.n_clicks' and clear_clicks:
        company_filter = None
        industry_filter = None
        selected_article_rows = []
        selected_company_rows = []

    # Get dropdown options
    company_options = get_company_options()
    industry_options = get_industry_options()

    # Get selected article PK
    selected_article_pk = None
    if selected_article_rows:
        articles_data = get_articles(company_filter, industry_filter)
        if not articles_data.empty and selected_article_rows[0] < len(articles_data):
            selected_article_pk = articles_data.iloc[selected_article_rows[0]]['PK']

    # Get selected company PK  
    selected_company_pk = None
    if selected_company_rows:
        companies_data = get_companies(selected_article_pk)
        if not companies_data.empty and selected_company_rows[0] < len(companies_data):
            selected_company_pk = companies_data.iloc[selected_company_rows[0]]['Company Name']

    # Get filtered data
    articles_data = get_articles(selected_company_pk if selected_company_pk else company_filter, industry_filter)
    companies_data = get_companies(selected_article_pk)
    scatter_data = get_scatter_plot_data(selected_company_pk if selected_company_pk else company_filter, industry_filter, selected_article_pk, aggregation_type)

    # Update articles table
    articles_records = articles_data.to_dict('records') if not articles_data.empty else []

    # Update companies table
    companies_records = companies_data.to_dict('records') if not companies_data.empty else []

    # Update scatter plot
    if not scatter_data.empty:
        period_label = "Week" if aggregation_type == "weekly" else "Month"
        fig = px.scatter(
            scatter_data, 
            x='period', 
            y='y_position',
            hover_data=['title', 'published_date'],
            title=f'Articles Published by {period_label} (Each dot represents one article)'
        )
        fig.update_traces(
            marker=dict(size=8, opacity=0.7),
            hovertemplate=f'<b>%{{customdata[0]}}</b><br>Published: %{{customdata[1]}}<br>{period_label}: %{{x}}<extra></extra>'
        )
        fig.update_layout(
            xaxis_title=f"{period_label} Starting",
            yaxis_title=f"Articles in {period_label}",
            yaxis=dict(tickmode='linear', dtick=1),
            hovermode='closest',
            xaxis=dict(
                rangeslider=dict(
                    visible=True,
                    thickness=0.1
                ),
                type="date"
            )
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
    article_count = f"{len(articles_data)} articles"
    company_count = f"{len(companies_data)} companies"

    # Update filter status
    filters = []
    if company_filter:
        filters.append(f"Company: {company_filter}")
    if industry_filter:
        filters.append(f"Industry: {industry_filter}")
    if selected_article_pk:
        filters.append(f"Article selected")
    if selected_company_pk:
        filters.append(f"Company: {selected_company_pk}")

    if filters:
        filter_status = f"Active filters: {', '.join(filters)}"
    else:
        filter_status = "No filters applied"

    return (articles_records, companies_records, fig, article_count, company_count, 
            filter_status, selected_article_pk or '', selected_company_pk or '',
            company_options, industry_options)

@app.callback(
    [Output('company-filter', 'value'),
     Output('industry-filter', 'value')],
    [Input('clear-filters', 'n_clicks')]
)
@log_callback_trigger
def clear_filters(n_clicks):
    ctx = callback_context
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'clear-filters.n_clicks' and n_clicks:
        return [None, None]
    return [dash.no_update, dash.no_update]

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=5000, debug=True)