# BackendForge API

A production-ready REST API built with **FastAPI**, **PostgreSQL**, **Redis**, and **Docker**.  
Batteries included: JWT auth with refresh token rotation, RBAC, background jobs, file uploads, structured logging, and full test coverage.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Cache | Redis 7 |
| Auth | JWT (python-jose) + bcrypt |
| Background Jobs | Celery + Redis broker |
| Testing | Pytest + pytest-asyncio + httpx |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
backendforge-api/
├── app/
│   ├── main.py                  # FastAPI app factory, middleware, lifespan
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (env vars)
│   │   ├── security.py          # JWT creation/decoding, password hashing
│   │   └── logging.py           # structlog setup
│   ├── api/
│   │   ├── deps.py              # Auth dependencies, RBAC factories
│   │   └── routes/
│   │       ├── auth.py          # Register, login, refresh, logout, password reset
│   │       ├── users.py         # Profile, admin user management
│   │       ├── files.py         # File upload
│   │       ├── admin.py         # Admin dashboard
│   │       └── health.py        # Health checks
│   ├── models/
│   │   ├── user.py              # User, UserRole
│   │   └── token.py             # RefreshToken, UploadedFile
│   ├── schemas/
│   │   ├── auth.py              # Request/response schemas for auth
│   │   ├── user.py              # User schemas
│   │   └── file.py              # File schemas
│   ├── services/
│   │   ├── auth_service.py      # Auth business logic
│   │   ├── user_service.py      # User CRUD + Redis cache
│   │   ├── email_service.py     # Celery tasks for email
│   │   └── file_service.py      # File validation + storage
│   ├── db/
│   │   ├── session.py           # Async SQLAlchemy engine + Base
│   │   └── redis.py             # Redis client singleton
│   ├── middleware/
│   │   ├── logging.py           # Request logging middleware
│   │   └── exception_handler.py # Global exception handlers
│   └── utils/
│       └── seed.py              # Admin user seed
├── tests/
│   ├── conftest.py              # Pytest fixtures (SQLite test DB)
│   ├── test_health.py
│   ├── test_auth.py
│   └── test_users.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── .env.example
└── README.md
```

---

## Quick Start

### Prerequisites
- Docker ≥ 24 and Docker Compose v2
- (For local dev) Python 3.11+

---

### 1. Docker — the fastest path

```bash
# Clone and enter the project
git clone https://github.com/your-username/backendforge-api.git
cd backendforge-api

# Copy environment file
cp .env.example .env

# Build and start everything (DB, Redis, API, Celery worker)
docker compose up --build

# In a separate terminal — run migrations (first time only)
docker compose run --rm migrate
```

The API is now running at:
- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health:** http://localhost:8000/api/v1/health

Seed admin credentials (from `.env`):
- **Email:** `admin@backendforge.dev`
- **Password:** `Admin@1234`

---

### 2. Local Development (without Docker)

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# SQLite driver for tests
pip install aiosqlite

# Copy and edit env (point DATABASE_URL at a local Postgres, REDIS_URL at local Redis)
cp .env.example .env

# Run DB migrations
alembic upgrade head

# Seed admin user
python -m app.utils.seed

# Start the API
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.services.email_service.celery_app worker --loglevel=info
```

---

## Migration Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Generate a new migration (after changing models)
alembic revision --autogenerate -m "describe_your_change"

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

---

## Test Commands

```bash
# Install test extras
pip install aiosqlite

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run a specific test file
pytest tests/test_auth.py -v

# Run a specific test
pytest tests/test_auth.py::test_login -v
```

Tests use **SQLite in-memory** — no running Postgres or Redis required.

---

## API Endpoints

### Auth `/api/v1/auth`
| Method | Path | Description |
|---|---|---|
| POST | `/register` | Create a new account |
| POST | `/login` | Get access + refresh tokens |
| POST | `/refresh` | Rotate refresh token |
| POST | `/logout` | Revoke refresh token |
| POST | `/forgot-password` | Request reset email |
| POST | `/reset-password` | Set new password with token |

### Users `/api/v1/users`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/me` | User+ | Get own profile (cached) |
| PATCH | `/me` | User+ | Update name / bio |
| GET | `/` | Manager+ | List all users |
| GET | `/{id}` | Manager+ | Get user by ID |
| PATCH | `/{id}` | Admin | Update role / active status |

### Files `/api/v1/files`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/upload` | User+ | Upload a file (max 10 MB) |

### Admin `/api/v1/admin`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/dashboard` | Admin | DB + Redis stats |

### Health `/api/v1/health`
| Method | Path | Description |
|---|---|---|
| GET | `/` | Basic liveness check |
| GET | `/detailed` | DB + Redis connectivity |

---

## Roles & Permissions

| Role | Access |
|---|---|
| `user` | Own profile only |
| `manager` | List / view all users |
| `admin` | Full access including role management |

---

## Environment Variables

See `.env.example` for the full list. Key variables:

```env
SECRET_KEY=           # Min 32 chars — change in production!
DATABASE_URL=         # async postgres URL
REDIS_URL=            # redis://host:port/db
SMTP_HOST=            # for password reset emails
ADMIN_EMAIL=          # seeded admin email
ADMIN_PASSWORD=       # seeded admin password
```

---

## Packaging and Deployment

### Zip the project locally

```bash
cd ..
zip -r backendforge-api.zip backendforge-api/ \
  --exclude "backendforge-api/.venv/*" \
  --exclude "backendforge-api/__pycache__/*" \
  --exclude "backendforge-api/*.pyc" \
  --exclude "backendforge-api/test.db" \
  --exclude "backendforge-api/uploads/*" \
  --exclude "backendforge-api/.git/*"
```

### Upload to GitHub

```bash
cd backendforge-api
git init
git add .
git commit -m "feat: initial BackendForge API"
git branch -M main
git remote add origin https://github.com/your-username/backendforge-api.git
git push -u origin main
```

---

## Production Checklist

- [ ] Set a strong random `SECRET_KEY` (at least 64 chars)
- [ ] Set `APP_ENV=production` and `DEBUG=false`
- [ ] Configure real SMTP credentials
- [ ] Set `ALLOWED_ORIGINS` to your frontend domain
- [ ] Use a managed Postgres (RDS, Supabase, Neon)
- [ ] Use a managed Redis (Upstash, ElastiCache)
- [ ] Add a reverse proxy (Nginx / Caddy) with TLS
- [ ] Enable Celery Flower for task monitoring
- [ ] Set up log aggregation (Datadog, Grafana Loki)

---

## License

MIT
#   b a c k e n d f o r g e - a p i  
 