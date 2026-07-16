# Autonomous Multi-Region Payment & Identity Settlement Network

Enterprise-grade project foundation with a **complete authentication, authorization,
and federated identity backend**. Payment/settlement business logic (ledgers,
settlement instructions, regional routing rules) is still out of scope for this
phase — see "Explicitly out of scope" below — but every auth, RBAC, session, and
identity concern is fully implemented, migrated, and tested against a real database.

## Tech stack

| Layer      | Choices |
|------------|---------|
| Frontend   | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui, React Query, Framer Motion |
| Backend    | FastAPI, PostgreSQL, SQLAlchemy 2.0 (async), Redis |
| Auth       | JWT (access + refresh tokens), bcrypt password hashing |
| Infra      | Docker, Docker Compose |

## Repository layout

```
apmisn/
├── docker-compose.yml        # orchestrates db, redis, backend, frontend
├── .env.example               # root env vars consumed by docker-compose
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                # migration environment + 0001_initial_schema (all tables)
│   ├── tests/                  # pytest integration suite (auth, RBAC, identity, MFA, sessions)
│   └── app/
│       ├── main.py             # FastAPI app factory, middleware, routers, startup seeding
│       ├── core/                # config, security (JWT/hashing), logging, exceptions, audit
│       ├── db/                  # SQLAlchemy base + async session + idempotent seed script
│       ├── models/              # User, Role/Permission, RefreshToken/Session, MFA,
│       │                        #   Identity/IdentityVerificationHistory/IdentitySignal, AuditLog
│       ├── schemas/             # Pydantic request/response schemas for every resource
│       ├── api/v1/endpoints/     # auth, users, roles, permissions, identity, sessions, health
│       ├── api/deps.py           # get_current_user, has_role(), has_permission(), status checks
│       ├── middleware/           # request logging, malformed-auth-header rejection
│       └── redis_client/         # Redis connection factory
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.ts        # design tokens (see globals.css for HSL vars)
    └── src/
        ├── app/                  # App Router: /, /login, /dashboard/*
        ├── components/
        │   ├── ui/                # shadcn primitives (button, card, sheet, ...)
        │   ├── layout/            # Sidebar, Navbar, DashboardShell
        │   └── providers/         # ThemeProvider, QueryProvider
        ├── lib/                   # cn(), Axios client w/ refresh interceptor, token storage
        ├── hooks/                 # useLogin, useLogout, useCurrentUser
        └── types/                 # shared TS types mirroring backend schemas
```

## What's implemented

### Authentication & Authorization backend (this phase)

- **User types / RBAC seed data** — seven roles seeded on startup: `Customer`,
  `Merchant`, `Bank`, `Settlement Authority`, `Fraud Analyst`, `Compliance Officer`,
  `Super Admin` (`app/db/seed.py`), each pre-wired to a sensible default permission set.
- **Signup / Login / Logout** — `POST /api/v1/auth/{signup,login,logout}`. Signup
  hashes passwords with bcrypt, assigns the default `Customer` role, and creates the
  user's `Identity` and `MFA` records in the same transaction.
- **JWT access + refresh tokens** — short-lived access tokens and longer-lived
  refresh tokens (`app/core/security.py`), refresh tokens stored server-side as
  SHA-256 hashes (`refresh_tokens` table), never in plaintext.
- **Refresh token rotation + reuse detection** — `POST /api/v1/auth/refresh` issues
  a new pair and marks the old token `is_used`; replaying an already-used token is
  treated as a compromise signal and revokes **every** active token/session for
  that user.
- **Remember me** — `login` accepts `remember_me`; extends both the session
  (30 days vs 1 day) and issues a 30-day refresh token.
- **Password hashing, change, and reset** — bcrypt via `passlib`;
  `POST /api/v1/auth/change-password` (requires current password);
  `POST /api/v1/auth/reset-password/{request,confirm}` (enumeration-safe: always
  returns the same generic message regardless of whether the email exists).
- **Email verification (mock)** — `POST /api/v1/auth/email-verification/{request,verify}`
  issues a short-lived JWT "token" (logged/returned instead of emailed) and, on
  verification, raises the user's identity confidence score and logs a verification
  history entry.
- **MFA (mock OTP)** — `POST /api/v1/auth/mfa/{setup,enable,disable}` plus a
  login-time challenge (`mfa_required` + `mfa_token`) resolved via
  `POST /api/v1/auth/mfa/verify-login`. The OTP code is a fixed, configurable mock
  (`settings.MFA_OTP_CODE`) rather than real TOTP — call out clearly as mock per spec.
- **Session management** — every login creates a `sessions` row (IP, user agent,
  expiry); `GET /api/v1/sessions/` lists active sessions,
  `POST /api/v1/sessions/{id}/revoke` revokes one (own session, or any session for
  a superuser).
- **Token revocation** — logout, session revoke, and refresh-reuse detection all
  revoke the underlying `refresh_tokens` rows so revoked tokens can never be
  redeemed again.
