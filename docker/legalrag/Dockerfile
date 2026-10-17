FROM ghcr.io/astral-sh/uv:0.6.14-python3.13-bookworm

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libavif-dev \
    pkg-config \
    libjpeg-dev \
    gcc \
    unzip \
    zip \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    curl \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY src/ .

# Create directory structure for Alembic
RUN mkdir -p /app/models/db_schemes/insurance_rag/

COPY docker/legalrag/alembic.ini \
    /app/models/db_schemes/insurance_rag/alembic.ini

COPY docker/legalrag/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]