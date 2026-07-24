# Mantis Bridge API

Express bridge in `impact_tracker/server` that wraps [MantisBT REST](https://github.com/mantisbt/mantisbt) (`{MANTIS_BASE}/api/rest`) for the Impact Tracker UI and script clients.

Upstream OpenAPI reference: [mantisbt `api/rest`](https://github.com/mantisbt/mantisbt/tree/master/api/rest) (see `mantisbt_openapi.yaml` in that tree).

## Base URL

| Environment | URL |
|-------------|-----|
| Local Bridge | `http://localhost:5100/api` |
| Upstream Mantis | `${MANTIS_BASE_URL}/api/rest` (default `https://mantis.newgen.co/api/rest`) |

Health (no auth): `GET /health` or `GET /api/health`.

## Auth flow

Mantis REST has **no username/password login**. A login is an **API token** validated with `GET /users/me`.

1. Client `POST /api/auth/login` with `{ "token": "<mantis-api-token>" }`
2. Bridge calls Mantis `GET /users/me`
3. On success, Bridge stores `mantisToken` + `user` in an **httpOnly cookie session**
4. Browser sends the cookie on subsequent requests (`credentials: include` / axios `withCredentials: true`)
5. Optional **Authorization** header passthrough: if present, that token is used for the call and the session is **not** mutated (useful for scripts)

| Bridge route | Behavior | Upstream |
|--------------|----------|----------|
| `POST /api/auth/login` | Validate token, set session | `GET /users/me` |
| `POST /api/auth/token` | Alias of login (UI compat) | same |
| `POST /api/auth/logout` | Clear cookie session | — |
| `GET /api/auth/me` | Session user, or live `/users/me` if Authorization only | `GET /users/me` (passthrough) |

Env: `SESSION_SECRET` (cookie signing), `MANTIS_BASE_URL`, `PROXY_PORT`.

PubKit SSO remains stubbed (`AUTH_MODE=pubkit` falls back to token session).

## Route map (Bridge → Mantis)

### Issues (`/tickets` aliases for UI)

| Bridge | Method | Upstream |
|--------|--------|----------|
| `/api/tickets` | GET | `GET /issues` |
| `/api/tickets/:id` | GET | `GET /issues/{id}` |
| `/api/tickets` | POST | `POST /issues` |
| `/api/tickets/:id` | PATCH | `PATCH /issues/{id}` |
| `/api/tickets/:id` | DELETE | close via `PATCH` (`?mode=close`, default) or `DELETE /issues/{id}` (`?mode=delete`) |
| `/api/tickets/:id/notes` | POST | `POST /issues/{id}/notes` |
| `/api/tickets/:id/notes/:noteId` | DELETE | `DELETE /issues/{id}/notes/{noteId}` |

### Projects / users / handlers

| Bridge | Method | Upstream |
|--------|--------|----------|
| `/api/projects` | GET | `GET /projects` |
| `/api/projects/:id` | GET | `GET /projects/{id}` |
| `/api/projects/:id/handlers` | GET | `GET /projects/{id}/handlers` |
| `/api/handlers?project_id=` | GET | same |
| `/api/users?project_id=` | GET | `GET /projects/{id}/users` (or `/users/me` if no project) |

### Filters / config

| Bridge | Method | Upstream |
|--------|--------|----------|
| `/api/filters` | GET | `GET /filters` |
| `/api/filters/:id` | GET | `GET /filters/{id}` |
| `/api/config` | GET | `GET /config` (falls back to local `config/impact.json`) |
| `/api/config/impact` | GET | local `config/impact.json` only |

### Errors

Failed Mantis calls return JSON:

```json
{ "message": "...", "status": 401, "mantis": { } }
```

## Phase 2 (not in this Bridge yet)

Attachments (multipart), relationships, tags, monitors — document later; not implemented.

## Client factory

`createMantisClient(token)` in `services/mantisClient.js` builds a per-request axios client (`baseURL = ${MANTIS_BASE}/api/rest`, `Authorization: token`) with shared error mapping.
