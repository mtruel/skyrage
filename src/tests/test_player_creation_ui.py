"""Tests for player creation via web interface."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db import Base
from main import app


@pytest.fixture
def test_engine():
    """Create a test database engine with check_same_thread=False for SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session_maker(test_engine):
    """Create a session maker for tests."""
    return sessionmaker(bind=test_engine)


@pytest.fixture
def test_app(test_engine, test_session_maker, monkeypatch):
    """Create a test client with a test database."""

    def mock_get_db_session():
        return test_session_maker()

    monkeypatch.setattr("api.get_db_session", mock_get_db_session)
    monkeypatch.setattr("main.get_db_session", mock_get_db_session)
    client = TestClient(app)
    return client


@pytest.fixture
def test_session(test_session_maker):
    """Create a test session for direct database manipulation in tests."""
    session = test_session_maker()
    yield session
    session.close()


def test_create_player_returns_html_row(test_app):
    """Test that creating a player returns an HTML table row."""
    response = test_app.post(
        "/player/create",
        data={"username": "testuser", "surname": "TestSurname"},
    )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    # Check that the response contains expected HTML elements
    html = response.text
    assert "player-row-testuser" in html
    assert "testuser" in html
    assert "TestSurname" in html
    assert 'hx-post="/player/update"' in html
    assert 'hx-delete="/api/players/testuser"' in html


def test_create_player_without_surname(test_app):
    """Test creating a player without a surname."""
    response = test_app.post(
        "/player/create",
        data={"username": "nosurname", "surname": ""},
    )
    assert response.status_code == 200

    html = response.text
    assert "player-row-nosurname" in html
    assert "nosurname" in html
    assert 'placeholder="(no surname)"' in html


def test_create_duplicate_player_fails(test_app):
    """Test that creating a duplicate player returns an error."""
    # Create first player
    response1 = test_app.post(
        "/player/create",
        data={"username": "duplicate", "surname": "First"},
    )
    assert response1.status_code == 200

    # Try to create duplicate
    response2 = test_app.post(
        "/player/create",
        data={"username": "duplicate", "surname": "Second"},
    )
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


def test_create_player_empty_username_fails(test_app):
    """Test that creating a player with empty username fails."""
    response = test_app.post(
        "/player/create",
        data={"username": "   ", "surname": "Test"},
    )
    assert response.status_code == 400
    assert "required" in response.json()["detail"].lower()
