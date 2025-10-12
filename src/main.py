from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from api import router as api_router
from db import GameDB, PlayerDB, get_db_session, init_db

app = FastAPI()

# Initialize database
init_db()

# Include API routes
app.include_router(api_router)

templates = Jinja2Templates(directory=Path("src/templates"))


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Landing page with list of games."""
    session = get_db_session()
    try:
        games = session.query(GameDB).order_by(GameDB.created_at.desc()).limit(20).all()
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "games": games},
        )
    finally:
        session.close()


@app.get("/game/new", response_class=HTMLResponse)
async def new_game_page(request: Request):
    """Display player selection page for creating a new game."""
    session = get_db_session()
    try:
        players = session.query(PlayerDB).order_by(PlayerDB.username).all()
        return templates.TemplateResponse(
            "new_game.html",
            {"request": request, "players": players},
        )
    finally:
        session.close()


@app.post("/game/create")
async def create_new_game(request: Request, players: list[str] = Form(...)):
    """Create a new game with selected players and redirect to game page."""
    session = get_db_session()
    try:
        # Validate we have at least 2 players
        if not players or len(players) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 players are required to start a game",
            )

        # Create game with selected players
        game = GameDB(player_usernames=players)
        session.add(game)
        session.commit()
        session.refresh(game)

        # Auto-create player records if they don't exist (shouldn't happen since we're selecting from existing)
        for username in game.player_usernames:
            existing = session.query(PlayerDB).filter_by(username=username).first()
            if not existing:
                player = PlayerDB(username=username, surname=None)
                session.add(player)
        session.commit()

        # Redirect to the newly created game page
        return RedirectResponse(url=f"/game/{game.id}", status_code=303)
    finally:
        session.close()


@app.delete("/game/{game_id}")
async def delete_game(game_id: int):
    """Delete a game and all its associated rounds."""
    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        session.delete(game)
        session.commit()

        return {"success": True, "message": "Game deleted successfully"}
    finally:
        session.close()


@app.get("/players", response_class=HTMLResponse)
async def players_page(request: Request):
    """Display all players with their usernames and surnames."""
    session = get_db_session()
    try:
        players = session.query(PlayerDB).order_by(PlayerDB.username).all()
        return templates.TemplateResponse(
            "players.html",
            {"request": request, "players": players},
        )
    finally:
        session.close()


@app.post("/player/update", response_class=HTMLResponse)
async def update_player_surname(
    request: Request, username: str = Form(...), surname: str = Form(...)
):
    """Update a player's surname via HTMX."""
    session = get_db_session()
    try:
        player = session.query(PlayerDB).filter_by(username=username).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        # Update surname (allow empty string to clear it)
        player.surname = surname.strip() if surname.strip() else None
        session.commit()

        # Return the updated display HTML fragment for HTMX
        is_empty = not player.surname
        display_class = "surname-empty" if is_empty else ""
        display_text = player.surname or "(no surname)"

        return f"""
            <div class="surname-display">
                <span class="{display_class}">{display_text}</span>
            </div>
        """
    finally:
        session.close()


@app.post("/player/create")
async def create_player(
    request: Request, username: str = Form(...), surname: str = Form("")
):
    """Create a new player."""
    session = get_db_session()
    try:
        # Validate username
        if not username or not username.strip():
            raise HTTPException(status_code=400, detail="Username is required")

        username = username.strip()

        # Check if player already exists
        existing = session.query(PlayerDB).filter_by(username=username).first()
        if existing:
            raise HTTPException(
                status_code=400, detail=f"Player '{username}' already exists"
            )

        # Create new player
        player = PlayerDB(
            username=username, surname=surname.strip() if surname.strip() else None
        )
        session.add(player)
        session.commit()

        return {"success": True, "username": username, "surname": player.surname}
    finally:
        session.close()


