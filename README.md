# Support CRM

**English** · [Ελληνικά](README.el.md)


A Windows desktop CRM for IT remote-support businesses: manage clients, track RustDesk and phone support sessions with a built-in timer, sell prepaid support packages, and issue receipts and invoices as PDFs — all on top of a MariaDB/MySQL database.

Built with **Python 3.11**, **PySide6 (Qt 6)** and **MariaDB**. The UI is bilingual (Greek / English).

> Developed as a university thesis project.

---

## Features

**Clients & remote support**
- Client records (individuals and businesses, with VAT number), client card with history
- One-click remote connection through **RustDesk** (launches the local RustDesk client with the client's ID)
- Support sessions with live timer, technician assignment and session type (RustDesk / phone)

**Billing**
- Hourly billing based on session duration
- Prepaid **support packages** (hours, price, discounts, expiry) with automatic deduction of used hours
- Overage handling: when a package runs out or expires, the remaining time is billed hourly as an outstanding balance
- Payments, partial payments and an **outstanding balances (debts)** screen per client
- **Package expirations** screen with optional reminder email

**Documents**
- PDF **receipts and invoices** (ReportLab) with VAT split, sequential numbering and saved copies per type
- Visual **PDF template editor** (drag-and-drop fields, grid, zoom)
- Send a document to the client by email (SMTP settings configurable in the app)

**Reporting**
- Dashboard with KPI cards, 6-month revenue chart and alert panels
- Period-based financial & activity reports, export to Excel
- **Technician performance** dashboard (sessions, hours, average duration, clients served, billed amounts)

**Administration**
- User login with bcrypt-hashed passwords
- Role-based access: **Administrators** and **Technicians**, with per-user permission checklist
- **Audit log** of database changes
- Database **backup & restore** (pure Python via PyMySQL) with an automatic daily backup and retention
- Schema migrations runnable from *Settings → Maintenance*
- CSV data import (with preview and Greek `cp1253` encoding support)
- Standalone **database configurator** tool for first-time setup
- Update checker and license-key validation against a remote endpoint

---

## Tech stack

| Area | Technology |
|---|---|
| Language | Python 3.11 |
| GUI | PySide6 (Qt 6), custom QSS stylesheet, SVG icons |
| Database | MariaDB / MySQL via PyMySQL (configurator uses `mysql-connector-python`) |
| PDF | ReportLab (DejaVu Sans fonts for Greek text) |
| Excel | openpyxl |
| Security | bcrypt password hashing, role/permission tables |
| Remote access | RustDesk (external client) |
| Networking | requests (update check, license validation) |
| Packaging | Nuitka + NSIS installer script |
| Server side | Small PHP license-validation endpoint (`server_files/`) |

---

## Architecture

The code follows a layered structure:

```
UI (PySide6 views & dialogs)  →  Services (business logic)  →  Repositories  →  MariaDB
```

```
.
├── main.py                  # Application entry point (login, license check, main window)
├── config.py                # Settings; loads DB config from config/db_config.json or .env
├── configurator_main.py     # Standalone database configurator
├── configurator/            # Configurator UI & logic
├── ui/                      # Main window, views (widgets/), dialogs, i18n (el/en)
├── services/                # Sessions, billing, receipts, email, backup, auth, RustDesk, reports…
├── db/
│   ├── connection.py        # Connection management
│   ├── repositories/        # Data access per entity
│   ├── migrations/          # Numbered SQL migrations
│   └── schema_consolidated.sql  # Full schema for a fresh install
├── models/                  # Data classes
├── resources/               # Icons, fonts, QSS stylesheet
├── Logo/                    # Application logo & icon
├── server_files/            # PHP license-validation endpoint
├── build_nuitka.py          # Build script (Nuitka)
└── build-nuitka/            # NSIS installer script
```

---

## Getting started

### Requirements
- Windows 10/11
- Python 3.11
- MariaDB (or MySQL) server
- [RustDesk](https://rustdesk.com/) client installed (for remote sessions)

### Installation

```bash
git clone https://github.com/Filipposanag/support-crm.git
cd support-crm

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Database configuration

Option A — configurator (recommended):

```bash
python configurator_main.py
```

The configurator saves the connection to `config/db_config.json`, can create the database and load `db/schema_consolidated.sql`.

Option B — manual:

1. Copy `config/db_config.example.json` to `config/db_config.json` and fill in your credentials, **or**
2. Copy `.env.example` to `.env` and fill in the `DB_*` values (used only when `config/db_config.json` does not exist).

Both files are git-ignored.

### Run

```bash
python main.py
```

or double-click `run.bat`.

On a fresh schema a default `admin` account is created (see the comment in `db/schema_consolidated.sql`). **Change its password after the first login.**

### License validation

On startup the application validates a license key online. The endpoint is set in `LICENSE_VALIDATION_CONFIG` in `config.py`; a minimal PHP implementation is provided in `server_files/validate_license.php`. To run your own instance, point that URL to your own endpoint.

### Build (optional)

```bash
python build_nuitka.py
```

Produces a standalone Windows build with Nuitka; `build-nuitka/installer_nuitka.nsi` packages it with NSIS.

---

## Screenshots

_Add screenshots here (e.g. `docs/screenshots/dashboard.png`)._

---

## License

See [LICENSE.txt](LICENSE.txt).
