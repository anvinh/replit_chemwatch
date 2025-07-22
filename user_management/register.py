"""
Module: register
This module provides the layout and callback functions for the user registration page of Hercules.
Includes functionality for user input validation, duplicate email checking, and user registration.
Layout Components:
- `register_layout`: Defines the UI layout for the registration page
                as well as sign-up and back-to-login buttons, error messages, and a success modal.
Callbacks:
- `validate_email(email: str) -> str | bool`: Validates the email format
- `validate_name(name: str) -> str | bool`: Validates the name format
- `is_duplicate_email(email: str) -> bool | int`: Checks if the given email already exists
`                                                    in the 'hercules_users' database table.
- `register_user: Handles the user registration process, including input validation,
                    duplicate email checking, and database insertion.
- `redirect_to_login(n_intervals: int) -> tuple[str, bool]`:
                    Redirects the user to the login page after a specified interval.
"""

import re
from datetime import datetime
from typing import Any
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import dash
from dash import callback, Output, Input, State, dcc
from dash.exceptions import PreventUpdate
from utils.logger_config import logger
from utils.email_templates import (
    new_registration_alert_email_template,
    new_registration_confirmation_template,
)
from layout_functions.email_automation import send_email
from shared_code.connections.pg_service import PostgresService
import os

environment = os.getenv("ENVIRONMENT", "dev")
pg = PostgresService(schema="chemwatch")

register_layout = dmc.Center(
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
                dmc.Text("Please sign up to access Hercules:", className="lead"),
                dmc.TextInput(
                    label="Your name:",
                    placeholder="Name",
                    leftSection=DashIconify(icon="mdi:account"),
                    id="name_box_register",
                    debounce=True,
                ),
                dmc.TextInput(
                    label="Your email:",
                    placeholder="Email",
                    leftSection=DashIconify(icon="mdi:email"),
                    id="email_box_register",
                    debounce=True,
                ),
                dmc.TextInput(
                    label="Request Access:",
                    placeholder="Please provide a reason for access",
                    leftSection=DashIconify(icon="mdi:comment-question"),
                    id="reason_box_register",
                    mt=20,
                ),
                dmc.Alert(
                    "",
                    title="Error!",
                    color="red",
                    hide=True,
                    id="output_alert_register",
                ),
                dmc.Button(
                    "Sign Up",
                    id="sign_up_button",
                    variant="outline",
                    rightSection=DashIconify(icon="mdi:account-plus", color="#4267b2"),
                    className="submit_button",
                    mt=20,
                ),
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
            w=350,
        ),
        dmc.Modal(
            id="modal_register",
            title="Registration Successful",
            children="You have successfully registered! Please wait for approval! "
            "\n Redirecting to the login page...",
            opened=False,
            centered=True,
        ),
        dcc.Interval(
            id="redirect_timer_register", interval=3000, n_intervals=0, disabled=True
        ),
    ],
    m="xl",
    p="xl",
    id="sign_up_container",
)


@callback(
    Output("email_box_register", "error"),
    Input("email_box_register", "value"),
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
    Output("name_box_register", "error"),
    Input("name_box_register", "value"),
    prevent_initial_call=True,
)
def validate_name(name: str) -> str | bool:
    """
    Validates the name format when the focus changes from the name input field.

    Parameters:
    - name (str) : the name entered by user

    Returns:
    - str | bool: A message indicating whether the email is valid or not.
    """

    if not name:
        return "Name cannot be empty."
    name_regex = r"^[a-zA-ZäöüÄÖÜß\s\-']+$"
    if re.match(name_regex, name):
        return False
    return "Invalid name format. Please enter a valid name."


def is_duplicate_email(email: str) -> bool | int:
    """
    Checks if the given email already exists in the 'hercules_users' database table.
    Args:
        email (str): The email address to check for duplication.
    Returns:
        bool | int:
            - True if the email exists in the database.
            - False if the email does not exist in the database.
            - -1 if an error occurs during the database query.
    """

    email_check_query = "SELECT COUNT(*) FROM hercules_users WHERE email = :email"
    email_check_params = {"email": email}

    try:
        email_check_result = pg.do_read(email_check_query, email_check_params)["data"]
        if not email_check_result.empty and email_check_result.iloc[0]["count"] > 0:
            return True
    except Exception as e:
        logger.error(f"Error checking existing email: {e}")
        return -1

    return False


