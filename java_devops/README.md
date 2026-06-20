# IMPACT Deploy Dashboard

Deployment automation for the IMPACT Tomcat/Java application.
Runs entirely inside your **existing Tomcat** — no Python, no Node.js, no extra server.

---

## Folder Structure

```
C:\_IMPACT\deploy\
│
├── settings.local.json       Local machine overrides (paths, port) — not committed
│
├── webapps\                  ← Copy these files to Tomcat webapps\ROOT\devops\
│   ├── dashboard.jsp         Main dashboard UI
│   ├── api.jsp               All API endpoints (deploy, status, config, tomcat, logs)
│   ├── stream.jsp            SSE live deploy log stream
│   ├── logs.jsp              Tomcat server log console
│   ├── log-tail.jsp          SSE live Tomcat log tail
│   └── assets\
│       ├── deploy-config.json Shared config (SFTP, paths, Tomcat targets, build settings)
│       └── Deploy-Impact.ps1  PowerShell deploy script (package deploy + git build deploy)
│
└── archive\                  Superseded approaches (kept for reference)
    ├── python\               Flask dashboard + embeddable widget
    ├── java\                 Java Servlet approach
    └── hta\                  Standalone Windows HTA file
```

---

## Pages

| URL | Description |
|-----|-------------|
| `/devops/dashboard.jsp` | Deploy dashboard — trigger deploys, view history, manage Tomcat |
| `/devops/logs.jsp`      | Tomcat log console — view & live-tail catalina/localhost logs |

---

## Key Files

| File | Purpose |
|------|---------|
| `webapps/assets/deploy-config.json` | All environments, paths, Tomcat manager credentials, and build settings |
| `webapps/assets/Deploy-Impact.ps1` | The deployment script called by the dashboard for package and git-build modes |
| `api.jsp` | Server-side logic — reads config, runs PS1, proxies Tomcat Manager API |
| `stream.jsp` | Streams deploy output line-by-line to the browser via SSE |
| `logs.jsp` | Tomcat log viewer with live tail, search, and level filtering |
| `log-tail.jsp` | SSE endpoint that tails a Tomcat log file in real time |

---

## Deploy Modes

### Package Deploy

- Downloads the latest zip from SFTP
- Unzips into the configured process folder
- Archives the current live deployment items into `webRoot\archived\<version>\`
- Copies extracted files into the selected Tomcat web root
- Moves the processed zip to the configured backup folder

### Git Build Deploy

- Archives the current live deployment items into `webRoot\archived\<version>\`
- Runs `git pull` in the configured repo
- Runs the configured gulp build command
- Copies the configured build output folder into the selected Tomcat web root

---

## How Deploy Works

```
Browser → POST api.jsp?action=deploy
    └── api.jsp spawns background Thread
          ├── ProcessBuilder → /assets/Deploy-Impact.ps1 (resolved from the deployed webapp root)
          ├── Each output line → published to SSE subscribers
          └── On finish → writes .log file + updates deploy-history.json with target, version, and status

Browser → GET stream.jsp (EventSource)
    └── Replays buffered lines, subscribes to new output
          └── Closes when deploy finishes
```

The left sidebar shows recent deployment history with target, version, status, and a link to the saved log.

---

## Requirements

- Java 11+ / Tomcat 9+
- PowerShell 5.1+ on the same Windows server
- WinSCP installed at `C:\Program Files (x86)\WinSCP\`
- Git installed and available on `PATH` for git-build mode
- Gulp build command available on the server for git-build mode
- Tomcat Manager app enabled (for Tomcat control features)

---

## Config Areas

`webapps/assets/deploy-config.json` includes:

- `winscp` for WinSCP paths and session logging
- `remote` and `local` for package download, unzip, and backup paths
- `deployTargets` for target Tomcat web roots and Manager settings
- `build` for source repo path, branch, gulp command, working folder, and build output folder
