"""Tests for config.py configuration management."""

import tempfile
from pathlib import Path

import pytest

from config import get_database_url, load_config


class TestLoadConfig:
    """Tests for load_config() function."""

    def test_load_config_file_exists(self):
        """Test loading config from an existing YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("database_path: test.db\n")
            f.write("some_other_setting: value\n")
            config_path = f.name

        try:
            config = load_config(config_path)
            assert config["database_path"] == "test.db"
            assert config["some_other_setting"] == "value"
        finally:
            Path(config_path).unlink()

    def test_load_config_file_missing(self):
        """Test loading config when file doesn't exist returns defaults."""
        config = load_config("nonexistent_file.yaml")
        assert config == {"database_path": "skyrage.db"}

    def test_load_config_empty_file(self):
        """Test loading config from empty YAML file returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            config = load_config(config_path)
            assert config == {}
        finally:
            Path(config_path).unlink()

    def test_load_config_with_path_object(self):
        """Test loading config with Path object instead of string."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("database_path: test.db\n")
            config_path = Path(f.name)

        try:
            config = load_config(config_path)
            assert config["database_path"] == "test.db"
        finally:
            config_path.unlink()

    def test_load_config_malformed_yaml(self):
        """Test loading malformed YAML returns None or empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:")
            config_path = f.name

        try:
            # Should raise or return gracefully
            with pytest.raises(Exception):
                load_config(config_path)
        finally:
            Path(config_path).unlink()


class TestGetDatabaseUrl:
    """Tests for get_database_url() function."""

    def test_get_database_url_default(self):
        """Test getting database URL with default config."""
        url = get_database_url("nonexistent_config.yaml")
        assert url == "sqlite:///skyrage.db"

    def test_get_database_url_custom_path(self):
        """Test getting database URL with custom path from config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("database_path: custom.db\n")
            config_path = f.name

        try:
            url = get_database_url(config_path)
            assert url == "sqlite:///custom.db"
        finally:
            Path(config_path).unlink()

    def test_get_database_url_in_memory(self):
        """Test getting database URL for in-memory database."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("database_path: ':memory:'\n")
            config_path = f.name

        try:
            url = get_database_url(config_path)
            assert url == "sqlite:///:memory:"
        finally:
            Path(config_path).unlink()

    def test_get_database_url_absolute_path(self):
        """Test getting database URL with absolute path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("database_path: /tmp/test.db\n")
            config_path = f.name

        try:
            url = get_database_url(config_path)
            assert url == "sqlite:////tmp/test.db"
        finally:
            Path(config_path).unlink()

    def test_get_database_url_relative_path(self):
        """Test getting database URL with relative path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("database_path: data/test.db\n")
            config_path = f.name

        try:
            url = get_database_url(config_path)
            assert url == "sqlite:///data/test.db"
        finally:
            Path(config_path).unlink()

    def test_get_database_url_with_path_object(self):
        """Test getting database URL with Path object."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("database_path: test.db\n")
            config_path = Path(f.name)

        try:
            url = get_database_url(config_path)
            assert url == "sqlite:///test.db"
        finally:
            config_path.unlink()

    def test_get_database_url_empty_config(self):
        """Test getting database URL when config is empty."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            url = get_database_url(config_path)
            # Should use default
            assert url == "sqlite:///skyrage.db"
        finally:
            Path(config_path).unlink()

    def test_get_database_url_special_characters(self):
        """Test getting database URL with special characters in path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("database_path: 'my-test_db.sqlite'\n")
            config_path = f.name

        try:
            url = get_database_url(config_path)
            assert url == "sqlite:///my-test_db.sqlite"
        finally:
            Path(config_path).unlink()
