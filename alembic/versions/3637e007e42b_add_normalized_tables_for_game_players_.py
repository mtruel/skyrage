"""add_normalized_tables_for_game_players_and_round_scores

Revision ID: 3637e007e42b
Revises:
Create Date: 2025-10-13 00:09:16.477374

"""

from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "3637e007e42b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add normalized tables and migrate existing data."""
    conn = op.get_bind()

    # Check if we're migrating existing tables or creating fresh
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    has_existing_data = "games" in existing_tables

    if has_existing_data:
        print("🔄 Migrating existing database to normalized schema...")
        upgrade_with_migration(conn)
    else:
        print("🆕 Creating fresh normalized schema...")
        upgrade_fresh()


def upgrade_fresh() -> None:
    """Create all tables fresh (no existing data)."""
    # Create tables
    op.create_table(
        "players",
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("surname", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("username"),
    )

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_usernames_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "game_players",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("player_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["username"], ["players.username"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "username"),
    )

    op.create_table(
        "rounds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("player_raw_scores_json", sa.Text(), nullable=True),
        sa.Column("round_ender_username", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
        ),
        sa.ForeignKeyConstraint(
            ["round_ender_username"],
            ["players.username"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "round_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("raw_score", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["username"], ["players.username"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def upgrade_with_migration(conn) -> None:
    """Migrate existing database with data preservation."""
    print("  📋 Step 1: Creating new normalized tables...")

    # Create new junction/normalized tables
    op.create_table(
        "game_players",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("player_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["username"], ["players.username"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "username"),
    )

    op.create_table(
        "round_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("raw_score", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["username"], ["players.username"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Make JSON columns nullable (for backward compatibility during migration)
    with op.batch_alter_table("games") as batch_op:
        batch_op.alter_column(
            "player_usernames_json", existing_type=sa.Text(), nullable=True
        )

    with op.batch_alter_table("rounds") as batch_op:
        batch_op.alter_column(
            "player_raw_scores_json", existing_type=sa.Text(), nullable=True
        )

    print("  📊 Step 2: Migrating game player data...")
    migrate_game_players(conn)

    print("  📊 Step 3: Migrating round scores data...")
    migrate_round_scores(conn)

    print("  ✅ Migration complete!")


def migrate_game_players(conn) -> None:
    """Migrate game player data from JSON to normalized table."""
    # Fetch all games with their player JSON
    games_result = conn.execute(
        text(
            "SELECT id, player_usernames_json FROM games WHERE player_usernames_json IS NOT NULL"
        )
    )

    game_players_data = []
    for game_id, player_json in games_result:
        if not player_json:
            continue

        try:
            player_usernames = json.loads(player_json)
            for order, username in enumerate(player_usernames):
                game_players_data.append(
                    {"game_id": game_id, "username": username, "player_order": order}
                )
        except (json.JSONDecodeError, TypeError) as e:
            print(
                f"    ⚠️  Warning: Could not parse player JSON for game {game_id}: {e}"
            )
            continue

    if game_players_data:
        conn.execute(
            text("""
                INSERT INTO game_players (game_id, username, player_order)
                VALUES (:game_id, :username, :player_order)
            """),
            game_players_data,
        )
        print(f"    ✓ Migrated {len(game_players_data)} game-player associations")


def migrate_round_scores(conn) -> None:
    """Migrate round score data from JSON to normalized table."""
    # Fetch all rounds with their score JSON
    rounds_result = conn.execute(
        text(
            "SELECT id, player_raw_scores_json FROM rounds WHERE player_raw_scores_json IS NOT NULL"
        )
    )

    round_scores_data = []
    for round_id, scores_json in rounds_result:
        if not scores_json:
            continue

        try:
            scores_dict = json.loads(scores_json)
            for username, raw_score in scores_dict.items():
                round_scores_data.append(
                    {"round_id": round_id, "username": username, "raw_score": raw_score}
                )
        except (json.JSONDecodeError, TypeError) as e:
            print(
                f"    ⚠️  Warning: Could not parse scores JSON for round {round_id}: {e}"
            )
            continue

    if round_scores_data:
        conn.execute(
            text("""
                INSERT INTO round_scores (round_id, username, raw_score)
                VALUES (:round_id, :username, :raw_score)
            """),
            round_scores_data,
        )
        print(f"    ✓ Migrated {len(round_scores_data)} round scores")


def downgrade() -> None:
    """Downgrade schema - remove normalized tables and restore JSON-only."""
    print("⚠️  Downgrading: Removing normalized tables...")
    print("    Note: JSON columns will be preserved with existing data")

    # Drop normalized tables
    op.drop_table("round_scores")
    op.drop_table("game_players")

    # Restore JSON columns to NOT NULL (only if you want strict schema)
    # Skipping this to allow flexibility

    print("  ✓ Downgrade complete")
