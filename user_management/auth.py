"""
Module: user_management.auth
It includes user loading, login manager initialization, and a user class definition.
- `User`: Represents a us er in the system with attributes such as user_id, name, email, admin_access, and approved.
- `load_user(user_id: int) -> User | None`: Loads a user from the database based on the provided user ID.
- `init_login_manager(server)`: Configures the login manager for the given server instance (e.g., a Flask app).
Classes:
    User: Represents a user in the system with attributes such as user_id, name, email, admin_access, and approved.
"""

from flask_login import (
    LoginManager,
    UserMixin,
)
from utils.logger_config import logger
from shared_code.connections.pg_service import PostgresService
import os

environment = os.getenv("ENVIRONMENT", "dev")
pg = PostgresService(schema="chemwatch")

login_manager = LoginManager()
login_manager.login_view = "login"


class User(UserMixin):
    """
    Represents a user in the system.

    Attributes:
        user_id (int): The user_id of the user.
        name (str): The name of the user.
        email (str): The email of the user.
        admin_access (bool): Whether the user has admin access.
        approved (bool): Whether the user is approved.
    """

    def __init__(
        self, user_id: int, name: str, email: str, admin_access: bool, approved: bool
    ) -> None:
        self.user_id = user_id
        self.name = name
        self.email = email
        self.admin_access = admin_access
        self.approved = approved

    def get_id(self) -> int:
        """
        Returns the unique identifier for the user.

        Returns:
            int: The user_id of the user.
        """
        return self.user_id


@login_manager.user_loader
def load_user(user_id: int) -> User | None:
    """
    Loads a user from the database based on the provided user ID.
    Args:
        user_id (int): The unique identifier of the user to be loaded.
    Returns:
        User | None: A User object if the user is found, otherwise None.
    Raises:
        Exception: Logs an error and returns None if an exception occurs during the database query.
    """
    query = "SELECT * FROM hercules_users WHERE user_id = :user_id"
    params = {"user_id": user_id}

    try:
        result = pg.do_read(query, params)["data"]

        if not result.empty:
            user_record = result.iloc[0]
            return User(
                user_id=int(user_record["user_id"]),
                name=user_record["name"],
                email=user_record["email"],
                admin_access=user_record["is_admin"],
                approved=user_record["is_approved"],
            )
        return None

    except Exception as e:
        logger.error(f"Error loading user {user_id}: {e}")
        return None


def init_login_manager(server):
    """
    Initialize the login manager for the given server.

    This function sets up the login manager by configuring the server's
    secret key and initializing the login manager with the server instance.

    Args:
        server: The server instance (e.g., a Flask app) to configure the
                login manager for.
    """
    # TODO: move to secrets
    server.secret_key = "your_secret_key"
    login_manager.init_app(server)
    server.config["PERMANENT_SESSION_LIFETIME"] = 36 * 60 * 60  # in seconds
    server.config["SESSION_COOKIE_NAME"] = "hercules_session"
    server.config["SESSION_COOKIE_HTTPONLY"] = True
    server.config["SESSION_COOKIE_SECURE"] = True
    server.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    return server
