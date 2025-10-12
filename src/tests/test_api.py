"""Tests for API endpoints in api.py."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db import Base, GameDB, PlayerDB, RoundDB
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


class TestPlayerEndpoints:
    """Tests for player CRUD endpoints."""

    def test_create_player_new(self, test_app):
        """Test creating a new player."""
        response = test_app.post(
            "/api/players",
            json={"username": "alice", "surname": "Johnson"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "alice"
        assert data["surname"] == "Johnson"
        assert "created_at" in data

    def test_create_player_existing(self, test_app, test_session):
        """Test creating a player that already exists returns 200."""
        # Create player first
        player = PlayerDB(username="bob", surname="Smith")
        test_session.add(player)
        test_session.commit()

        # Try to create again
        response = test_app.post(
            "/api/players",
            json={"username": "bob", "surname": "Different"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "bob"
        # Original surname is preserved
        assert data["surname"] == "Smith"

    def test_create_player_no_surname(self, test_app):
        """Test creating a player without surname."""
        response = test_app.post(
            "/api/players",
            json={"username": "charlie"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "charlie"
        assert data["surname"] is None

    def test_list_players_empty(self, test_app):
        """Test listing players when none exist."""
        response = test_app.get("/api/players")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_players_multiple(self, test_app, test_session):
        """Test listing multiple players."""
        players = [
            PlayerDB(username="alice", surname="Johnson"),
            PlayerDB(username="bob", surname="Smith"),
            PlayerDB(username="charlie", surname=None),
        ]
        for player in players:
            test_session.add(player)
        test_session.commit()

        response = test_app.get("/api/players")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        usernames = {p["username"] for p in data}
        assert usernames == {"alice", "bob", "charlie"}

    def test_get_player_exists(self, test_app, test_session):
        """Test getting a specific player that exists."""
        player = PlayerDB(username="alice", surname="Johnson")
        test_session.add(player)
        test_session.commit()

        response = test_app.get("/api/players/alice")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "alice"
        assert data["surname"] == "Johnson"

    def test_get_player_not_found(self, test_app):
        """Test getting a player that doesn't exist."""
        response = test_app.get("/api/players/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_player_surname(self, test_app, test_session):
        """Test updating a player's surname."""
        player = PlayerDB(username="alice", surname="Johnson")
        test_session.add(player)
        test_session.commit()

        response = test_app.put(
            "/api/players/alice",
            json={"username": "alice", "surname": "Williams"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["surname"] == "Williams"

        # Verify in database
        updated = test_session.query(PlayerDB).filter_by(username="alice").first()
        assert updated.surname == "Williams"

    def test_update_player_not_found(self, test_app):
        """Test updating a player that doesn't exist."""
        response = test_app.put(
            "/api/players/nonexistent",
            json={"username": "nonexistent", "surname": "Test"},
        )
        assert response.status_code == 404

    def test_delete_player_success(self, test_app, test_session):
        """Test deleting a player with no game associations."""
        player = PlayerDB(username="alice", surname="Johnson")
        test_session.add(player)
        test_session.commit()

        response = test_app.delete("/api/players/alice")
        assert response.status_code == 204

        # Verify deleted
        deleted = test_session.query(PlayerDB).filter_by(username="alice").first()
        assert deleted is None

    def test_delete_player_not_found(self, test_app):
        """Test deleting a player that doesn't exist."""
        response = test_app.delete("/api/players/nonexistent")
        assert response.status_code == 404

    def test_delete_player_in_game(self, test_app, test_session):
        """Test deleting a player who is in a game."""
        player = PlayerDB(username="alice", surname="Johnson")
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(player)
        test_session.add(game)
        test_session.commit()

        response = test_app.delete("/api/players/alice")
        assert response.status_code == 400
        assert "participated in games" in response.json()["detail"].lower()

    def test_delete_player_in_round_scores(self, test_app, test_session):
        """Test deleting a player who has scores in rounds."""
        player = PlayerDB(username="alice", surname="Johnson")
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(player)
        test_session.add(game)
        test_session.commit()

        round_obj = RoundDB(
            game_id=game.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 15},
            round_ender_username="bob",
        )
        test_session.add(round_obj)
        test_session.commit()

        response = test_app.delete("/api/players/alice")
        assert response.status_code == 400
        assert "participated in games" in response.json()["detail"].lower()

    def test_delete_player_ended_round(self, test_app, test_session):
        """Test deleting a player who ended a round."""
        player = PlayerDB(username="alice", surname="Johnson")
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(player)
        test_session.add(game)
        test_session.commit()

        round_obj = RoundDB(
            game_id=game.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 15},
            round_ender_username="alice",
        )
        test_session.add(round_obj)
        test_session.commit()

        response = test_app.delete("/api/players/alice")
        assert response.status_code == 400
        assert "participated in games" in response.json()["detail"].lower()

    def test_delete_dangling_players(self, test_app, test_session):
        """Test deleting all players not associated with games."""
        # Create mix of players
        players = [
            PlayerDB(username="alice", surname="Johnson"),  # in game
            PlayerDB(username="bob", surname="Smith"),  # in game
            PlayerDB(username="charlie", surname="Brown"),  # dangling
            PlayerDB(username="david", surname="Jones"),  # dangling
        ]
        for player in players:
            test_session.add(player)
        test_session.commit()

        # Create game with alice and bob
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()

        response = test_app.delete("/api/dangling_players")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 2
        assert set(data["deleted_usernames"]) == {"charlie", "david"}
        assert data["total_players"] == 4
        assert data["protected_players"] == 2

        # Verify charlie and david are gone
        remaining = test_session.query(PlayerDB).all()
        assert len(remaining) == 2
        assert {p.username for p in remaining} == {"alice", "bob"}


class TestGameEndpoints:
    """Tests for game CRUD endpoints."""

    def test_create_game(self, test_app, test_session):
        """Test creating a new game."""
        response = test_app.post(
            "/api/games",
            json={"player_usernames": ["alice", "bob", "charlie"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["player_usernames"] == ["alice", "bob", "charlie"]
        assert data["finished_at"] is None
        assert data["round_count"] == 0
        assert "id" in data
        assert "created_at" in data

        # Verify players were auto-created
        players = test_session.query(PlayerDB).all()
        assert len(players) == 3

    def test_create_game_existing_players(self, test_app, test_session):
        """Test creating a game with existing players."""
        # Create players first
        players = [
            PlayerDB(username="alice", surname="Johnson"),
            PlayerDB(username="bob", surname="Smith"),
        ]
        for player in players:
            test_session.add(player)
        test_session.commit()

        response = test_app.post(
            "/api/games",
            json={"player_usernames": ["alice", "bob"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["player_usernames"] == ["alice", "bob"]

        # Verify no duplicate players created
        all_players = test_session.query(PlayerDB).all()
        assert len(all_players) == 2

    def test_list_games_empty(self, test_app):
        """Test listing games when none exist."""
        response = test_app.get("/api/games")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_games_multiple(self, test_app, test_session):
        """Test listing multiple games."""
        games = [
            GameDB(player_usernames=["alice", "bob"]),
            GameDB(player_usernames=["charlie", "david"]),
            GameDB(player_usernames=["eve", "frank", "grace"]),
        ]
        for game in games:
            test_session.add(game)
        test_session.commit()

        response = test_app.get("/api/games")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_list_games_with_limit(self, test_app, test_session):
        """Test listing games with limit parameter."""
        # Create 5 games
        for i in range(5):
            game = GameDB(player_usernames=[f"player{i}", f"player{i + 10}"])
            test_session.add(game)
        test_session.commit()

        response = test_app.get("/api/games?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_game_exists(self, test_app, test_session):
        """Test getting a specific game that exists."""
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()

        response = test_app.get(f"/api/games/{game.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game.id
        assert data["player_usernames"] == ["alice", "bob"]

    def test_get_game_not_found(self, test_app):
        """Test getting a game that doesn't exist."""
        response = test_app.get("/api/games/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_end_game(self, test_app, test_session):
        """Test ending a game."""
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()
        assert game.finished_at is None

        response = test_app.put(f"/api/games/{game.id}/end")
        assert response.status_code == 200
        data = response.json()
        assert data["finished_at"] is not None

        # Verify in database
        test_session.refresh(game)
        assert game.finished_at is not None

    def test_end_game_already_finished(self, test_app, test_session):
        """Test ending a game that's already finished."""
        from datetime import UTC, datetime

        game = GameDB(player_usernames=["alice", "bob"])
        game.finished_at = datetime.now(UTC)
        test_session.add(game)
        test_session.commit()

        response = test_app.put(f"/api/games/{game.id}/end")
        assert response.status_code == 400
        assert "already finished" in response.json()["detail"].lower()

    def test_end_game_not_found(self, test_app):
        """Test ending a game that doesn't exist."""
        response = test_app.put("/api/games/999/end")
        assert response.status_code == 404


class TestRoundEndpoints:
    """Tests for round creation and listing endpoints."""

    def test_create_round(self, test_app, test_session):
        """Test creating a round for a game."""
        game = GameDB(player_usernames=["alice", "bob", "charlie"])
        test_session.add(game)
        test_session.commit()

        response = test_app.post(
            f"/api/games/{game.id}/rounds",
            json={
                "player_raw_scores": {"alice": 10, "bob": 15, "charlie": 20},
                "round_ender_username": "bob",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["game_id"] == game.id
        assert data["round_number"] == 1
        assert data["player_raw_scores"] == {"alice": 10, "bob": 15, "charlie": 20}
        assert data["round_ender_username"] == "bob"
        assert "id" in data
        assert "created_at" in data

    def test_create_round_game_not_found(self, test_app):
        """Test creating a round for non-existent game."""
        response = test_app.post(
            "/api/games/999/rounds",
            json={
                "player_raw_scores": {"alice": 10},
                "round_ender_username": "alice",
            },
        )
        assert response.status_code == 404

    def test_create_round_finished_game(self, test_app, test_session):
        """Test creating a round for a finished game."""
        from datetime import UTC, datetime

        game = GameDB(player_usernames=["alice", "bob"])
        game.finished_at = datetime.now(UTC)
        test_session.add(game)
        test_session.commit()

        response = test_app.post(
            f"/api/games/{game.id}/rounds",
            json={
                "player_raw_scores": {"alice": 10, "bob": 15},
                "round_ender_username": "alice",
            },
        )
        assert response.status_code == 400
        assert "finished game" in response.json()["detail"].lower()

    def test_create_round_player_not_in_game(self, test_app, test_session):
        """Test creating a round with a player not in the game."""
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()

        response = test_app.post(
            f"/api/games/{game.id}/rounds",
            json={
                "player_raw_scores": {"alice": 10, "charlie": 20},
                "round_ender_username": "alice",
            },
        )
        assert response.status_code == 400
        assert "not in this game" in response.json()["detail"].lower()

    def test_create_round_ender_not_in_game(self, test_app, test_session):
        """Test creating a round with round ender not in the game."""
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()

        response = test_app.post(
            f"/api/games/{game.id}/rounds",
            json={
                "player_raw_scores": {"alice": 10, "bob": 15},
                "round_ender_username": "charlie",
            },
        )
        assert response.status_code == 400
        assert "not in this game" in response.json()["detail"].lower()

    def test_create_multiple_rounds(self, test_app, test_session):
        """Test creating multiple rounds increments round number."""
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()

        # Create first round
        response1 = test_app.post(
            f"/api/games/{game.id}/rounds",
            json={
                "player_raw_scores": {"alice": 10, "bob": 15},
                "round_ender_username": "alice",
            },
        )
        assert response1.status_code == 201
        assert response1.json()["round_number"] == 1

        # Create second round
        response2 = test_app.post(
            f"/api/games/{game.id}/rounds",
            json={
                "player_raw_scores": {"alice": 20, "bob": 25},
                "round_ender_username": "bob",
            },
        )
        assert response2.status_code == 201
        assert response2.json()["round_number"] == 2

    def test_list_rounds_empty(self, test_app, test_session):
        """Test listing rounds for a game with no rounds."""
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()

        response = test_app.get(f"/api/games/{game.id}/rounds")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_rounds_multiple(self, test_app, test_session):
        """Test listing multiple rounds for a game."""
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()

        rounds = [
            RoundDB(
                game_id=game.id,
                round_number=1,
                player_raw_scores={"alice": 10, "bob": 15},
                round_ender_username="alice",
            ),
            RoundDB(
                game_id=game.id,
                round_number=2,
                player_raw_scores={"alice": 20, "bob": 25},
                round_ender_username="bob",
            ),
        ]
        for round_obj in rounds:
            test_session.add(round_obj)
        test_session.commit()

        response = test_app.get(f"/api/games/{game.id}/rounds")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["round_number"] == 1
        assert data[1]["round_number"] == 2

    def test_list_rounds_game_not_found(self, test_app):
        """Test listing rounds for non-existent game."""
        response = test_app.get("/api/games/999/rounds")
        assert response.status_code == 404
