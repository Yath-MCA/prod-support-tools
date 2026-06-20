<%@page import="java.io.*,java.util.*,java.net.*,java.nio.file.*,java.time.*,java.util.regex.*,java.util.Base64"%>
<%@page contentType="application/json;charset=UTF-8" trimDirectiveWhitespaces="true"%>
<%!
/* ─────────────────────────────────────────────────────────────
   IMPACT Deploy — api.jsp
   All API actions handled here via ?action= parameter.
   Shared deploy state stored in ServletContext (application scope).
   ───────────────────────────────────────────────────────────── */

static final String CONFIG_WEB_PATH  = "/assets/deploy-config.json";
static final String PS1_WEB_PATH     = "/assets/Deploy-Impact.ps1";
static final String HISTORY_WEB_PATH = "/deploy-history.json";
static final String LOG_DIR_WEB_PATH = "/logs";

static String resolveWebRoot(ServletContext ctx) throws IOException {
    String realPath = ctx.getRealPath("/");
    if (realPath != null && !realPath.isEmpty()) {
        return Paths.get(realPath).normalize().toString();
    }
    try {
        URL rootUrl = ctx.getResource("/");
        if (rootUrl == null) throw new FileNotFoundException("Web root not found");
        return Paths.get(rootUrl.toURI()).normalize().toString();
    } catch (URISyntaxException e) {
        throw new IOException("Unable to resolve web root", e);
    }
}

static String resolveWebPath(ServletContext ctx, String webPath) throws IOException {
    String relative = webPath.startsWith("/") ? webPath.substring(1) : webPath;
    return Paths.get(resolveWebRoot(ctx), relative).normalize().toString();
}

static String repeatChar(char ch, int count) {
    StringBuilder sb = new StringBuilder();
    for (int i = 0; i < count; i++) sb.append(ch);
    return sb.toString();
}

static void sortFilesByLastModifiedDesc(File[] files) {
    Arrays.sort(files, new Comparator<File>() {
        public int compare(File a, File b) {
            long aTime = a.lastModified();
            long bTime = b.lastModified();
            if (aTime == bTime) return 0;
            return aTime < bTime ? 1 : -1;
        }
    });
}

/* ── File helpers ── */
static String readFile(String path) throws IOException {
    return new String(Files.readAllBytes(Paths.get(path)), "UTF-8");
}
static void writeFile(String path, String content) throws IOException {
    Files.write(Paths.get(path), content.getBytes("UTF-8"));
}
static String readBody(HttpServletRequest req) throws IOException {
    StringBuilder sb = new StringBuilder();
    try (BufferedReader br = req.getReader()) {
        String line;
        while ((line = br.readLine()) != null) sb.append(line);
    }
    return sb.toString();
}

/* ── Simple JSON field extractor (no external JAR needed) ── */
static String jsonStr(String json, String key) {
    Pattern p = Pattern.compile("\"" + Pattern.quote(key) + "\"\\s*:\\s*\"([^\"\\\\]*)\"");
    Matcher m = p.matcher(json);
    return m.find() ? m.group(1) : "";
}

static String jsonEsc(String s) {
    if (s == null) return "";
    return s.replace("\\", "\\\\").replace("\"", "\\\"");
}

static String extractVersion(List<String> lines) {
    if (lines == null) return "";
    for (String line : lines) {
        if (line == null) continue;
        int versionIndex = line.indexOf("Version:");
        if (versionIndex >= 0) {
            return line.substring(versionIndex + "Version:".length()).trim();
        }
    }
    return "";
}

/* ── Extract a named object block from a JSON array by "name" field ── */
static String findBlock(String json, String nameValue) {
    int idx = json.indexOf("\"" + nameValue + "\"");
    if (idx < 0) return "";
    int start = json.lastIndexOf("{", idx);
    if (start < 0) return "";
    int depth = 0, i = start;
    while (i < json.length()) {
        char c = json.charAt(i);
        if      (c == '{') depth++;
        else if (c == '}') { depth--; if (depth == 0) return json.substring(start, i+1); }
        i++;
    }
    return "";
}

