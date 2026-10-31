# Brightloop

Intelligent subscription management and recurring billing with three separate workspaces: Platform Admin, Customer, and Company.

## Stack

- React 18 + Vite + Tailwind CSS + shadcn/ui
- Python + FastAPI + SQLAlchemy + Alembic
- PostgreSQL
- JWT access/refresh tokens and Argon2id password hashing
- ReportLab invoice PDFs

## Demo accounts

After seeding, all three roles share the password `DemoPass123!`

| Role | Email | Lands on |
| --- | --- | --- |
| Admin | `admin@example.com` | `/admin/dashboard` |
| Staff | `staff@example.com` | `/staff/dashboard` |
| Customer | `customer@example.com` | `/my/dashboard` |

Registration creates a customer account and asks which active company workspace to join. Platform Admin provisions Company Admin accounts; company admins manage their own company staff.

## Local setup (Windows)

1. Copy environment files:

```powershell
copy .env.example .env
copy frontend\.env.example frontend\.env
```

2. Create a PostgreSQL database named `Brightloop Software` with user/password `Brightloop Software`, or change `DATABASE_URL` in `.env`.

3. Backend (Python 3.12 recommended):

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

4. Frontend:

```powershell
cd frontend
npm install
npm run dev
```

5. Open `http://localhost:5173`. API docs: `http://localhost:8000/docs`.

For a UI-only preview, run `npm run build` and `npm run preview -- --host 0.0.0.0` from `frontend`; Vite prints the preview URL. API-backed features still require the backend and database.

## MVP workflow

1. Sign in as Admin and create products, variants and daily/weekly/monthly/yearly plans. Products and plans can be edited or archived; variants track an attribute, option name and price surcharge.
2. Register a customer (or use the demo Customer account) and maintain billing contact details in Customers.
3. Configure the company's GST rate/state in Company Settings and create a quotation for a customer and plan. Mark it sent, accept it, then convert it into a subscription.
4. Run billing from Invoices. Each subscription period can produce one invoice; run it again safely to process any additional due periods.
5. Record full or partial manual payments from Payments. Invoice balances update from payment records.
6. Customers can browse their company's plans, request subscriptions and plan changes, accept quotations, view only their own subscriptions/invoices/payments, download invoice PDFs, and pay outstanding invoices through Razorpay Checkout in test mode.

## Three-panel delivery

1. **Platform Admin:** company lifecycle, company administrator provisioning, platform-wide KPIs, audit/report views, and administrative access.
2. **Customer:** company-scoped catalog and quotations, subscription change requests, invoice/payment history, account details, PDFs, and test-mode online checkout.
3. **Company:** isolated dashboard, product/plan/variant catalog, customers, staff, quotations, subscriptions, billing, invoices, manual payments, customer requests, and company settings.

To enable customer checkout, set `RAZORPAY_KEY_ID` to a Razorpay test key and `RAZORPAY_KEY_SECRET` in the backend environment. Checkout is disabled if test credentials are absent. Payment confirmation verifies the checkout signature and confirms captured amount/currency/order with Razorpay before applying the payment to the invoice.

For a local preview without PostgreSQL, use SQLite by setting `$env:DATABASE_URL = 'sqlite:///./Brightloop Software-preview.db'` in `backend`, then run the migrations and seed commands shown above. Docker Compose and production setup continue to use PostgreSQL.

The API starts an hourly in-process billing scheduler by default. Set `ENABLE_BILLING_SCHEDULER=false` to disable it, or change `BILLING_INTERVAL_HOURS`. Run one API worker when using the in-process scheduler; use a separate dedicated worker before scaling the API to multiple processes.

## Tests

```powershell
cd backend
$env:APP_ENV = "test"
.\.venv\Scripts\pytest.exe -q
```

## Docker Compose

Docker Desktop is optional. When installed:

```powershell
docker compose up --build
```

## Project status

See [the implementation checklist](documentation/PROJECT_CHECKLIST.md) for completed slices and remaining work. Company GST settings drive configurable CGST/SGST or IGST calculation, recurring invoices receive sequential company/financial-year numbers, discount codes/usage and quotation templates are isolated by company, draft quotations support edits and same-cadence plan line items, and those line snapshots flow to recurring subscriptions, invoices, and PDFs. Credit notes adjust invoice balances, while manual refunds preserve the original payment and reopen the due balance. Company staff can print or email invoices when the browser and SMTP configuration allow it. External gateway refund execution, billing-run retry history, ERP item tax/HSN details, and full browser/PostgreSQL/Docker verification remain outstanding.
