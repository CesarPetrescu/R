FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY README.md ./
COPY CHANGELOG.md LICENSE ./
COPY Dockerfile docker-compose.yml ./
COPY src ./src
COPY tests ./tests
COPY docs ./docs
COPY status ./status

RUN python -m pip install --upgrade pip \
    && python -m pip install -e . pytest

CMD ["python", "-m", "pytest", "-q"]
