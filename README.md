# 📊 GST Accounting Management System

A full-featured Django + PostgreSQL accounting web app with GST support, built for Indian SMEs.

## 🚀 Quick Start (Docker)

### Prerequisites
- Docker Desktop installed
- Docker Compose available

### Run in 3 steps:

```bash
# 1. Clone / extract the project
cd accounting_app

# 2. Start with Docker Compose
docker-compose up --build

# 3. Open in browser
# http://localhost:8000
```

That's it! Seed data is loaded automatically.

---

## 🔑 Login Credentials

| User  | Username | Password | Role  |
|-------|----------|----------|-------|
| Admin | `admin`  | `admin123` | Full access |
| Staff | `staff`  | `staff123` | View + create vouchers |

---

## 🏗️ Project Structure

```
accounting_app/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── manage.py
├── entrypoint.sh
├── config/
│   ├── settings.py       # Django settings
│   ├── urls.py           # Root URL config
│   └── wsgi.py
├── apps/
│   ├── core/             # Authentication, User model
│   │   ├── models.py     # Custom User (admin/staff roles)
│   │   ├── views.py      # Login, dashboard, user management
│   │   └── management/commands/seed_data.py
│   ├── masters/          # Company profile, Chart of Accounts
│   │   ├── models.py     # CompanyProfile, Account
│   │   └── views.py
│   ├── transactions/     # Journal Vouchers
│   │   ├── models.py     # JournalVoucher, JournalVoucherLine (with GST)
│   │   └── views.py
│   └── reports/          # All financial reports
│       └── views.py      # Ledger, Trial Balance, P&L, Balance Sheet, GST
├── templates/
│   ├── base.html         # Sidebar layout
│   ├── core/             # Login, dashboard, users
│   ├── masters/          # Company, Accounts
│   ├── transactions/     # Voucher CRUD
│   └── reports/          # All report templates
└── static/
```

---

## 📱 Features

### Authentication
- Admin and Staff roles
- Admin: full CRUD + posting vouchers + user management
- Staff: create drafts, view reports

### Masters
- **Company Profile**: GSTIN, PAN, financial year, address
- **Chart of Accounts**: 5 categories (Assets, Liabilities, Income, Expenses, Equity)
  - Sub-accounts supported (parent-child)
  - Opening balances (Debit/Credit)
  - GST account flagging

### Transactions
- **Journal Voucher** with multi-line Dr/Cr
- Real-time balance validation (must balance before saving)
- Optional GST per line:
  - Intra-state: CGST + SGST
  - Inter-state: IGST
  - Auto-calculate from taxable value + rate
- Draft → Posted workflow
- Voucher number auto-generation

### Reports
- **Ledger**: Any account, date filter, running balance
- **Trial Balance**: Opening + Period movement + Closing
- **Profit & Loss**: Income vs Expenses, net profit
- **Balance Sheet**: Assets = Liabilities + Equity (with check)
- **GST Report**: CGST/SGST/IGST summary by period
- All reports are print-friendly

---

## 🛠️ Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL (or use SQLite by removing DATABASE_URL)
export DATABASE_URL="postgresql://user:pass@localhost:5432/accounting_db"

# Migrate
python manage.py migrate

# Load seed data
python manage.py seed_data

# Run server
python manage.py runserver
```

---

## 🗄️ Database Models

### User (core.User)
- Extends Django AbstractUser
- `role`: admin | staff

### CompanyProfile (masters.CompanyProfile)
- name, GSTIN, PAN, address, financial_year

### Account (masters.Account)
- code, name, category (assets/liabilities/income/expenses/equity)
- account_type, parent (FK to self), opening_balance

### JournalVoucher (transactions.JournalVoucher)
- voucher_number, date, narration, reference, status (draft/posted)

### JournalVoucherLine (transactions.JournalVoucherLine)
- account (FK), debit_amount, credit_amount
- has_gst, gst_rate, taxable_value, cgst_amount, sgst_amount, igst_amount

---

## 🌱 Sample Seed Data

7 sample journal entries loaded automatically:
1. Sales invoice with intra-state GST (CGST+SGST 18%)
2. Purchase with GST input credit
3. Monthly salary payment
4. Rent payment (cash)
5. Customer payment receipt
6. Service invoice with inter-state GST (IGST 18%)
7. Outstanding electricity bill (draft)

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | (set in docker-compose) | Django secret key |
| `DATABASE_URL` | (set in docker-compose) | PostgreSQL connection URL |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hostnames |

---

## 🔧 Useful Commands

```bash
# View logs
docker-compose logs -f web

# Django shell
docker-compose exec web python manage.py shell

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Reset and reload seed data
docker-compose exec web python manage.py flush --noinput
docker-compose exec web python manage.py seed_data

# Run with fresh database
docker-compose down -v
docker-compose up --build
```

---

## 🏦 API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/` | Dashboard |
| GET/POST | `/login/` | Authentication |
| GET | `/masters/company/` | Company profile |
| GET | `/masters/accounts/` | Chart of accounts |
| GET | `/transactions/` | Voucher list |
| GET/POST | `/transactions/create/` | New voucher |
| GET | `/reports/ledger/` | Ledger report |
| GET | `/reports/trial-balance/` | Trial balance |
| GET | `/reports/profit-loss/` | P&L statement |
| GET | `/reports/balance-sheet/` | Balance sheet |
| GET | `/reports/gst/` | GST report |
| GET | `/transactions/api/accounts/` | Accounts JSON API |
