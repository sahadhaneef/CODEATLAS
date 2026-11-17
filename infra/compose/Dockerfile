FROM python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
WORKDIR /app
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml alembic.ini ./
COPY services/api ./services/api
COPY migrations ./migrations
RUN python -m pip install --no-deps --no-build-isolation . && useradd --uid 10001 --create-home app
USER 10001
CMD ["python", "-m", "uvicorn", "codeatlas.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
