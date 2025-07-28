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

# Parse date columns
articles_df["published_at"] = pd.to_datetime(articles_df["published_at"], errors="coerce")
articles_df["modified_at"] = pd.to_datetime(articles_df["modified_at"], errors="coerce")

# Create Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # maybe replace by init_login_manager() from Hercules


def get_articles(company_filter=None, industry_filter=None, article_pk=None):
    """Get filtered articles"""
    try:
        df = articles_df.copy()

        if company_filter:
            company_pks = companies_df[
                companies_df["company_name"].isin(company_filter)
            ]["primary_key"].tolist()
            if company_pks:
                df = df[df["primary_key"].isin(company_pks)]
            else:
                return pd.DataFrame()  # No matching companies found

        if industry_filter:
            df = df[df["isic_name"].isin(industry_filter)]

        if article_pk:
            df = df.loc[df.primary_key==article_pk]

        # Sort by published date descending
        df = df.sort_values("published_at", ascending=False, na_position="last")

        # Format data for display
        data = []
        for _, article in df.iterrows():
            data.append(
                {
                    "pk": article["primary_key"],
                    "article_id": article["article_id"] or "",
                    "title": (
                        f"[{article['title']}]({article['url']})" if pd.notna(article["title"]) else ""
                    ),
                    "url": article["url"] or "",
                    "published_at": article["published_at"].strftime("%Y-%m-%d %H:%M") or "",
                    "country_code": article["country_code"] or "",
                    "isic_name": article["isic_name"] or "",
                    "search_term": article["search_term"] or "",
                    # "company_name": article["company_name"] or "",
                    # "litigation_reason": article["litigation_reason"] or "",
                    # "claim_category": article["claim_category"] or "",
                    # "source_of_pfas": article["source_of_pfas"] or "",
                    # "settlement_amount": article["settlement_amount"] or "",
                    # "settlement_paid_date": article["settlement_paid_date"] or "",
                },
            )

        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Error fetching articles: {str(e)}")
        return pd.DataFrame()


