# How to Use — IMPACT Deploy Dashboard

---

## 1. First-Time Setup

### Step 1 — Edit webapps/assets/deploy-config.json

Open `C:\_IMPACT\deploy\webapps\assets\deploy-config.json` and fill in your values:

```json
{
  "sftpEnvs": [
    { "name": "UAT", "hostName": "your-sftp-host", "userName": "user", "password": "pass" }
  ]
}
```

For git-build deploys, also set the build section:

```json
{
  "build": {
    "repoPath": "D:\\IMPACT-SOURCE",
    "branch": "main",
    "buildWorkingDir": "D:\\IMPACT-SOURCE",
    "gulpCommand": "gulp build",
    "outputDir": "D:\\IMPACT-SOURCE\\dist"
  }
}
```

For each deploy target, set the Tomcat manager URL, credentials, log directory:
```json
{
  "tomcat": {
    "managerUrl":  "http://localhost:8080",
    "user":        "admin",
    "password":    "yourpassword",
    "appPath":     "/",
    "serviceName": "Tomcat9UAT",
    "logDir":      "D:\\UAT-apache-tomcat-9-0-106\\logs"
  }
}
```

### Step 2 — Enable Tomcat Manager (optional, for Tomcat controls)

Add to `{TOMCAT_HOME}\conf\tomcat-users.xml`:
```xml
<role rolename="manager-script"/>
<user username="admin" password="yourpassword" roles="manager-script"/>
```
Restart Tomcat after editing.

### Step 3 — Copy JSP files to Tomcat

```
Copy webapps\ contents to:
  {TOMCAT_HOME}\webapps\ROOT\devops\
```

Files to copy:
```
index.jsp
api.jsp
stream.jsp
logs.jsp
log-tail.jsp
```

No restart needed — Tomcat hot-reloads JSP files automatically.

---

## 2. Open the Dashboard

```
http://localhost:8080/devops/dashboard.jsp
```

---

## 3. Run a Deployment

### Option A — Package Deploy

1. Select **SFTP Environment** (where to download the zip from)
2. Select **Deploy Target** (which Tomcat to deploy to)
3. Click **▶ Deploy Now**
4. Watch live output in the **Live Logs** terminal
5. Green `SUCCESS` = done. Red `FAILED` = check the log output

Package deploy automatically:
- Archives current live files into `webRoot\archived\<current-version>\`
- Downloads the latest zip from SFTP → `D:\_UAT_CODE_FTP\in\`
- Unzips → `D:\_UAT_CODE_FTP\process\`
- Copies files to the selected Tomcat web root
- Moves the processed zip to the configured backup folder
- Saves the full deploy log in `C:\_IMPACT\deploy\logs\`

### Option B — Git Build Deploy

1. Select **SFTP Environment**
2. Select **Deploy Target**
3. Click **Git Build Deploy**
4. Watch live output in the **Live Logs** terminal

Git build deploy automatically:
- Archives current live files into `webRoot\archived\<current-version>\`
- Runs `git pull`
- Runs the configured gulp build command
- Copies the configured build output folder to the selected Tomcat web root
- Saves the full deploy log in `C:\_IMPACT\deploy\logs\`

Note:
- The selected SFTP environment is still shown in deploy status/history, but git-build mode does not download a zip.

---

## 4. View Deploy History

The left sidebar shows the last 12 deployments.
Each entry includes target, deployed version, SFTP environment, status, and a link to the saved log file.
Click the **📄 log** link on any entry to view the full output log.

---

## 5. Manage Tomcat Servers

Click the **Tomcat Servers** tab.

| Button | Action |
|--------|--------|
| ↺ Reload App | Hot-reload via Tomcat Manager — no restart, sessions kept |
| ▶ Start App | Start a stopped app via Manager API |
| ■ Stop App | Stop the app via Manager API |
| ⟳ Restart Service | `net stop` then `net start` the Windows service |
| ▶ Start Service | `net start {serviceName}` |
| ■ Stop Service | `net stop {serviceName}` |

Each card shows **UP** / **DOWN** status and running app count.

---

## 6. View Tomcat Logs

Open: `http://localhost:8080/devops/logs.jsp`

Or click **Tomcat Logs** in the dashboard header.

Features:
- Select target server (UAT, QA, LIVE…)
- Select log file (`catalina.out`, `localhost.log`, etc.)
- Choose how many lines to show (100 / 500 / 1000 / 2000)
- **Live Tail** toggle — auto-streams new lines as Tomcat writes them
- **Search** — filter lines in real time
- **Level filter** — show only INFO / WARN / ERROR / SEVERE

---

## 7. Edit Config from Browser

Click the **Config Editor** tab in the dashboard.
Edit `assets/deploy-config.json` directly in the browser and click **Save Config**.
Changes take effect on the next deploy — no restart needed.

---

## 8. Adding a New Environment

Add a row to `webapps/assets/deploy-config.json`:

```json
{
  "name": "STAGING",
  "keywordInFilename": "-STAGING",
  "webRoot": "D:\\STAGING-tomcat\\webapps\\ROOT\\",
  "tomcat": {
    "managerUrl":  "http://localhost:8085",
    "user":        "admin",
    "password":    "admin123",
    "appPath":     "/",
    "serviceName": "Tomcat9STAGING",
    "logDir":      "D:\\STAGING-tomcat\\logs"
  }
}
```

It appears in all dropdowns immediately — no code changes needed.

---

## 9. Running the PS1 Script Directly (without dashboard)

### Package deploy

```powershell
cd C:\_IMPACT\deploy
.\webapps\assets\Deploy-Impact.ps1 -SftpEnv UAT -TargetEnv UAT -ConfigPath .\webapps\assets\deploy-config.json
```

### Git build deploy

```powershell
cd C:\_IMPACT\deploy
.\webapps\assets\Deploy-Impact.ps1 -TargetEnv UAT -DeployMode gitbuild -ConfigPath .\webapps\assets\deploy-config.json
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Deploy button does nothing | Check browser console. Ensure Tomcat is running. |
| `No file found` in logs | No zip on the SFTP server matching the selected env |
| `Build repo path not found` | Check `build.repoPath` in `deploy-config.json` |
| `Build output dir not found after build` | Check `build.outputDir` and your gulp output folder |
| `git` or `gulp` not recognized | Install them on the server or update the build command |
| Tomcat card shows DOWN | Check `managerUrl`, credentials in config, and that Manager app is enabled |
| Log viewer shows empty | Check `logDir` path in config for that target |
| WinSCP error | Verify WinSCP installed at `C:\Program Files (x86)\WinSCP\` |
