<%@page import="java.io.*,java.util.*,java.net.*,java.nio.file.*,java.util.regex.*"%>
<%@page contentType="text/event-stream;charset=UTF-8" buffer="none" autoFlush="true"%>
<%!
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

static String jsonStr(String json, String key) {
    Matcher m = Pattern.compile("\"" + Pattern.quote(key) + "\"\\s*:\\s*\"([^\"\\\\]*)\"").matcher(json);
    return m.find() ? m.group(1) : "";
}

static String findTargetBlock(String configJson, String name) {
    int idx = configJson.indexOf("\"" + name + "\"");
    if (idx < 0) return "";
    int s = configJson.lastIndexOf("{", idx), depth = 0, i = s;
    while (i < configJson.length()) {
        char c = configJson.charAt(i);
        if (c == '{') depth++;
        else if (c == '}') { depth--; if (depth == 0) return configJson.substring(s, i + 1); }
        i++;
    }
    return "";
}

static String findTomcatBlock(String block) {
    int idx = block.indexOf("\"tomcat\"");
    if (idx < 0) return "";
    int s = block.indexOf("{", idx), depth = 0, i = s;
    while (i < block.length()) {
        char c = block.charAt(i);
        if (c == '{') depth++;
        else if (c == '}') { depth--; if (depth == 0) return block.substring(s, i + 1); }
        i++;
    }
    return "";
}
%>
<%
/* ─────────────────────────────────────────────────────────────
   log-tail.jsp — SSE live tail of a Tomcat log file
   Params: target, file, offset (byte position to start from)
   ───────────────────────────────────────────────────────────── */
response.setHeader("Cache-Control",              "no-cache");
response.setHeader("X-Accel-Buffering",          "no");
response.setHeader("Access-Control-Allow-Origin","*");

String target   = request.getParameter("target");
String fileName = new File(request.getParameter("file") != null ? request.getParameter("file") : "").getName();
long   offset   = 0;
try { offset = Long.parseLong(request.getParameter("offset")); } catch (Exception ignored) {}

/* ── Resolve log file path from config ── */
String webRoot = resolveWebRoot(application);
String CONFIG_PATH2 = Paths.get(webRoot, "assets", "deploy-config.json").normalize().toString();
String configJson   = new String(Files.readAllBytes(Paths.get(CONFIG_PATH2)), "UTF-8");

String tgtBlock = findTargetBlock(configJson, target);
String tcBlock  = findTomcatBlock(tgtBlock);
String logDir   = jsonStr(tcBlock, "logDir");

PrintWriter pw = response.getWriter();

if (logDir.isEmpty() || fileName.isEmpty()) {
    pw.write("data: ERROR: No logDir configured for target: " + target + "\n\n");
    pw.write("data: __DONE__\n\n");
    pw.flush();
    return;
}

File logFile = new File(logDir, fileName);
if (!logFile.exists()) {
    pw.write("data: File not found: " + logFile.getAbsolutePath() + "\n\n");
    pw.write("data: __DONE__\n\n");
    pw.flush();
    return;
}

long pos = offset > 0 ? offset : logFile.length(); // start from end if no offset

try (RandomAccessFile raf = new RandomAccessFile(logFile, "r")) {
    raf.seek(pos);
    while (!pw.checkError()) {
        long newLen = logFile.length();
        if (newLen < pos) {
            // File rotated — restart from beginning
            pos = 0;
            raf.seek(0);
            pw.write("data: [Log file rotated — restarting from beginning]\n\n");
            pw.flush();
        }
        if (newLen > pos) {
            raf.seek(pos);
            String line;
            while ((line = raf.readLine()) != null) {
                String decoded = new String(line.getBytes("ISO-8859-1"), "UTF-8");
                String safe = decoded.replace("\r", "");
                pw.write("data: " + safe + "\n\n");
            }
            pos = raf.getFilePointer();
            pw.flush();
        } else {
            // No new data — send ping
            pw.write("data: __PING__\n\n");
            pw.flush();
        }
        Thread.sleep(800);
    }
} catch (InterruptedException ignored) {
} catch (Exception e) {
    pw.write("data: ERROR: " + e.getMessage() + "\n\n");
}
%>
