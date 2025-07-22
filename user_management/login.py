"""
Module: login

This module provides the layout and callback functions for the login page of Hercules.
It includes functionality for user authentication, email validation, and login/logout operations.

Layout Components:
- `login_layout`: Defines the UI layout for the login page, including email input,
    login and register buttons, and error messages.

Callbacks:
- `validate_email(email: str) -> str | bool`: Validates the email format.
- `send_magic_link(login_n_clicks: int, email: str, invalid_email: str | bool, url: str)
    -> tuple`: Handles sending the magic login link and error handling.
- `update_logout(logout_n_clicks: int | None) -> str`: Handles the logout process.
- clientside callback to poll refresh and update the resend email timer
"""

import re
import os
import uuid
from datetime import datetime, timedelta
import dash
from dash import callback, Output, Input, State, clientside_callback, dcc
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from flask_login import logout_user
from utils.logger_config import logger
from utils.email_templates import magic_login_email_template
from shared_code.connections.pg_service import PostgresService
from layout_functions.email_automation import send_email

environment = os.getenv("ENVIRONMENT", "dev")
pg = PostgresService(schema="chemwatch")

login_layout = dmc.Center(
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
            [
                dmc.Text("Please log in to continue:", className="lead"),
                dmc.TextInput(
                    label="Your Email:",
                    placeholder="Email",
                    leftSection=DashIconify(icon="mdi:user"),
                    id="email_box_login",
                    debounce=True,
                    n_submit=0,
                ),
                dmc.Alert(
                    "",
                    title="Error!",
                    color="red",
                    hide=True,
                    id="output_alert_login",
                ),
                dmc.Button(
                    "Login",
                    id="login_button",
                    variant="outline",
                    rightSection=DashIconify(icon="mdi:login", color="#4267b2"),
                    className="submit_button",
                    mt=20,
                ),
                dmc.Divider(color="#4267b2", size="xs", variant="dashed", mt=60, mb=20),
                dmc.Text(
                    "Don't have an account yet? You can sign up to access Hercules.",
                    mt=10,
                    className="lead",
                ),
                dmc.Anchor(
                    dmc.Button(
                        "Register",
                        variant="outline",
                        rightSection=DashIconify(
                            icon="mdi:account-plus", color="#4267b2"
                        ),
                        className="submit_button",
                        mt=10,
                        fullWidth=True,
                    ),
                    href="/register",
                ),
            ],
            w=350,
        ),
        dcc.Interval(id="poll_auth", interval=1000, n_intervals=1, disabled=True),
        dcc.Store(id="email_sent_flag", data=0),
    ],
    m="xl",
    p="xl",
    id="login_container",
)


@callback(
    Output("email_box_login", "error"),
    Input("email_box_login", "value"),
    prevent_initial_call=True,
)
def validate_email(email: str) -> str | bool:
    """
    Validates the email format when the focus changes from the email input field.

    Parameters:
    - email (str): The email entered by the user.

    Returns:
    - str | bool: An error message if the email format is invalid, otherwise False.
    """

    if not email:
        return "Email cannot be empty."

    email_regex = r"^[a-zA-Z0-9_.+-]+@allianz\.(com|de)$"
    if re.match(email_regex, email):
        return False
    return "Invalid email format. Please enter a valid Allianz email \
        (e.g., @allianz.com or @allianz.de)."