/* ── Extract a named sub-object ── */
static String findSubObject(String block, String key) {
    int idx = block.indexOf("\"" + key + "\"");
    if (idx < 0) return "";
    int start = block.indexOf("{", idx);
    if (start < 0) return "";
    int depth = 0, i = start;
    while (i < block.length()) {
        char c = block.charAt(i);
        if      (c == '{') depth++;
        else if (c == '}') { depth--; if (depth == 0) return block.substring(start, i+1); }
        i++;
    }
    return "";
}

/* ── Publish a log line to buffer + all SSE subscribers ── */
@SuppressWarnings("unchecked")
static void publish(ServletContext ctx, String line) {
    List<String> buf = (List<String>) ctx.getAttribute("impact.log");
    List<PrintWriter> subs = (List<PrintWriter>) ctx.getAttribute("impact.subs");
    if (buf  != null) buf.add(line);
    if (subs != null) {
        Iterator<PrintWriter> it = subs.iterator();
        while (it.hasNext()) {
            PrintWriter pw = it.next();
            try { pw.write("data: " + line + "\n\n"); pw.flush(); }
            catch (Exception e) { it.remove(); }
        }
    }
}

/* ── Append entry to history JSON file ── */
static synchronized void appendHistory(String historyPath, String entry) {
    try {
        String raw = "[]";
        File f = new File(historyPath);
        if (f.exists()) raw = new String(Files.readAllBytes(f.toPath()), "UTF-8").trim();
        if (!raw.startsWith("[")) raw = "[]";
        String body = raw.substring(1, raw.lastIndexOf("]")).trim();
        String newRaw = "[" + entry + (body.isEmpty() ? "" : "," + body) + "]";
        // keep last 50
        int count = 0, i = 0;
        while (i < newRaw.length() && count < 51) { if (newRaw.charAt(i)=='{') count++; i++; }
        writeFile(historyPath, newRaw);
    } catch (Exception e) { /* best effort */ }
}

/* ── Write per-deploy log file ── */
static String writeDeployLog(String logDir, String sftp, String target, String status, String startedAt,
                              String version, List<String> lines) {
    try {
        String divider = repeatChar('=', 60);
        new File(logDir).mkdirs();
        String ts = startedAt.replace(":", "-").replaceAll("\\..*", "").substring(0, 19);
        String fname = ts + "-" + target + "-" + status + ".log";
        StringBuilder sb = new StringBuilder();
        sb.append("IMPACT Deploy Log\n");
        sb.append(divider).append("\n");
        sb.append("SFTP   : ").append(sftp).append("\n");
        sb.append("Target : ").append(target).append("\n");
        sb.append("Version: ").append(version == null || version.isEmpty() ? "-" : version).append("\n");
        sb.append("Started: ").append(startedAt).append("\n");
        sb.append("Status : ").append(status.toUpperCase()).append("\n");
        sb.append(divider).append("\n\n");
        for (String l : lines) sb.append(l).append("\n");
        writeFile(Paths.get(logDir, fname).toString(), sb.toString());
        return fname;
    } catch (Exception e) { return ""; }
}

/* ── Tomcat Manager HTTP call ── */
static String tomcatCall(String baseUrl, String user, String pass, String endpoint) {
    try {
        URL url = new URL(baseUrl.replaceAll("/$","") + "/manager/text" + endpoint);
        HttpURLConnection con = (HttpURLConnection) url.openConnection();
        con.setConnectTimeout(6000); con.setReadTimeout(8000);
        String creds = Base64.getEncoder().encodeToString((user+":"+pass).getBytes("UTF-8"));
        con.setRequestProperty("Authorization", "Basic " + creds);
        con.connect();
        BufferedReader br = new BufferedReader(new InputStreamReader(
            con.getResponseCode() < 400 ? con.getInputStream() : con.getErrorStream()));
        StringBuilder sb = new StringBuilder();
        String l; while ((l=br.readLine())!=null) sb.append(l).append("\n");
        return sb.toString().trim();
    } catch (Exception e) { return "ERROR: " + e.getMessage(); }
}

