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

## GitHub repo banao aur push karo

**Option A – Script se (recommended)**  
Pehle GitHub CLI install karo aur login karo, phir script chalao:

```bash
brew install gh
gh auth login
./scripts/create_repo_and_push.sh
```

Script automatically repo `topupgo-django` create karega aur push karega. Alag naam ke liye: `./scripts/create_repo_and_push.sh my-repo-name`

**Option B – Token se (gh nahi ho to)**  
GitHub pe Personal Access Token banao (Settings → Developer settings → Personal access tokens), phir:

```bash
export GITHUB_TOKEN=your_token_here
./scripts/create_repo_and_push.sh
```

**Option C – Manual**  
1. https://github.com/new pe jao → repo name: `topupgo-django` → Create repository.  
2. Local project me:

```bash
git remote add origin https://github.com/YOUR_USERNAME/topupgo-django.git
git push -u origin main
```

`YOUR_USERNAME` ki jagah apna GitHub username daalo.

---

## Git: Sirf apna naam Contributors me (cursoragent na aaye)

**Issue kyu aata hai:** Jab Cursor/IDE se commit karte ho to commit message me `Co-authored-by: Cursor <cursoragent@cursor.com>` add ho jata hai. GitHub isko second author maan kar **cursoragent** ko bhi Contributors me dikhata hai.

**Future me issue na aaye – 2 tarike:**

### 1) Commit & push Terminal se (recommended)

Cursor ki jagah **Terminal.app** use karo jab commit/push karna ho:

```bash
cd /Users/apple/Desktop/topupgo-django
git add .
git commit -m "Your message"
git push origin main
```

Isse Cursor co-author add nahi karega, sirf tumhara naam rahega.

### 2) Cursor se commit karte waqt message edit karo

Agar Cursor se hi commit karna hai to **Commit message** me se ye line **delete** karo (agar dikhe):

```
Co-authored-by: Cursor <cursoragent@cursor.com>
```

Phir commit karo. Tab bhi sirf tumhara naam aayega.

---

**Agar phir bhi cursoragent Contributors me aa jaye:** ye script chalao (saare purane commits se Co-authored-by hata ke force push karega):

```bash
chmod +x scripts/fix_contributors.sh
./scripts/fix_contributors.sh
```

Uske baad GitHub pe repo page **refresh** karo; 1–2 min me Contributors update ho jata hai.
