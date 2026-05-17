# Company Structure Service


## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy async sessions
- Alembic migrations
- PostgreSQL 16
- uv for dependency management
- Docker Compose for local infrastructure

## Environment

Create `.env` in the project root. You can start from `.env.sample`:

```env
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=company_manager
LOG_LEVEL=INFO
```

The values above are correct for Docker Compose, because the app connects to the `db` service inside the Docker network.

# How to run
Download the project locally from GitHub:

```bash
git clone https://github.com/boris-devs/company-structure-service.git
```

## Run With Docker Compose


This is the recommended way to run the project.

```bash
docker compose up --build
```

Compose will:

1. Start PostgreSQL on host port `5433`.
2. Wait until PostgreSQL is healthy.
3. Run Alembic migrations with `uv run alembic upgrade head`.
4. Start the API with `uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload`.

Open the API docs:

```text
http://localhost:8000/docs
```

Open the ReDoc docs:

```text
http://localhost:8000/redoc
```

Stop the services:

```bash
docker compose down
```

Stop the services and remove the database volume:

```bash
docker compose down -v
```

## Useful Commands

Create a new Alembic migration after model changes:

```bash
uv run alembic revision --autogenerate -m "describe change"
```

Apply migrations:

```bash
uv run alembic upgrade head
```

Run Ruff checks:

```bash
uv run ruff check .
```

## API Overview

Base prefix:

```text
/api/v1
```

Department endpoints:

```text
POST   /api/v1/departments/
POST   /api/v1/departments/{department_id}/employees/
GET    /api/v1/departments/{department_id}/
PATCH  /api/v1/departments/{department_id}/
DELETE /api/v1/departments/{department_id}/
```

For exact request and response schemas, use the generated Swagger UI at `/docs`.

## Notes

- Do not commit real production secrets in `.env`.
- Docker Compose uses `POSTGRES_HOST=db`.
- Local execution uses `POSTGRES_HOST=localhost` and `POSTGRES_PORT=5433` if PostgreSQL is started through Compose.
