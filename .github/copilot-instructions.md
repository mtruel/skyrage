# Skyrage – AI agent working notes

## Big picture
- Minimal Python project targeting 3.13 with a src layout; entry point is `src/main.py`.
- Goals in `README.md` indicate a small web app for Skyjo game tracking with API + DB (FastAPI + Sqlalchemy) and a frontend (FastAPI + HTMX)
- Package management uses uv (presence of `uv.lock`). Use uv for installs and running Python.

## Stack and tooling (as declared)
- Runtime: Python >= 3.13
- Web: fastapi + htmx
- ORM/DB: Sqlalchemy
- Tests: pytest
- Lint/format: ruff and ty
- Package manager: uv

## Common workflows
- Install deps (creates a virtual env if needed):
  ```sh
  uv sync
  ```
- Run the current app:
  ```sh
  uv run fastapi src/main.py
  ```
- Run tests :
  ```sh
  uv run pytest -q
  ```
- Lint and format:
  ```sh
  uvx ruff check .
  uvx ruff format .
  uvx ty check .
  ```

## Mandatory
- At the end of every task, run the formater, linter and tests. 

## Conventions visible in this repo
- Source code lives under `src/`. Keep new modules there (e.g., `src/api.py`, `src/db.py`) and import relatively within `src`.
- Keep tooling simple: allays use uv commands (`uv run …` / `uv sync`), `uv run pytest` for tests, `uvx ruff ...` and `uvx ty check` for lint/format.
- Prefer small, composable modules over one large file as features grow.


## Notes and gaps for agents
- If you introduce config or env vars, document them in `README.md`. Ask me to define them in an .env file. 
- Use the context7 mcp to get docs of the library you use as needed.