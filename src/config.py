"""Configuration management for Skyrage."""

from pathlib import Path

import yaml


def load_config(config_path: str | Path = "config.yaml") -> dict:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to the config file (default: config.yaml in project root)

    Returns:
        Dictionary containing configuration values
    """
    config_file = Path(config_path)

    if not config_file.exists():
        # Return default config if file doesn't exist
        return {"database_path": "skyrage.db"}

    with open(config_file) as f:
        config = yaml.safe_load(f)

    return config or {}


def get_database_url(config_path: str | Path = "config.yaml") -> str:
    """
    Get the database URL from config.

    Args:
        config_path: Path to the config file

    Returns:
        SQLAlchemy database URL string
    """
    config = load_config(config_path)
    db_path = config.get("database_path", "skyrage.db")

    # Handle in-memory database
    if db_path == ":memory:":
        return "sqlite:///:memory:"

    # Regular file-based database
    return f"sqlite:///{db_path}"
