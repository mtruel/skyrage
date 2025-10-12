"""Tests for edge cases in game logic."""

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


class TestGameWinnerEdgeCases:
    """Tests for edge cases in determining game winners."""

    def test_tie_for_winner_two_players(self, test_session):
        """Test game with tie between two players."""
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

        # Add rounds where both end with same score
        rounds = [
            RoundDB(
                game_id=game_db.id,
                round_number=1,
                player_raw_scores={"alice": 10, "bob": 10},
                round_ender_username="alice",
            ),
            RoundDB(
                game_id=game_db.id,
                round_number=2,
                player_raw_scores={"alice": 5, "bob": 5},
                round_ender_username="bob",
            ),
        ]
        for round_obj in rounds:
            test_session.add(round_obj)
        test_session.commit()

        # Convert and check - should pick one consistently
        game = Game.from_db(game_db, test_session)
        winner = game.winner()
        totals = game.player_total_scores()

        # Both should have same score
        assert totals[Player(username="alice", surname="Johnson")] == 15
        assert totals[Player(username="bob", surname="Smith")] == 15

        # Winner should be one of them (min() picks arbitrarily but consistently)
        assert winner.username in ["alice", "bob"]

    def test_tie_for_winner_multiple_players(self, test_session):
        """Test game with tie among multiple players."""
        # Create players
        players = [
            PlayerDB(username="alice", surname="A"),
            PlayerDB(username="bob", surname="B"),
            PlayerDB(username="charlie", surname="C"),
        ]
        for player in players:
            test_session.add(player)
        test_session.commit()

        # Create game
        game_db = GameDB(player_usernames=["alice", "bob", "charlie"])
        test_session.add(game_db)
        test_session.commit()

        # All end with same score
        round_obj = RoundDB(
            game_id=game_db.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 10, "charlie": 10},
            round_ender_username="alice",
        )
        test_session.add(round_obj)
        test_session.commit()

        # Convert and check
        game = Game.from_db(game_db, test_session)
        winner = game.winner()
        totals = game.player_total_scores()

        # All should have same score
        assert all(score == 10 for score in totals.values())
        assert winner.username in ["alice", "bob", "charlie"]

    def test_negative_scores_winner(self, test_session):
        """Test game where winner has negative total score."""
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

        # Add rounds with negative scores
        rounds = [
            RoundDB(
                game_id=game_db.id,
                round_number=1,
                player_raw_scores={"alice": -5, "bob": 10},
                round_ender_username="alice",
            ),
            RoundDB(
                game_id=game_db.id,
                round_number=2,
                player_raw_scores={"alice": -10, "bob": 5},
                round_ender_username="alice",
            ),
        ]
        for round_obj in rounds:
            test_session.add(round_obj)
        test_session.commit()

        # Convert and check
        game = Game.from_db(game_db, test_session)
        winner = game.winner()
        totals = game.player_total_scores()

        assert totals[Player(username="alice", surname="Johnson")] == -15
        assert totals[Player(username="bob", surname="Smith")] == 15
        assert winner.username == "alice"


class TestBoundaryScores:
    """Tests for boundary score values."""

    def test_minimum_score_negative_fifteen(self, test_session):
        """Test with minimum valid score of -15."""
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        round_obj = RoundDB(
            game_id=game_db.id,
            round_number=1,
            player_raw_scores={"alice": -15, "bob": 0},
            round_ender_username="alice",
        )
        test_session.add(round_obj)
        test_session.commit()

        game = Game.from_db(game_db, test_session)
        totals = game.player_total_scores()
        assert totals[Player(username="alice", surname="Johnson")] == -15

    def test_maximum_score_120(self, test_session):
        """Test with maximum valid score of 120."""
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        round_obj = RoundDB(
            game_id=game_db.id,
            round_number=1,
            player_raw_scores={"alice": 0, "bob": 120},
            round_ender_username="alice",
        )
        test_session.add(round_obj)
        test_session.commit()

        game = Game.from_db(game_db, test_session)
        totals = game.player_total_scores()
        assert totals[Player(username="bob", surname="Smith")] == 120

    def test_zero_score(self, test_session):
        """Test with zero scores."""
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        round_obj = RoundDB(
            game_id=game_db.id,
            round_number=1,
            player_raw_scores={"alice": 0, "bob": 0},
            round_ender_username="alice",
        )
        test_session.add(round_obj)
        test_session.commit()

        game = Game.from_db(game_db, test_session)
        totals = game.player_total_scores()
        assert totals[Player(username="alice", surname="Johnson")] == 0
        assert totals[Player(username="bob", surname="Smith")] == 0

    def test_score_doubling_at_boundary(self, test_session):
        """Test score doubling with boundary values."""
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        # Bob ends with 120, alice has lower score - bob's should double
        round_obj = RoundDB(
            game_id=game_db.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 120},
            round_ender_username="bob",
        )
        test_session.add(round_obj)
        test_session.commit()

        game = Game.from_db(game_db, test_session)
        rounds = game.rounds
        final_scores = rounds[0].final_scores()

        assert final_scores[Player(username="alice", surname="Johnson")] == 10
        assert final_scores[Player(username="bob", surname="Smith")] == 240  # doubled


