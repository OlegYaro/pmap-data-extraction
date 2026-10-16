FROM python:3.14-slim

RUN pip install --no-cache-dir poetry==2.4.1

WORKDIR /app
COPY pyproject.toml poetry.lock README.md ./
RUN poetry config virtualenvs.create false && poetry install --only main --no-root

COPY src ./src
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./
RUN poetry install --only-root

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