@app.get("/game/{game_id}", response_class=HTMLResponse)
async def game_page(request: Request, game_id: int):
    """Main game page."""
    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        # Fetch player details (username and surname) for all players in the game
        player_details = []
        for username in game.player_usernames:
            player = session.query(PlayerDB).filter_by(username=username).first()
            if player:
                player_details.append(
                    {"username": player.username, "surname": player.surname}
                )
            else:
                # Fallback if player not found in DB
                player_details.append({"username": username, "surname": None})

        # Build display data for completed rounds
        rounds_display = []
        for round_db in game.rounds:
            scores = round_db.player_raw_scores
            min_score = min(scores.values()) if scores else None

            final_scores = {}
            displays = {}
            details = {}

            # First pass: calculate all final scores to find the minimum
            for username in game.player_usernames:
                if username in scores:
                    raw_score = scores[username]
                    finished_first = round_db.round_ender_username == username
                    is_lowest = raw_score == min_score

                    # Calculate final score with doubling rule
                    if finished_first and not is_lowest and raw_score > 0:
                        final_score = raw_score * 2
                    else:
                        final_score = raw_score

                    final_scores[username] = final_score

            # Find the minimum final score (after doubling)
            min_final_score = min(final_scores.values()) if final_scores else None

            # Second pass: build display strings with winner marker
            for username in game.player_usernames:
                if username in scores:
                    raw_score = scores[username]
                    finished_first = round_db.round_ender_username == username
                    is_lowest = raw_score == min_score
                    final_score = final_scores[username]
                    is_winner = final_score == min_final_score

                    # Build display string (just the final score, aligned right)
                    displays[username] = str(final_score)

                    # Build detail display - show "winner", "finished first" text and raw score if doubled
                    detail_parts = []
                    if is_winner:
                        detail_parts.append("winner")
                    if finished_first:
                        detail_parts.append("finished first")
                    if finished_first and not is_lowest and raw_score > 0:
                        detail_parts.append(f"[{raw_score} x2]")
                    details[username] = " ".join(detail_parts) if detail_parts else ""

            rounds_display.append(
                {
                    "number": round_db.round_number,
                    "displays": displays,
                    "details": details,
                    "final_scores": final_scores,
                }
            )

        # Current round data (empty for new round)
        current_round = {"scores": {}, "finished_first": None}

        # Check if game is finished
        game_ended = game.finished_at is not None
        winner_text = ""
        if game_ended:
            # Calculate final totals
            final_totals = {username: 0 for username in game.player_usernames}
            for round_display in rounds_display:
                for username, score in round_display["final_scores"].items():
                    final_totals[username] += score

            min_total = min(final_totals.values())
            winners = [u for u, s in final_totals.items() if s == min_total]
            winner_text = f"Winner: {', '.join(winners)} with {min_total} points!"

        return templates.TemplateResponse(
            "game.html",
            {
                "request": request,
                "game_id": game_id,
                "players": game.player_usernames,
                "player_details": player_details,
                "rounds": rounds_display,
                "current_round": current_round,
                "game_ended": game_ended,
                "winner_text": winner_text,
            },
        )
    finally:
        session.close()


@app.post("/game/{game_id}/update-player-name", response_class=HTMLResponse)
async def update_player_name(
    request: Request, game_id: int, player_idx: int = Form(...), name: str = Form(...)
):
    """Update a player's name."""
    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if game.finished_at is not None:
            raise HTTPException(status_code=400, detail="Cannot edit finished game")

        if 0 <= player_idx < len(game.player_usernames):
            player_usernames = game.player_usernames
            old_username = player_usernames[player_idx]
            new_username = name or f"Player {player_idx + 1}"

            # Check if new username already exists in game
            if new_username != old_username and new_username in player_usernames:
                # Just redirect back without change
                return await game_page(request, game_id)

            player_usernames[player_idx] = new_username
            game.player_usernames = player_usernames

            # Create player record if doesn't exist
            existing = session.query(PlayerDB).filter_by(username=new_username).first()
            if not existing:
                player = PlayerDB(username=new_username, surname=None)
                session.add(player)

            session.commit()

        return await game_page(request, game_id)
    finally:
        session.close()


