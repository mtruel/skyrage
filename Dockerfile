# syntax=docker/dockerfile:1

# =========================================
# Stage 1: Build Stage - Install Dependencies
# =========================================
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-alpine AS builder

# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-install-project --no-dev

# =========================================
# Stage 2: Final Runtime Stage
# =========================================
FROM python:${PYTHON_VERSION}-alpine AS final

# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY src ./src
COPY config.yaml ./

# Create directory for database
RUN mkdir -p /app/data

# Set PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Set PYTHONPATH so Python can find modules in src/
ENV PYTHONPATH="/app/src"

# Expose the port that FastAPI listens on
EXPOSE 8000

# Run the FastAPI application using uvicorn
CMD ["fastapi", "run", "src/main.py", "--host", "0.0.0.0", "--port", "8000"]
