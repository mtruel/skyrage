# Docker Deployment Guide

## Quick Start

1. **Prepare the data directory:**
   ```bash
   mkdir -p data2
   ```

2. **Run with Docker Compose:**
   ```bash
   docker compose up -d
   ```

3. **Access the application:**
   - Open your browser at `http://localhost:8001`
   - The database will be persisted in the `data2` directory

## Configuration

You can override configuration via environment variables in `docker-compose.yml`:

```yaml
services:
  skyrage:
    environment:
      - DATABASE_PATH=/app/data/skyrage.db
```

## Viewing Logs

```bash
docker logs skyrage-app
# or follow logs:
docker logs -f skyrage-app
```

## Stopping the Application

```bash
docker compose down
```

To also remove the data volume:
```bash
docker compose down -v
```

## Troubleshooting

### Container keeps restarting

Check the logs for errors:
```bash
docker logs skyrage-app --tail 50
```

Common causes:
- Port 8001 already in use on the host
- Database corruption (delete `data2/skyrage.db` and restart)
- Missing data2 directory
