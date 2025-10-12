"""Simple tests for database models and operations."""

import pytest
from sqlalchemy.orm import sessionmaker

from db import Base, GameDB, PlayerDB, RoundDB, create_engine


@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    # Create engine for in-memory database
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()

    yield session

    session.close()
    engine.dispose()


class TestPlayerDB:
    """Simple tests for PlayerDB model."""

    def test_create_player(self, test_db):
        """Test creating a player in the database."""
        player = PlayerDB(username="alice123", surname="Johnson")
        test_db.add(player)
        test_db.commit()

        # Retrieve and verify
        retrieved = test_db.query(PlayerDB).filter_by(username="alice123").first()
        assert retrieved is not None
        assert retrieved.username == "alice123"
        assert retrieved.surname == "Johnson"

    def test_player_unique_username(self, test_db):
        """Test that username must be unique."""
        player1 = PlayerDB(username="bob", surname="Smith")
        test_db.add(player1)
        test_db.commit()
        test_db.expunge(player1)  # Remove from session to avoid identity conflict

        # Try to add another player with same username
        player2 = PlayerDB(username="bob", surname="Jones")
        test_db.add(player2)

        with pytest.raises(Exception):  # Will raise IntegrityError
            test_db.commit()

    def test_query_all_players(self, test_db):
        """Test querying all players."""
        players = [
            PlayerDB(username="alice", surname="Johnson"),
            PlayerDB(username="bob", surname="Smith"),
            PlayerDB(username="charlie", surname="Brown"),
        ]
        for player in players:
            test_db.add(player)
        test_db.commit()

        all_players = test_db.query(PlayerDB).all()
        assert len(all_players) == 3


class TestGameDB:
    """Simple tests for GameDB model."""

    def test_create_game(self, test_db):
        """Test creating a game in the database."""
        game = GameDB(player_usernames=["alice", "bob", "charlie"])
        test_db.add(game)
        test_db.commit()

        # Retrieve and verify
        retrieved = test_db.query(GameDB).first()
        assert retrieved is not None
        assert retrieved.player_usernames == ["alice", "bob", "charlie"]
        assert retrieved.finished_at is None

    def test_game_with_rounds(self, test_db):
        """Test creating a game with rounds."""
        # Create a game
        game = GameDB(player_usernames=["alice", "bob"])
        test_db.add(game)
        test_db.commit()

        # Add rounds to the game
        round1 = RoundDB(
            game_id=game.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 15},
            round_ender_username="alice",
        )
        round2 = RoundDB(
            game_id=game.id,
            round_number=2,
            player_raw_scores={"alice": 8, "bob": 12},
            round_ender_username="bob",
        )
        test_db.add(round1)
        test_db.add(round2)
        test_db.commit()

        # Retrieve and verify
        retrieved_game = test_db.query(GameDB).first()
        assert len(retrieved_game.rounds) == 2
        assert retrieved_game.rounds[0].round_number == 1
        assert retrieved_game.rounds[1].round_number == 2


class TestRoundDB:
    """Simple tests for RoundDB model."""

    def test_create_round(self, test_db):
        """Test creating a round in the database."""
        # First create a game
        game = GameDB(player_usernames=["alice", "bob"])
        test_db.add(game)
        test_db.commit()

        # Create a round
        round_obj = RoundDB(
            game_id=game.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 15},
            round_ender_username="alice",
        )
        test_db.add(round_obj)
        test_db.commit()

        # Retrieve and verify
        retrieved = test_db.query(RoundDB).first()
        assert retrieved is not None
        assert retrieved.round_number == 1
        assert retrieved.player_raw_scores == {"alice": 10, "bob": 15}
        assert retrieved.round_ender_username == "alice"

    def test_round_json_serialization(self, test_db):
        """Test that player scores are properly serialized to JSON."""
        game = GameDB(player_usernames=["alice", "bob", "charlie"])
        test_db.add(game)
        test_db.commit()

        scores = {"alice": -5, "bob": 10, "charlie": 20}
        round_obj = RoundDB(
            game_id=game.id,
            round_number=1,
            player_raw_scores=scores,
            round_ender_username="bob",
        )
        test_db.add(round_obj)
        test_db.commit()

        # Retrieve and verify deserialization
        retrieved = test_db.query(RoundDB).first()
        assert retrieved.player_raw_scores == scores
        assert retrieved.player_raw_scores["alice"] == -5


class TestDatabaseRelationships:
    """Simple tests for database relationships."""

    def test_game_round_cascade_delete(self, test_db):
        """Test that deleting a game deletes its rounds."""
        game = GameDB(player_usernames=["alice", "bob"])
        test_db.add(game)
        test_db.commit()

        round1 = RoundDB(
            game_id=game.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 15},
            round_ender_username="alice",
        )
        test_db.add(round1)
        test_db.commit()

        # Verify round exists
        assert test_db.query(RoundDB).count() == 1

        # Delete game
        test_db.delete(game)
        test_db.commit()

        # Verify round is also deleted
        assert test_db.query(RoundDB).count() == 0

    def test_multiple_games(self, test_db):
        """Test creating multiple games."""
        game1 = GameDB(player_usernames=["alice", "bob"])
        game2 = GameDB(player_usernames=["charlie", "dave"])
        test_db.add_all([game1, game2])
        test_db.commit()

        all_games = test_db.query(GameDB).all()
        assert len(all_games) == 2