class TestRoundEdgeCases:
    """Tests for edge cases in round logic."""

    def test_round_ender_has_tied_lowest_score(self):
        """Test when round ender ties for lowest score (no penalty)."""
        alice = Player(username="alice", surname="Johnson")
        bob = Player(username="bob", surname="Smith")

        round_obj = Round(
            player_raw_scores={alice: 10, bob: 10},
            round_ender=alice,
        )
        final = round_obj.final_scores()

        # No penalty since alice tied for lowest
        assert final[alice] == 10
        assert final[bob] == 10

    def test_round_ender_zero_score_not_lowest(self):
        """Test when round ender has 0 (not doubled even though not lowest)."""
        alice = Player(username="alice", surname="Johnson")
        bob = Player(username="bob", surname="Smith")

        round_obj = Round(
            player_raw_scores={alice: -5, bob: 0},
            round_ender=bob,
        )
        final = round_obj.final_scores()

        # Bob has 0, not lowest, but 0 is not positive so no doubling
        assert final[alice] == -5
        assert final[bob] == 0

    def test_single_player_round(self):
        """Test round with only one player (edge case)."""
        alice = Player(username="alice", surname="Johnson")

        round_obj = Round(
            player_raw_scores={alice: 10},
            round_ender=alice,
        )
        final = round_obj.final_scores()

        # Should not double since alice has the lowest (only) score
        assert final[alice] == 10

        winner = round_obj.winner()
        assert winner == alice


class TestFinishedGameMutations:
    """Tests for attempting to mutate finished games."""

    def test_finished_game_flag(self, test_session):
        """Test that finished_at flag is set correctly."""
        from datetime import UTC, datetime

        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        # Initially not finished
        assert game_db.finished_at is None

        # Mark as finished
        game_db.finished_at = datetime.now(UTC)
        test_session.commit()

        # Now finished
        assert game_db.finished_at is not None

    def test_finished_game_can_still_be_queried(self, test_session):
        """Test that finished games can still be queried normally."""
        from datetime import UTC, datetime

        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        game_db = GameDB(player_usernames=["alice", "bob"])
        game_db.finished_at = datetime.now(UTC)
        test_session.add(game_db)
        test_session.commit()

        round_obj = RoundDB(
            game_id=game_db.id,
            round_number=1,
            player_raw_scores={"alice": 10, "bob": 15},
            round_ender_username="alice",
        )
        test_session.add(round_obj)
        test_session.commit()

        # Can still convert to domain model
        game = Game.from_db(game_db, test_session)
        assert len(game.rounds) == 1
        assert len(game.players) == 2


class TestEmptyAndMinimalGames:
    """Tests for empty and minimal game configurations."""

    def test_game_with_no_players(self, test_session):
        """Test creating a game with no players."""
        game_db = GameDB(player_usernames=[])
        test_session.add(game_db)
        test_session.commit()

        game = Game.from_db(game_db, test_session)
        assert len(game.players) == 0
        assert len(game.rounds) == 0

    def test_game_with_one_player(self, test_session):
        """Test game with single player."""
        alice = PlayerDB(username="alice", surname="Johnson")
        test_session.add(alice)
        test_session.commit()

        game_db = GameDB(player_usernames=["alice"])
        test_session.add(game_db)
        test_session.commit()

        round_obj = RoundDB(
            game_id=game_db.id,
            round_number=1,
            player_raw_scores={"alice": 10},
            round_ender_username="alice",
        )
        test_session.add(round_obj)
        test_session.commit()

        game = Game.from_db(game_db, test_session)
        assert len(game.players) == 1
        assert len(game.rounds) == 1

        winner = game.winner()
        assert winner.username == "alice"

    def test_round_with_empty_scores(self, test_session):
        """Test round with empty scores dict (edge case)."""
        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        # This is technically invalid but tests edge case
        round_obj = RoundDB(
            game_id=game_db.id,
            round_number=1,
            player_raw_scores={},
            round_ender_username="alice",
        )
        test_session.add(round_obj)
        test_session.commit()

        # Should not crash
        assert round_obj.player_raw_scores == {}


class TestLargeScoreRanges:
    """Tests for handling large cumulative scores."""

    def test_very_large_positive_cumulative(self, test_session):
        """Test handling very large positive cumulative scores."""
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        # Add many rounds with high scores
        for i in range(10):
            round_obj = RoundDB(
                game_id=game_db.id,
                round_number=i + 1,
                player_raw_scores={"alice": 120, "bob": 100},
                round_ender_username="bob",
            )
            test_session.add(round_obj)
        test_session.commit()

        game = Game.from_db(game_db, test_session)
        totals = game.player_total_scores()

        # Alice: 10 rounds * 120 = 1200
        assert totals[Player(username="alice", surname="Johnson")] == 1200
        # Bob: 10 rounds * 100 = 1000
        assert totals[Player(username="bob", surname="Smith")] == 1000

    def test_very_large_negative_cumulative(self, test_session):
        """Test handling very large negative cumulative scores."""
        alice = PlayerDB(username="alice", surname="Johnson")
        bob = PlayerDB(username="bob", surname="Smith")
        test_session.add(alice)
        test_session.add(bob)
        test_session.commit()

        game_db = GameDB(player_usernames=["alice", "bob"])
        test_session.add(game_db)
        test_session.commit()

        # Add many rounds with negative scores
        for i in range(10):
            round_obj = RoundDB(
                game_id=game_db.id,
                round_number=i + 1,
                player_raw_scores={"alice": -15, "bob": 0},
                round_ender_username="alice",
            )
            test_session.add(round_obj)
        test_session.commit()

        game = Game.from_db(game_db, test_session)
        totals = game.player_total_scores()

        # Alice: 10 rounds * -15 = -150
        assert totals[Player(username="alice", surname="Johnson")] == -150
        assert totals[Player(username="bob", surname="Smith")] == 0
