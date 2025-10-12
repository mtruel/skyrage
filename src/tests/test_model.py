"""Tests for Pydantic models in model.py."""

import pytest

from model import Game, Player, Round


class TestPlayer:
    """Tests for the Player model."""

    def test_player_creation(self):
        """Test creating a Player instance."""
        player = Player(username="alice123", surname="Johnson")
        assert player.username == "alice123"
        assert player.surname == "Johnson"

    def test_player_equality(self):
        """Test that Players with same data are equal."""
        player1 = Player(username="alice", surname="Johnson")
        player2 = Player(username="alice", surname="Johnson")
        assert player1 == player2

    def test_player_hashable(self):
        """Test that Players can be used as dict keys."""
        player = Player(username="alice", surname="Johnson")
        scores = {player: 10}
        assert scores[player] == 10


class TestRound:
    """Tests for the Round model."""

    @pytest.fixture
    def players(self):
        """Create test players."""
        return {
            "alice": Player(username="alice", surname="Johnson"),
            "bob": Player(username="bob", surname="Smith"),
            "charlie": Player(username="charlie", surname="Brown"),
        }

    def test_round_creation(self, players):
        """Test creating a Round instance."""
        round_obj = Round(
            player_raw_scores={
                players["alice"]: 15,
                players["bob"]: 10,
                players["charlie"]: 20,
            },
            round_ender=players["bob"],
        )
        assert round_obj.round_ender == players["bob"]
        assert len(round_obj.player_raw_scores) == 3

    def test_final_scores_no_penalty(self, players):
        """Test final scores when round ender has lowest score (no penalty)."""
        round_obj = Round(
            player_raw_scores={
                players["alice"]: 15,
                players["bob"]: 10,
                players["charlie"]: 20,
            },
            round_ender=players["bob"],
        )
        final = round_obj.final_scores()
        # Bob ended the round and has lowest score, so no penalty
        assert final[players["bob"]] == 10
        assert final[players["alice"]] == 15
        assert final[players["charlie"]] == 20

    def test_final_scores_with_penalty(self, players):
        """Test final scores when round ender doesn't have lowest score (penalty applied)."""
        round_obj = Round(
            player_raw_scores={
                players["alice"]: 10,
                players["bob"]: 15,
                players["charlie"]: 20,
            },
            round_ender=players["bob"],
        )
        final = round_obj.final_scores()
        # Bob ended the round but doesn't have lowest score, so penalty is applied
        assert final[players["bob"]] == 30  # 15 * 2
        assert final[players["alice"]] == 10
        assert final[players["charlie"]] == 20

    def test_final_scores_penalty_negative_score(self, players):
        """Test that negative scores are NOT doubled even with penalty."""
        round_obj = Round(
            player_raw_scores={
                players["alice"]: 10,
                players["bob"]: -5,
                players["charlie"]: 20,
            },
            round_ender=players["bob"],
        )
        final = round_obj.final_scores()
        # Bob ended with negative score, no doubling even though not lowest
        assert final[players["bob"]] == -5  # NOT doubled
        assert final[players["alice"]] == 10
        assert final[players["charlie"]] == 20

    def test_final_scores_tie_for_lowest(self, players):
        """Test when round ender ties for lowest score."""
        round_obj = Round(
            player_raw_scores={
                players["alice"]: 10,
                players["bob"]: 10,
                players["charlie"]: 20,
            },
            round_ender=players["bob"],
        )
        final = round_obj.final_scores()
        # Bob ties for lowest, so no penalty (not greater than min)
        assert final[players["bob"]] == 10
        assert final[players["alice"]] == 10
        assert final[players["charlie"]] == 20

    def test_winner(self, players):
        """Test getting the round winner."""
        round_obj = Round(
            player_raw_scores={
                players["alice"]: 15,
                players["bob"]: 10,
                players["charlie"]: 20,
            },
            round_ender=players["alice"],
        )
        winner = round_obj.winner()
        assert winner == players["bob"]

    def test_winner_with_penalty(self, players):
        """Test winner when someone gets doubled penalty."""
        round_obj = Round(
            player_raw_scores={
                players["alice"]: 10,
                players["bob"]: 15,
                players["charlie"]: 20,
            },
            round_ender=players["bob"],
        )
        winner = round_obj.winner()
        # Alice wins with 10 (Bob gets doubled to 30, Charlie has 20)
        assert winner == players["alice"]