/* ── Read last N lines of a file efficiently using RandomAccessFile ── */
static String tailFile(String filePath, int maxLines) {
    File f = new File(filePath);
    if (!f.exists()) return "File not found: " + filePath;
    List<String> lines = new ArrayList<>();
    try (RandomAccessFile raf = new RandomAccessFile(f, "r")) {
        long fileLen = raf.length();
        if (fileLen == 0) return "";
        long pos = fileLen - 1;
        StringBuilder sb = new StringBuilder();
        while (pos >= 0 && lines.size() < maxLines) {
            raf.seek(pos);
            char c = (char) raf.read();
            if (c == '\n' && sb.length() > 0) {
                lines.add(0, sb.reverse().toString());
                sb.setLength(0);
            } else if (c != '\r') {
                sb.append(c);
            }
            pos--;
        }
        if (sb.length() > 0) lines.add(0, sb.reverse().toString());
    } catch (Exception e) { return "Error reading file: " + e.getMessage(); }
    StringBuilder result = new StringBuilder();
    for (String l : lines) result.append(l).append("\n");
    return result.toString();
}

/* ── Windows service control ── */
static String serviceCmd(String action, String serviceName) {
    if (serviceName == null || serviceName.isEmpty()) return "No serviceName configured";
    try {
        Process p = new ProcessBuilder("net", action, serviceName)
            .redirectErrorStream(true).start();
        BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()));
        StringBuilder sb = new StringBuilder();
        String l; while ((l=br.readLine())!=null) sb.append(l).append("\n");
        p.waitFor();
        return sb.toString().trim();
    } catch (Exception e) { return "ERROR: " + e.getMessage(); }
}
%>
<%
/* ── Init shared state ── */
synchronized (application) {
    if (application.getAttribute("impact.status") == null) {
        application.setAttribute("impact.status",    "idle");
        application.setAttribute("impact.sftp",      "");
        application.setAttribute("impact.target",    "");
        application.setAttribute("impact.startedAt", "");
        application.setAttribute("impact.log",  Collections.synchronizedList(new ArrayList<String>()));
        application.setAttribute("impact.subs", Collections.synchronizedList(new ArrayList<PrintWriter>()));
    }
}

response.setHeader("Access-Control-Allow-Origin",  "*");
response.setHeader("Access-Control-Allow-Headers", "Content-Type");
response.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");

final String CONFIG_PATH  = resolveWebPath(application, CONFIG_WEB_PATH);
final String PS1_PATH     = resolveWebPath(application, PS1_WEB_PATH);
final String HISTORY_PATH = resolveWebPath(application, HISTORY_WEB_PATH);
final String LOG_DIR      = resolveWebPath(application, LOG_DIR_WEB_PATH);

String action = request.getParameter("action");
if (action == null) action = "";

/* ══════════════════════════════════════════════════════════
   action=config  GET  — return raw deploy-config.json
   ══════════════════════════════════════════════════════════ */
