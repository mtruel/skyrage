"""Tests for player creation via new game interface."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db import Base, PlayerDB
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


def test_new_game_page_player_creation_returns_html(test_app, test_session):
    """Test that creating a player from new game page returns HTML."""
    response = test_app.post(
        "/player/create",
        data={"username": "newgameuser", "surname": "NewGameSurname"},
    )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    # Verify player was created in database
    player = test_session.query(PlayerDB).filter_by(username="newgameuser").first()
    assert player is not None
    assert player.surname == "NewGameSurname"


def test_new_game_page_loads_with_new_player(test_app, test_session):
    """Test that new game page shows newly created players."""
    # Create a player
    test_app.post(
        "/player/create",
        data={"username": "testplayer", "surname": "TestSurname"},
    )

    # Load new game page
    response = test_app.get("/game/new")
    assert response.status_code == 200
    assert "testplayer" in response.text
    assert "TestSurname" in response.text
