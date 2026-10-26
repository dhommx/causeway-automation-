# PIE Automation Portal: Guide

This guide covers what the portal is for, how it is built, how to run it and how to extend it. Read it before changing anything. `implementation.md` lists the phases, and `CLAUDE.md` holds the working rules for AI assistants.

---

## 1. The case

PIE's Finance team repeats the same spreadsheet work every day. They export a file from one system (Zoho, AFS, Focus, IBL, Benefit), clean it, apply the same filters, conditions and calculations, check the totals, and type the results into another system (PACT ERP) or into a report. The work is slow and repetitive, and every manual step is a chance to make a mistake.

The portal holds all of these automations in one place. Each one follows the same pattern:

| Step | What happens |
|---|---|
| **Input** | The user uploads one or more Excel/CSV files. Some values are read from images (for example the AFS and PIE amounts in an email) and typed in by hand. |
| **Process** | The portal reads the files, checks them, and applies the automation's rules: filters, conditions, calculations and cleanup. |
| **Output** | The portal produces an Excel file in the required format, plus anything that should be shown on screen (for example the values to type into PACT). |
| **History** | Every run is saved for audit: input files, manual entries, the rule version used, outputs, who ran it and when. |

The portal runs on a local machine or server inside PIE and must stay fast with large files.

### First department: Finance

Four automations come from the proposals in `../Proposals/`:

| # | Automation | Today | Target | Status |
|---|---|---|---|---|
| 01 | Causeway Sales Reconciliation | 15 min / day | 5 min / day | Live (step 1, reconciliation, done) |
| 02 | Start Back Invoicing | 15 min / day | 3 min / day | Planned |
| 03 | Cash Collection | 1 hour / day | 10 min / day | Planned |
| 04 | Threshold Alert System | ~10 min / file | 2-3 min / file | Planned |

Process notes for automation 01 are in `../../Notes(User_Experince)/neasi_organised.txt`.

### Where this is going

Today the user uploads the files and downloads the result. Each proposal has a "full automation" option that the portal must be ready for. In that option the portal pulls data from the source systems through their APIs (Zoho, PIE POS, Benefit, the AFS mailbox) and sends the results onward (PACT, a shared folder, email), on a schedule if needed. That is why data sources and destinations are kept separate from the workflow logic (see *Connectors*).

---

## 2. Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.12 + FastAPI**, Pydantic v2 | Python has the strongest Excel and data tools. FastAPI gives a typed REST API with OpenAPI docs for free. |
| Excel reading | **Polars + fastexcel** (calamine) | Very fast on large files; reads .xlsx .xlsm .xls .xlsb .ods. CSV goes through Polars. |
| Password-protected files | **msoffcrypto-tool** | The AFS file is emailed with a password. |
| Excel writing (new file) | **XlsxWriter** | Fast, full control of formatting. |
| Excel editing (existing file) | **openpyxl** | XlsxWriter cannot edit. Used when the output must keep the original sheet and add new ones. |
| Money | Python **`Decimal`** | Floats drift. BHD has 3 decimals and reconciliations must match exactly. |
| Rules / conditions | Our own **condition engine** (JSON → Polars expressions) | Users change rates, codes and filters without a code change. Every change is a new version. |
| Database | **PostgreSQL 16**, SQLAlchemy 2, Alembic | Runs, files, rule versions, audit log, connections and the job queue all in one place. |
| Background jobs | **Procrastinate** (queue stored in Postgres) | Large files don't block the UI. Gives retries and scheduled runs without running Redis. |
| File storage | Local folder through **fsspec**, files named by SHA-256 | Files are never overwritten. Moving to MinIO/S3 later is a setting. |
| Frontend | **React 19 + TypeScript + Vite** | Internal single-page app; no server rendering needed. |
| UI | **Tailwind CSS v4**, lucide icons, Poppins | Design tokens in one file (`frontend/src/index.css`). PIE brand colours. |
| Data grid | **AG Grid Community** | Virtual scrolling, so 100k-row previews stay smooth; sorting and filters built in. |
| Data fetching | **TanStack Query** + **openapi-fetch** | API types are generated from the backend, so the frontend can't drift from it. |
| Running it | **Docker Compose** (db, api, worker, web) | One command on the server. |
| Tooling | uv, ruff, pytest (backend); pnpm, ESLint, tsc (frontend) | |