if ("config".equals(action)) {
    out.print(readFile(CONFIG_PATH));

/* ══════════════════════════════════════════════════════════
   action=saveconfig  POST  — write body to deploy-config.json
   ══════════════════════════════════════════════════════════ */
} else if ("saveconfig".equals(action)) {
    String body = readBody(request);
    writeFile(CONFIG_PATH, body);
    out.print("{\"ok\":true}");

/* ══════════════════════════════════════════════════════════
   action=status  GET  — return current deploy state
   ══════════════════════════════════════════════════════════ */
} else if ("status".equals(action)) {
    String status    = (String) application.getAttribute("impact.status");
    String sftp      = (String) application.getAttribute("impact.sftp");
    String target    = (String) application.getAttribute("impact.target");
    String startedAt = (String) application.getAttribute("impact.startedAt");
    out.print("{\"status\":\"" + status + "\",\"sftpEnv\":\"" + sftp +
              "\",\"targetEnv\":\"" + target + "\",\"startedAt\":\"" + startedAt + "\"}");

/* ══════════════════════════════════════════════════════════
   action=history  GET  — return deploy-history.json
   ══════════════════════════════════════════════════════════ */
} else if ("history".equals(action)) {
    File hf = new File(HISTORY_PATH);
    out.print(hf.exists() ? readFile(HISTORY_PATH) : "[]");

/* ══════════════════════════════════════════════════════════
   action=deploy  POST  — start deploy background thread
   ══════════════════════════════════════════════════════════ */
} else if ("deploy".equals(action)) {
    String curStatus = (String) application.getAttribute("impact.status");
    if ("running".equals(curStatus)) {
        response.setStatus(409);
        out.print("{\"error\":\"Deploy already running\"}");
    } else {
        String body = readBody(request);
        final String sftpEnv    = jsonStr(body, "sftpEnv");
        final String targetEnv  = jsonStr(body, "targetEnv");
        final String deployMode = jsonStr(body, "deployMode").isEmpty() ? "package" : jsonStr(body, "deployMode");
        final String startedAt = LocalDateTime.now().toString();
        final ServletContext ctx = application;

        // Reset state
        application.setAttribute("impact.status",    "running");
        application.setAttribute("impact.sftp",      sftpEnv);
        application.setAttribute("impact.target",    targetEnv);
        application.setAttribute("impact.startedAt", startedAt);
        @SuppressWarnings("unchecked")
        List<String> log = (List<String>) application.getAttribute("impact.log");
        log.clear();

        Thread t = new Thread(new Runnable() {
            public void run() {
                List<String> runLines = new ArrayList<String>();
                publish(ctx, "Starting — Mode:" + deployMode + "  SFTP:" + sftpEnv + "  Target:" + targetEnv);
                runLines.add("Starting — Mode:" + deployMode + "  SFTP:" + sftpEnv + "  Target:" + targetEnv);

                List<String> cmd = Arrays.asList(
                    "powershell", "-ExecutionPolicy", "Bypass",
                    "-File",       PS1_PATH,
                    "-SftpEnv",    sftpEnv,
                    "-TargetEnv",  targetEnv,
                    "-DeployMode", deployMode,
                    "-ConfigPath", CONFIG_PATH
                );

                boolean success = false;
                try {
                    Process proc = new ProcessBuilder(cmd).redirectErrorStream(true).start();
                    try (BufferedReader br = new BufferedReader(
                            new InputStreamReader(proc.getInputStream(), "UTF-8"))) {
                        String line;
                        while ((line = br.readLine()) != null) {
                            publish(ctx, line);
                            runLines.add(line);
                        }
                    }
                    success = proc.waitFor() == 0;
                } catch (Exception e) {
                    String err = "[ERROR] " + e.getMessage();
                    publish(ctx, err);
                    runLines.add(err);
                }

                String finalStatus = success ? "success" : "failed";
                String version = extractVersion(runLines);
                String logFile = writeDeployLog(LOG_DIR, sftpEnv, targetEnv, finalStatus, startedAt, version, runLines);
                publish(ctx, success ? "===== SUCCESS =====" : "===== FAILED =====");
                publish(ctx, "__DONE__");

                ctx.setAttribute("impact.status", finalStatus);

                // Write history entry
                appendHistory(HISTORY_PATH, "{\"sftpEnv\":\"" + jsonEsc(sftpEnv) + "\",\"targetEnv\":\"" + jsonEsc(targetEnv) +
                    "\",\"version\":\"" + jsonEsc(version) + "\",\"status\":\"" + jsonEsc(finalStatus) + "\",\"startedAt\":\"" + jsonEsc(startedAt) +
                    "\",\"logFile\":\"" + jsonEsc(logFile) + "\"}");
            }
        });
        t.setDaemon(true);
        t.start();

        out.print("{\"ok\":true,\"message\":\"Deploy started\"}");
    }

/* ══════════════════════════════════════════════════════════
   action=tomcat-status  GET  ?target=UAT
   ══════════════════════════════════════════════════════════ */
} else if ("tomcat-status".equals(action)) {
    String target = request.getParameter("target");
    String statusConfig = readFile(CONFIG_PATH);
    String statusTargetBlock = findBlock(statusConfig, target);
    String statusTomcatBlock = findSubObject(statusTargetBlock, "tomcat");
    String statusUrl = jsonStr(statusTomcatBlock, "managerUrl");
    String statusUser = jsonStr(statusTomcatBlock, "user");
    String statusPass = jsonStr(statusTomcatBlock, "password");
    if (statusUrl.isEmpty()) {
        out.print("{\"ok\":false,\"raw\":\"No tomcat config for: " + target + "\"}");
    } else {
        String raw = tomcatCall(statusUrl, statusUser, statusPass, "/list");
        boolean ok = raw.startsWith("OK");
        StringBuilder apps = new StringBuilder("[");
        if (ok) {
            String[] lines = raw.split("\n");
            for (int i = 1; i < lines.length; i++) {
                String[] parts = lines[i].split(":");
                if (parts.length >= 3) {
                    if (apps.length() > 1) apps.append(",");
                    apps.append("{\"path\":\"").append(parts[0])
                        .append("\",\"state\":\"").append(parts[1])
                        .append("\",\"sessions\":\"").append(parts[2]).append("\"}");
                }
            }
        }
        apps.append("]");
        String safeRaw = raw.replace("\"","\\\"").replace("\n"," ");
        out.print("{\"ok\":" + ok + ",\"raw\":\"" + safeRaw + "\",\"apps\":" + apps + "}");
    }

/* ══════════════════════════════════════════════════════════
   action=tomcat-action  POST  ?target=UAT&cmd=reload
   ══════════════════════════════════════════════════════════ */
} else if ("tomcat-action".equals(action)) {
    String target  = request.getParameter("target");
    String cmd     = request.getParameter("cmd");
    String actionConfig  = readFile(CONFIG_PATH);
    String actionTargetBlock  = findBlock(actionConfig, target);
    String actionTomcatBlock   = findSubObject(actionTargetBlock, "tomcat");
    String url     = jsonStr(actionTomcatBlock, "managerUrl");
    String user    = jsonStr(actionTomcatBlock, "user");
    String pass    = jsonStr(actionTomcatBlock, "password");
    String appPath = jsonStr(actionTomcatBlock, "appPath");
    if (appPath.isEmpty()) appPath = "/";
    String svc = jsonStr(actionTomcatBlock, "serviceName");

    String raw; boolean ok;
    switch (cmd == null ? "" : cmd) {
        case "reload":         raw = tomcatCall(url, user, pass, "/reload?path="   + appPath); ok = raw.startsWith("OK"); break;
        case "start-app":      raw = tomcatCall(url, user, pass, "/start?path="    + appPath); ok = raw.startsWith("OK"); break;
        case "stop-app":       raw = tomcatCall(url, user, pass, "/stop?path="     + appPath); ok = raw.startsWith("OK"); break;
        case "start-service":  raw = serviceCmd("start", svc); ok = !raw.startsWith("ERROR"); break;
        case "stop-service":   raw = serviceCmd("stop",  svc); ok = !raw.startsWith("ERROR"); break;
        case "restart-service":
            String s1 = serviceCmd("stop",  svc);
            String s2 = serviceCmd("start", svc);
            raw = s1 + "\n" + s2; ok = !s2.startsWith("ERROR"); break;
        default: raw = "Unknown cmd: " + cmd; ok = false;
    }
    String safeRaw = raw.replace("\"","\\\"").replace("\n"," ");
    out.print("{\"ok\":" + ok + ",\"raw\":\"" + safeRaw + "\",\"source\":\"jsp\"}");

/* ══════════════════════════════════════════════════════════
   action=logfiles  GET  — list log files
   ══════════════════════════════════════════════════════════ */
} else if ("logfiles".equals(action)) {
    File dir = new File(LOG_DIR);
    File[] files = dir.exists() ? dir.listFiles(new FilenameFilter() {
        public boolean accept(File d, String n) {
            return n.endsWith(".log");
        }
    }) : new File[0];
    if (files == null) files = new File[0];
    sortFilesByLastModifiedDesc(files);
    StringBuilder sb = new StringBuilder("[");
    for (int i = 0; i < files.length; i++) {
        if (i > 0) sb.append(",");
        sb.append("\"").append(files[i].getName()).append("\"");
    }
    out.print(sb.append("]").toString());

/* ══════════════════════════════════════════════════════════
   action=logfile  GET  ?file=<filename>  — return log file
   ══════════════════════════════════════════════════════════ */
} else if ("logfile".equals(action)) {
    String fname = new File(request.getParameter("file")).getName(); // prevent traversal
    File f = new File(LOG_DIR, fname);
    response.setContentType("text/plain;charset=UTF-8");
    if (f.exists()) {
        out.print(readFile(f.getAbsolutePath()));
    } else {
        response.setStatus(404);
        out.print("Not found: " + fname);
    }

/* ══════════════════════════════════════════════════════════
   action=tomcat-logfiles  GET  ?target=UAT
   List log files in the target's Tomcat logDir
   ══════════════════════════════════════════════════════════ */
} else if ("tomcat-logfiles".equals(action)) {
    String target = request.getParameter("target");
    String tomcatLogsConfig = readFile(CONFIG_PATH);
    String tomcatLogsTargetBlock = findBlock(tomcatLogsConfig, target);
    String tomcatLogsBlock  = findSubObject(tomcatLogsTargetBlock, "tomcat");
    String logDir2  = jsonStr(tomcatLogsBlock, "logDir");
    if (logDir2.isEmpty()) {
        out.print("{\"ok\":false,\"files\":[],\"error\":\"No logDir configured for " + target + "\"}");
    } else {
        File dir = new File(logDir2);
        File[] files = dir.exists()
            ? dir.listFiles(new FilenameFilter() {
                public boolean accept(File d, String n) {
                    return n.endsWith(".log") || n.endsWith(".txt") || n.equals("catalina.out");
                }
            })
            : new File[0];
        if (files == null) files = new File[0];
        sortFilesByLastModifiedDesc(files);
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < files.length; i++) {
            if (i > 0) sb.append(",");
            sb.append("{\"name\":\"").append(files[i].getName())
              .append("\",\"size\":").append(files[i].length())
              .append(",\"modified\":").append(files[i].lastModified()).append("}");
        }
        out.print("{\"ok\":true,\"logDir\":\"" + logDir2.replace("\\","\\\\") + "\",\"files\":" + sb + "]}");
    }