class TestGame:
    """Tests for the Game model."""

    @pytest.fixture
    def players(self):
        """Create test players."""
        return {
            "alice": Player(username="alice", surname="Johnson"),
            "bob": Player(username="bob", surname="Smith"),
            "charlie": Player(username="charlie", surname="Brown"),
        }

    @pytest.fixture
    def sample_game(self, players):
        """Create a sample game with multiple rounds."""
        round1 = Round(
            player_raw_scores={
                players["alice"]: 10,
                players["bob"]: 15,
                players["charlie"]: 20,
            },
            round_ender=players["alice"],
        )
        round2 = Round(
            player_raw_scores={
                players["alice"]: 8,
                players["bob"]: 5,
                players["charlie"]: 12,
            },
            round_ender=players["bob"],
        )
        round3 = Round(
            player_raw_scores={
                players["alice"]: 18,
                players["bob"]: 10,
                players["charlie"]: 15,
            },
            round_ender=players["charlie"],
        )
        return Game(
            rounds=[round1, round2, round3],
            players=[players["alice"], players["bob"], players["charlie"]],
        )

    def test_game_creation(self, sample_game, players):
        """Test creating a Game instance."""
        assert len(sample_game.rounds) == 3
        assert len(sample_game.players) == 3
        assert players["alice"] in sample_game.players

    def test_player_total_scores(self, sample_game, players):
        """Test calculating total scores for each player."""
        totals = sample_game.player_total_scores()
        # Round 1: Alice=10, Bob=15, Charlie=20
        # Round 2: Alice=8, Bob=5, Charlie=12
        # Round 3: Alice=18, Bob=10, Charlie=15*2=30 (penalty!)
        assert totals[players["alice"]] == 36  # 10 + 8 + 18
        assert totals[players["bob"]] == 30  # 15 + 5 + 10
        assert totals[players["charlie"]] == 62  # 20 + 12 + 30

    def test_player_cumulative_scores(self, sample_game, players):
        """Test calculating cumulative scores per round."""
        cumulative = sample_game.player_cumulative_scores()
        # Alice: [10, 18, 36]
        assert cumulative[players["alice"]] == [10, 18, 36]
        # Bob: [15, 20, 30]
        assert cumulative[players["bob"]] == [15, 20, 30]
        # Charlie: [20, 32, 62] (gets penalty in round 3)
        assert cumulative[players["charlie"]] == [20, 32, 62]

    def test_winner(self, sample_game, players):
        """Test determining the game winner."""
        winner = sample_game.winner()
        # Bob has lowest total (30)
        assert winner == players["bob"]

    def test_game_with_penalty(self, players):
        """Test game where penalty affects winner."""
        round1 = Round(
            player_raw_scores={
                players["alice"]: 10,
                players["bob"]: 15,
                players["charlie"]: 20,
            },
            round_ender=players["bob"],  # Bob doesn't have lowest, gets doubled
        )
        game = Game(
            rounds=[round1],
            players=[players["alice"], players["bob"], players["charlie"]],
        )
        totals = game.player_total_scores()
        # Bob gets penalty: 15 * 2 = 30
        assert totals[players["bob"]] == 30
        assert totals[players["alice"]] == 10
        assert totals[players["charlie"]] == 20

        winner = game.winner()
        assert winner == players["alice"]

    def test_empty_game(self, players):
        """Test game with no rounds."""
        game = Game(rounds=[], players=[players["alice"], players["bob"]])
        totals = game.player_total_scores()
        assert totals[players["alice"]] == 0
        assert totals[players["bob"]] == 0

    def test_cumulative_with_negative_scores(self, players):
        """Test cumulative scores with negative values."""
        round1 = Round(
            player_raw_scores={
                players["alice"]: -5,
                players["bob"]: 10,
            },
            round_ender=players["alice"],
        )
        round2 = Round(
            player_raw_scores={
                players["alice"]: 8,
                players["bob"]: -2,
            },
            round_ender=players["bob"],
        )
        game = Game(rounds=[round1, round2], players=[players["alice"], players["bob"]])

        cumulative = game.player_cumulative_scores()
        # Alice: [-5, 3]
        assert cumulative[players["alice"]] == [-5, 3]
        # Bob: [10, 8]
        assert cumulative[players["bob"]] == [10, 8]

    def test_multiple_rounds_with_penalties(self, players):
        """Test complex game with multiple penalty scenarios."""
        # Round 1: Alice ends but doesn't win -> penalty
        round1 = Round(
            player_raw_scores={
                players["alice"]: 15,
                players["bob"]: 10,
                players["charlie"]: 20,
            },
            round_ender=players["alice"],
        )
        # Round 2: Bob ends and wins -> no penalty
        round2 = Round(
            player_raw_scores={
                players["alice"]: 12,
                players["bob"]: 8,
                players["charlie"]: 15,
            },
            round_ender=players["bob"],
        )
        # Round 3: Charlie ends but doesn't win -> penalty
        round3 = Round(
            player_raw_scores={
                players["alice"]: 5,
                players["bob"]: 10,
                players["charlie"]: 12,
            },
            round_ender=players["charlie"],
        )

        game = Game(
            rounds=[round1, round2, round3],
            players=[players["alice"], players["bob"], players["charlie"]],
        )

        totals = game.player_total_scores()
        # Alice: (15*2) + 12 + 5 = 47
        assert totals[players["alice"]] == 47
        # Bob: 10 + 8 + 10 = 28
        assert totals[players["bob"]] == 28
        # Charlie: 20 + 15 + (12*2) = 59
        assert totals[players["charlie"]] == 59

        winner = game.winner()
        assert winner == players["bob"]
