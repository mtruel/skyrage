"""Tests for domain model conversion from database models."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base, GameDB, PlayerDB, RoundDB
from model import Game, Player, Round


@pytest.fixture
def test_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()
    yield session
    session.close()


class TestPlayerFromDB:
    """Tests for Player.from_db() conversion."""

    def test_from_db_with_surname(self, test_session):
        """Test converting PlayerDB with surname to Player."""
        player_db = PlayerDB(username="alice", surname="Johnson")
        test_session.add(player_db)
        test_session.commit()

        player = Player.from_db(player_db)
        assert player.username == "alice"
        assert player.surname == "Johnson"

    def test_from_db_without_surname(self, test_session):
        """Test converting PlayerDB without surname to Player."""
        player_db = PlayerDB(username="bob", surname=None)
        test_session.add(player_db)
        test_session.commit()

        player = Player.from_db(player_db)
        assert player.username == "bob"
        assert player.surname is None


class TestRoundFromDB:
    """Tests for Round.from_db() conversion."""

    def test_from_db_basic(self, test_session):
        """Test basic round conversion."""
        # Create players
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        # Create game and round
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()

        round_db = RoundDB(
            game_id=game.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 15},
            round_ender_username="alice",
        )
        test_session.add(round_db)
        test_session.commit()

        # Convert to domain model
        round_obj = Round.from_db(round_db, test_session)
        assert len(round_obj.player_raw_scores) == 2
        assert round_obj.round_ender.username == "alice"

        # Check scores are correct
        alice_player = Player(username="alice", surname="Johnson")
        bob_player = Player(username="bob", surname="Smith")
        assert round_obj.player_raw_scores[alice_player] == 10
        assert round_obj.player_raw_scores[bob_player] == 15

    def test_from_db_multiple_players(self, test_session):
        """Test round conversion with multiple players."""
        # Create players
        players = [
            PlayerDB(username="alice", surname="A"),
            PlayerDB(username="bob", surname="B"),
            PlayerDB(username="charlie", surname="C"),
        ]
        for player in players:
            test_session.add(player)
        test_session.commit()

        # Create game and round
        game = GameDB(player_usernames=["alice", "bob", "charlie"])
        test_session.add(game)
        test_session.commit()

        round_db = RoundDB(
            game_id=game.id,
            round_number=1,
            player_raw_scores={"alice": 5, "bob": 10, "charlie": 15},
            round_ender_username="bob",
        )
        test_session.add(round_db)
        test_session.commit()

        # Convert to domain model
        round_obj = Round.from_db(round_db, test_session)
        assert len(round_obj.player_raw_scores) == 3
        assert round_obj.round_ender.username == "bob"

    def test_from_db_missing_round_ender(self, test_session):
        """Test round conversion fails when round ender not found."""
        # Create only alice, not bob
        alice = PlayerDB(username="alice", surname="Johnson")
        test_session.add(alice)
        test_session.commit()

        # Create game and round with bob as ender
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()

        round_db = RoundDB(
            game_id=game.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 15},
            round_ender_username="bob",
        )
        test_session.add(round_db)
        test_session.commit()

        # Should raise ValueError
        with pytest.raises(ValueError, match="not found"):
            Round.from_db(round_db, test_session)

    def test_from_db_missing_player_in_scores(self, test_session):
        """Test round conversion when a player in scores doesn't exist."""
        # Create only alice
        alice = PlayerDB(username="alice", surname="Johnson")
        test_session.add(alice)
        test_session.commit()

        # Create game and round with bob in scores
        game = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game)
        test_session.commit()

        round_db = RoundDB(
            game_id=game.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 15},
            round_ender_username="alice",
        )
        test_session.add(round_db)
        test_session.commit()

        # Convert - should skip bob
        round_obj = Round.from_db(round_db, test_session)
        assert len(round_obj.player_raw_scores) == 1
        alice_player = Player(username="alice", surname="Johnson")
        assert alice_player in round_obj.player_raw_scores


