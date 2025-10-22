"""Tests for dangling players deletion functionality."""

from db import PlayerDB, get_db_session, init_db
from tests.conftest import create_game_with_players, create_round_with_scores


def test_delete_dangling_players_empty_db(tmp_path):
    """Test deleting dangling players when database is empty."""
    from api import router
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    # Setup test database
    db_path = tmp_path / "test.db"
    database_url = f"sqlite:///{db_path}"
    init_db(database_url)

    # Create app with router
    app = FastAPI()
    app.include_router(router)

    # Create test client
    client = TestClient(app)

    # Mock get_db_session to use test database
    import api

    original_get_db = api.get_db_session

    def mock_get_db():
        from db import get_db_session

        return get_db_session(database_url)

    api.get_db_session = mock_get_db  # type: ignore[method-assign]

    try:
        # Test with empty database
        response = client.delete("/api/dangling_players")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
        assert data["deleted_usernames"] == []
        assert data["total_players"] == 0
        assert data["protected_players"] == 0
    finally:
        api.get_db_session = original_get_db


def test_delete_dangling_players_with_dangling(tmp_path):
    """Test deleting dangling players when some exist."""
    from api import router
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    # Setup test database
    db_path = tmp_path / "test.db"
    database_url = f"sqlite:///{db_path}"
    init_db(database_url)

    # Create test data
    session = get_db_session(database_url)
    try:
        # Create players - some will be dangling
        dangling1 = PlayerDB(username="dangling1", surname="Dangling")
        dangling2 = PlayerDB(username="dangling2", surname="Also Dangling")
        protected = PlayerDB(username="protected", surname="Protected")

        session.add_all([dangling1, dangling2, protected])

        # Create a game with the protected player
        game = create_game_with_players(session, ["protected"])
        session.commit()
        session.refresh(game)
    finally:
        session.close()

    # Create app with router
    app = FastAPI()
    app.include_router(router)

    # Create test client
    client = TestClient(app)

    # Mock get_db_session to use test database
    import api

    original_get_db = api.get_db_session

    def mock_get_db():
        from db import get_db_session

        return get_db_session(database_url)

    api.get_db_session = mock_get_db  # type: ignore[method-assign]

    try:
        # Test deleting dangling players
        response = client.delete("/api/dangling_players")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 2
        assert set(data["deleted_usernames"]) == {"dangling1", "dangling2"}
        assert data["total_players"] == 3
        assert data["protected_players"] == 1

        # Verify protected player still exists
        response = client.get("/api/players/protected")
        assert response.status_code == 200

        # Verify dangling players are gone
        response = client.get("/api/players/dangling1")
        assert response.status_code == 404
    finally:
        api.get_db_session = original_get_db


def test_delete_dangling_players_with_rounds(tmp_path):
    """Test that players in rounds are protected."""
    from api import router
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    # Setup test database
    db_path = tmp_path / "test.db"
    database_url = f"sqlite:///{db_path}"
    init_db(database_url)

    # Create test data
    session = get_db_session(database_url)
    try:
        # Create players
        dangling = PlayerDB(username="dangling", surname="Dangling")
        in_round = PlayerDB(username="in_round", surname="InRound")
        round_ender = PlayerDB(username="round_ender", surname="RoundEnder")

        session.add_all([dangling, in_round, round_ender])

        # Create a game
        game = create_game_with_players(session, ["in_round", "round_ender"])
        session.commit()
        session.refresh(game)

        # Create a round
        create_round_with_scores(
            session,
            game.id,
            1,
            {"in_round": 10, "round_ender": 20},
            "round_ender",
        )
        session.commit()
    finally:
        session.close()

    # Create app with router
    app = FastAPI()
    app.include_router(router)

    # Create test client
    client = TestClient(app)

    # Mock get_db_session to use test database
    import api

    original_get_db = api.get_db_session

    def mock_get_db():
        from db import get_db_session

        return get_db_session(database_url)

    api.get_db_session = mock_get_db  # type: ignore[method-assign]

    try:
        # Test deleting dangling players
        response = client.delete("/api/dangling_players")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 1
        assert data["deleted_usernames"] == ["dangling"]
        assert data["total_players"] == 3
        assert data["protected_players"] == 2

        # Verify protected players still exist
        response = client.get("/api/players/in_round")
        assert response.status_code == 200
        response = client.get("/api/players/round_ender")
        assert response.status_code == 200
    finally:
        api.get_db_session = original_get_db
