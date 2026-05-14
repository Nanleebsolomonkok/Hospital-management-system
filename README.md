# Hospital Management System

A production-quality Flask hospital management system with Blueprint architecture, rate-limited auth, connection pooling, live search, pagination, and a fully redesigned professional interface.

## What's New in v2

| Area | v1 | v2 |
|------|----|----|
| **Architecture** | Single 500-line `app.py` | Application factory + 8 Blueprints |
| **Rate limiting** | None | `flask-limiter` — 10 logins/min, 30/hr |
| **DB connections** | New connection per request | MySQL connection pool (5 connections) |
| **Input validation** | Basic `.get()` checks | `sanitise_str()` + `require_fields()` on every endpoint |
| **Pagination** | All records loaded at once | Server-side pagination on patients, appointments, billing, audit log |
| **Live search** | None | Debounced 300ms search on patients and audit log |
| **Loading states** | "⏳ Loading…" text | Animated skeleton loaders on every data table and stat card |
| **Error handling** | Generic | Per-blueprint try/catch, custom 404 page, rate-limit 429 handler |
| **Session** | Re-fetched on every page | Cached in `sessionStorage` for instant sidebar render |
| **Password change** | Basic | Live requirement checklist with real-time feedback |
| **User management** | Reset password only | Reset password + toggle active/inactive |
| **Design** | Navy/gold, Jinja2 macros | Inter + Plus Jakarta Sans, clean clinical design system |
| **Breadcrumbs** | None | Present on detail and form pages |
| **404 page** | Flask default | Custom branded error page |

---

## Architecture

```
medicore_v2/
├── run.py                      ← Entry point
├── app/
│   ├── __init__.py             ← create_app() factory, blueprint registration
│   ├── core/
│   │   ├── db.py               ← MySQL connection pool + DbCursor context manager
│   │   ├── helpers.py          ← password hashing, sanitisation, pagination, audit
│   │   └── decorators.py       ← @login_required, @role_required
│   └── api/                    ← Blueprints (one per domain)
│       ├── auth.py             ← login, logout, session, change-password
│       ├── patients.py         ← list (paginated+search), detail, register
│       ├── appointments.py     ← list (paginated), schedule
│       ├── medical.py          ← add record
│       ├── billing.py          ← list (paginated), process payment
│       ├── admin.py            ← users, reset-password, toggle-active, audit-log
│       ├── dashboard.py        ← role-specific dashboard data
│       └── formdata.py         ← dropdown data for forms
├── static/
│   ├── css/medicore.css        ← Full design system (tokens, sidebar, cards, tables…)
│   └── js/medicore.js          ← HMS namespace: init, skeleton, search, pagination
└── templates/                  ← 18 standalone HTML files (no Jinja2)
    ├── login.html
    ├── 404.html
    ├── dashboard_{admin,doctor,receptionist,billing,guest}.html
    ├── patients.html
    ├── patient_detail.html
    ├── register_patient.html
    ├── appointments.html
    ├── schedule_appointment.html
    ├── add_medical_record.html
    ├── billing.html
    ├── admin_users.html
    ├── admin_audit.html
    └── change_password.html
```

---

## Getting Started

### Prerequisites
- Python 3.8+
- MySQL 8.0+

### Installation

```bash
git clone https://github.com/your-username/medicore.git
cd medicore

python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Import database schema
mysql -u root -p < schema.sql
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
SECRET_KEY=replace-with-a-long-random-string
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=HospitalManagement_STU001
DB_PORT=3306
FLASK_DEBUG=false
PORT=5000
```

### Run

```bash
python run.py
```

Visit `http://localhost:5000`

---

## Demo Accounts

Password for all: **`password`**

| Role | Username |
|------|----------|
| Admin | `admin` |
| Doctor | `doctor1` |
| Receptionist | `reception1` |
| Billing | `billing1` |


## Key Design Patterns

**DbCursor context manager** — every DB operation auto-commits on success, auto-rolls back on exception, and always closes the connection:
```python
with DbCursor() as (cur, conn):
    cur.execute('SELECT ...')
    rows = cur.fetchall()
# connection returned to pool automatically
```

**Blueprint separation** — each domain is its own file; adding a new feature means creating a new blueprint and registering it in `create_app()`, not editing a monolithic file.

**Skeleton loaders** — every page that fetches data calls `HMS.skeletonRows(cols, rows)` before the API call and replaces it with real content when the data arrives.

**Session cache** — `HMS.init()` stores the session in `sessionStorage` so the sidebar renders instantly on subsequent page loads without waiting for `/api/session`.

---

## Security Notes

- Login is rate-limited to **10 requests/minute** and **30/hour** per IP
- All string inputs are sanitised and length-capped before hitting the DB
- Stored procedures handle patient registration and appointment scheduling (server-side constraint checking)
- DB triggers prevent scheduling with inactive doctors, deletion of paid bills, etc.
- SHA-256 password hashing (upgrade to bcrypt for production)

---

## Academic Context

Developed as a university semester project demonstrating full-stack development, relational database design, stored procedures, triggers, and role-based access control.

---

## License

Educational use only. Not licensed for commercial deployment.
