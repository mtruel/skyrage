from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory=Path("src/templates"))

# In-memory game state (will be replaced with database later)
game_state: dict[str, Any] = {
    "players": ["Player 1", "Player 2", "Player 3"],
    "rounds": [],  # List of completed rounds
    "current_round": {
        "scores": {},  # player_idx: score
        "finished_first": None,  # player_idx who finished first
    },
}


def reset_game() -> None:
    """Reset the game state."""
    game_state["players"] = ["Player 1", "Player 2", "Player 3"]
    game_state["rounds"] = []
    game_state["current_round"] = {"scores": {}, "finished_first": None}


def calculate_round_result(
    raw_score: int, finished_first: bool, is_lowest: bool
) -> tuple[int, str]:
    """
    Calculate the final score for a round and generate display info.

    Returns:
        tuple: (final_score, display_string)
    """
    indicators = []
    final_score = raw_score

    if finished_first:
        indicators.append("[1]")
        # Double the score if finished first but NOT lowest
        if not is_lowest:
            final_score = raw_score * 2

    if is_lowest:
        indicators.append("[C]")

    display = (
        " ".join(indicators) + f" {final_score}" if indicators else str(final_score)
    )
    return final_score, display


def get_cumulative_score(player_idx: int, up_to_round: int | None = None) -> int:
    """Get cumulative score for a player up to a specific round."""
    total = 0
    rounds = game_state["rounds"][:up_to_round] if up_to_round else game_state["rounds"]
    for round_data in rounds:
        if player_idx in round_data["final_scores"]:
            total += round_data["final_scores"][player_idx]
    return total


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/game", response_class=HTMLResponse)
async def game_page(request: Request):
    """Main game page."""
    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "players": game_state["players"],
            "rounds": game_state["rounds"],
            "current_round": game_state["current_round"],
        },
    )


@app.post("/game/update-player-name", response_class=HTMLResponse)
async def update_player_name(
    request: Request, player_idx: int = Form(...), name: str = Form(...)
):
    """Update a player's name."""
    if 0 <= player_idx < len(game_state["players"]):
        game_state["players"][player_idx] = name or f"Player {player_idx + 1}"

    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "players": game_state["players"],
            "rounds": game_state["rounds"],
            "current_round": game_state["current_round"],
        },
    )


@app.post("/game/add-player", response_class=HTMLResponse)
async def add_player(request: Request):
    """Add a new player."""
    player_num = len(game_state["players"]) + 1
    game_state["players"].append(f"Player {player_num}")

    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "players": game_state["players"],
            "rounds": game_state["rounds"],
            "current_round": game_state["current_round"],
        },
    )


@app.post("/game/update-score", response_class=HTMLResponse)
async def update_score(
    request: Request, player_idx: int = Form(...), score: str = Form(...)
):
    """Update a player's score for the current round."""
    try:
        score_val = int(score) if score.strip() else None
        if score_val is not None:
            game_state["current_round"]["scores"][player_idx] = score_val
        elif player_idx in game_state["current_round"]["scores"]:
            del game_state["current_round"]["scores"][player_idx]
    except ValueError:
        pass

    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "players": game_state["players"],
            "rounds": game_state["rounds"],
            "current_round": game_state["current_round"],
        },
    )


@app.post("/game/toggle-first", response_class=HTMLResponse)
async def toggle_first(request: Request, player_idx: int = Form(...)):
    """Toggle the 'finished first' checkbox for a player."""
    current = game_state["current_round"]["finished_first"]
    if current == player_idx:
        game_state["current_round"]["finished_first"] = None
    else:
        game_state["current_round"]["finished_first"] = player_idx

    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "players": game_state["players"],
            "rounds": game_state["rounds"],
            "current_round": game_state["current_round"],
        },
    )


@app.post("/game/save-round", response_class=HTMLResponse)
async def save_round(request: Request):
    """Save the current round and start a new one."""
    current = game_state["current_round"]

    # Only save if we have some scores
    if current["scores"]:
        # Find the lowest score
        scores = current["scores"]
        min_score = min(scores.values()) if scores else None

        # Calculate final scores and display info
        final_scores = {}
        displays = {}
        details = {}

        for player_idx in range(len(game_state["players"])):
            if player_idx in scores:
                raw_score = scores[player_idx]
                finished_first = current["finished_first"] == player_idx
                is_lowest = raw_score == min_score

                final_score, display = calculate_round_result(
                    raw_score, finished_first, is_lowest
                )
                final_scores[player_idx] = final_score
                displays[player_idx] = display

                # Build detail display
                if finished_first and not is_lowest:
                    details[player_idx] = f"[{raw_score}x2] {final_score}"
                else:
                    details[player_idx] = str(raw_score)

        # Save the round
        round_num = len(game_state["rounds"]) + 1
        game_state["rounds"].append(
            {
                "number": round_num,
                "raw_scores": scores.copy(),
                "final_scores": final_scores,
                "displays": displays,
                "details": details,
                "finished_first": current["finished_first"],
            }
        )

        # Reset current round
        game_state["current_round"] = {"scores": {}, "finished_first": None}

    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "players": game_state["players"],
            "rounds": game_state["rounds"],
            "current_round": game_state["current_round"],
        },
    )


@app.post("/game/end-game", response_class=HTMLResponse)
async def end_game(request: Request):
    """End the game and show the winner."""
    # Calculate final cumulative scores
    final_scores = {}
    for player_idx in range(len(game_state["players"])):
        final_scores[player_idx] = get_cumulative_score(player_idx)

    # Find winner(s) - lowest score wins
    if final_scores:
        min_score = min(final_scores.values())
        winners = [idx for idx, score in final_scores.items() if score == min_score]
        winner_names = [game_state["players"][idx] for idx in winners]
        winner_text = f"Winner: {', '.join(winner_names)} with {min_score} points!"
    else:
        winner_text = "No rounds played yet!"

    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "players": game_state["players"],
            "rounds": game_state["rounds"],
            "current_round": game_state["current_round"],
            "game_ended": True,
            "winner_text": winner_text,
        },
    )
