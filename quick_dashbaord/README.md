# Prod Support Dashboard

React + Vite dashboard for monitoring production data from MongoDB REST API.

## Setup

```bash
npm install
cp .env.local .env.local   # already included
npm run dev
```

Open http://localhost:5173

## Environment

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:5000/api` | REST API base URL |
| `VITE_REFRESH_INTERVAL` | `30000` | Auto-refresh in ms (0 to disable) |

## Pages

| Route | Description |
|---|---|
| `/dashboard` | KPI cards, activity charts, recent files table |
| `/files` | rFileslist — filter by role, record type, date |
| `/doc-history` | rdocviewhistory — filter by username, session ID, date |
| `/link-sharing` | rlinksharing — filter by process, role, date |
| `/settings` | Change API URL, refresh interval, theme |

## API Endpoints Expected

```
GET /api/rFileslist
GET /api/rdocviewhistory
GET /api/rlinksharing
```

**Mock data is used automatically when the API is unreachable** — the UI always renders.

## Build

```bash
npm run build    # outputs to dist/
npm run preview  # preview the production build
```
