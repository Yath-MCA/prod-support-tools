Create a production-ready local dashboard using React + Vite with the following specs:

## Tech Stack
- React 18 + Vite
- Tailwind CSS for styling
- Axios for API calls
- React Query (TanStack Query) for data fetching & caching
- React Router v6 for navigation
- Recharts for charts/graphs

## Project Structure
src/
├── api/              # Axios instances & API calls
├── components/       # Reusable UI components
│   ├── ui/           # Base components (Button, Card, Badge, Modal)
│   └── layout/       # Sidebar, Header, Footer
├── pages/            # Route-level page components
├── hooks/            # Custom React hooks
├── context/          # Global state (AuthContext, ThemeContext)
├── utils/            # Helpers, formatters, constants
└── config/           # Env config, API base URLs

## Features Required

### Layout
- Collapsible sidebar with navigation icons + labels
- Top header with: page title, search bar, user avatar, dark/light toggle
- Responsive layout (mobile + desktop)
- Dark mode support via Tailwind dark class

### Dashboard Page
- KPI summary cards (total records, active sessions, recent activity)
- Line chart — activity over time using timeiso_c (ISODate)
- Bar chart — records grouped by rolename
- Recent activity table with columns:
  identifier | username | rolename | recordtype | timeiso_c | timestamp

### Data Collections (MongoDB backend — REST API)
Connect to these 3 endpoints:

GET /api/rFileslist
Fields: identifier(string), timeiso_c(ISODate), rolename(string),
        username(string), timestamp(string), recordtype(string)

GET /api/rdocviewhistory
Fields: identifier(string), timeiso_c(ISODate), username(string),
        session_id(string), rolename(string)

GET /api/rlinksharing
Fields: identifier(string), timeiso_c(ISODate), username(string),
        session_id(string), rolename(string), process(string),
        remarks(string), session_end_time(ISODate)

### Pages
1. Dashboard     — KPI cards + charts + recent activity table
2. Files List    — Table view of rFileslist with search + filter by rolename/recordtype
3. Doc History   — Table view of rdocviewhistory with filter by username/session_id
4. Link Sharing  — Table view of rlinksharing with filter by process/rolename
5. Settings      — API base URL config, theme toggle, refresh interval

### Table Features (all pages)
- Column sorting (asc/desc)
- Search/filter by key fields
- Pagination (10/25/50 rows per page)
- Export to CSV button
- Date range filter on timeiso_c
- Loading skeleton while fetching
- Empty state with message when no data

### API Layer (src/api/)
- Axios instance with baseURL from .env (VITE_API_BASE_URL)
- Request/response interceptors for error handling
- React Query hooks per collection:
  useRFilesList({ filters, page, limit })
  useRDocViewHistory({ filters, page, limit })
  useRLinkSharing({ filters, page, limit })
- Auto-refresh every 30 seconds (configurable)

### Environment Config
.env.local:
VITE_API_BASE_URL=http://localhost:5000/api
VITE_REFRESH_INTERVAL=30000

### Error Handling
- API error boundary with retry button
- Toast notifications for success/error (react-hot-toast)
- Network offline detection banner

### Code Quality
- TypeScript optional but preferred
- ESLint + Prettier config
- Absolute imports via vite path alias (@/ → src/)
- All components functional with hooks
- No class components

## Deliverables
1. Full working Vite project scaffold
2. package.json with all dependencies
3. vite.config.js with path aliases
4. tailwind.config.js with dark mode
5. All page components with mock data fallback
6. README.md with setup instructions

Start by generating the full project structure, 
then implement each file one by one.
Use mock data when API is unavailable so the UI 
always renders without a running backend.