---

## 3. How it fits together

```
Browser (React)  ──/api/v1──►  API (FastAPI)  ──►  PostgreSQL
                                   │   ▲               ▲  (runs, files, rules, audit, job queue)
                                   │   │               │
                                   ▼   │               │
                              Storage folder      Worker (Procrastinate)
                              (files by SHA-256)   runs the workflow, saves outputs
```

A run goes like this:

1. The user uploads files → `POST /api/v1/files` saves them to storage and records them.
2. The preview grid reads the first 1,000 rows of a sheet → `GET /api/v1/files/{id}/preview`.
3. The user presses **Run automation** → `POST /api/v1/runs`. The API checks the inputs against what the workflow declares, links the current rule version, saves a `queued` run and puts a job on the queue.
4. The worker picks up the job and calls the workflow's `run()`. Outputs are saved to storage and linked to the run; the result (metrics, tables, warnings, log) is saved on the run.
5. The page polls the run every second and shows the result and download buttons.
6. Every step writes an audit event.

---

## 4. Folder layout

```
causeway-automation-/
├── guide.md                 this file
├── implementation.md        phases, plain language
├── CLAUDE.md                rules for AI assistants
├── docker-compose.yml       db, api, worker, web
├── .env.example             settings for docker compose
├── backend/
│   ├── app/
│   │   ├── main.py          FastAPI app, routers, startup
│   │   ├── config.py        settings (env vars prefixed AP_)
│   │   ├── db.py, models.py database session and tables
│   │   ├── jobs.py          job queue + worker task (scheduled jobs go here later)
│   │   ├── api/             routes (HTTP layer only), schemas, deps
│   │   ├── services/        what the routes call: files, runs, rules
│   │   ├── core/            shared tools: excel, money, conditions, storage, audit, secrets
│   │   ├── connectors/      Source / Destination interface + built-ins (upload, download)
│   │   └── workflows/
│   │       ├── base.py      what a workflow is (slots, fields, rules, run)
│   │       ├── registry.py  finds all workflows at startup; list of departments
│   │       ├── common.py    shared steps (e.g. passthrough)
│   │       └── finance/<automation>/workflow.py   one folder per automation
│   ├── alembic/             database migrations
│   └── tests/
└── frontend/
    └── src/
        ├── pages/           HomePage, WorkflowPage, NotFoundPage
        ├── components/
        │   ├── layout/      AppShell, TopBar
        │   ├── ui/          Button, Panel, Tabs, DataGrid, StatusPill, MetricTile, EmptyState
        │   ├── home/        AutomationCard
        │   └── workflow/    Run / History / Rules tabs and their parts
        ├── lib/             api client + one file per domain (workflows, files, runs, rules)
        ├── constants/       icon map, tab list
        └── index.css        design tokens
```

The layering copies the Compliance Portal: routes → services → models on the backend, and `components/<feature>` + `components/ui` + `lib/<domain>` on the frontend.

---

## 5. Running it

### Getting the code

The code lives at **https://github.com/dhommx/causeway-automation-** (branch `main`).

```bash
git clone https://github.com/dhommx/causeway-automation-.git
cd causeway-automation-
```

Commits are made under your own git identity (`git config user.name` / `user.email`). To push, sign in once with the GitHub CLI (`gh auth login`, HTTPS) using an account that has write access to the repository. Never put a password or token in the code, the docs or a committed `.env`.

### What you need installed

| Tool | Version used | Used for |
|---|---|---|
| Docker + Docker Compose | Docker 29, Compose v5 | the database; the whole stack on a server |
| Python | 3.12 or newer | backend |
| uv | 0.13 | Python packages and running the backend (`curl -LsSf https://astral.sh/uv/install.sh \| sh`) |
| Node.js | 20 | frontend |
| pnpm | 9.15.9 (pinned in `frontend/package.json`) | frontend packages (`corepack enable` installs it) |

For a server, only Docker is needed.

### Settings

The backend reads environment variables prefixed with `AP_`, from the shell or from `backend/.env`. Docker Compose reads `.env` next to `docker-compose.yml` (copy it from `.env.example`). Neither `.env` file is committed.

