FROM python:3.12-slim AS builder

# Receive the port from docker-compose build args
ARG APP_PORT

WORKDIR /app

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python -

# Environment variables for Poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Copy project files
COPY poetry.lock pyproject.toml ./

# Install dependencies using Poetry (without dev dependencies)
RUN /root/.local/bin/poetry install --only main --no-interaction --no-ansi --no-root

# -- Final stage --
FROM python:3.12-slim

WORKDIR /app

# Install necessary packages for running the application
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the installed dependencies from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . /app/

#Create Log base folder if it doesn't exist
RUN mkdir -p /var/log/techbuddy

# Set environment variables for Poetry and Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Expose the necessary port
# Set the port as an environment variable inside the container
ENV PORT=${APP_PORT}
EXPOSE ${PORT}

# Command to run the application (use shell form for variable expansion)
ENTRYPOINT ["/bin/sh", "-c", "gunicorn src.backend.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers 1"]