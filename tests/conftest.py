import os
import tempfile
import pytest
from app import create_app
from config import TestConfig
import database


@pytest.fixture
def app():
    """Create and configure a test Flask application with an isolated temporary database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    class CustomTestConfig(TestConfig):
        DATABASE_PATH = db_path
        TESTING = True
        GEMINI_API_KEY = ""  # Force demo mode during automated tests

    flask_app = create_app(CustomTestConfig)

    with flask_app.app_context():
        database.init_db()

    yield flask_app

    # Teardown: close and remove temporary test database
    try:
        os.close(db_fd)
        if os.path.exists(db_path):
            os.remove(db_path)
    except OSError:
        pass


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()