@app.get("/game/{game_id}/available-players", response_class=HTMLResponse)
async def get_available_players(request: Request, game_id: int):
    """Get list of available players (not already in the game) for modal selection."""
    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        # Get all players from database
        all_players = session.query(PlayerDB).order_by(PlayerDB.username).all()

        # Filter out players already in the game
        available_players = [
            p for p in all_players if p.username not in game.player_usernames
        ]

        # Return HTML fragment for the modal
        if not available_players:
            return """
                <div style="text-align: center; padding: 2rem; color: #666;">
                    <p>No additional players available.</p>
                    <p>All players in the database are already in this game.</p>
                </div>
            """

        html_parts = []
        for player in available_players:
            surname_html = (
                f'<div class="player-surname">{player.surname}</div>'
                if player.surname
                else ""
            )
            html_parts.append(
                f"""
                <div class="modal-player-btn" onclick="selectPlayerForGame('{player.username}', {game_id})">
                    <div class="player-username">{player.username}</div>
                    {surname_html}
                </div>
                """
            )

        return "".join(html_parts)
    finally:
        session.close()


@app.post("/game/{game_id}/add-player", response_class=HTMLResponse)
async def add_player(request: Request, game_id: int, username: str = Form(None)):
    """Add a player to the game by username."""
    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if game.finished_at is not None:
            raise HTTPException(status_code=400, detail="Cannot edit finished game")

        # If username is provided, use it; otherwise generate a default name
        if username:
            # Check if player already in game
            if username in game.player_usernames:
                raise HTTPException(
                    status_code=400, detail="Player already in this game"
                )
            new_username = username
        else:
            # Fallback to old behavior for backward compatibility
            player_num = len(game.player_usernames) + 1
            new_username = f"Player {player_num}"

        player_usernames = game.player_usernames
        player_usernames.append(new_username)
        game.player_usernames = player_usernames

        # Create player record if doesn't exist
        existing = session.query(PlayerDB).filter_by(username=new_username).first()
        if not existing:
            player = PlayerDB(username=new_username, surname=None)
            session.add(player)

        session.commit()

        return await game_page(request, game_id)
    finally:
        session.close()


@app.post("/game/{game_id}/save-round", response_class=HTMLResponse)
async def save_round(request: Request, game_id: int):
    """Save the current round."""
    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if game.finished_at is not None:
            raise HTTPException(status_code=400, detail="Cannot edit finished game")

        # Parse form data
        form = await request.form()
        scores = {}
        finished_first = None
        errors = []

        for key, value in form.items():
            if key.startswith("score_"):
                player_idx = int(key.split("_")[1])
                username = game.player_usernames[player_idx]

                if value and isinstance(value, str) and value.strip():
                    try:
                        score_value = int(value)
                        # Validate score range
                        if score_value < -15 or score_value > 120:
                            errors.append(
                                f"Score for {username} ({score_value}) is outside the valid range (-15 to 120)"
                            )
                        else:
                            scores[username] = score_value
                    except ValueError:
                        errors.append(
                            f"Invalid score for {username}: '{value}' is not a valid number"
                        )
            elif key == "finished_first" and value and isinstance(value, str):
                finished_first = int(value)

        # Validate that all players have scores
        if len(scores) < len(game.player_usernames):
            missing_players = [
                username for username in game.player_usernames if username not in scores
            ]
            errors.append(f"Missing scores for: {', '.join(missing_players)}")

        # If there are validation errors, return to game page with errors
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))

        # Need at least some scores and a round ender
        if not scores:
            raise HTTPException(
                status_code=400, detail="No scores provided for this round"
            )

        # Determine round ender
        if finished_first is not None and 0 <= finished_first < len(
            game.player_usernames
        ):
            round_ender_username = game.player_usernames[finished_first]
        else:
            # Default to first player who has a score
            round_ender_username = next(iter(scores.keys()))

        # Create round
        from db import RoundDB

        round_number = len(game.rounds) + 1
        round_obj = RoundDB(
            game_id=game_id,
            round_number=round_number,
            player_raw_scores=scores,
            round_ender_username=round_ender_username,
        )
        session.add(round_obj)
        session.commit()

        return await game_page(request, game_id)
    finally:
        session.close()


@app.post("/game/{game_id}/end-game", response_class=HTMLResponse)
async def end_game(request: Request, game_id: int):
    """End the game and show the winner."""
    from datetime import UTC, datetime

    session = get_db_session()
    try:
        game = session.query(GameDB).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        game.finished_at = datetime.now(UTC)
        session.commit()

        return await game_page(request, game_id)
    finally:
        session.close()