def get_companies(article_filter=None):
    """Get filtered companies"""
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

        # Format data for display
        data = []
        for _, company in df.iterrows():
            data.append(
                {
                    "pk": str(company["primary_key"]),
                    "company_name": company["company_name"] or "",
                    "litigation_reason":  company["litigation_reason"] or "",
                    "claim_category": company["claim_category"] or "",
                    "source_of_pfas": company["source_of_pfas"] or "",
                    "settlement_finalized": (
                        "Yes" if company["settlement_finalized"] else "No"
                    ),
                    "settlement_amount": settlement_amount,
                    "settlement_paid_date": (
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
            company_pks = companies_df[companies_df["company_name"].isin(company_filter)][
                "primary_key"
            ]
            art_df = art_df[art_df["primary_key"].isin(company_pks)]

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
                    "title": (
                        str(article["title"]) if pd.notna(article["title"]) else ""
                    ),
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
                    lambda x: x.sort_values("published_at").assign(
                        y_position=range(1, len(x) + 1)
                    ),
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


def draw_info_box(
    title,
    published_at,
    url,
    country,
    industry_isic,
    company_name,
    litigation_reason,
    claim_category,
    source_of_pfas,
    settlement_finalized,
    settlement_amount,
    settlement_paid_date,
):
    info_box = dbc.Card(
        [
            dbc.CardHeader(
                [html.H5(title, className="mb-0")], className="bg-transparent"
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.P(
                                        [
                                            html.Strong("Published at: "),
                                            pd.to_datetime(published_at).strftime(
                                                "%Y-%m-%d %H:%M",
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    html.P(
                                        [
                                            html.Strong("Country: "),
                                            country,
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
                                            html.I(
                                                className="fas fa-external-link-alt me-2"
                                            ),
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
                                        [html.Strong("Industry: "), industry_isic],
                                        className="mb-2",
                                    ),
                                    html.P(
                                        [
                                            html.Strong(
                                                "Is Settlement finalized?: "
                                            ),
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


# App layout
app.title = "Hercules Chemwatch"
app.layout = dbc.Container(
    [
        dcc.Location(id="url", refresh="callback-nav"),
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
                                                        html.I(
                                                            className="fas fa-calendar me-1"
                                                        ),
                                                        "Start Date",
                                                    ],
                                                ),
                                                dcc.DatePickerSingle(
                                                    id="start-date-filter",
                                                    date=(
                                                        datetime.now()
                                                        - pd.DateOffset(years=2)
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
                                                        html.I(
                                                            className="fas fa-calendar me-1"
                                                        ),
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
                                            multi=True,
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
                                            multi=True,
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
                                html.Div(
                                    id="filter-status", className="text-muted small"
                                ),
                                # Contact/Feedback
                                html.Div(
                                    [
                                        html.Hr(),
                                        html.P(
                                            [
                                                html.I(className="fas fa-envelope me-2"),
                                                "Questions or feedback? "
                                                "Contact us!",
                                                html.A(
                                                    "ali.barandov@agcs.allianz.com",
                                                    href="mailto:ali.barandov@agcs.allianz.com",
                                                    className="text-primary",
                                                    style={"textDecoration": "underline"}
                                                ),
                                            ],
                                            className="mt-3 mb-0 text-muted small",
                                            style={"fontSize": "0.95rem"}
                                        ),
                                    ],
                                    className="mt-auto"
                                ),
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
                        html.H1(
                            "PFAS Articles & Companies Dashboard", className="display-6"
                        ),
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
                                                html.I(
                                                    className="fas fa-chart-scatter me-2"
                                                ),
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
                                        html.Div(
                                            id="article-info-box", className="mt-3"
                                        ),
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
                                                        html.I(
                                                            className="fas fa-newspaper me-2"
                                                        ),
                                                        "Articles",
                                                    ],
                                                    className="mb-0",
                                                ),
                                                dbc.Badge(
                                                    id="article-count", color="primary"
                                                ),
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
                                                    "id": "title",
                                                    "type": "text",
                                                    "presentation": "markdown"
                                                },
                                                {
                                                    "name": "Published Date",
                                                    "id": "published_at",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Country",
                                                    "id": "country_code",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Industry",
                                                    "id": "isic_name",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Search Term",
                                                    "id": "search_term",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "PK",
                                                    "id": "pk",
                                                    "type": "text",
                                                },
                                            ],
                                            data=[],
                                            sort_action="native",
                                            sort_by=[{"column_id": "published_at", "direction": "desc"}],
                                            filter_action="native",
                                            filter_options={"case": "insensitive"},
                                            page_action="native",
                                            page_current=0,
                                            page_size=10,
                                            row_selectable="multi",
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
                                                    "if": {"column_id": "title"},
                                                    "width": "30%",
                                                    "whiteSpace": "normal",
                                                    "height": "auto",
                                                },
                                                {
                                                    "if": {"column_id": "pk"},
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
                                                        html.I(
                                                            className="fas fa-building me-2"
                                                        ),
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
                                                    "id": "company_name",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Litigation Reason",
                                                    "id": "litigation_reason",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Claim Category",
                                                    "id": "claim_category",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Source of PFAS",
                                                    "id": "source_of_pfas",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Settlement Finalized",
                                                    "id": "settlement_finalized",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "Settlement Amount",
                                                    "id": "settlement_amount",
                                                    "type": "text",
                                                },
                                                {
                                                    "name": "PK",
                                                    "id": "pk",
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
                                                    "if": {"column_id": "company_name"},
                                                    "width": "20%",
                                                },
                                                {
                                                    "if": {"column_id": "pk"},
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
    ],
    fluid=True,
)



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
@log_callback_trigger
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
    
    Input("company-filter", "value"),
    Input("industry-filter", "value"),
    Input("articles-table", "selected_rows"),
    Input("companies-table", "selected_rows"),
    Input("clear-filters", "n_clicks"),
    Input("aggregation-type", "children"),
    Input("start-date-filter", "date"),
    Input("end-date-filter", "date"),
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
):
    ctx = callback_context

    # Handle clear filters: when only the button "clear filters" is clicked
    if (
        ctx.triggered
        and ctx.triggered[0]["prop_id"] == "clear-filters.n_clicks"
        and clear_clicks
    ):
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
        if not (articles_data_temp.empty and 
                selected_article_rows[0] < len(articles_data_temp)
        ):
            selected_article_pk = articles_data_temp.iloc[selected_article_rows[0]][
                "pk"
            ]

    # Get selected company PK (not used for chart filtering)
    selected_company_pk = None
    if selected_company_rows:
        companies_data_temp = get_companies(selected_article_pk)
        if not companies_data_temp.empty and selected_company_rows[0] < len(
            companies_data_temp
        ):
            selected_company_pk = companies_data_temp.iloc[selected_company_rows[0]][
                "company_name"
            ]

    # Get filtered data (chart only uses main filters, not table selections)
    articles_data = get_articles(company_filter, industry_filter)
    companies_data = get_companies(
        selected_article_pk,
    )  # Companies table still filtered by selected article
    scatter_data = get_scatter_plot_data(
        company_filter,
        industry_filter,
        None,   # Chart ignores table selections
        aggregation_type,
    )  

    # Update articles table
    articles_records = (
        articles_data.to_dict("records") if not articles_data.empty else []
    )

    # Update companies table
    companies_records = (
        companies_data.to_dict("records") if not companies_data.empty else []
    )

    # This code introduces dynamic range slider configuration with data-driven min/max values,
    # 2-year pre-selected range, and enhanced user interaction features.
    # Update scatter plot
    MAP_AGGREGATION_TYPE_TO_NAME_FOR_UI = {
        "weekly": "Week",
        "quarterly": "Quarter",
        "monthly": "Month",
    }
    if not scatter_data.empty:
        period_label = MAP_AGGREGATION_TYPE_TO_NAME_FOR_UI.get(aggregation_type, "Month")

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
            preselected_start = max(
                two_years_ago, data_min_date
            )  # Don't go before data starts
            preselected_end = data_max_date

        fig = px.scatter(
            scatter_data,
            x="period",
            y="y_position",
            hover_data=["title", "published_at"],
            title=f"Articles published by {period_label} (Each dot represents one article)",
        )
        fig.update_traces(
            marker={"size": 8, "opacity": 0.7},
            # TODO: wrap text does not work with <b style="display: inline-block;
            #       max-width: 600px; word-wrap: break-word; white-space: normal;">
            hovertemplate = (
                f'<b style="display: inline-block; max-width: 600px; '
                f'word-wrap: break-word; white-space: normal;">%{{customdata[0]}}</b><br>'
                f'Published: %{{customdata[4]}}<br>'
                f'{period_label}: %{{customdata[5]}}<extra></extra>'
            ),
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
            hoverlabel={
                "bgcolor": "white",
                "bordercolor": "gray",
                "font_size": 12,
                "font_family": "Arial",
                "font_color": "black",
                "align": "left",
                "namelength": -1,
            },
            hovermode="closest",
            xaxis_title="The bar shows all articles in the database. "
                "Slide left and right to review the articles in sections of the full history.",
            yaxis_title=f"Articles per {period_label}, sorted by publication date",
            yaxis={
                "tickmode": "linear",
                "dtick": (
                    max(1, max(scatter_data["y_position"]) // 5)
                    if not scatter_data.empty
                    else 1
                ),
                # Dynamic tick step to limit to max 10 ticks
                "range": (
                    [0.5, max(scatter_data["y_position"]) + 1.5]
                    if not scatter_data.empty
                    else [0, 2]
                ),
            },
            # Start y-axis from 1 (0.5 padding)
            xaxis={
                "type": "date",
                "range": [
                    preselected_start,
                    preselected_end,
                ],  # Pre-selected range (last 2 years)
                "rangeslider": {
                    "visible": True,
                    "thickness": 0.08,  # Reduced thickness (8% of plot height)
                    "bgcolor": "rgba(0,0,0,0.1)",  # Light background
                    "borderwidth": 1,
                    "bordercolor": "rgb(204,204,204)",
                    "range": [data_min_date, data_max_date],  # Full data range in slider
                    "yaxis": {"rangemode": "fixed"},  # Keep y-axis fixed when sliding
                },
                # Add range buttons for quick navigation
                "rangeselector": {
                    "buttons": [
                        {"count": 3, "label": "3M", "step": "month", "stepmode": "backward"},
                        {"count": 6, "label": "6M", "step": "month", "stepmode": "backward"},
                        {"count": 1, "label": "1Y", "step": "year", "stepmode": "backward"},
                        {"count": 2, "label": "2Y", "step": "year", "stepmode": "backward"},
                    ],
                    "bgcolor": "rgba(0,0,0,0.1)",
                    "bordercolor": "rgb(204,204,204)",
                    "borderwidth": 1,
                    "font": {"size": 12},
                    "x": 0.01,
                    "y": 0.99,
                    "xanchor": "left",
                    "yanchor": "top",
                },
            },
            # Add title with data range info
            title={
                "text": (
                    f"{period_label}ly Articles Published<br>"
                    f"<sub>Data Range: {data_min_date.strftime('%Y-%m-%d')} to {data_max_date.strftime('%Y-%m-%d')} | "
                    f"Showing: {preselected_start.strftime('%Y-%m-%d')} to {preselected_end.strftime('%Y-%m-%d')}</sub>"
                ),
                "x": 0.5,
                "font": {"size": 16},
            },
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
            font={"size": 16, "color": "gray"},
        )
        fig.update_layout(xaxis={"visible": False}, yaxis={"visible": False})

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
    [
        Output("company-filter", "value"),
        Output("industry-filter", "value"),
        Output("articles-table", "filter_query"),
        Output("companies-table", "filter_query"),
    ],
    [Input("clear-filters", "n_clicks")],
)
@log_callback_trigger
def clear_filters(n_clicks):
    ctx = callback_context
    if (
        ctx.triggered
        and ctx.triggered[0]["prop_id"] == "clear-filters.n_clicks"
        and n_clicks
    ):
        return [None, None, "", ""]
    return [dash.no_update, dash.no_update, dash.no_update, dash.no_update]


# Callback for handling click events on scatter plot
@app.callback(
    Output("article-info-box", "children"),
    Input("scatter-plot-chart", "clickData"),
    Input("articles-table", "selected_rows"),
    State("articles-table", "data"),
    prevent_initial_call=True,
)
@log_callback_trigger
def display_article_info(
    click_data,
    selected_article_rows,
    articles_data,
):
    ctx = callback_context
    
    # Only process if "click data" triggered the callback
    if (ctx.triggered and 
        click_data and
        ctx.triggered[0]["prop_id"] == "scatter-plot-chart.clickData"
        ):
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

            # Create info box content
            info_box =draw_info_box(
                title,
                published_at,
                url,
                country,
                industry_isic,
                company_name,
                litigation_reason,
                claim_category,
                source_of_pfas,
                settlement_finalized,
                settlement_amount,
                settlement_paid_date,
            )
            
            return info_box

        except Exception as e:
            logging.error(f"Error displaying article info: {str(e)}")
            return html.Div(
                [dbc.Alert("Error loading article information from chart", color="danger")]
            )
        
    elif (ctx.triggered and 
        selected_article_rows and
        ctx.triggered[0]["prop_id"] == "articles-table.selected_rows"
        ):
        try:
            print(articles_data)
            one_article_is_selected = len(selected_article_rows)==1
            pk = selected_article_rows[0]
            print(pk)
            # Get article data based on selected row
            # if one_article_is_selected:
            #     pk = articles_data[pk]["primary_key"]
            primary_key = articles_data[pk]["pk"]
            print(f"primary_key {primary_key}")

            article_data = get_scatter_plot_data(article_filter=primary_key)
            print(f"article_data {article_data}")
            article_data = article_data.to_dict("records")
            print(f"article_data {article_data}")

            title = article_data["title"] if one_article_is_selected else '...'
            published_at = article_data["published_at"] if one_article_is_selected else '...'
            pk = article_data["primary_key"] if one_article_is_selected else '...'
            url = article_data["url"] if one_article_is_selected else '...'
            country = article_data["country"] if one_article_is_selected else '...'
            industry_isic = article_data["industry_isic"] if one_article_is_selected else '...'
            company_name = article_data["company_name"] if one_article_is_selected else '...'
            litigation_reason = article_data["litigation_reason"] if one_article_is_selected else '...'
            claim_category = article_data["claim_category"] if one_article_is_selected else '...'
            source_of_pfas = article_data["source_of_pfas"] if one_article_is_selected else '...'
            settlement_finalized = article_data["settlement_finalized"] if one_article_is_selected else '...'
            settlement_amount = article_data["settlement_amount"] if one_article_is_selected else '...'
            settlement_paid_date = article_data["settlement_paid_date"] if one_article_is_selected else '...'
            
            info_box =draw_info_box(
                title,
                published_at,
                url,
                country,
                industry_isic,
                company_name,
                litigation_reason,
                claim_category,
                source_of_pfas,
                settlement_finalized,
                settlement_amount,
                settlement_paid_date,
            )

            return info_box
            
        except Exception as e:
            logging.error(f"Error displaying article info: {str(e)}")
            return html.Div(
                [dbc.Alert("Error loading article information from articles table", color="danger")]
            )
    
    else:
        return html.Div()
    

# Callback to sync date filters with range slider
@app.callback(
    Output("start-date-filter", "date"), 
    Output("end-date-filter", "date"),
    Input("scatter-plot-chart", "relayoutData"),
    prevent_initial_call=True,
)
@log_callback_trigger
def sync_date_filters_with_range_slider(relayout_data):
    if (
        relayout_data
        and "xaxis.range[0]" in relayout_data
        and "xaxis.range[1]" in relayout_data
    ):
        start_date = pd.to_datetime(relayout_data["xaxis.range[0]"]).date()
        end_date = pd.to_datetime(relayout_data["xaxis.range[1]"]).date()
        return start_date, end_date
    return dash.no_update, dash.no_update


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=5000, debug=True)