@callback(
    Output("output_alert_register", "children"),
    Output("output_alert_register", "hide"),
    Output("modal_register", "opened"),
    Output("redirect_timer_register", "disabled"),
    Output("sign_up_button", "disabled"),
    Input("sign_up_button", "n_clicks"),
    State("name_box_register", "value"),
    State("name_box_register", "error"),
    State("email_box_register", "value"),
    State("email_box_register", "error"),
    State("reason_box_register", "value"),
    State("url", "href"),
    prevent_initial_call=True,
)
def register_user(
    sign_up_n_clicks: int,
    name: str,
    invalid_name: str | bool,
    email: str,
    invalid_email: str | bool,
    reason: str,
    url: str,
) -> tuple[str, bool, bool, bool]:
    """
    Handles user registration by validating inputs, checking for duplicate emails,
    and inserting the user into the database.

    Parameters:
    - sign_up_n_clicks (int): Number of times the sign-up button is clicked.
    - name (str): User's name.
    - invalid_name (bool|str): Error status for the name input.
    - email (str): User's email.
    - invalid_email (bool|str): Error status for the email input.
    - reason (str): Reason for requesting access.
    - url (str): Current URL, used to generate a link for the admin email.

    Returns:
    - tuple[str, bool, bool, bool]: Alert message, alert visibility, modal state, and timer state.
    """
    if sign_up_n_clicks is None or invalid_name or invalid_email:
        raise PreventUpdate

    if not all([name, email, reason]):
        return _generate_error_response("Please fill all fields.")

    duplicate_check = is_duplicate_email(email)
    if duplicate_check == -1:
        logger.error("Error checking for duplicate email.")
        return _generate_error_response(
            "An error occurred during registration. Please try again later."
        )
    if duplicate_check:
        logger.warning(f"Duplicate email found: {email}")
        return _generate_error_response(
            "This email is already registered. Please use a different email."
        )

    query = """
        INSERT INTO hercules_users (name, email, approval_reason, is_admin, is_approved) 
        VALUES (:name, :email, :approval_reason, :is_admin, :is_approved)
    """
    params = {
        "name": name,
        "email": email,
        "approval_reason": reason,
        "is_approved": False,
        "is_admin": False,
    }

    result = pg.do_insert(query, params)

    if result["success"]:
        logger.info(f"User {email} registered successfully.")

        # User email
        email_message_user = new_registration_confirmation_template.format(
            name=name,
            year=datetime.now().year,
        )
        user_email_flag = send_email(
            from_list="tmu-hercules-risk-monitoring@agcs.allianz.com",
            to_list=email,
            mail_subject="Hercules Registration Confirmation",
            mail_body=email_message_user,
            logo_path="assets/hercules_logo_ai_factory_small.png",
        )

        # Admin email
        base_url = url.rsplit("/", 1)[0]
        admin_panel_link = f"{base_url}/admin_panel"
        email_message_admin = new_registration_alert_email_template.format(
            email=email,
            name=name,
            reason=reason,
            admin_panel_link=admin_panel_link,
            year=datetime.now().year,
        )

        query = """
            SELECT email FROM hercules_users WHERE is_admin = True
        """
        admin_emails = pg.do_read(query)["data"]
        if admin_emails.empty:
            logger.error("No admin emails found for sending registration alert.")
            return _generate_error_response(
                "An error occurred during registration. Please try again later."
            )
        admin_email_list = ", ".join(admin_emails["email"].tolist())

        admin_email_flag = send_email(
            from_list="tmu-hercules-risk-monitoring@agcs.allianz.com",
            to_list=admin_email_list,
            mail_subject="New User Registration on Hercules",
            mail_body=email_message_admin,
        )
        if user_email_flag and admin_email_flag:
            logger.info(f"New registration email sent to {email} and admins")
            return "", True, True, False, True

        logger.error(f"Error sending new registration email to {email}")
        return "", True, True, False, True

    logger.error(f"Registration error: {result["message"]}")
    return _generate_error_response(
        "An error occurred during registration. Please try again later."
    )


def _generate_error_response(message: str) -> tuple[str, bool, Any, Any, Any]:
    """
    Generates an error response for the registration process.

    Args:
        message (str): The error message to display.

    Returns:
        tuple: A tuple containing the error message, alert visibility, and modal state.
    """
    return message, False, dash.no_update, dash.no_update, dash.no_update


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Output("redirect_timer_register", "disabled", allow_duplicate=True),
    Input("redirect_timer_register", "n_intervals"),
    prevent_initial_call=True,
)
def redirect_to_login(n_intervals: int) -> tuple[str, bool]:
    """
    Redirects to the login page after a specified interval.

    Args:
        n_intervals (int): The number of intervals that have passed.

    Returns:
        tuple: A tuple containing the redirect URL and whether to disable the timer.
    """
    if n_intervals > 0:
        return "/login", True
    raise PreventUpdate
