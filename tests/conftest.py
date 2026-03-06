import pytest
import os
import sqlite3
from app import app as flask_app
from database import init_db, DATABASE_NAME
import database
import werkzeug.urls
import urllib.parse

# Fix for pytest-flask compatibility with Werkzeug 3.0+
if not hasattr(werkzeug.urls, 'url_quote'):
    werkzeug.urls.url_quote = urllib.parse.quote

if not hasattr(werkzeug, '__version__'):
    import importlib.metadata
    try:
        werkzeug.__version__ = importlib.metadata.version("werkzeug")
    except importlib.metadata.PackageNotFoundError:
        werkzeug.__version__ = "3.0.1" # Fallback

@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture(autouse=True)
def test_db(monkeypatch, tmp_path):
    """Set up a fresh database for each test."""
    db_file = tmp_path / "test_attendance.db"
    # Monkeypatch the database name in the database module
    monkeypatch.setattr(database, "DATABASE_NAME", str(db_file))
    
    # Initialize the database schema
    init_db()
    
    yield db_file
    
    # No explicit cleanup needed as tmp_path is managed by pytest
