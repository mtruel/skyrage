"""Test player deletion logic."""

from typing import cast

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import delete_player
from db import Base, GameDB, PlayerDB, RoundDB, get_db_session


@pytest.fixture
def test_engine():
    """Create a test database engine with in-memory SQLite."""
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


@pytest.fixture(autouse=True)
def mock_db_session(test_session_maker, monkeypatch):
    """Mock get_db_session to use test database for all tests in this module."""

    def mock_get_db_session():
        return test_session_maker()

    monkeypatch.setattr("api.get_db_session", mock_get_db_session)
    monkeypatch.setattr(
        "src.tests.test_player_deletion.get_db_session", mock_get_db_session
    )


class TestPlayerDeletion:
    """Test cases for player deletion endpoint."""

    def test_delete_player_without_games(self):
        """Test that a player without game history can be deleted."""
        session = get_db_session()
        try:
            # Create a player
            player = PlayerDB(username="test_player", surname="Test")
            session.add(player)
            session.commit()

            # Delete should succeed
            delete_player("test_player")

            # Verify player is gone
            deleted = session.query(PlayerDB).filter_by(username="test_player").first()
            assert deleted is None

        finally:
            # Cleanup
            session.query(PlayerDB).filter_by(username="test_player").delete()
            session.commit()
            session.close()

    def test_delete_player_with_round_participation(self):
        """Test that a player who participated in a round cannot be deleted."""
        session = get_db_session()
        game = None
        try:
            # Create players
            p1 = PlayerDB(username="player1", surname="One")
            p2 = PlayerDB(username="player2", surname="Two")
            session.add_all([p1, p2])
            session.commit()

            # Create a game
            game = GameDB(player_usernames=["player1", "player2"])
            session.add(game)
            session.commit()

            # Create a round where player1 participated
            round1 = RoundDB(
                game_id=game.id,
                round_number=1,
                player_raw_scores={"player1": 10, "player2": 15},
                round_ender_username="player2",
            )
            session.add(round1)
            session.commit()

            # Try to delete player1 - should fail
            with pytest.raises(HTTPException) as exc_info:
                delete_player("player1")

            exc = cast(HTTPException, exc_info.value)
            assert exc.status_code == 400
            # Should now catch it at the game level
            assert "participated in games" in exc.detail

            # Verify player1 still exists
            still_exists = session.query(PlayerDB).filter_by(username="player1").first()
            assert still_exists is not None

        finally:
            # Cleanup
            if game:
                session.query(RoundDB).filter_by(game_id=game.id).delete()
                session.query(GameDB).filter_by(id=game.id).delete()
            session.query(PlayerDB).filter_by(username="player1").delete()
            session.query(PlayerDB).filter_by(username="player2").delete()
            session.commit()
            session.close()

    def test_delete_player_as_round_ender(self):
        """Test that a player who ended a round cannot be deleted."""
        session = get_db_session()
        game = None
        try:
            # Create players
            p1 = PlayerDB(username="player1", surname="One")
            p2 = PlayerDB(username="player2", surname="Two")
            session.add_all([p1, p2])
            session.commit()

            # Create a game
            game = GameDB(player_usernames=["player1", "player2"])
            session.add(game)
            session.commit()

            # Create a round where player1 ended the round
            round1 = RoundDB(
                game_id=game.id,
                round_number=1,
                player_raw_scores={"player1": 10, "player2": 15},
                round_ender_username="player1",
            )
            session.add(round1)
            session.commit()

            # Try to delete player1 - should fail
            with pytest.raises(HTTPException) as exc_info:
                delete_player("player1")

            # Should catch it at the game level first
            exc = cast(HTTPException, exc_info.value)
            assert exc.status_code == 400
            assert "participated in games" in exc.detail

        finally:
            # Cleanup
            if game:
                session.query(RoundDB).filter_by(game_id=game.id).delete()
                session.query(GameDB).filter_by(id=game.id).delete()
            session.query(PlayerDB).filter_by(username="player1").delete()
            session.query(PlayerDB).filter_by(username="player2").delete()
            session.commit()
            session.close()

    def test_delete_player_in_game_without_rounds(self):
        """Test that a player in a game (even without rounds) cannot be deleted."""
        session = get_db_session()
        game = None
        try:
            # Create players
            p1 = PlayerDB(username="player1", surname="One")
            p2 = PlayerDB(username="player2", surname="Two")
            session.add_all([p1, p2])
            session.commit()

            # Create a game with no rounds yet
            game = GameDB(player_usernames=["player1", "player2"])
            session.add(game)
            session.commit()

            # Try to delete player1 - should fail
            with pytest.raises(HTTPException) as exc_info:
                delete_player("player1")

            exc = cast(HTTPException, exc_info.value)
            assert exc.status_code == 400
            assert "participated in games" in exc.detail

            # Verify player1 still exists
            still_exists = session.query(PlayerDB).filter_by(username="player1").first()
            assert still_exists is not None

        finally:
            # Cleanup
            if game:
                session.query(GameDB).filter_by(id=game.id).delete()
            session.query(PlayerDB).filter_by(username="player1").delete()
            session.query(PlayerDB).filter_by(username="player2").delete()
            session.commit()
            session.close()
