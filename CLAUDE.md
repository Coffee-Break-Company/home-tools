# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`home-tools` is a household-management app. Its current feature is **bill tracking**: a list of recurring bills, whether each is paid this month, and a daily Telegram reminder for bills approaching their due date.

**All user-facing UI text must be in Brazilian Portuguese only** — labels, buttons, messages, and backend error `detail` strings. Do not introduce English (or any other language) in user-visible strings.

This is a monorepo with two independently deployed apps:

- `frontend/` — Vite + React 19 + TypeScript + Tailwind v4 + shadcn/ui, hosted on Vercel.
- `backend/` — FastAPI (Python 3.12, managed with `uv`), hosted on Render via Docker (`render.yaml`, `backend/Dockerfile`).

## Git conventions

- **Never commit directly to `main`/`master`** — always work on a branch and open a PR.
- **Commit messages must be a single line** — subject only, no body and no trailers.
- **Commit in small, focused commits**, one logical change each (e.g. backend and frontend changes separated).

## Commands

Backend (run from `backend/`):

```bash
uv run uvicorn main:app --reload   # dev server
uv run pytest                       # run all tests
uv run pytest tests/test_main.py::test_name   # single test
uv sync --group dev                 # install deps incl. dev
```

Frontend (run from `frontend/`):

```bash
npm run dev                  # dev server
npm run build                # tsc -b && vite build
npm run lint                 # eslint
npm run test                 # vitest (watch)
npm run test -- --run        # vitest single run (what CI uses)
npm run test -- --run src/__tests__/pages/Bills.test.tsx   # single file
```

CI (`.github/workflows/tests.yml`) runs both test suites on every PR and on push to `main`.

## Architecture

### "Paid" status is derived from Google Drive, not the database

There is no payment record in the database. A bill is considered **paid for a given month** if its Google Drive folder contains a receipt file whose name starts with that month's Portuguese name (e.g. `Junho 2026.pdf`). See `check_payment_exists` and `MONTHS_PT` in `backend/main.py`. File-name matching is accent-insensitive via `normalize()`.

Consequences when changing anything related to payments:

- `bills` rows store only `id`, `name`, `due_day`, and `drive_folder_id`. The folder is the source of truth for payment.
- Uploading a receipt (`POST /api/bills/{id}/receipt`) writes a month-named file into the bill's Drive folder; `receipt_file_name()` must keep producing names that `check_payment_exists` matches.
- Month-vs-year edge cases are handled deliberately (a `due_day` past month end is clamped; a receipt month ahead of the current month is treated as the previous year). Preserve this logic.

### Auth: Supabase Google OAuth + an allow-list, enforced on both ends

- The frontend signs in with Supabase Google OAuth (`AuthContext.tsx`), then calls `GET /api/auth/verify`. `AuthState` distinguishes `unauthenticated` (no session) from `unauthorized` (valid Google login, but email not allowed).
- The backend's `verify_user` dependency validates the Supabase JWT **and** checks the email against the `allowed_emails` Supabase table. Every protected endpoint depends on it. Adding a user means inserting into `allowed_emails`, not changing code.
- The frontend talks to the backend through the `api` helper in `frontend/src/lib/api.ts`, which attaches the Supabase bearer token. `ProtectedRoute` gates pages. Routes are defined in `App.tsx` (`/` Home, `/contas` Bills, `/login`).

### The daily reminder is an external cron hitting one endpoint

`POST /api/cron/scan` is the whole reminder system. It is **not** triggered by the app — a GitHub Actions schedule (`.github/workflows/bill-reminder.yml`, 11:00 UTC ≈ 08:00 BRT) curls it with an `X-Cron-Secret` header that must match the `CRON_SECRET` env var. The endpoint finds unpaid bills due within `REMINDER_DAYS_AHEAD` days and sends one Telegram message (`_build_reminder_message` builds an HTML message with a monospace urgency table). Timezone is fixed to `America/Sao_Paulo`.

### Configuration

Backend reads everything from env vars (see `render.yaml` for the full list): `SUPABASE_URL`, `SUPABASE_KEY`, Google service-account creds, `CRON_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `REMINDER_DAYS_AHEAD`. The frontend uses `VITE_API_URL` (backend base URL) plus Supabase keys; when `VITE_API_URL` is unset, API calls go to a relative path.

**Google service-account credentials** are loaded two ways (`get_drive_service` in `backend/main.py`):

- **Local execution:** place the service-account JSON file in the repo root (e.g. `controle-pagamentos-*.json`) and point `GOOGLE_CREDENTIALS_PATH` at it. Without this file, Drive access (and therefore payment status and receipt upload) will not work locally.
- **Production:** the same JSON is base64-encoded into the `GOOGLE_CREDENTIALS_JSON` env var instead. When set, it takes precedence over the local file path.
