<%@page import="java.io.*,java.util.*"%>
<%@page contentType="text/event-stream;charset=UTF-8" buffer="none" autoFlush="true"%>
<%
/* ─────────────────────────────────────────────────────────────
   IMPACT Deploy — stream.jsp
   Server-Sent Events endpoint. Replays buffered log lines to
   late-joining clients, then subscribes for new lines until
   the deploy finishes.
   ───────────────────────────────────────────────────────────── */
response.setHeader("Cache-Control",             "no-cache");
response.setHeader("X-Accel-Buffering",         "no");
response.setHeader("Access-Control-Allow-Origin","*");

@SuppressWarnings("unchecked")
List<String>      logBuf = (List<String>)      application.getAttribute("impact.log");
@SuppressWarnings("unchecked")
List<PrintWriter> subs   = (List<PrintWriter>) application.getAttribute("impact.subs");

PrintWriter pw = response.getWriter();

/* Replay buffered lines so page-reload clients catch up */
if (logBuf != null) {
    synchronized (logBuf) {
        for (String line : logBuf) {
            if ("__DONE__".equals(line)) { pw.write("data: __DONE__\n\n"); pw.flush(); return; }
            pw.write("data: " + line + "\n\n");
        }
    }
    pw.flush();
}

/* Subscribe */
if (subs != null) subs.add(pw);

try {
    while (!pw.checkError()) {
        Thread.sleep(400);
        String status = (String) application.getAttribute("impact.status");
        if (!"running".equals(status)) {
            pw.write("data: __DONE__\n\n");
            pw.flush();
            break;
        }
        pw.write("data: __PING__\n\n");
        pw.flush();
    }
} catch (InterruptedException ignored) {
} finally {
    if (subs != null) subs.remove(pw);
}
%>
