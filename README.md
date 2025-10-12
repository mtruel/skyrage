# Skyrage 

Skyrage is a small web app to track results of for the SkyjoGames. 

Simples features: 
- An history of all pasts games 
- A ranking of players
- A statistics page for each player
- A page to record a new game while playing
- Detailled page for each recorded game

## Quick Start

### Local Development

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Run the application:
   ```bash
   uv run fastapi dev src/main.py
   ```

3. Open your browser at `http://localhost:8000`

### Docker Deployment

1. Build and run with Docker Compose:
   ```bash
   docker compose up -d
   ```

2. Access at `http://localhost:8000`

For detailed Docker instructions, see [README.Docker.md](./README.Docker.md)

## Development

### Running Tests

```bash
uv run pytest -q
```

### Linting and Formatting

```bash
uvx ruff check .
uvx ruff format .
uvx ty check .
```

## Configuration

The application can be configured via:
- `config.yaml` file (default: `database_path: "skyrage.db"`)
- `DATABASE_PATH` environment variable (takes precedence)

## Plan 

- [x] Make a first working backend with API and database
- [x] Make a first working frontend with FastAPI and HTMX
- [ ] Add Docker deployment supportrage is a small web app to track results of for the SkyjoGames. 

Simples features: 
- An history of all pasts games 
- A ranking of players
- A statistics page for each player
- A page to record a new game while playing
- Detailled page for each recorded game

## Plan 

- [ ] Make a first working backend with API and database
- [ ] Make a first working frontend with FastAPI and HTMX