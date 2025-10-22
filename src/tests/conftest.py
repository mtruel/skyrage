"""Shared test fixtures and utilities."""

from sqlalchemy.orm import Session

from db import GameDB, GamePlayerDB, RoundDB, RoundScoreDB


def create_game_with_players(session: Session, player_usernames: list[str]) -> GameDB:
    """
    Create a game with properly populated normalized tables.

    Args:
        session: SQLAlchemy session
        player_usernames: List of player usernames for the game

    Returns:
        GameDB object with both JSON and normalized data populated
    """
    # Create game with JSON (for backward compatibility)
    game = GameDB(player_usernames=player_usernames)
    session.add(game)
    session.flush()  # Get the game ID

    # Populate normalized game_players table
    for order, username in enumerate(player_usernames):
        game_player = GamePlayerDB(
            game_id=game.id, username=username, player_order=order
        )
        session.add(game_player)

    session.flush()
    return game


def create_round_with_scores(
    session: Session,
    game_id: int,
    round_number: int,
    player_raw_scores: dict[str, int],
    round_ender_username: str,
) -> RoundDB:
    """
    Create a round with properly populated normalized tables.

    Args:
        session: SQLAlchemy session
        game_id: ID of the game this round belongs to
        round_number: Round number
        player_raw_scores: Dict mapping username to raw score
        round_ender_username: Username of player who ended the round

    Returns:
        RoundDB object with both JSON and normalized data populated
    """
    # Create round with JSON (for backward compatibility)
    round_obj = RoundDB(
        game_id=game_id,
        round_number=round_number,
        player_raw_scores=player_raw_scores,
        round_ender_username=round_ender_username,
    )
    session.add(round_obj)
    session.flush()  # Get the round ID

    # Populate normalized round_scores table
    for username, raw_score in player_raw_scores.items():
        round_score = RoundScoreDB(
            round_id=round_obj.id, username=username, raw_score=raw_score
        )
        session.add(round_score)

    session.flush()
    return round_obj
