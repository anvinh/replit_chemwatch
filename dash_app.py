# Refactored scatter plot data processing and updated plot to display individual articles stacked vertically with dynamic range slider configuration.
import logging
import os
from datetime import datetime
import hashlib

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, callback_context, dash_table, dcc, html, State
from dash.exceptions import PreventUpdate

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Simple session storage (in production, use proper session management)
user_sessions = {}

# Load data from CSV files
articles_df = pd.read_csv("attached_assets/temp_chemwatch_all_articles_dev.csv")
companies_df = pd.read_csv("attached_assets/temp_chemwatch_all_companies_dev.csv")

# Parse date columns
articles_df["published_at"] = pd.to_datetime(articles_df["published_at"], errors="coerce")
articles_df["modified_at"] = pd.to_datetime(articles_df["modified_at"], errors="coerce")

# Create Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Authentication functions
def load_users():
    """Load users from CSV file"""
    try:
        return pd.read_csv("attached_assets/users.csv")
    except FileNotFoundError:
        # Create default users file if it doesn't exist
        default_users = pd.DataFrame({
            'username': ['admin', 'demo'],
            'password': ['admin123', 'demo123'],
            'name': ['Admin User', 'Demo User'],
            'email': ['admin@company.com', 'demo@company.com'],
            'is_approved': [True, True]
        })
        default_users.to_csv("attached_assets/users.csv", index=False)
        return default_users

def authenticate_user(username, password):
    """Authenticate user with username and password"""
    users_df = load_users()
    user = users_df[(users_df['username'] == username) & (users_df['password'] == password)]
    if not user.empty and user.iloc[0]['is_approved']:
        return user.iloc[0].to_dict()
    return None

def is_authenticated(session_id):
    """Check if session is authenticated"""
    return session_id in user_sessions

def create_session(user_data):
    """Create a new session for authenticated user"""
    session_id = hashlib.md5(f"{user_data['username']}{datetime.now()}".encode()).hexdigest()
    user_sessions[session_id] = user_data
    return session_id

def get_user_from_session(session_id):
    """Get user data from session"""
    return user_sessions.get(session_id)

