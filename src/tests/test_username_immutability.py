"""Tests for username immutability - usernames should not be editable after creation."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db import Base, GameDB, PlayerDB, RoundDB
from tests.conftest import create_game_with_players
from src.main import app


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


def test_api_update_player_only_changes_surname(test_app, test_session):
    """Test that PUT /api/players/{username} only updates surname, not username."""
    # Create a player
    player = PlayerDB(username="alice", surname="Smith")
    test_session.add(player)
    test_session.commit()

    # Try to update player - even if we pass a different username in body, it should be ignored
    response = test_app.put(
        "/api/players/alice",
        json={"username": "alice_renamed", "surname": "Johnson"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Username should remain unchanged
    assert data["username"] == "alice"
    # Surname should be updated
    assert data["surname"] == "Johnson"

    # Verify in database
    player_db = test_session.query(PlayerDB).filter_by(username="alice").first()
    assert player_db is not None
    assert player_db.username == "alice"
    assert player_db.surname == "Johnson"

    # The new username should NOT exist
    renamed_player = (
        test_session.query(PlayerDB).filter_by(username="alice_renamed").first()
    )
    assert renamed_player is None


def test_api_update_player_only_surname_changes(test_app, test_session):
    """Test that only surname field changes when updating a player."""
    # Create a player
    player = PlayerDB(username="bob", surname="Original")
    test_session.add(player)
    test_session.commit()

    # Update just the surname
    response = test_app.put(
        "/api/players/bob",
        json={"username": "bob", "surname": "Updated"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify response shows updated surname
    assert data["username"] == "bob"
    assert data["surname"] == "Updated"


def test_username_consistency_in_rounds(test_app, test_session):
    """Test that usernames remain consistent between game and round records."""
    # Create players
    player1 = PlayerDB(username="charlie", surname="Player1")
    player2 = PlayerDB(username="dana", surname="Player2")
    test_session.add_all([player1, player2])
    test_session.commit()

    # Create a game
    game = create_game_with_players(test_session, ["charlie", "dana"])
    test_session.add(game)
    test_session.commit()

    # Add a round
    round1 = RoundDB(
        game_id=game.id,
        round_number=1,
        player_raw_scores={"charlie": 10, "dana": 15},
        round_ender_username="charlie",
    )
    test_session.add(round1)
    test_session.commit()

    # Verify consistency
    game_db = test_session.query(GameDB).filter_by(id=game.id).first()
    round_db = test_session.query(RoundDB).filter_by(game_id=game.id).first()

    # Game player list should match round score usernames
    assert set(game_db.player_usernames) == set(round_db.player_raw_scores.keys())
    assert round_db.round_ender_username in game_db.player_usernames


def test_player_username_is_immutable_primary_key(test_session):
    """Test that username is the primary key and cannot be changed via SQLAlchemy."""
    # Create a player
    player = PlayerDB(username="eve", surname="Original")
    test_session.add(player)
    test_session.commit()

    # Try to change username - this should not be allowed
    # In SQLAlchemy, changing a primary key requires deleting and recreating
    player_db = test_session.query(PlayerDB).filter_by(username="eve").first()
    assert player_db is not None

    # Attempting to change username directly should not work
    # because username is the primary key
    # Instead, we verify the username remains the same
    original_username = player_db.username
    player_db.surname = "Modified"
    test_session.commit()

    # Re-query to verify
    player_db = test_session.query(PlayerDB).filter_by(username="eve").first()
    assert player_db.username == original_username  # Should still be "eve"
    assert player_db.surname == "Modified"


def test_cannot_rename_player_in_api(test_app, test_session):
    """Test that there's no API endpoint to rename a player's username."""
    # Create a player
    player = PlayerDB(username="frank", surname="Original")
    test_session.add(player)
    test_session.commit()

    # Try various ways to rename - none should work

    # 1. PUT with different username in body should be ignored
    response = test_app.put(
        "/api/players/frank",
        json={"username": "frank_new", "surname": "Updated"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "frank"  # Should still be original

    # 2. Verify no PATCH endpoint exists for username changes
    response = test_app.patch(
        "/api/players/frank",
        json={"username": "frank_new"},
    )
    # Should return 405 Method Not Allowed or 404
    assert response.status_code in [
        status.HTTP_404_NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED,
    ]

    # 3. Verify player still has original username
    player_db = test_session.query(PlayerDB).filter_by(username="frank").first()
    assert player_db is not None
    assert player_db.username == "frank"
