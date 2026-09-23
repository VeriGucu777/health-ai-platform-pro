# Health AI Platform Pro — Frontend

Phase 1A responsive Next.js scaffold for the Health AI Platform Pro web application. This frontend connects to the FastAPI backend in this repository and is English-primary with a structure prepared for future Turkish localization.

## Prerequisites

- Node.js 20 LTS or newer
- npm 10+
- Running FastAPI backend (see [README.md](../README.md))

## Installation

```powershell
cd frontend
npm install
copy .env.example .env.local
```

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Base URL of the FastAPI backend (no trailing slash) | `http://127.0.0.1:8001` |
| `NEXT_PUBLIC_API_USE_DEV_PROXY` | When `true` in development, browser uses same-origin `/api/v1` (see `API_PROXY_TARGET`) | `true` |
| `API_PROXY_TARGET` | Server-only rewrite target in `next.config.ts` (not exposed to the browser) | `https://…onrender.com` |

The centralized API client reads this value from `src/lib/config/env.ts` and targets `/api/v1` routes. Do not hard-code backend URLs inside components.

**Local UI + production API:** Production backends must not allow `localhost` in `CORS_ORIGINS`. Enable the dev proxy (`NEXT_PUBLIC_API_USE_DEV_PROXY=true` and `API_PROXY_TARGET`) so the browser talks to `http://localhost:3000/api/v1` only. Restart `npm run dev` after changing env vars.

## Local Development

1. Start the backend from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

2. Start the frontend dev server:

```powershell
cd frontend
npm run dev
```

3. Open http://localhost:3000

The backend CORS configuration already allows `http://localhost:3000` for local development.

## Backend Connection

- API base: `${NEXT_PUBLIC_API_BASE_URL}/api/v1`
- Health check (future connectivity use): `GET /api/v1/health`
- Auth routes (future phases): `POST /api/v1/auth/register`, `POST /api/v1/auth/login`

Phase 1A login and register pages are presentation-only and do not send authentication requests.

Central client entry point: `src/lib/api/index.ts`

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Start Next.js development server |
| `npm run build` | Production build |
| `npm run start` | Start production server |
| `npm run lint` | ESLint checks |
| `npm run typecheck` | TypeScript validation (`tsc --noEmit`) |

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # App Router pages and layout
│   ├── components/          # Reusable UI and layout components
│   ├── content/en/          # English copy (i18n-ready)
│   └── lib/
│       ├── api/             # Centralized API client
│       ├── config/          # Environment helpers
│       └── i18n/            # Locale scaffolding
├── .env.example
└── README.md
```

## Phase 1A Scope

Included:

- Landing, login, and register placeholder pages
- Responsive header, footer, navigation, button, form input, page container
- Accessibility basics (semantic HTML, labels, keyboard navigation, focus states)
- Environment-driven API client foundation

Not included yet:

- Real authentication flows
- Protected routes and session management
- Full i18n implementation
- Billing, admin, tenancy, RBAC, consent, audit, or ML lifecycle features

## Medical Safety

Do not place real patient identifiers or sensitive clinical data in UI examples, browser logs, or source code. Decision-support outputs must remain clearly labeled as non-diagnostic in future phases.