/* ══════════════════════════════════════════════════════════
   action=tomcat-logcontent  GET  ?target=UAT&file=catalina.out&lines=500
   Read last N lines of a Tomcat log file
   ══════════════════════════════════════════════════════════ */
} else if ("tomcat-logcontent".equals(action)) {
    response.setContentType("text/plain;charset=UTF-8");
    String target   = request.getParameter("target");
    String fileName = new File(request.getParameter("file") != null ? request.getParameter("file") : "").getName();
    int    lines    = 500;
    try { lines = Integer.parseInt(request.getParameter("lines")); } catch (Exception ignored) {}
    lines = Math.min(lines, 5000);

    String logContentConfig = readFile(CONFIG_PATH);
    String logContentTargetBlock = findBlock(logContentConfig, target);
    String logContentTomcatBlock  = findSubObject(logContentTargetBlock, "tomcat");
    String logDir2  = jsonStr(logContentTomcatBlock, "logDir");

    if (logDir2.isEmpty() || fileName.isEmpty()) {
        out.print("No logDir or file specified.");
    } else {
        String filePath = logDir2 + File.separator + fileName;
        out.print(tailFile(filePath, lines));
    }

/* ══════════════════════════════════════════════════════════
   action=tomcat-logsize  GET  ?target=UAT&file=catalina.out
   Return current file size (used by log-tail.jsp for change detection)
   ══════════════════════════════════════════════════════════ */
} else if ("tomcat-logsize".equals(action)) {
    String target   = request.getParameter("target");
    String fileName = new File(request.getParameter("file") != null ? request.getParameter("file") : "").getName();
    String logSizeConfig = readFile(CONFIG_PATH);
    String logSizeTargetBlock = findBlock(logSizeConfig, target);
    String logSizeTomcatBlock  = findSubObject(logSizeTargetBlock, "tomcat");
    String logDir2  = jsonStr(logSizeTomcatBlock, "logDir");
    long   size     = new File(logDir2 + File.separator + fileName).length();
    out.print("{\"size\":" + size + "}");

} else {
    response.setStatus(400);
    out.print("{\"error\":\"Unknown action: " + action + "\"}");
}
%>
