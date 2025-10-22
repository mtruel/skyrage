"""Database models and configuration for Skyrage."""

import json
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Engine,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class PlayerDB(Base):
    """Database model for a player."""

    __tablename__ = "players"

    username: Mapped[str] = mapped_column(String(100), primary_key=True, nullable=False)
    surname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    game_players: Mapped[list["GamePlayerDB"]] = relationship(
        "GamePlayerDB", back_populates="player", cascade="all, delete-orphan"
    )
    round_scores: Mapped[list["RoundScoreDB"]] = relationship(
        "RoundScoreDB", back_populates="player", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Player(username='{self.username}', surname='{self.surname}')>"


class GamePlayerDB(Base):
    """Junction table for game-player many-to-many relationship."""

    __tablename__ = "game_players"

    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    username: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("players.username", ondelete="CASCADE"),
        primary_key=True,
    )
    player_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    game: Mapped["GameDB"] = relationship("GameDB", back_populates="game_players")
    player: Mapped["PlayerDB"] = relationship("PlayerDB", back_populates="game_players")

    def __repr__(self) -> str:
        return f"<GamePlayer(game_id={self.game_id}, username='{self.username}', order={self.player_order})>"


class RoundScoreDB(Base):
    """Table for individual player scores within a round."""

    __tablename__ = "round_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(100), ForeignKey("players.username", ondelete="CASCADE"), nullable=False
    )
    raw_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    round: Mapped["RoundDB"] = relationship("RoundDB", back_populates="round_scores")
    player: Mapped["PlayerDB"] = relationship("PlayerDB", back_populates="round_scores")

    def __repr__(self) -> str:
        return f"<RoundScore(round_id={self.round_id}, username='{self.username}', score={self.raw_score})>"


class RoundDB(Base):
    """Database model for a round within a game."""

    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # DEPRECATED: Will be removed after migration to normalized schema
    player_raw_scores_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Store round_ender username
    round_ender_username: Mapped[str] = mapped_column(
        String(100), ForeignKey("players.username"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    game: Mapped["GameDB"] = relationship("GameDB", back_populates="rounds")
    round_ender: Mapped["PlayerDB"] = relationship("PlayerDB")
    round_scores: Mapped[list["RoundScoreDB"]] = relationship(
        "RoundScoreDB", back_populates="round", cascade="all, delete-orphan"
    )

    @property
    def player_raw_scores(self) -> dict[str, int]:
        """Get player raw scores from normalized table or fallback to JSON."""
        if self.round_scores:
            # Use normalized data
            return {score.username: score.raw_score for score in self.round_scores}
        elif self.player_raw_scores_json:
            # Fallback to legacy JSON
            return json.loads(self.player_raw_scores_json)
        return {}

    @player_raw_scores.setter
    def player_raw_scores(self, value: dict[str, int]) -> None:
        """Set player raw scores (will be stored in normalized table)."""
        # During migration, still set JSON for backward compatibility
        self.player_raw_scores_json = json.dumps(value)

    def __repr__(self) -> str:
        return f"<Round(id={self.id}, game_id={self.game_id}, round_number={self.round_number})>"


class GameDB(Base):
    """Database model for a game."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # DEPRECATED: Will be removed after migration to normalized schema
    player_usernames_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    rounds: Mapped[list["RoundDB"]] = relationship(
        "RoundDB", back_populates="game", cascade="all, delete-orphan"
    )
    game_players: Mapped[list["GamePlayerDB"]] = relationship(
        "GamePlayerDB",
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="GamePlayerDB.player_order",
    )

    @property
    def player_usernames(self) -> list[str]:
        """Get player usernames from normalized table or fallback to JSON."""
        if self.game_players:
            # Use normalized data, ordered by player_order
            return [
                gp.username
                for gp in sorted(self.game_players, key=lambda x: x.player_order)
            ]
        elif self.player_usernames_json:
            # Fallback to legacy JSON
            return json.loads(self.player_usernames_json)
        return []

    @player_usernames.setter
    def player_usernames(self, value: list[str]) -> None:
        """Set player usernames (will be stored in normalized table)."""
        # During migration, still set JSON for backward compatibility
        self.player_usernames_json = json.dumps(value)

    def __repr__(self) -> str:
        return f"<Game(id={self.id}, created_at={self.created_at}, rounds={len(self.rounds)})>"


# Database configuration
def get_default_database_url() -> str:
    """Get the default database URL from config file."""
    try:
        from config import get_database_url

        return get_database_url()
    except Exception:
        # Fallback if config can't be loaded
        return "sqlite:///skyrage.db"


def get_engine(database_url: str | None = None) -> Engine:
    """Create and return a database engine."""
    if database_url is None:
        database_url = get_default_database_url()
    return create_engine(database_url, echo=False)


def get_session_maker(database_url: str | None = None) -> sessionmaker[Session]:
    """Create and return a session maker."""
    engine = get_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db(database_url: str | None = None):
    """Initialize the database by creating all tables."""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)


def get_db_session(database_url: str | None = None) -> Session:
    """Get a database session. Use as a context manager or call close() when done."""
    session_maker = get_session_maker(database_url)
    return session_maker()


def get_or_create_player(
    session: Session, username: str, surname: str | None = None
) -> tuple[PlayerDB, bool]:
    """
    Get an existing player or create a new one.

    Args:
        session: SQLAlchemy session to use for database operations
        username: Player's username (primary key)
        surname: Optional surname (only used when creating new player)

    Returns:
        Tuple of (player, created) where created is True if player was newly created
    """
    existing = session.query(PlayerDB).filter_by(username=username).first()
    if existing:
        return (existing, False)

    # Create new player
    player = PlayerDB(username=username, surname=surname)
    session.add(player)
    return (player, True)
