"""REST API endpoints for Skyrage."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from db import GameDB, PlayerDB, RoundDB, get_db_session

router = APIRouter(prefix="/api")


# Request/Response Models
class PlayerCreate(BaseModel):
    username: str
    surname: str | None = None


class PlayerResponse(BaseModel):
    username: str
    surname: str | None = None
    created_at: datetime


class GameCreate(BaseModel):
    player_usernames: list[str]


class GameResponse(BaseModel):
    id: int
    player_usernames: list[str]
    created_at: datetime
    finished_at: datetime | None = None
    round_count: int


class RoundCreate(BaseModel):
    player_raw_scores: dict[str, int]
    round_ender_username: str


class RoundResponse(BaseModel):
    id: int
    game_id: int
    round_number: int
    player_raw_scores: dict[str, int]
    round_ender_username: str
    created_at: datetime


# Player Endpoints
@router.post(
    "/players", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED
)
def create_player(player_data: PlayerCreate):
    """Create a new player or return existing one."""
    session = get_db_session()
    try:
        # Check if player already exists
        existing = (
            session.query(PlayerDB).filter_by(username=player_data.username).first()
        )
        if existing:
            # Return existing player instead of error
            return PlayerResponse(
                username=existing.username,
                surname=existing.surname,
                created_at=existing.created_at,
            )

        # Create new player
        player = PlayerDB(
            username=player_data.username,
            surname=player_data.surname,
        )
        session.add(player)
        session.commit()
        session.refresh(player)

        return PlayerResponse(
            username=player.username,
            surname=player.surname,
            created_at=player.created_at,
        )
    finally:
        session.close()


@router.get("/players", response_model=list[PlayerResponse])
def list_players():
    """List all players."""
    session = get_db_session()
    try:
        players = session.query(PlayerDB).all()
        return [
            PlayerResponse(
                username=p.username,
                surname=p.surname,
                created_at=p.created_at,
            )
            for p in players
        ]
    finally:
        session.close()


@router.get("/players/{username}", response_model=PlayerResponse)
def get_player(username: str):
    """Get a specific player by username."""
    session = get_db_session()
    try:
        player = session.query(PlayerDB).filter_by(username=username).first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with username '{username}' not found",
            )

        return PlayerResponse(
            username=player.username,
            surname=player.surname,
            created_at=player.created_at,
        )
    finally:
        session.close()


@router.put("/players/{username}", response_model=PlayerResponse)
def update_player(username: str, player_data: PlayerCreate):
    """Update a player's surname."""
    session = get_db_session()
    try:
        player = session.query(PlayerDB).filter_by(username=username).first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with username '{username}' not found",
            )

        player.surname = player_data.surname
        session.commit()
        session.refresh(player)

        return PlayerResponse(
            username=player.username,
            surname=player.surname,
            created_at=player.created_at,
        )
    finally:
        session.close()


@router.delete("/players/{username}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player(username: str):
    """Delete a player if they have no associated games or rounds."""
    session = get_db_session()
    try:
        player = session.query(PlayerDB).filter_by(username=username).first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with username '{username}' not found",
            )

        # Check if player appears in any game's player list
        all_games = session.query(GameDB).all()
        for game in all_games:
            if username in game.player_usernames:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete player '{username}' - they are part of game #{game.id}. Player data must be preserved for game history.",
                )

        # Check if player appears in any round's player_raw_scores
        all_rounds = session.query(RoundDB).all()
        for round_db in all_rounds:
            if username in round_db.player_raw_scores:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete player '{username}' - they have participated in games. Player data must be preserved for game history.",
                )

        # Check if player ended any rounds
        rounds_count = (
            session.query(RoundDB).filter_by(round_ender_username=username).count()
        )
        if rounds_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete player '{username}' - they have ended {rounds_count} round(s). Player data must be preserved for game history.",
            )

        session.delete(player)
        session.commit()
    finally:
        session.close()