@callback(
    Output("output_alert_login", "title"),
    Output("output_alert_login", "children"),
    Output("output_alert_login", "hide"),
    Output("output_alert_login", "color"),
    Output("login_button", "disabled"),
    Output("login_button", "children"),
    Output("poll_auth", "disabled"),
    Output("email_sent_flag", "data"),
    Input("login_button", "n_clicks"),
    Input("email_box_login", "n_submit"),
    State("email_box_login", "value"),
    State("url", "href"),
    State("email_sent_flag", "data"),
    # this flag used here since there is a desync between server and client side callback
    # and the resend email can be spammed for a second for multiple emails
    prevent_initial_call=True,
    running=[
        (
            Output("login_button", "children"),
            dmc.Loader(size="sm", color="blue"),
            "Login",
        ),
        (Output("login_button", "disabled"), True, False),
        (Output("email_sent_flag", "data"), 60, 0),
    ],
)
def send_magic_link(
    login_n_clicks: int,
    email_submit: int,
    email: str,
    url: str,
    email_sent_flag: int,
) -> tuple:
    """
    Handles sending the magic login link and error handling.

    Parameters:
    - login_n_clicks (int): The number of times the login button has been clicked.
    - email_submit (int): Enter button input for email text input.
    - email (str): The email entered by the user.
    - url (str): The current page URL.
    - email_sent_flag (int): flad for email resend timer

    Returns:
    - tuple: Outputs for updating the UI components.
    """
    if validate_email(email):  # reusing the validate_email callback
        raise PreventUpdate

    if (
        (login_n_clicks is None or login_n_clicks == 0)
        and (email_submit is None or email_submit == 0)
        or email_sent_flag > 0
    ):
        raise PreventUpdate

    try:
        # Check if the email is registered
        user_data = pg.do_read(
            "SELECT * FROM hercules_users WHERE email = :email", {"email": email}
        )["data"]
        if user_data.empty:
            logger.warning("Email not registered")
            return _generate_error_response("Email not registered!")

        if not user_data.iloc[0]["is_approved"]:
            logger.warning("Email not approved")
            return _generate_error_response(
                "Your email is not approved. Please contact the admin."
            )

        # token and expiry time
        token = str(uuid.uuid4())
        expiry_time = datetime.now() + timedelta(minutes=10)

        # Insert or update the magic link in the database
        insert_query = """
            INSERT INTO hercules_login_magic_link (email, token, expiry)
            VALUES (:email, :token, :expiry)
            ON CONFLICT (email) DO UPDATE SET token = :token, expiry = :expiry
        """
        insert_params = {"email": email, "token": token, "expiry": expiry_time}
        if not pg.do_insert(insert_query, insert_params)["success"]:
            logger.error(f"Error inserting magic link for {email}")
            return _generate_error_response(
                "An error occurred. Please try again later."
            )

        # Send the magic login email
        base_url = url.rsplit("/", 1)[0]
        magic_link = f"{base_url}/magic_login?token={token}"
        email_message = magic_login_email_template.format(
            name=user_data.iloc[0]["name"],
            magic_link=magic_link,
            year=datetime.now().year,
        )
        if send_email(
            from_list="tmu-hercules-risk-monitoring@agcs.allianz.com",
            to_list=email,
            mail_subject="Hercules Login Link",
            mail_body=email_message,
            logo_path="assets/hercules_logo_ai_factory_small.png",
        ):
            logger.info(f"Magic login link sent to {email}")
            return (
                "Email Sent..!",
                "A magic login link has been sent to your email. Please click on the link from the same device.",
                False,
                "blue",
                True,
                dmc.Loader(size="sm", color="blue"),
                False,
                60,
            )

        logger.error(f"Error sending magic login email to {email}")
        return _generate_error_response("An error occurred. Please try again later.")

    except Exception as e:
        logger.error(f"Login error: {e}")
        return _generate_error_response("An error occurred. Please try again later.")


def _generate_error_response(message: str) -> tuple:
    """
    Generates a standard error response tuple for Dash callbacks.
    """
    return (
        "Error..!",
        message,
        False,
        "red",
        False,
        dash.no_update,
        dash.no_update,
        dash.no_update,
    )


# Note (KG): this is the best idea I could think to implement this. Feel free to optimize it.

# This clientside callback polls the local storage for the `hercules_logged_in` flag to
# check if the user is logged in.
# The flag is set in the magic_login.py file if the user is logged in successfully.

# 1. If logged in, it redirects the user to the "/overview" page and resets the flag.
# 2. Disables the polling mechanism after 10 minutes (600 intervals)
#       to prevent unnecessary requests.
# 3. Manages the countdown timer for the "Resend Email" button:
#    - If the countdown is active (`email_sent_flag > 0`),
#       it updates the button text to show the remaining time.
#    - Once the countdown ends, it enables the "Resend Email" button.
# - n_intervals (int): The number of intervals elapsed since the polling started.
# - email_sent_flag (int): The countdown timer value for the "Resend Email" button
#    - set to 60 when the button is initially clicked.

clientside_callback(
    """
    function(n_intervals, email_sent_flag) {
        console.log("Polling for auth complete");
        console.log("n_intervals:", n_intervals);
        // If user is logged in, redirect
        if (localStorage.getItem("hercules_logged_in") === '1') {
            localStorage.removeItem("hercules_logged_in");
            window.location.href = window.location.href;
            return [true, dash_clientside.no_update, 
                dash_clientside.no_update, dash_clientside.no_update];
        }
        if (n_intervals >= 600) {
            // Disable the timer after 10 minutes
            return [true, true, "Reload Page", email_sent_flag];
        }
        // Countdown logic
        if (email_sent_flag > 0) {
            // Enable button at start and after countdown
            return [false, true, `Resend Email in ${email_sent_flag} seconds`, email_sent_flag - 1];
        }
        // During countdown, disable button and show timer
        return [false, false, "Resend Email", 0];
    }
    """,
    Output("poll_auth", "disabled", allow_duplicate=True),
    Output("login_button", "disabled", allow_duplicate=True),
    Output("login_button", "children", allow_duplicate=True),
    Output("email_sent_flag", "data", allow_duplicate=True),
    Input("poll_auth", "n_intervals"),
    State("email_sent_flag", "data"),
    prevent_initial_call=True,
)


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("logout_button", "n_clicks"),
    prevent_initial_call=True,
)
def update_logout(logout_n_clicks: int | None) -> str:
    """
    Update the logout functionality.

    Parameters:
    - logout_n_clicks (int): The number of times the logout button has been clicked.

    Returns:
    - str: The URL to redirect to after logging out.
    """
    if logout_n_clicks is None:
        raise PreventUpdate
    logger.info("Logout Callback")
    logout_user()
    return "/"
