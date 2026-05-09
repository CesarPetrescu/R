FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY README.md ./
COPY CHANGELOG.md LICENSE ./
COPY Dockerfile docker-compose.yml ./
COPY src ./src
COPY runtime ./runtime
COPY tests ./tests
COPY docs ./docs
COPY automations ./automations
COPY status ./status

RUN python -m pip install --upgrade pip \
    && python -m pip install -e . pytest

CMD ["python", "-m", "pytest", "-q"]