# Game Endpoints
@router.post("/games", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
def create_game(game_data: GameCreate):
    """Create a new game. Auto-creates players if they don't exist."""
    session = get_db_session()
    try:
        # Auto-create players if they don't exist
        for username in game_data.player_usernames:
            existing = session.query(PlayerDB).filter_by(username=username).first()
            if not existing:
                player = PlayerDB(username=username, surname=None)
                session.add(player)
        session.commit()

        # Create game
        game = GameDB(player_usernames=game_data.player_usernames)
        session.add(game)
        session.commit()
        session.refresh(game)

        return GameResponse(
            id=game.id,
            player_usernames=game.player_usernames,
            created_at=game.created_at,
            finished_at=game.finished_at,
            round_count=len(game.rounds),
        )
    finally:
        session.close()


@router.get("/games", response_model=list[GameResponse])
def list_games(limit: int = 50):
    """List all games, most recent first."""
    session = get_db_session()
    try:
        games = (
            session.query(GameDB).order_by(GameDB.created_at.desc()).limit(limit).all()
        )
        return [
            GameResponse(
                id=g.id,
                player_usernames=g.player_usernames,
                created_at=g.created_at,
                finished_at=g.finished_at,
                round_count=len(g.rounds),
            )
            for g in games
        ]
    finally:
        session.close()


@router.get("/games/{game_id}", response_model=GameResponse)
def get_game(game_id: int):
    """Get a specific game by ID."""
    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game with id {game_id} not found",
            )

        return GameResponse(
            id=game.id,
            player_usernames=game.player_usernames,
            created_at=game.created_at,
            finished_at=game.finished_at,
            round_count=len(game.rounds),
        )
    finally:
        session.close()


@router.put("/games/{game_id}/end", response_model=GameResponse)
def end_game(game_id: int):
    """Mark a game as finished."""
    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game with id {game_id} not found",
            )

        if game.finished_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Game is already finished",
            )

        game.finished_at = datetime.now(UTC)
        session.commit()
        session.refresh(game)

        return GameResponse(
            id=game.id,
            player_usernames=game.player_usernames,
            created_at=game.created_at,
            finished_at=game.finished_at,
            round_count=len(game.rounds),
        )
    finally:
        session.close()


# Round Endpoints
@router.post(
    "/games/{game_id}/rounds",
    response_model=RoundResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_round(game_id: int, round_data: RoundCreate):
    """Add a round to a game."""
    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game with id {game_id} not found",
            )

        if game.finished_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add rounds to a finished game",
            )

        # Validate that all players in scores are in the game
        for username in round_data.player_raw_scores.keys():
            if username not in game.player_usernames:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Player '{username}' is not in this game",
                )

        # Validate round ender is in the game
        if round_data.round_ender_username not in game.player_usernames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Round ender '{round_data.round_ender_username}' is not in this game",
            )

        # Calculate next round number
        round_number = len(game.rounds) + 1

        # Create round
        round_obj = RoundDB(
            game_id=game_id,
            round_number=round_number,
            player_raw_scores=round_data.player_raw_scores,
            round_ender_username=round_data.round_ender_username,
        )
        session.add(round_obj)
        session.commit()
        session.refresh(round_obj)

        return RoundResponse(
            id=round_obj.id,
            game_id=round_obj.game_id,
            round_number=round_obj.round_number,
            player_raw_scores=round_obj.player_raw_scores,
            round_ender_username=round_obj.round_ender_username,
            created_at=round_obj.created_at,
        )
    finally:
        session.close()


@router.get("/games/{game_id}/rounds", response_model=list[RoundResponse])
def list_rounds(game_id: int):
    """List all rounds for a game."""
    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game with id {game_id} not found",
            )

        return [
            RoundResponse(
                id=r.id,
                game_id=r.game_id,
                round_number=r.round_number,
                player_raw_scores=r.player_raw_scores,
                round_ender_username=r.round_ender_username,
                created_at=r.created_at,
            )
            for r in game.rounds
        ]
    finally:
        session.close()
