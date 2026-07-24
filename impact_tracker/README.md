# Impact Tracker



Impact-scoped Mantis ticket web app (Create / Read / Update / Close-Delete) that talks to [https://mantis.newgen.co/](https://mantis.newgen.co/) through a local **Mantis Bridge API**.



## Stack



- **UI:** React 18 + Vite + Tailwind + TanStack Query (same pattern as `quick_dashbaord`)

- **Bridge:** Express on port `5100` — see [`server/BRIDGE.md`](./server/BRIDGE.md)

- **Auth (MVP):** Per-user cookie session after Mantis API token login (PubKit SSO stubbed for later)



## Quick start



```bash

cd impact_tracker

npm install

cd server && npm install && cd ..

npm start

```



- UI: http://localhost:5174

- Bridge: http://localhost:5100



Copy `.env.example` → `.env.local` if needed (`SESSION_SECRET`, `MANTIS_BASE_URL`, `PROXY_PORT`).



1. Open Mantis → **My Account → API Tokens** → create a token  

2. Paste it on the Impact Tracker login screen  

3. Set the real IMPACT `project_id` in **Settings** or `config/impact.json`



## Features



| Action | Where |

|--------|--------|

| List + Impact filters | `/tickets` |

| Detail + Mantis deep-link | `/tickets/:id` |

| Assign / status / priority | Detail sidebar |

| Notes / updates | Detail notes panel |

| Create | `/tickets/new` |

| Close (default) / hard delete | Detail actions |



## Auth



- Bridge stores the token in an **httpOnly session cookie** (not a process-wide singleton — multiple browsers can use different tokens)

- UI uses axios `withCredentials: true`; `401` clears session and returns to `/login`

- Preferred: `POST /api/auth/login` — alias `POST /api/auth/token` still works

- Scripts may send `Authorization: <token>` without mutating the cookie session



Adapter docs: [`server/auth/README.md`](./server/auth/README.md). PubKit stub: `server/auth/pubkitAdapter.stub.js`.



## Config



`config/impact.json` — projects, filter presets, status/priority options, Mantis view URL.



## Bridge API (summary)



Full route map → Mantis OpenAPI: [`server/BRIDGE.md`](./server/BRIDGE.md)



| Area | Routes |

|------|--------|

| Auth | `POST /api/auth/login` (alias `/token`), `logout`, `me` |

| Tickets | `GET/POST /api/tickets`, `GET/PATCH/DELETE /api/tickets/:id`, notes add/delete |

| Projects | `GET /api/projects`, `GET /api/projects/:id`, handlers |

| Users | `GET /api/users` |

| Filters | `GET /api/filters`, `GET /api/filters/:id` |

| Config | `GET /api/config`, `GET /api/config/impact` |


