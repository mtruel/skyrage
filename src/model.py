from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.scores import apply_doubling_penalty

if TYPE_CHECKING:
    from src.db import GameDB, PlayerDB, RoundDB


class Player(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    username: str
    surname: str | None = None

    def __hash__(self) -> int:
        """Make Player hashable for use as dict keys."""
        return hash(self.username)

    @classmethod
    def from_db(cls, player_db: "PlayerDB") -> "Player":
        """Create a Player from a database model."""
        return cls(
            username=player_db.username,
            surname=player_db.surname,
        )


class Round(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_raw_scores: dict[Player, int]
    round_ender: Player

    def winner(self) -> Player:
        """Return the player with the lowest score in the round."""
        final_scores = self.final_scores()
        return min(final_scores.keys(), key=lambda p: final_scores[p])

    def final_scores(self) -> dict[Player, int]:
        """
        Calculate final scores for each player, applying Skyjo doubling rule.

        If the round_ender doesn't have the lowest score and their score is positive,
        their score is doubled.
        """
        return apply_doubling_penalty(self.player_raw_scores, self.round_ender)

    @classmethod
    def from_db(cls, round_db: "RoundDB", session: Session) -> "Round":
        """
        Create a Round from a database model.

        Args:
            round_db: The database round object
            session: Active SQLAlchemy session to use for queries
        """
        from src.db import PlayerDB

        # Get player objects from usernames
        player_raw_scores = {}
        for username, score in round_db.player_raw_scores.items():
            player_db = session.query(PlayerDB).filter_by(username=username).first()
            if player_db:
                player_raw_scores[Player.from_db(player_db)] = score

        round_ender_db = (
            session.query(PlayerDB)
            .filter_by(username=round_db.round_ender_username)
            .first()
        )
        if not round_ender_db:
            raise ValueError(
                f"Round ender with username '{round_db.round_ender_username}' not found"
            )
        round_ender = Player.from_db(round_ender_db)

        return cls(player_raw_scores=player_raw_scores, round_ender=round_ender)


class Game(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rounds: list[Round]
    players: list[Player]

    def player_cumulative_scores(self) -> dict[Player, list[int]]:
        """
        Return cumulative scores for each player after each round.

        Returns a dict where each player maps to a list of their cumulative totals
        after each round. For example, if a player scored [10, 15, 20] in three rounds,
        this would return [10, 25, 45].
        """
        cumulative: dict[Player, list[int]] = {player: [] for player in self.players}

        for round_obj in self.rounds:
            round_scores = round_obj.final_scores()

            for player in self.players:
                score = round_scores.get(player, 0)
                previous_total = cumulative[player][-1] if cumulative[player] else 0
                cumulative[player].append(previous_total + score)

        return cumulative

    def player_total_scores(self) -> dict[Player, int]:
        """
        Return the total score for each player across all rounds.
        """
        totals: dict[Player, int] = {player: 0 for player in self.players}

        for round_obj in self.rounds:
            round_scores = round_obj.final_scores()
            for player, score in round_scores.items():
                totals[player] += score

        return totals

    def winner(self) -> Player:
        """Return the player with the lowest total score across all rounds."""
        total_scores = self.player_total_scores()
        return min(total_scores.keys(), key=lambda p: total_scores[p])

    @classmethod
    def from_db(cls, game_db: "GameDB", session: Session) -> "Game":
        """
        Create a Game from a database model.

        Args:
            game_db: The database game object
            session: Active SQLAlchemy session to use for queries
        """
        from src.db import PlayerDB

        # Collect all usernames we need to load
        all_usernames = set(game_db.player_usernames)
        for round_db in game_db.rounds:
            all_usernames.update(round_db.player_raw_scores.keys())
            all_usernames.add(round_db.round_ender_username)

        # Bulk load all players in a single query
        players_db = (
            session.query(PlayerDB).filter(PlayerDB.username.in_(all_usernames)).all()
        )
        players_dict = {p.username: Player.from_db(p) for p in players_db}

        # Create rounds using the pre-loaded player data
        rounds = []
        for round_db in game_db.rounds:
            player_raw_scores = {
                players_dict[username]: score
                for username, score in round_db.player_raw_scores.items()
                if username in players_dict
            }
            round_ender = players_dict.get(round_db.round_ender_username)
            if not round_ender:
                raise ValueError(
                    f"Round ender with username '{round_db.round_ender_username}' not found"
                )
            rounds.append(
                Round(player_raw_scores=player_raw_scores, round_ender=round_ender)
            )

        # Get player objects from usernames
        players = [
            players_dict[username]
            for username in game_db.player_usernames
            if username in players_dict
        ]

        return cls(rounds=rounds, players=players)
