"""
Module: magic_login
This module provides the layout and callback functions for the magic login functionality
- A layout for displaying the magic login form and related components.
- Validation of magic login tokens from the URL query string.
- User authentication and login functionality using a magic link.
- Redirection to the home page after a successful login.
- `magic_login_layout`: The main layout for the magic login page.
- `reset_success_modal`: A modal displayed upon successful login.
- `validate_magic_link`: Validates the magic login token from the URL query string,
    handles user authentication, and redirects to the home page upon success.
- `clientside_callback`: Clears the local storage and closes the window after a successful login.
"""

from datetime import datetime
import dash
from dash import callback, Output, Input, dcc, clientside_callback
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from flask import session
from flask_login import login_user
from ..user_management.auth import User
from utils.logger_config import logger
from shared_code.connections.pg_service import PostgresService
import os

environment = os.getenv("ENVIRONMENT", "dev")
pg = PostgresService(schema="chemwatch")


magic_login_layout = dmc.Center(
    [
        dmc.Card(
            children=[
                dmc.CardSection(
                    dmc.Image(
                        src=r"assets\hercules_logo_ai_factory.png",
                        alt="hercules logo",
                        mt=20,
                    ),
                ),
                dmc.Text(
                    "Hercules is an AI-based tool for continuous monitoring \
                    of US lawyer activity for a list of pharmaceutical products and companies. \
                    Data is updated on a weekly basis.",
                    mt="sm",
                    className="lead",
                ),
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            w=350,
            mr=50,
        ),
        dmc.Card(
            id="magic_login_card",
            w=350,
        ),
        dmc.Modal(
            id="reset_success_modal",
            title="Login successful!",
            children="Your login is successful. Redirecting to the home page...",
            opened=False,
            centered=True,
        ),
        dcc.Interval(
            id="redirect_timer_reset_pass", interval=3000, n_intervals=0, disabled=True
        ),
    ],
    m="xl",
    p="xl",
    id="magic_login_container",
)


@callback(
    Output("magic_login_card", "children"),
    Output("magic_login_store", "data"),
    Output("url", "pathname"),
    Input("url", "pathname"),
    Input("url", "search"),
)
def validate_magic_link(pathname: str, search: str) -> tuple:
    """
    Validates a magic link provided in the URL and performs user login if valid.
    Args:
        pathname (str): The pathname from the URL.
        search (str): The query string from the URL.
    Returns:
        tuple: A tuple containing the card children, store data, and pathname.
    """
    if pathname != "/magic_login":
        raise PreventUpdate

    # Extract token from query string
    token = search.split("token=")[1] if "token=" in search else None
    if not token:
        logger.error("No token found in the URL.")
        return _generate_error_response("Invalid or expired magic link.")

    # Validate token
    now = datetime.now()
    query = """
        SELECT email FROM hercules_login_magic_link
        WHERE token = :token AND expiry > :now
    """
    result = pg.do_read(query, {"token": token, "now": now})["data"]
    if result.empty:
        logger.error("Token validation failed or token expired.")
        return _generate_error_response("Invalid or expired magic link.")

    email = result.iloc[0]["email"]

    # Invalidate the token
    if not _invalidate_token(token, now):
        return _generate_error_response(
            "Error: Failed to validate magic link. Please try again later."
        )

    # Authenticate user
    return _authenticate_user(email)


def _generate_error_response(message: str) -> tuple:
    """
    Generates an error response with a message and a back-to-login button.
    """
    return (
        [
            dmc.Text(message, c="red", className="lead", mt=50),
            dmc.Anchor(
                dmc.Button(
                    "Back to Login",
                    id="back_to_login_button_register",
                    variant="outline",
                    rightSection=DashIconify(icon="mdi:login", color="#4267b2"),
                    className="submit_button",
                    mt=10,
                    fullWidth=True,
                ),
                href="/login",
            ),
        ],
        dash.no_update,
        dash.no_update,
    )


def _invalidate_token(token: str, now: datetime) -> bool:
    """
    Invalidates the magic link token by setting its expiry to the current time.
    """
    update_query = """
        UPDATE hercules_login_magic_link
        SET expiry = :now
        WHERE token = :token
    """
    result = pg.do_update(update_query, {"now": now, "token": token})
    if not result["success"]:
        logger.error("Failed to invalidate the token.")
        return False
    return True


def _authenticate_user(email: str) -> tuple:
    """
    Authenticates the user based on the provided email and logs them in.
    """
    user_query = "SELECT * FROM hercules_users WHERE email = :email"
    user_data = pg.do_read(user_query, {"email": email})["data"]
    if user_data.empty:
        return _generate_error_response(
            "An error occurred while logging in. Please try again later."
        )

    user_record = user_data.iloc[0]
    if not user_record["is_approved"]:
        return _generate_error_response(
            "Your account is not approved yet. Please contact the admin."
        )

    user = User(
        int(user_record["user_id"]),
        user_record["name"],
        user_record["email"],
        user_record["is_admin"],
        user_record["is_approved"],
    )
    login_user(user)
    session.permanent = True
    logger.info(f"User {email} logged in via magic link.")
    return (
        [
            dmc.Text(
                "Login successful! Redirecting to homepage...",
                className="lead",
                mt=50,
            ),
        ],
        {"login_success": True},
        dash.no_update,
    )


clientside_callback(
    """
    function(data) {
        if (data && data.login_success) {
            localStorage.setItem('hercules_logged_in', '1');
            window.close();
        }
        return null;
    }
    """,
    Output("magic_login_store", "clear_data"),
    Input("magic_login_store", "data"),
)
