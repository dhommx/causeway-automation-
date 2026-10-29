# CLAUDE.md: PIE Automation Portal

Read `guide.md` (case, stack, layout, rules) and `implementation.md` (phases) before working here.

## What this is

An internal portal holding PIE's automations, one department at a time (Finance first). Each automation: upload Excel files and type a few values → apply rules (filters, conditions, calculations) → produce an Excel output → keep every run for audit. Backend is FastAPI + Polars + Postgres + Procrastinate; frontend is React + Vite + Tailwind + AG Grid.

## Scope rules

- **Do not add business logic, conditions, rates or calculations to an automation unless the user gives instructions for that specific automation.** Until then a live automation uses `passthrough` and has empty rules.
- Do only what was asked. Reuse existing patterns (look at the closest existing file first). If something else looks needed, ask before doing it, and list similar issues instead of fixing them.
- Never `git push` or open PRs unless asked in that message. No Claude/AI attribution in commits.

## Must-follow rules

- **Pages never scroll.** Build screens from `components/ui/Panel.tsx`; panels scroll inside. Keep `min-h-0` on flex/grid parents. Check at 1440x900 that `document.scrollingElement.scrollHeight <= innerHeight`.
- **Money is `Decimal`**, through `app/core/money.py`. Never float arithmetic on amounts. BHD = 3 places, half-up.
- **Excel goes through `app/core/excel.py`**: never edit an uploaded file; outputs are new files.
- **Changeable values are rules**, not constants: put them in `default_rules`, read them from `ctx.rules`. Conditions use `app/core/conditions.py`.
- **Files go through `app/services/files.py`** into the data folder (`app/core/storage.py`, guide.md §6 Data folder). Never write files anywhere else, never overwrite one, never commit `Data/`.
- **Audit everything that changes data** with `app/core/audit.record` in the same transaction. Never update or delete audit rows, stored files or rule versions.
- **Workflows don't call outside systems.** Inputs and outputs go through connectors (`app/connectors/`); credentials go in `connections`, encrypted.
- Design tokens only (`frontend/src/index.css`): no raw colours in components. Controls are at least 44px tall, with visible focus.
- New DB column/table → Alembic migration. API schema change → `pnpm gen:api` (API running) so `src/lib/api-types.ts` follows.

## Commands

```bash
docker compose up -d db                                         # Postgres on :5450
cd backend
uv run alembic upgrade head
uv run uvicorn app.main:app --port 4500 --reload                # API, docs at /docs
uv run python -m procrastinate --app=app.jobs.app worker        # job worker (needs -m, not the bare script)
uv run pytest && uv run ruff check . && uv run ruff format .
cd frontend
pnpm dev                                                        # :3500, proxies /api to :4500
pnpm typecheck && pnpm lint && pnpm build
pnpm gen:api                                                    # regenerate API types
```

`AP_RUN_INLINE=true` in `backend/.env` runs jobs inside the API (no worker needed). Tests set it themselves and use the `automation_portal_test` database.

## Gotchas

- Don't use `pkill -f` from the shell; it matches its own command line. Stop processes by PID.
- The full Docker stack (`docker compose up -d`) shares the Postgres job queue with a local dev API/worker. Don't run both workers at once, because they use different data folders.
- AG Grid v36 needs `ModuleRegistry.registerModules([AllCommunityModule])` (done in `main.tsx`) and themes through `themeQuartz.withParams`.
- Polars 2.x is strict about mixed int/float in one column when building frames.

## Where things go

- New automation: `backend/app/workflows/<dept>/<name>/workflow.py` (+ `logic.py`, tests). See guide.md §7.
- Automation-specific UI: `frontend/src/components/workflow/<name>/`.
- Shared UI pieces: `frontend/src/components/ui/`. API calls: `frontend/src/lib/<domain>.ts`.
- After finishing a phase or a piece of one, update its status in `implementation.md`.
- Causeway: every condition, popup, calculation and fix is explained in `docs/causeway/README.md` (ERP upload columns in `docs/causeway/erp-files.md`). Update them in the same change, with the date.
