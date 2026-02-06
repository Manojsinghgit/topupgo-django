# TopUpGo Django

Django project with REST Framework – **account** app (Account table) and **wallet** app (Wallet + Transaction tables). Database: **PostgreSQL** (optional SQLite fallback).

## Apps

- **account** – Account model (email, username, phone_no, profile_photo, etc.)
- **wallet** – Wallet table + Transaction table (address, balance, transaction_id, amount, fee, final_amount, etc.)

## Database: PostgreSQL

Project uses **PostgreSQL** by default. Create DB and set env (or use `.env`):

```bash
# Create database (PostgreSQL must be running)
createdb topupgo

# Copy env example and edit password
cp .env.example .env
# Edit .env: POSTGRES_PASSWORD=your_password
```

Env vars (see `.env.example`):

- `POSTGRES_DB` (default: topupgo)
- `POSTGRES_USER` (default: postgres)
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST` (default: localhost)
- `POSTGRES_PORT` (default: 5432)

To use **SQLite** instead (no PostgreSQL needed):

```bash
export USE_SQLITE=1
python manage.py migrate
```

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# With PostgreSQL: create DB, set .env, then:
python manage.py migrate
python manage.py runserver

# Or with SQLite:
USE_SQLITE=1 python manage.py migrate
USE_SQLITE=1 python manage.py runserver
```

Migrations are already created (`account`, `wallet`). Run `python manage.py migrate` after DB is ready.

## Swagger / API docs

- **Swagger UI:** http://127.0.0.1:8000/swagger/
- **ReDoc:** http://127.0.0.1:8000/redoc/
- **OpenAPI JSON:** http://127.0.0.1:8000/swagger.json

Run server: `python manage.py runserver` (or `USE_SQLITE=1 python manage.py runserver`).

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET, POST | `/api/accounts/` | List / Create account |
| GET, PUT, PATCH, DELETE | `/api/accounts/<id>/` | Account detail |
| GET, POST | `/api/wallets/` | List / Create wallet |
| GET, PUT, PATCH, DELETE | `/api/wallets/<id>/` | Wallet detail |
| GET, POST | `/api/transactions/` | List / Create transaction |
| GET, PUT, PATCH, DELETE | `/api/transactions/<id>/` | Transaction detail |

## Push to GitHub (repo banao aur push karo)

Repo already init + first commit ho chuka hai. Ab GitHub pe naya repo banao aur push karo:

1. GitHub.com pe jao → **New repository** → name: `topupgo-django` (ya jo chaho) → Create.
2. Local project me remote add karke push karo:

```bash
git remote add origin https://github.com/YOUR_USERNAME/topupgo-django.git
git branch -M main
git push -u origin main
```

`YOUR_USERNAME` ki jagah apna GitHub username daalo. Agar repo name alag hai to URL me wahi use karo.
