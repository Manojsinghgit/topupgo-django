# TopUpGo Django

Django project with REST Framework – **account** app (Account table) and **wallet** app (Wallet + Transaction tables).

## Apps

- **account** – Account model (email, username, phone_no, profile_photo, etc.)
- **wallet** – Wallet table + Transaction table (address, balance, transaction_id, amount, fee, final_amount, etc.)

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET, POST | `/api/accounts/` | List / Create account (account app) |
| GET, PUT, PATCH, DELETE | `/api/accounts/<id>/` | Account detail |
| GET, POST | `/api/wallets/` | List / Create wallet (wallet app) |
| GET, POST | `/api/transactions/` | List / Create transaction (wallet app) |

## Account POST body (example)

```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "phone_no": "+919876543210",
  "first_name": "John",
  "last_name": "Doe"
}
```

## Git push (apne repo pe)

```bash
git init
git add .
git commit -m "Initial: Django DRF, account, wallet, transaction"
git remote add origin https://github.com/YOUR_USERNAME/topupgo-django.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.
