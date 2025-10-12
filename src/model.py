from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from src.db import GameDB, PlayerDB, RoundDB


class Player(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    username: str
    first_name: str
    last_name: str

    @classmethod
    def from_db(cls, player_db: "PlayerDB") -> "Player":
        """Create a Player from a database model."""
        return cls(
            username=player_db.username,
            first_name=player_db.first_name,
            last_name=player_db.last_name,
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
        final_scores = {}

        # Calculate raw scores first
        min_score = min(self.player_raw_scores.values())

        for player, raw_score in self.player_raw_scores.items():
            # Check if this player ended the round and doesn't have lowest score
            if player == self.round_ender and raw_score > min_score and raw_score > 0:
                # Apply doubling penalty
                final_scores[player] = raw_score * 2
            else:
                final_scores[player] = raw_score

        return final_scores

    @classmethod
    def from_db(cls, round_db: "RoundDB") -> "Round":
        """Create a Round from a database model."""
        from src.db import PlayerDB, get_db_session

        # Get player objects from usernames
        session = get_db_session()
        try:
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
        finally:
            session.close()


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
    def from_db(cls, game_db: "GameDB") -> "Game":
        """Create a Game from a database model."""
        from src.db import PlayerDB, get_db_session

        rounds = [Round.from_db(round_db) for round_db in game_db.rounds]

        # Get player objects from usernames
        session = get_db_session()
        try:
            players = []
            for username in game_db.player_usernames:
                player_db = session.query(PlayerDB).filter_by(username=username).first()
                if player_db:
                    players.append(Player.from_db(player_db))

            return cls(rounds=rounds, players=players)
        finally:
            session.close()