- **RBAC + permission-based authorization** — `app/api/deps.py` exposes
  `has_role(*names)` and `has_permission(*names)` dependency factories used to
  protect routes (e.g. only `Super Admin`/`Compliance Officer` can change user
  status; only privileged roles can read another user's identity).
- **User status checks** — `active` / `suspended` / `disabled` enforced both at
  login and on every authenticated request via `get_current_user`.
- **Profile, settings, avatar (mock), activity logs** —
  `GET/PUT /api/v1/users/profile`, `POST /api/v1/users/profile/avatar` (URL stored
  via audit log — no file storage in this phase), and
  `GET /api/v1/users/activity-logs` (the user's own audit trail).
- **Federated Identity module** — `Identity` (region, confidence score,
  verification status), `IdentityVerificationHistory`, and `IdentitySignal` tables;
  full CRUD + verification workflow under `/api/v1/identity/*`, restricted to the
  owning user or privileged roles (`Bank`, `Fraud Analyst`, `Compliance Officer`,
  `Settlement Authority`, `Super Admin`) as appropriate.
- **Audit logging** — every sensitive mutation (login, logout, password change,
  role change, identity verification, etc.) writes an `AuditLog` row with actor,
  action, resource, IP, user agent, and structured details.
- **Database migrations** — `alembic/versions/0001_initial_schema.py` creates every
  table (`users`, `roles`, `permissions`, `user_roles`, `role_permissions`,
  `refresh_tokens`, `sessions`, `mfa`, `identity`, `identity_verification_history`,
  `identity_signals`, `audit_logs`) with the correct constraints and indexes.
- **Consistent error handling** — a single `AppError` hierarchy
  (`NotFoundError`, `UnauthorizedError`, `ForbiddenError`, `ConflictError`,
  `ValidationError`) mapped to a uniform `{"error": {"code","message","details"}}`
  JSON envelope for every 4xx/5xx response.
- **Structured logging** — JSON/console logs via `structlog`, request IDs bound
  per-request and echoed in the `X-Request-ID` response header.
- **Integration test suite** — `backend/tests/` covers signup/login/refresh
  rotation & reuse detection/logout/password reset/email verification (`test_auth_flow.py`),
  RBAC and route protection (`test_rbac.py`), the identity/verification workflow
  (`test_identity.py`), mock MFA (`test_mfa.py`), and session management
  (`test_sessions.py`), run against a real Postgres instance.

### Foundation (prior phase, unchanged)

- **Docker setup** — multi-stage Dockerfiles for both services, `docker-compose.yml`
  wiring Postgres, Redis, backend, and frontend with healthchecks and a shared network.
- **Environment variables** — `.env.example` at root and in `backend/`; `frontend/.env.example`.
- **Frontend architecture** — App Router route groups (`(auth)`, `(dashboard)`), typed
  API client, React Query hooks, provider composition in `layout.tsx`. The frontend UI
  for the features above has **not** been built yet — backend-first, per this phase's scope.
- **Theme** — light/dark HSL design tokens in `globals.css`, toggled via `next-themes`.
- **Responsive layout, Sidebar, Navbar, Dashboard shell** — see
  `src/components/layout/`. Sidebar collapses into a slide-over `Sheet` below `md`.

## Default credentials (seeded on first startup)

| Email                     | Password         | Role        |
|----------------------------|------------------|-------------|
| `admin@apmisn.internal`    | `SuperAdmin@123` | Super Admin |

Change or remove this account before deploying anywhere near production.

## Running the database migration

```bash
cd backend
alembic upgrade head
```

The app also seeds roles/permissions/the super admin automatically on startup
(`app/main.py` lifespan handler), so a fresh `docker compose up` is enough to get
a usable system — `alembic upgrade head` is only required if you're not letting
SQLAlchemy create tables for you in a fresh environment.

## Running the backend test suite

```bash
docker compose up -d db redis     # or point DATABASE_URL at any disposable Postgres
cd backend
pip install -r requirements.txt
pytest
```

Tests create and drop the full schema around the session and wipe row data between
tests, so point `DATABASE_URL` at a database you don't mind being reset.

## Running locally with Docker

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend docs (Swagger): http://localhost:8000/api/v1/docs
- Backend health: http://localhost:8000/api/v1/health/live

## Running without Docker

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # point POSTGRES_HOST / REDIS_HOST at localhost if running services locally
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Verified before hand-off

- Every backend file (`app/`, `tests/`, `alembic/`) passes `python -m py_compile` —
  no syntax errors.
- The auth/RBAC/identity module tree was reviewed end-to-end for consistency:
  models ↔ schemas ↔ endpoints ↔ migration all line up (this pass fixed two small
  issues: a redundant `role_id` field in `AssignPermissionRequest`, and the
  `AuthHeaderMiddleware` existing but never being registered in `main.py`).
- This sandbox had no network access, so `pip install -r requirements.txt`,
  `alembic upgrade head` against a live Postgres, and `pytest` itself could not be
  executed here — run the commands under "Running the backend test suite" above
  in an environment with network/Docker access to get a live pass/fail signal.

## Explicitly out of scope for this phase

Payment/settlement business logic: settlement instructions, ledger reconciliation,
regional payment routing rules, and their corresponding data models, endpoints, and
UI. Real (non-mock) email delivery and real TOTP-based MFA are also out of scope —
both are implemented as documented mocks per the spec. No frontend UI exists yet
for any of the auth/RBAC/identity features above; the backend API is complete and
ready for a frontend phase to consume.