class TestGameFromDB:
    """Tests for Game.from_db() conversion."""

    def test_from_db_no_rounds(self, test_session):
        """Test converting a game with no rounds."""
        # Create players
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        # Create game
        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        # Convert
        game = Game.from_db(game_db, test_session)
        assert len(game.players) == 2
        assert len(game.rounds) == 0
        assert {p.username for p in game.players} == {"alice", "bob"}

    def test_from_db_with_rounds(self, test_session):
        """Test converting a game with multiple rounds."""
        # Create players
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        # Create game
        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        # Add rounds
        rounds = [
            RoundDB(
                game_id=game_db.id,
                round_number=1,
                player_raw_scores={"alice": 10, "bob": 15},
                round_ender_username="alice",
            ),
            RoundDB(
                game_id=game_db.id,
                round_number=2,
                player_raw_scores={"alice": 20, "bob": 25},
                round_ender_username="bob",
            ),
        ]
        for round_obj in rounds:
            test_session.add(round_obj)
        test_session.commit()

        # Convert
        game = Game.from_db(game_db, test_session)
        assert len(game.rounds) == 2
        assert len(game.players) == 2

        # Check rounds are correct
        assert game.rounds[0].round_ender.username == "alice"
        assert game.rounds[1].round_ender.username == "bob"

    def test_from_db_bulk_loading(self, test_session):
        """Test that Game.from_db() efficiently loads all players at once."""
        # Create many players
        players = [
            PlayerDB(username=f"player{i}", surname=f"Surname{i}") for i in range(10)
        ]
        for player in players:
            test_session.add(player)
        test_session.commit()

        # Create game with 5 players
        game_db = GameDB(
            player_usernames=["player0", "player1", "player2", "player3", "player4"]
        )
        test_session.add(game_db)
        test_session.commit()

        # Add rounds using different players as round enders
        rounds = [
            RoundDB(
                game_id=game_db.id,
                round_number=1,
                player_raw_scores={
                    "player0": 10,
                    "player1": 15,
                    "player2": 20,
                    "player3": 25,
                    "player4": 30,
                },
                round_ender_username="player0",
            ),
            RoundDB(
                game_id=game_db.id,
                round_number=2,
                player_raw_scores={
                    "player0": 5,
                    "player1": 10,
                    "player2": 15,
                    "player3": 20,
                    "player4": 25,
                },
                round_ender_username="player1",
            ),
        ]
        for round_obj in rounds:
            test_session.add(round_obj)
        test_session.commit()

        # Convert - should work efficiently
        game = Game.from_db(game_db, test_session)
        assert len(game.players) == 5
        assert len(game.rounds) == 2

    def test_from_db_winner(self, test_session):
        """Test that game winner calculation works after conversion."""
        # Create players
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        charlie = PlayerDB(username="charlie", surname="Brown")
        test_session.add(alice)
        test_session.add(bob)
        test_session.add(charlie)
        test_session.commit()

        # Create game
        game_db = GameDB(player_usernames=["alice", "bob", "charlie"])
        test_session.add(game_db)
        test_session.commit()

        # Add rounds where alice has lowest total
        rounds = [
            RoundDB(
                game_id=game_db.id,
                round_number=1,
                player_raw_scores={"alice": 5, "bob": 10, "charlie": 15},
                round_ender_username="alice",
            ),
            RoundDB(
                game_id=game_db.id,
                round_number=2,
                player_raw_scores={"alice": 10, "bob": 20, "charlie": 25},
                round_ender_username="alice",
            ),
        ]
        for round_obj in rounds:
            test_session.add(round_obj)
        test_session.commit()

        # Convert and check winner
        game = Game.from_db(game_db, test_session)
        winner = game.winner()
        assert winner.username == "alice"

        # Check total scores
        totals = game.player_total_scores()
        assert totals[Player(username="alice", surname="Johnson")] == 15
        assert totals[Player(username="bob", surname="Smith")] == 30
        assert totals[Player(username="charlie", surname="Brown")] == 40

    def test_from_db_cumulative_scores(self, test_session):
        """Test that cumulative score calculation works after conversion."""
        # Create players
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        # Create game
        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        # Add rounds
        rounds = [
            RoundDB(
                game_id=game_db.id,
                round_number=1,
                player_raw_scores={"alice": 10, "bob": 15},
                round_ender_username="alice",
            ),
            RoundDB(
                game_id=game_db.id,
                round_number=2,
                player_raw_scores={"alice": 5, "bob": 20},
                round_ender_username="alice",
            ),
            RoundDB(
                game_id=game_db.id,
                round_number=3,
                player_raw_scores={"alice": 20, "bob": 10},
                round_ender_username="bob",
            ),
        ]
        for round_obj in rounds:
            test_session.add(round_obj)
        test_session.commit()

        # Convert and check cumulative scores
        game = Game.from_db(game_db, test_session)
        cumulative = game.player_cumulative_scores()

        alice_player = Player(username="alice", surname="Johnson")
        bob_player = Player(username="bob", surname="Smith")

        assert cumulative[alice_player] == [10, 15, 35]
        assert cumulative[bob_player] == [15, 35, 45]

    def test_from_db_missing_player(self, test_session):
        """Test game conversion when a player in game list doesn't exist."""
        # Create only alice
        alice = PlayerDB(username="alice", surname="Johnson")
        test_session.add(alice)
        test_session.commit()

        # Create game with alice and bob (bob doesn't exist)
        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        # Convert - should only include alice
        game = Game.from_db(game_db, test_session)
        assert len(game.players) == 1
        assert game.players[0].username == "alice"

    def test_from_db_empty_game(self, test_session):
        """Test converting a game with empty player list."""
        game_db = GameDB(player_usernames=[])
        test_session.add(game_db)
        test_session.commit()

        game = Game.from_db(game_db, test_session)
        assert len(game.players) == 0
        assert len(game.rounds) == 0