def create_login_layout():
    """Create login page layout"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H2("ChemWatch Login", className="text-center mb-4"),
                        dbc.Input(
                            id="username-input",
                            placeholder="Username",
                            type="text",
                            className="mb-3"
                        ),
                        dbc.Input(
                            id="password-input",
                            placeholder="Password",
                            type="password",
                            className="mb-3"
                        ),
                        dbc.Button(
                            "Login",
                            id="login-button",
                            color="primary",
                            className="w-100 mb-3"
                        ),
                        dbc.Alert(
                            id="login-alert",
                            is_open=False,
                            duration=4000,
                            color="danger"
                        ),
                        html.Div([
                            html.P("Demo credentials:", className="mt-3 mb-1"),
                            html.Small("Username: admin, Password: admin123", className="text-muted d-block"),
                            html.Small("Username: demo, Password: demo123", className="text-muted")
                        ])
                    ])
                ], style={"max-width": "400px"})
            ], width=12, className="d-flex justify-content-center align-items-center", style={"min-height": "100vh"})
        ])
    ], fluid=True)

def create_dashboard_layout():
    """Create main dashboard layout"""


def get_articles(company_filter=None, industry_filter=None):
    """Get filtered articles from CSV data"""
    try:
        df = articles_df.copy()

        if company_filter:
            # Find companies that match the filter and get their associated articles by pk
            company_pks = companies_df[
                companies_df["company_name"].str.contains(company_filter, case=False, na=False)
            ]["primary_key"].tolist()

            if company_pks:
                df = df[df["primary_key"].isin(company_pks)]
            else:
                return pd.DataFrame()  # No matching companies found

        if industry_filter:
            df = df[df["isic_name"] == industry_filter]

        # Sort by published date descending
        df = df.sort_values("published_at", ascending=False, na_position="last")

        # Format data for display
        data = []
        for _, article in df.iterrows():
            data.append(
                {
                    "PK": str(article["primary_key"]),
                    "Article ID": (
                        str(article["article_id"]) if pd.notna(article["article_id"]) else ""
                    ),
                    "Title": str(article["title"]) if pd.notna(article["title"]) else "",
                    "URL": str(article["url"]) if pd.notna(article["url"]) else "",
                    "Published Date": (
                        article["published_at"].strftime("%Y-%m-%d %H:%M")
                        if pd.notna(article["published_at"])
                        else ""
                    ),
                    "Country": (
                        str(article["country_code"]) if pd.notna(article["country_code"]) else ""
                    ),
                    "Industry": str(article["isic_name"]) if pd.notna(article["isic_name"]) else "",
                    "Search Term": (
                        str(article["search_term"]) if pd.notna(article["search_term"]) else ""
                    ),
                },
            )

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
            df = df[df["primary_key"] == article_filter]

        # Sort by company name
        df = df.sort_values("company_name", na_position="last")

        # Format data for display
        data = []
        for _, company in df.iterrows():
            settlement_amount = ""
            if pd.notna(company["settlement_amount"]):
                currency = (
                    str(company["settlement_currency"])
                    if pd.notna(company["settlement_currency"])
                    else ""
                )
                amount_str = str(company["settlement_amount"])

                # Handle range values (e.g., "10500000000.00 to 12500000000.00")
                if " to " in amount_str:
                    settlement_amount = f"{currency} {amount_str}".strip()
                else:
                    try:
                        amount = float(amount_str)
                        settlement_amount = f"{currency} {amount:,.0f}".strip()
                    except ValueError:
                        settlement_amount = f"{currency} {amount_str}".strip()

            data.append(
                {
                    "PK": str(company["primary_key"]),
                    "Company Name": (
                        str(company["company_name"]) if pd.notna(company["company_name"]) else ""
                    ),
                    "Litigation Reason": (
                        str(company["litigation_reason"])
                        if pd.notna(company["litigation_reason"])
                        else ""
                    ),
                    "Claim Category": (
                        str(company["claim_category"])
                        if pd.notna(company["claim_category"])
                        else ""
                    ),
                    "Source of PFAS": (
                        str(company["source_of_pfas"])
                        if pd.notna(company["source_of_pfas"])
                        else ""
                    ),
                    "Settlement Finalized": "Yes" if company["settlement_finalized"] else "No",
                    "Settlement Amount": settlement_amount,
                    "Settlement Date": (
                        str(company["settlement_paid_date"])
                        if pd.notna(company["settlement_paid_date"])
                        else ""
                    ),
                },
            )

        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Error fetching companies: {str(e)}")
        return pd.DataFrame()


def get_scatter_plot_data(
    company_filter=None,
    industry_filter=None,
    article_filter=None,
    aggregation_type="weekly",
):
    """Get data for scatter plot showing articles published per week or month"""
    try:
        art_df = articles_df.copy()
        com_df = companies_df.copy()

        if company_filter:
            company_pks = companies_df[companies_df["company_name"] == company_filter][
                "primary_key"
            ].tolist()

            if company_pks:
                art_df = art_df[art_df["primary_key"].isin(company_pks)]
            else:
                return pd.DataFrame()

        if industry_filter:
            art_df = art_df[art_df["isic_name"] == industry_filter]

        if article_filter:
            art_df = art_df[art_df["primary_key"] == article_filter]

        # Filter out rows with null published_at
        art_df = art_df[pd.notna(art_df["published_at"])]

        fill_values = {
            "company_name": "-",
            "litigation_reason": "-",
            "claim_category": "-",
            "source_of_pfas": "-",
            "settlement_finalized": False,
            "settlement_amount": 0,
            "settlement_paid_date": "-",
        }

        grouped_com_df = (
            com_df.fillna(value=fill_values)
            .groupby("primary_key")
            .agg(
                {
                    "company_name": lambda x: ", ".join(sorted(set(x))),
                    "litigation_reason": lambda x: ", ".join(sorted(set(x))),
                    "claim_category": lambda x: ", ".join(sorted(set(x))),
                    "source_of_pfas": lambda x: ", ".join(sorted(set(x))),
                    "settlement_finalized": "any",
                    "settlement_amount": "sum",
                    "settlement_paid_date": lambda x: ", ".join(sorted(set(x))),
                },
            )
        )

        # Join with companies data to get liability information
        df = art_df.merge(grouped_com_df, on="primary_key", how="left")

        data = []
        for _, article in df.iterrows():
            if aggregation_type == "weekly":
                # Get the start of the week (Monday)
                period_start = article["published_at"] - pd.Timedelta(
                    days=article["published_at"].weekday(),
                )
                iso_year, iso_week, _ = period_start.isocalendar()
                period_key = period_start.strftime("%Y-%m-%d")
                period_name = f"{iso_year}-{iso_week:02d}"
            elif aggregation_type == "quarterly":
                # Get the start of the quarter
                quarter = (article["published_at"].month - 1) // 3 + 1
                period_start = pd.Timestamp(
                    year=article["published_at"].year,
                    month=(quarter - 1) * 3 + 1,
                    day=1,
                )
                iso_year = period_start.year
                period_key = period_start.strftime("%Y-%m")
                period_name = f"{iso_year}-Q{quarter}"
            else:  # monthly
                # Get the start of the month
                period_start = article["published_at"].replace(day=1)
                iso_year = period_start.year
                period_key = period_start.strftime("%Y-%m")
                period_name = f"{iso_year}-{period_start.strftime('%b')}"  # Jan, Feb

            data.append(
                {
                    "period": period_key,
                    "title": str(article["title"]) if pd.notna(article["title"]) else "",
                    "published_at": article["published_at"],
                    "primary_key": str(article["primary_key"]),
                    "url": article["url"],
                    "published_on": article["published_at"].strftime("%Y-%m-%d"),
                    "country": article[
                        "country_code"
                    ],  # TODO: return country name from country code
                    "industry_isic": article["isic_name"],
                    "period_name": period_name,
                    "company_name": article["company_name"],
                    "litigation_reason": article["litigation_reason"],
                    "claim_category": article["claim_category"],
                    "source_of_pfas": article["source_of_pfas"],
                    "settlement_finalized": article["settlement_finalized"],
                    "settlement_amount": article["settlement_amount"],
                    "settlement_paid_date": article["settlement_paid_date"],
                },
            )

        plot_df = pd.DataFrame(data)
        if not plot_df.empty:
            # Group by period and add vertical positioning for dots (starting from 1)
            plot_df_grouped = (
                plot_df.groupby("period")
                .apply(
                    lambda x: x.sort_values("published_at").assign(y_position=range(1, len(x) + 1)),
                    include_groups=False,
                )
                .reset_index()
            )
            return plot_df_grouped

        return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error fetching scatter plot data: {str(e)}")
        return pd.DataFrame()


def get_company_options():
    """Get options for company dropdown"""
    company_names = companies_df["company_name"].unique()
    company_names = sorted(company_names)
    options = [{"label": company, "value": company} for company in company_names]
    return options


def get_industry_options():
    """Get options for industry dropdown"""
    industry_names = articles_df["isic_name"].unique()
    industry_names = sorted(industry_names)
    options = [{"label": industry, "value": industry} for industry in industry_names]
    return options


return dbc.Container(
    [
        dbc.Row(
            [
                # Sidebar
                dbc.Col(
                    [
                        html.Div(
                            [
                                # Header
                                html.Div(
                                    [
                                        html.H1("ChemWatch", className="display-6"),
                                        html.P(
                                            "a HERCULES spin-off",
                                            className="text-muted",
                                        ),
                                    ],
                                    className="mb-4",
                                    style={"borderBottom": "1px solid #dee2e6"},
                                ),
                                html.H4(
                                    [html.I(className="fas fa-filter me-2"), "Filters"],
                                    className="mb-4",
                                ),
                                # Date Filters Section
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                dbc.Label(
                                                    [
                                                        html.I(className="fas fa-calendar me-1"),
                                                        "Start Date",
                                                    ],
                                                ),
                                                dcc.DatePickerSingle(
                                                    id="start-date-filter",
                                                    date=(
                                                        datetime.now() - pd.DateOffset(years=2)
                                                    ).date(),
                                                    display_format="YYYY-MM-DD",
                                                    style={
                                                        "width": "100%",
                                                        "height": "38px",
                                                        "borderRadius": "0.375rem",
                                                        "border": "1px solid #ced4da",
                                                        "fontSize": "1rem",
                                                        "padding": "0.375rem 0.75rem",
                                                    },
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        html.Div(
                                            [
                                                dbc.Label(
                                                    [
                                                        html.I(className="fas fa-calendar me-1"),
                                                        "End Date",
                                                    ],
                                                ),
                                                dcc.DatePickerSingle(
                                                    id="end-date-filter",
                                                    date=datetime.now().date(),
                                                    display_format="YYYY-MM-DD",
                                                    style={
                                                        "width": "100%",
                                                        "height": "38px",
                                                        "borderRadius": "0.375rem",
                                                        "border": "1px solid #ced4da",
                                                        "fontSize": "1rem",
                                                        "padding": "0.375rem 0.75rem",
                                                    },
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                    ],
                                    className="mb-4 pb-3",
                                    style={"borderBottom": "1px solid #dee2e6"},
                                ),
                                # Company Filter
                                html.Div(
                                    [
                                        dbc.Label("Company Filter"),
                                        dcc.Dropdown(
                                            id="company-filter",
                                            placeholder="Select company...",
                                            style={
                                                "border": "1",
                                                "padding": "0",
                                                "outline": "none",
                                            },
                                        ),
                                    ],
                                    className="mb-4",
                                ),
                                # Industry Filter
                                html.Div(
                                    [
                                        dbc.Label("Industry Filter"),
                                        dcc.Dropdown(
                                            id="industry-filter",
                                            placeholder="Select industry...",
                                            style={
                                                "border": "1",
                                                "padding": "0",
                                                "outline": "none",
                                            },
                                        ),
                                    ],
                                    className="mb-4",
                                ),
                                # Clear Filters Button
                                dbc.Button(
                                    "Clear Filters",
                                    id="clear-filters",
                                    color="outline-secondary",
                                    className="w-100 mb-3",
                                ),
                                # Filter Status
                                html.Div(id="filter-status", className="text-muted small"),
                            ],
                            className="p-3 bg-light",
                        ),
                    ],
                    width=3,
                    className="vh-100 position-fixed",
                ),
                # Main Content
                dbc.Col(
                    [
                        # Header
                        html.H1("PFAS Articles & Companies Dashboard", className="display-6"),
                        html.P(
                            "Monitor and analyze PFAS-related articles and company involvement",
                            className="text-muted",
                        ),
                        # Scatter Plot Chart
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(className="fas fa-chart-scatter me-2"),
                                                "Articles Published by Time Period",
                                            ],
                                            className="mb-0",
                                        ),
                                    ],
                                ),
                                dbc.CardBody(
                                    [
                                        dcc.Graph(id="scatter-plot-chart"),
                                        html.Div(
                                            [
                                                dbc.ButtonGroup(
                                                    [
                                                        dbc.Button(
                                                            "Weekly",
                                                            id="weekly-btn",
                                                            color="outline-primary",
                                                            className="me-2",
                                                        ),
                                                        dbc.Button(
                                                            "Monthly",
                                                            id="monthly-btn",
                                                            color="primary",
                                                            className="me-2",
                                                        ),
                                                        dbc.Button(
                                                            "Quarterly",
                                                            id="quarterly-btn",
                                                            color="outline-primary",
                                                        ),
                                                    ],
                                                    className="d-flex justify-content-center mt-3",
                                                ),
                                            ],
                                        ),
                                        # Article info box
                                        html.Div(id="article-info-box", className="mt-3"),
                                    ],
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Articles Table
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.Div(
                                            [
                                                html.H5(
                                                    [
                                                        html.I(className="fas fa-newspaper me-2"),
                                                        "Articles",
                                                    ],
                                                    className="mb-0",
                                                ),
                                                dbc.Badge(id="article-count", color="primary"),
                                            ],
                                            className="d-flex justify-content-between align-items-center",
                                        ),
                                    ],
                                ),
                                dbc.CardBody(
                                    [
                                        dash_table.DataTable(
                                            id="articles-table",
                                            columns=[
                                                {
                                                    "name": "Title",
                                                    "id": "Title",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Published Date",
                                                    "id": "Published Date",
                                                    "type": "datetime",
                                                },
                                                {
                                                    "name": "Country",
                                                    "id": "Country",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Industry",
                                                    "id": "Industry",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Search Term",
                                                    "id": "Search Term",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "PK",
                                                    "id": "PK",
                                                    "type": "text",
                                                },
                                            ],
                                            data=[],
                                            sort_action="native",
                                            filter_action="native",
                                            filter_options={"case": "insensitive"},
                                            page_action="native",
                                            page_current=0,
                                            page_size=10,
                                            row_selectable="single",
                                            selected_rows=[],
                                            style_cell={
                                                "textAlign": "left",
                                                "padding": "10px",
                                                "fontFamily": "Arial",
                                                "cursor": "pointer",  # Make rows appear clickable
                                            },
                                            style_header={
                                                "backgroundColor": "rgb(230, 230, 230)",
                                                "fontWeight": "bold",
                                            },
                                            style_data_conditional=[
                                                {
                                                    "if": {"row_index": "odd"},
                                                    "backgroundColor": "rgb(248, 248, 248)",
                                                },
                                                {
                                                    "if": {"state": "selected"},
                                                    "backgroundColor": "rgba(0, 116, 217, 0.3)",
                                                    "border": "1px solid rgb(0, 116, 217)",
                                                },
                                            ],
                                            style_cell_conditional=[
                                                {
                                                    "if": {"column_id": "Title"},
                                                    "width": "30%",
                                                    "whiteSpace": "normal",
                                                    "height": "auto",
                                                },
                                                {
                                                    "if": {"column_id": "PK"},
                                                    "width": "0%",
                                                    "display": "none",
                                                },
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Companies Table
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.Div(
                                            [
                                                html.H5(
                                                    [
                                                        html.I(className="fas fa-building me-2"),
                                                        "Related Companies",
                                                    ],
                                                    className="mb-0",
                                                ),
                                                dbc.Badge(
                                                    id="company-count",
                                                    color="secondary",
                                                ),
                                            ],
                                            className="d-flex justify-content-between align-items-center",
                                        ),
                                    ],
                                ),
                                dbc.CardBody(
                                    [
                                        dash_table.DataTable(
                                            id="companies-table",
                                            columns=[
                                                {
                                                    "name": "Company Name",
                                                    "id": "Company Name",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Litigation Reason",
                                                    "id": "Litigation Reason",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Claim Category",
                                                    "id": "Claim Category",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Source of PFAS",
                                                    "id": "Source of PFAS",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Settlement Finalized",
                                                    "id": "Settlement Finalized",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Settlement Amount",
                                                    "id": "Settlement Amount",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "PK",
                                                    "id": "PK",
                                                    "type": "text",
                                                },
                                            ],
                                            data=[],
                                            sort_action="native",
                                            filter_action="native",
                                            filter_options={"case": "insensitive"},
                                            page_action="native",
                                            page_current=0,
                                            page_size=10,
                                            row_selectable="single",
                                            selected_rows=[],
                                            style_cell={
                                                "textAlign": "left",
                                                "padding": "10px",
                                                "fontFamily": "Arial",
                                                "cursor": "pointer",  # Make rows appear clickable
                                            },
                                            style_header={
                                                "backgroundColor": "rgb(230, 230, 230)",
                                                "fontWeight": "bold",
                                            },
                                            style_data_conditional=[
                                                {
                                                    "if": {"row_index": "odd"},
                                                    "backgroundColor": "rgb(248, 248, 248)",
                                                },
                                                {
                                                    "if": {"state": "selected"},
                                                    "backgroundColor": "rgba(0, 116, 217, 0.3)",
                                                    "border": "1px solid rgb(0, 116, 217)",
                                                },
                                            ],
                                            style_cell_conditional=[
                                                {
                                                    "if": {"column_id": "Company Name"},
                                                    "width": "20%",
                                                },
                                                {
                                                    "if": {"column_id": "PK"},
                                                    "width": "0%",
                                                    "display": "none",
                                                },
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                    width=9,
                    className="ms-auto",
                ),
            ],
        ),
        # Hidden div to store selected article PK
        html.Div(id="selected-article-pk", style={"display": "none"}),
        html.Div(id="selected-company-pk", style={"display": "none"}),
        # Hidden div to store aggregation type
        html.Div(id="aggregation-type", children="monthly", style={"display": "none"}),
        # Logout button
        html.Div([
            dbc.Button("Logout", id="logout-button", color="secondary", size="sm", className="position-fixed", 
                      style={"top": "10px", "right": "10px", "z-index": "1000"})
        ])
    ],
    fluid=True,
)

# App layout with authentication
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="session-store", storage_type="session"),
    html.Div(id="page-content")
])


# Authentication callbacks
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    State("session-store", "data")
)
def display_page(pathname, session_data):
    """Display login or dashboard based on authentication"""
    if session_data and is_authenticated(session_data.get("session_id")):
        return create_dashboard_layout()
    else:
        return create_login_layout()

@app.callback(
    [Output("session-store", "data"),
     Output("login-alert", "children"),
     Output("login-alert", "is_open"),
     Output("url", "pathname", allow_duplicate=True)],
    Input("login-button", "n_clicks"),
    [State("username-input", "value"),
     State("password-input", "value")],
    prevent_initial_call=True
)
def handle_login(n_clicks, username, password):
    """Handle login authentication"""
    if not n_clicks:
        raise PreventUpdate
    
    if not username or not password:
        return None, "Please enter both username and password", True, "/"
    
    user_data = authenticate_user(username, password)
    if user_data:
        session_id = create_session(user_data)
        return {"session_id": session_id, "user": user_data}, "", False, "/"
    else:
        return None, "Invalid username or password", True, "/"

@app.callback(
    [Output("session-store", "data", allow_duplicate=True),
     Output("url", "pathname", allow_duplicate=True)],
    Input("logout-button", "n_clicks"),
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    """Handle logout"""
    if not n_clicks:
        raise PreventUpdate
    return None, "/"

# Define a decorator for logging callback trigger
def log_callback_trigger(func):
    def wrapper(*args, **kwargs):
        ctx = callback_context
        if ctx.triggered:
            logging.debug(f"Callback triggered by: {ctx.triggered[0]['prop_id']}")
            logging.debug(f"Value                : {ctx.triggered}")
        else:
            logging.debug("Callback triggered without explicit input")
        return func(*args, **kwargs)

    return wrapper


# Callback for aggregation buttons
@app.callback(
    [
        Output("aggregation-type", "children"),
        Output("weekly-btn", "color"),
        Output("monthly-btn", "color"),
        Output("quarterly-btn", "color"),
    ],
    [
        Input("weekly-btn", "n_clicks"),
        Input("monthly-btn", "n_clicks"),
        Input("quarterly-btn", "n_clicks"),
    ],
    prevent_initial_call=False,
)
def update_aggregation_type(weekly_clicks, monthly_clicks, quarterly_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return "monthly", "outline-primary", "primary", "outline-primary"

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "weekly-btn":
        return "weekly", "primary", "outline-primary", "outline-primary"
    elif button_id == "monthly-btn":
        return "monthly", "outline-primary", "primary", "outline-primary"
    elif button_id == "quarterly-btn":
        return "quarterly", "outline-primary", "outline-primary", "primary"

    return "monthly", "outline-primary", "primary", "outline-primary"


# Main dashboard callback
@app.callback(
    [
        Output("articles-table", "data"),
        Output("companies-table", "data"),
        Output("scatter-plot-chart", "figure"),
        Output("article-count", "children"),
        Output("company-count", "children"),
        Output("filter-status", "children"),
        Output("selected-article-pk", "children"),
        Output("selected-company-pk", "children"),
        Output("company-filter", "options"),
        Output("industry-filter", "options"),
    ],
    [
        Input("company-filter", "value"),
        Input("industry-filter", "value"),
        Input("articles-table", "selected_rows"),
        Input("companies-table", "selected_rows"),
        Input("clear-filters", "n_clicks"),
        Input("aggregation-type", "children"),
        Input("start-date-filter", "date"),
        Input("end-date-filter", "date"),
    ],
    [State("session-store", "data")],
    prevent_initial_call=False,
)
@log_callback_trigger
def update_dashboard(
    company_filter,
    industry_filter,
    selected_article_rows,
    selected_company_rows,
    clear_clicks,
    aggregation_type,
    start_date,
    end_date,
    session_data,
):
    # Check authentication
    if not session_data or not is_authenticated(session_data.get("session_id")):
        raise PreventUpdate
    ctx = callback_context

    # Handle clear filters: when only the button "clear filters" is clicked
    if ctx.triggered and ctx.triggered[0]["prop_id"] == "clear-filters.n_clicks" and clear_clicks:
        company_filter = None
        industry_filter = None
        selected_article_rows = []
        selected_company_rows = []

    # Get dropdown options
    company_options = get_company_options()
    industry_options = get_industry_options()

    # Get selected article PK (for companies table filtering only)
    selected_article_pk = None
    if selected_article_rows:
        articles_data_temp = get_articles(company_filter, industry_filter)
        if not articles_data_temp.empty and selected_article_rows[0] < len(articles_data_temp):
            selected_article_pk = articles_data_temp.iloc[selected_article_rows[0]]["PK"]

    # Get selected company PK (not used for chart filtering)
    selected_company_pk = None
    if selected_company_rows:
        companies_data_temp = get_companies(selected_article_pk)
        if not companies_data_temp.empty and selected_company_rows[0] < len(companies_data_temp):
            selected_company_pk = companies_data_temp.iloc[selected_company_rows[0]]["Company Name"]

    # Get filtered data (chart only uses main filters, not table selections)
    articles_data = get_articles(company_filter, industry_filter)
    companies_data = get_companies(
        selected_article_pk,
    )  # Companies table still filtered by selected article
    scatter_data = get_scatter_plot_data(
        company_filter,
        industry_filter,
        None,
        aggregation_type,
    )  # Chart ignores table selections

    # Update articles table
    articles_records = articles_data.to_dict("records") if not articles_data.empty else []

    # Update companies table
    companies_records = companies_data.to_dict("records") if not companies_data.empty else []

    # This code introduces dynamic range slider configuration with data-driven min/max values, 2-year pre-selected range, and enhanced user interaction features.
    # Update scatter plot
    if not scatter_data.empty:
        if aggregation_type == "weekly":
            period_label = "Week"
        elif aggregation_type == "quarterly":
            period_label = "Quarter"
        else:
            period_label = "Month"

        # Calculate data-driven range slider bounds from original data
        data_min_date = scatter_data["published_at"].min()
        data_max_date = scatter_data["published_at"].max()

        # Use date filters as preselected range if provided, otherwise use 2-year default
        if start_date and end_date:
            preselected_start = pd.to_datetime(start_date).tz_localize("UTC")
            preselected_end = pd.to_datetime(end_date).tz_localize("UTC")
        else:
            # Set pre-selected range to last 2 years from data max date
            two_years_ago = data_max_date - pd.DateOffset(years=2)
            preselected_start = max(two_years_ago, data_min_date)  # Don't go before data starts
            preselected_end = data_max_date

        # Apply date filtering to displayed data if date filters are set
        # display_data = scatter_data.copy()
        # if start_date and end_date:
        #     start_datetime = pd.to_datetime(start_date).tz_localize('UTC')
        #     end_datetime = pd.to_datetime(end_date).tz_localize('UTC') + pd.Timedelta(days=1)
        #     display_data = scatter_data[
        #         (scatter_data['published_at'] >= start_datetime) &
        #         (scatter_data['published_at'] < end_datetime)
        #     ]

        fig = px.scatter(
            scatter_data,
            x="period",
            y="y_position",
            hover_data=["title", "published_at"],
            title=f"Articles Published by {period_label} (Each dot represents one article)",
        )
        fig.update_traces(
            marker=dict(size=8, opacity=0.7),
            # TODO: wrap text does not work with <b style="display: inline-block; max-width: 600px; word-wrap: break-word; white-space: normal;">
            hovertemplate=f'<b style="display: inline-block; max-width: 600px; word-wrap: break-word; white-space: normal;">%{{customdata[0]}}</b><br>Published: %{{customdata[4]}}<br>{period_label}: %{{customdata[5]}}<extra></extra>',
            customdata=scatter_data[
                [
                    "title",
                    "published_at",
                    "primary_key",
                    "url",
                    "published_on",
                    "period_name",
                    "country",
                    "industry_isic",
                    "company_name",
                    "litigation_reason",
                    "claim_category",
                    "source_of_pfas",
                    "settlement_finalized",
                    "settlement_amount",
                    "settlement_paid_date",
                ]
            ].values,
        )

        # Configure range slider with custom settings
        fig.update_layout(
            height=600,  # Increased height by 50% (from default ~400px to 600px)
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="gray",
                font_size=12,
                font_family="Arial",
                font_color="black",
                align="left",
                namelength=-1,
            ),
            xaxis_title="The bar shows all articles in the database. Slide left and right to review the articles in sections of the full history",
            yaxis_title=f"Articles per {period_label}",
            yaxis=dict(
                tickmode="linear",
                dtick=max(1, max(scatter_data["y_position"]) // 5) if not scatter_data.empty else 1,
                # Dynamic tick step to limit to max 10 ticks
                range=(
                    [0.5, max(scatter_data["y_position"]) + 1.5]
                    if not scatter_data.empty
                    else [0, 2]
                ),
            ),
            # Start y-axis from 1 (0.5 padding)
            hovermode="closest",
            xaxis=dict(
                type="date",
                range=[
                    preselected_start,
                    preselected_end,
                ],  # Pre-selected range (last 2 years)
                rangeslider=dict(
                    visible=True,
                    thickness=0.08,  # Reduced thickness (8% of plot height)
                    bgcolor="rgba(0,0,0,0.1)",  # Light background
                    borderwidth=1,
                    bordercolor="rgb(204,204,204)",
                    range=[data_min_date, data_max_date],  # Full data range in slider
                    yaxis=dict(rangemode="fixed"),  # Keep y-axis fixed when sliding
                ),
                # Add range buttons for quick navigation
                rangeselector=dict(
                    buttons=list(
                        [
                            dict(count=3, label="3M", step="month", stepmode="backward"),
                            dict(count=6, label="6M", step="month", stepmode="backward"),
                            dict(count=1, label="1Y", step="year", stepmode="backward"),
                            dict(count=2, label="2Y", step="year", stepmode="backward"),
                            dict(step="all", label="All"),
                        ],
                    ),
                    bgcolor="rgba(0,0,0,0.1)",
                    bordercolor="rgb(204,204,204)",
                    borderwidth=1,
                    font=dict(size=12),
                    x=0.01,
                    y=0.99,
                    xanchor="left",
                    yanchor="top",
                ),
            ),
            # Add title with data range info
            title=dict(
                text=f"{period_label}ly Articles Published<br><sub>Data Range: {data_min_date.strftime('%Y-%m-%d')} to {data_max_date.strftime('%Y-%m-%d')} | Showing: {preselected_start.strftime('%Y-%m-%d')} to {preselected_end.strftime('%Y-%m-%d')}</sub>",
                x=0.5,
                font=dict(size=16),
            ),
        )
    else:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for the selected filters",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            xanchor="center",
            yanchor="middle",
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False))

    # Update counts
    article_count = f"{len(articles_data)} articles"
    company_count = f"{len(companies_data)} companies"

    # Update filter status (only show main filters, not table selections)
    filters = []
    if company_filter:
        filters.append(f"Company: {company_filter}")
    if industry_filter:
        filters.append(f"Industry: {industry_filter}")

    if filters:
        filter_status = f"Active filters: {', '.join(filters)}"
    else:
        filter_status = "No filters applied"

    return (
        articles_records,
        companies_records,
        fig,
        article_count,
        company_count,
        filter_status,
        selected_article_pk or "",
        selected_company_pk or "",
        company_options,
        industry_options,
    )


@app.callback(
    [Output("company-filter", "value"), Output("industry-filter", "value")],
    [Input("clear-filters", "n_clicks")],
    [State("session-store", "data")],
)
@log_callback_trigger
def clear_filters(n_clicks, session_data):
    # Check authentication
    if not session_data or not is_authenticated(session_data.get("session_id")):
        raise PreventUpdate
    
    ctx = callback_context
    if ctx.triggered and ctx.triggered[0]["prop_id"] == "clear-filters.n_clicks" and n_clicks:
        return [None, None]
    return [dash.no_update, dash.no_update]


# Callback for handling click events on scatter plot
@app.callback(
    Output("article-info-box", "children"),
    [
        Input("scatter-plot-chart", "clickData"),
        Input("aggregation-type", "children"),
        Input("company-filter", "value"),
        Input("industry-filter", "value"),
        Input("start-date-filter", "date"),
        Input("end-date-filter", "date"),
    ],
    [State("session-store", "data")],
    prevent_initial_call=True,
)
@log_callback_trigger
def display_article_info(
    click_data,
    aggregation_type,
    company_filter,
    industry_filter,
    start_date,
    end_date,
    session_data,
):
    # Check authentication
    if not session_data or not is_authenticated(session_data.get("session_id")):
        raise PreventUpdate
    ctx = callback_context

    # Only process if click data triggered the callback
    if not ctx.triggered or ctx.triggered[0]["prop_id"] != "scatter-plot-chart.clickData":
        return html.Div()

    if not click_data:
        return html.Div()

    try:
        # Get the clicked point data
        point = click_data["points"][0]
        custom_data = point["customdata"]

        title = custom_data[0]
        published_at = custom_data[1]
        pk = custom_data[2]
        url = custom_data[3]
        country = custom_data[6]
        industry_isic = custom_data[7]
        company_name = custom_data[8]
        litigation_reason = custom_data[9]
        claim_category = custom_data[10]
        source_of_pfas = custom_data[11]
        settlement_finalized = custom_data[12]
        settlement_amount = custom_data[13]
        settlement_paid_date = custom_data[14]

        # Find the specific article
        df = articles_df.copy()
        article_data = df[df["primary_key"] == pk]

        if article_data.empty:
            return html.Div()

        article = article_data.iloc[0]

        # Create info box content
        info_box = dbc.Card(
            [
                dbc.CardHeader([html.H5(title, className="mb-0")], className="bg-transparent"),
                dbc.CardBody(
                    [
                        # dbc.Row([
                        #     dbc.Col([
                        #         html.H3(title, className="card-title")
                        #     ], width=12),
                        # ]),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.P(
                                            [
                                                html.Strong("Published: "),
                                                pd.to_datetime(published_at).strftime(
                                                    "%Y-%m-%d %H:%M",
                                                ),
                                            ],
                                            className="mb-2",
                                        ),
                                        html.P(
                                            [
                                                html.Strong("Claim Category: "),
                                                claim_category,
                                            ],
                                            className="mb-2",
                                        ),
                                        html.P(
                                            [
                                                html.Strong("Litigation Reasons: "),
                                                litigation_reason,
                                            ],
                                            className="mb-2",
                                        ),
                                        html.P(
                                            [
                                                html.Strong("Source of PFAS: "),
                                                source_of_pfas,
                                            ],
                                            className="mb-2",
                                        ),
                                        html.A(
                                            [
                                                html.I(className="fas fa-external-link-alt me-2"),
                                                "Read Full Article",
                                            ],
                                            href=url,
                                            target="_blank",
                                            className="btn btn-primary btn-sm",
                                        ),
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        html.P(
                                            [html.Strong("Companies: "), company_name],
                                            className="mb-2",
                                        ),
                                        html.P(
                                            [
                                                html.Strong("Is Settlement finalized?: "),
                                                "Yes" if settlement_finalized else "No",
                                            ],
                                            className="mb-2",
                                        ),
                                        html.P(
                                            [
                                                html.Strong("Settlement Amount: "),
                                                settlement_amount,
                                            ],
                                            className="mb-2",
                                        ),
                                        html.P(
                                            [
                                                html.Strong("Settlement Paid Date: "),
                                                (
                                                    "not reported"
                                                    if settlement_paid_date == "-"
                                                    else settlement_paid_date
                                                ),
                                            ],
                                            className="mb-2",
                                        ),
                                    ],
                                    width=6,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        return info_box

    except Exception as e:
        logging.error(f"Error displaying article info: {str(e)}")
        return html.Div([dbc.Alert("Error loading article information", color="danger")])


# Callback to sync date filters with range slider
@app.callback(
    [Output("start-date-filter", "date"), Output("end-date-filter", "date")],
    [Input("scatter-plot-chart", "relayoutData")],
    [State("session-store", "data")],
    prevent_initial_call=True,
)
@log_callback_trigger
def sync_date_filters_with_range_slider(relayout_data, session_data):
    # Check authentication
    if not session_data or not is_authenticated(session_data.get("session_id")):
        raise PreventUpdate
    
    if relayout_data and "xaxis.range[0]" in relayout_data and "xaxis.range[1]" in relayout_data:
        start_date = pd.to_datetime(relayout_data["xaxis.range[0]"]).date()
        end_date = pd.to_datetime(relayout_data["xaxis.range[1]"]).date()
        return start_date, end_date
    return dash.no_update, dash.no_update


# Add a separate callback to clear the info box when filters change
@app.callback(
    Output("article-info-box", "children", allow_duplicate=True),
    [
        Input("company-filter", "value"),
        Input("industry-filter", "value"),
        Input("start-date-filter", "date"),
        Input("end-date-filter", "date"),
        Input("aggregation-type", "children"),
    ],
    [State("session-store", "data")],
    prevent_initial_call=True,
)
@log_callback_trigger
def clear_article_info_on_filter_change(
    company_filter,
    industry_filter,
    start_date,
    end_date,
    aggregation_type,
    session_data,
):
    # Check authentication
    if not session_data or not is_authenticated(session_data.get("session_id")):
        raise PreventUpdate
    
    return html.Div()


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=5000, debug=True)