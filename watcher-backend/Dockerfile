FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, reproducible dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency definitions first (Docker layer caching)
COPY pyproject.toml ./

# Install all dependencies using uv
RUN uv pip install --system --no-cache ".[ai]"

COPY . .

# Ensure runtime directories exist
RUN mkdir -p \
    data/uploads \
    data/results \
    app/queries \
    graph/queries

EXPOSE 8001

# Liveness probe: GET /api/v1/health must return 200
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
