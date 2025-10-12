"""Database models and configuration for Skyrage."""

import json
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine
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

    def __repr__(self) -> str:
        return f"<Player(username='{self.username}', surname='{self.surname}')>"


class RoundDB(Base):
    """Database model for a round within a game."""

    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Store player_raw_scores as JSON: {username: score, ...}
    player_raw_scores_json: Mapped[str] = mapped_column(Text, nullable=False)

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

    @property
    def player_raw_scores(self) -> dict[str, int]:
        """Deserialize player_raw_scores from JSON."""
        return json.loads(self.player_raw_scores_json)

    @player_raw_scores.setter
    def player_raw_scores(self, value: dict[str, int]) -> None:
        """Serialize player_raw_scores to JSON."""
        self.player_raw_scores_json = json.dumps(value)

    def __repr__(self) -> str:
        return f"<Round(id={self.id}, game_id={self.game_id}, round_number={self.round_number})>"


class GameDB(Base):
    """Database model for a game."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Store player usernames as JSON list: ["alice", "bob", "charlie"]
    player_usernames_json: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    rounds: Mapped[list["RoundDB"]] = relationship(
        "RoundDB", back_populates="game", cascade="all, delete-orphan"
    )

    @property
    def player_usernames(self) -> list[str]:
        """Deserialize player usernames from JSON."""
        return json.loads(self.player_usernames_json)

    @player_usernames.setter
    def player_usernames(self, value: list[str]) -> None:
        """Serialize player usernames to JSON."""
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


def get_engine(database_url: str | None = None):
    """Create and return a database engine."""
    if database_url is None:
        database_url = get_default_database_url()
    return create_engine(database_url, echo=False)


def get_session_maker(database_url: str | None = None):
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