| Variable | Default (development only) | What it is |
|---|---|---|
| `AP_DATABASE_URL` | `postgresql+psycopg://automation:automation@localhost:5450/automation_portal` | the database |
| `AP_STORAGE_ROOT` | `backend/storage` | where uploaded and output files are kept |
| `AP_SECRET_KEY` | a fixed development key | encrypts stored passwords and connector credentials |
| `AP_CORS_ORIGINS` | `["http://localhost:3500"]` | which web addresses may call the API |
| `AP_RUN_INLINE` | `false` | `true` runs jobs inside the API, so no worker is needed |
| `AP_PREVIEW_ROW_LIMIT` | `1000` | rows shown in a file preview |
| `AP_MAX_UPLOAD_MB` | `200` | the largest file that can be uploaded |
| `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`, `WEB_PORT` | `automation`, `automation`, `automation_portal`, `5450`, `3500` | Docker Compose only |

**The default database password and secret key are public, because this repository is public.** They are fine on a laptop. On a server, set a real `DB_PASSWORD` and generate a new key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep that key safe: anything encrypted with it can't be read without it.

### Ports

| Service | Port |
|---|---|
| Web (Vite dev or nginx) | 3500 |
| API | 4500 (docs at http://localhost:4500/docs) |
| PostgreSQL | 5450 |

### Local development

```bash
# 1. Database
docker compose up -d db

# 2. Backend
cd backend
uv sync                      # first time only: installs Python and the packages
uv run alembic upgrade head
uv run uvicorn app.main:app --port 4500 --reload
# in a second terminal: the worker that runs the jobs
uv run python -m procrastinate --app=app.jobs.app worker

# 3. Frontend, in a third terminal
cd frontend
pnpm install                 # first time only
pnpm dev            # http://localhost:3500, /api is proxied to :4500
```

To skip the worker during quick development, set `AP_RUN_INLINE=true` in `backend/.env`. Runs then execute inside the API process.

### Everything in Docker (server)

```bash
cp .env.example .env      # set real passwords and AP_SECRET_KEY
docker compose up -d --build
# open http://<server>:3500
```

The API container runs the migrations on start. Uploaded and output files live in the `storage_data` volume and the database in `db_data`. **Back up both.**

### Checks

```bash
cd backend  && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd frontend && pnpm typecheck && pnpm lint && pnpm build
```

Backend tests create and use their own database (`automation_portal_test`), never the dev one.

---

## 6. Working rules

### Static pages

**A page never scrolls.** The window is split into fixed areas (top bar, page header, panels). When content is longer than its area, the **panel** scrolls, not the page.

- `html`, `body` and `#root` are `height: 100%; overflow: hidden`.
- Build every screen from `Panel` (`components/ui/Panel.tsx`). It has a fixed header and footer and a body that scrolls on its own. Use `scroll={false}` when the body is filled by something that scrolls itself (an AG Grid).
- Inside flex/grid layouts, every container on the way down needs `min-h-0` so children can shrink and scroll.
- On small screens the home grid stacks and scrolls inside its own area.

### Money

- Never use `float` for amounts. Use `app/core/money.py`: `to_decimal`, `money` (3 places, half-up), `percent_of`, `fmt`.
- Round once, at the step where the accountant would round, not at every line.

### Excel

- Workflows use `app/core/excel.py`, not the libraries directly: `read_sheets` (any Excel/CSV, handles passwords), `write_workbook` (new file), `edit_workbook` + `add_sheet` (keep the original sheet, add new ones).
- Never modify the uploaded file. Outputs are always new files.
- **Images** (.png .jpg .jpeg .webp) can be uploaded into a file slot with `kind="reference"`. They are shown on screen so the user can read values from them, and kept with the run for audit. They are **never processed**: workflows skip them (`InputFile.is_image`), and the preview shows the image instead of a grid.
- After an upload the user gets a notice with how many files were added and their formats (for example "3 files added · 2 XLSX, 1 PNG").

### Rules and conditions

- Values that may change (rates, account codes, SKU mappings, column lists, filters) belong in the workflow's **rules**, not in code. `default_rules` gives version 1; users change them in the **Rules** tab, and every save is a new version.
- Conditions use the condition engine (`app/core/conditions.py`): `{"field", "op", "value"}` or groups `{"all": [...]}`, `{"any": [...]}`, `{"not": ...}`. `apply_filter` filters rows; `classify` labels rows, and the first matching case wins.

### Audit

- Anything that changes data writes an audit event (`app/core/audit.record`) in the same transaction.
- Audit rows are never updated or deleted. Stored files are never overwritten. Rule sets are never edited in place.
- Until login exists, the actor is `anonymous`. `api/deps.current_actor` is the single place that will change.

### API

- Everything is under `/api/v1`. The UI is just one client, and other systems will use the same API later.
- After changing a schema in `backend/app/api/schemas.py`, run `pnpm gen:api` in `frontend/` with the API running, so the TypeScript types follow.
- Database changes always come with an Alembic migration: `uv run alembic revision --autogenerate -m "..."`, then review the file.

---

## 7. Adding or building an automation

1. Create `backend/app/workflows/<department>/<name>/workflow.py` with a `Workflow` subclass. The registry finds it on startup; nothing else needs registering. Copy an existing one.
2. Fill in its description: `key`, `name`, `department`, `number`, `summary`, `icon`, and the proposal facts (`current_time`, `target_time`, `frequency`).
3. Declare what it needs:
   - `file_slots`: each file the user uploads (label, required, multiple, password-protected, accepted formats). Use `kind="reference"` with `accept=IMAGE_ACCEPT` for images the user only looks at. A run refuses a file whose format the slot does not accept.
   - `manual_fields`: values typed by hand (text, number, money, date, select).
   - `default_rules`: rates, mappings and conditions.
4. Write `run(ctx)`. Read files with `ctx.files_for("slot")[0].sheets()`, typed values from `ctx.params`, rules from `ctx.rules`. Add outputs with `ctx.add_output(name, bytes)` and progress notes with `ctx.note()`. Return a `RunResult` with metrics, tables and warnings. Raise `WorkflowInputError("message for the user")` for bad input.
5. Put the logic in its own module next to `workflow.py` (for example `logic.py`) so it can be tested without the API.
6. Add tests that use a real worked example from Finance and check the exact totals.
7. To make a planned automation live, set `status = "live"` (or remove the line). The home card stops being blurred.
8. A new icon name also needs an entry in `frontend/src/constants/icons.ts`.
9. A new department goes in `DEPARTMENTS` in `workflows/registry.py`.

The UI for upload, preview, manual entries, run, result, history and rules is generic and adapts to what the workflow declares. An automation only needs its own screen parts when it has to show something special (for example the list of ERP entries to type), and those go in `frontend/src/components/workflow/<name>/`.

---

## 8. Connectors (future API links)

Workflows never talk to outside systems. They receive files through `RunContext`. Moving data in and out is the job of connectors (`backend/app/connectors/`):

- **Source**: brings files in. Built in: `upload`. Planned: email inbox (AFS file), Zoho API, PIE POS API, Benefit, Focus/IBL, shared folder.
- **Destination**: sends outputs out. Built in: `download`. Planned: shared folder, PACT import/API, email, webhook.

Credentials for an outside system go in the `connections` table, encrypted with `AP_SECRET_KEY` (`app/core/secrets.py`). They never go in code, logs or the UI.

So an automation that starts with "user uploads the Zoho export" can later switch to "the portal pulls it from Zoho at 8:00 every morning" by changing the connector and adding a scheduled job in `app/jobs.py`. The workflow itself doesn't change.

---

## 9. Plans for the future

Covered in detail in `implementation.md`. In short:

1. **Foundation and portal**: done.
2. **Causeway Sales Reconciliation** logic, as instructed by Finance.
3. **Login and roles**: users, departments, permissions, API tokens.
4. **The other three Finance automations**, including a condition builder screen for Threshold Alerts.
5. **Integrations**: connectors for email, Zoho, PIE POS, Benefit, Focus/IBL and PACT, plus scheduled runs.
6. **Reports and notifications**: monthly consolidated report, alerts, webhooks.
7. **Server hardening**: HTTPS, backups, monitoring, retention.
8. **Other departments.**
