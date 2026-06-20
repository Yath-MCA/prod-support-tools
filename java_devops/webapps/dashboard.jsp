<%@page contentType="text/html;charset=UTF-8" isELIgnored="true"%>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IMPACT Deploy Dashboard</title>
<link rel="stylesheet" type="text/css" href="css/dashboard.css">

</head>
<body>
<div class="app">

  <header class="header">
    <div class="logo">⚡ <span>IMPACT</span> Deploy</div>
    <div class="spacer"></div>
    <a href="logs.jsp" style="font-size:12px;color:var(--muted);text-decoration:none;
       padding:4px 10px;border:1px solid var(--border);border-radius:5px;margin-right:8px"
       onmouseover="this.style.color='var(--text)';this.style.background='#21262d'"
       onmouseout="this.style.color='var(--muted)';this.style.background='none'">
      📋 Tomcat Logs
    </a>
    <div class="pill" id="hdr-status">● Idle</div>
  </header>

  <div class="body">
    <aside class="sidebar">
      <div class="sidebar-section">
        <h3>Status</h3>
        <div class="status-card">
          <div class="status-row">
            <div class="status-dot idle" id="status-dot"></div>
            <div class="status-label" id="status-label">Idle</div>
          </div>
          <div class="status-meta" id="status-env">—</div>
          <div class="status-meta" id="status-time">—</div>
        </div>
      </div>
      <div class="sidebar-section">
        <h3>SFTP Environments</h3>
        <div id="env-list">—</div>
      </div>
      <div class="sidebar-section" style="flex:1">
        <h3>Deploy History</h3>
        <ul class="history-list" id="history-list">
          <li style="color:var(--muted);font-size:12px">No history yet.</li>
        </ul>
      </div>
    </aside>

    <main class="main">
      <div class="deploy-bar">
        <h2>Deploy Control</h2>
        <div class="deploy-controls">
          <div class="field">
            <label>SFTP Environment</label>
            <select id="sel-sftp"></select>
          </div>
          <div class="field">
            <label>Deploy Target</label>
            <select id="sel-target"></select>
          </div>
          <button class="btn btn-deploy" id="btn-deploy" onclick="startDeploy()">
            <span id="btn-icon">▶</span>
            <span id="btn-text">Deploy Now</span>
          </button>
          <button class="btn btn-deploy" id="btn-build-deploy" onclick="startGitBuildDeploy()">
            <span>⇅</span>
            <span>Git Build Deploy</span>
          </button>
          <button class="btn btn-clear" onclick="clearLogs()">Clear Logs</button>
        </div>
        <div class="progress-wrap">
          <div class="progress-bar" id="progress"></div>
        </div>
      </div>

      <div class="tabs">
        <div class="tab active" onclick="switchTab('logs',this)">Live Logs</div>
        <div class="tab" onclick="switchTab('tomcat',this)">Tomcat Servers</div>
        <div class="tab" onclick="switchTab('config',this)">Config Editor</div>
      </div>

      <div class="tab-panels">
        <div class="tab-panel active" id="tab-logs">
          <div class="terminal" id="terminal">
            <div class="terminal-empty">No deployment running. Press Deploy Now to start.</div>
          </div>
        </div>
        <div class="tab-panel" id="tab-tomcat">
          <div class="tomcat-grid" id="tomcat-grid">
            <div style="color:var(--muted);padding:20px">Loading servers…</div>
          </div>
        </div>
        <div class="tab-panel config-panel" id="tab-config">
          <div class="config-toolbar">
            <span class="note">Edit assets/deploy-config.json — changes take effect on next deploy.</span>
            <button class="btn btn-clear" onclick="saveConfig()">Save Config</button>
            <button class="btn btn-clear" onclick="loadConfig()">Reload</button>
          </div>
          <textarea class="config-editor" id="config-editor" spellcheck="false"></textarea>
        </div>
      </div>
    </main>
  </div>
</div>

<div class="toast-wrap" id="toasts"></div>

<script>
/* ── Build full endpoint URLs from the current dashboard location ── */
const PAGE_URL = new URL(window.location.href);
const API      = new URL('api.jsp', PAGE_URL).toString();
const STREAM   = new URL('stream.jsp', PAGE_URL).toString();

let evtSource  = null;
let autoScroll = true;

(async function init() {
  await Promise.all([loadConfig(), refreshStatus(), loadHistory()]);
  setInterval(refreshStatus, 3000);
  setInterval(loadHistory,   10000);
})();

/* ── Config ── */
async function loadConfig() {
  const res = await fetch(API + '?action=config');
  const cfg = await res.json();

  document.getElementById('sel-sftp').innerHTML = cfg.sftpEnvs
    .map(e => `<option value="${e.name}" ${e.name===cfg.activeSftpEnv?'selected':''}>${e.name}</option>`).join('');

  document.getElementById('sel-target').innerHTML = cfg.deployTargets
    .map(t => `<option value="${t.name}" ${t.name===cfg.defaultTarget?'selected':''}>${t.name}</option>`).join('');

  document.getElementById('env-list').innerHTML = cfg.sftpEnvs.map(e => {
    const ok = e.hostName && e.userName;
    return `<span class="env-pill"><span class="env-dot ${ok?'configured':''}"></span>
      ${e.name}${ok?' — '+e.hostName:' (not configured)'}</span>`;
  }).join('');

  document.getElementById('config-editor').value = JSON.stringify(cfg, null, 2);
}

async function saveConfig() {
  const raw = document.getElementById('config-editor').value;
  let parsed;
  try { parsed = JSON.parse(raw); } catch(e) { toast('Invalid JSON: '+e.message,'err'); return; }
  const res = await fetch(API + '?action=saveconfig', {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(parsed)
  });
  if (res.ok) { toast('Config saved.','ok'); await loadConfig(); }
  else        { toast('Save failed.','err'); }
}

/* ── History ── */
async function loadHistory() {
  const res  = await fetch(API + '?action=history');
  const list = await res.json();
  const ul   = document.getElementById('history-list');
  if (!list.length) return;
  ul.innerHTML = list.slice(0,12).map(h => {
    const dt  = h.startedAt ? new Date(h.startedAt) : null;
    const startedAt = dt ? formatIsoLocal(dt) : '—';
    const humanReadyBlity = dt ? timeAgo(dt) : '';
    const version = h.version ? ` · ${h.version}` : '';
    const link = h.logFile
      ? `<a href="${API}?action=logfile&file=${encodeURIComponent(h.logFile)}" target="_blank"
            style="color:var(--blue-h);font-size:11px;text-decoration:none">📄 log</a>` : '';
    return `<li class="history-item">
      <span class="h-env">${h.targetEnv||'—'}${version} ${link}</span>
      <span class="h-time">
        ${startedAt} · SFTP: ${h.sftpEnv||'—'}
        ${humanReadyBlity ? '<br />' + humanReadyBlity : ''}
      </span>
      <span class="h-badge ${h.status}">${h.status}</span></li>`;
  }).join('');
}

function formatIsoLocal(dt) {
  const pad = n => String(n).padStart(2, '0');
  return `${dt.getFullYear()}-${pad(dt.getMonth()+1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}`;
}

function timeAgo(dt) {
  const s = Math.floor((Date.now() - dt) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 172800) return "yesterday";
  if (s < 604800) return `${Math.floor(s / 86400)}d ago`;
  return `${Math.floor(s / 604800)}w ago`;
}


/* ── Status ── */
async function refreshStatus() {
  const res = await fetch(API + '?action=status');
  applyStatus(await res.json());
}

function applyStatus(s) {
  document.getElementById('status-dot').className   = 'status-dot '+s.status;
  document.getElementById('status-label').textContent = s.status.charAt(0).toUpperCase()+s.status.slice(1);
  document.getElementById('status-env').textContent  = s.targetEnv ? 'Target: '+s.targetEnv+'  · SFTP: '+s.sftpEnv : '—';
  document.getElementById('status-time').textContent = s.startedAt ? 'Started: '+formatIsoLocal(new Date(s.startedAt)) : '—';

  const colors = {idle:'#8b949e',running:'#e3b341',success:'#3fb950',failed:'#da3633'};
  const lbl = document.getElementById('status-label').textContent;
  const hdr = document.getElementById('hdr-status');
  hdr.textContent = '● '+lbl; hdr.style.color = colors[s.status]||'#8b949e';

  const running = s.status==='running';
  document.getElementById('btn-deploy').disabled = running;
  document.getElementById('btn-build-deploy').disabled = running;
  document.getElementById('btn-icon').innerHTML  = running ? '<div class="spinner"></div>' : '▶';
  document.getElementById('btn-text').textContent = running ? 'Deploying…' : 'Deploy Now';

  const prog = document.getElementById('progress');
  if (running) {
    prog.className = 'progress-bar indeterminate';
  } else if (s.status==='success') {
    prog.className='progress-bar'; prog.style.width='100%'; prog.style.background='var(--green)';
    setTimeout(()=>{prog.style.width='0';prog.style.background='var(--blue)'},2000);
  } else if (s.status==='failed') {
    prog.className='progress-bar'; prog.style.width='100%'; prog.style.background='var(--red)';
    setTimeout(()=>{prog.style.width='0';prog.style.background='var(--blue)'},2000);
  } else {
    prog.className='progress-bar'; prog.style.width='0';
  }
}

/* ── Deploy ── */
async function startDeploy() {
  await triggerDeploy('package');
}

async function startGitBuildDeploy() {
  await triggerDeploy('gitbuild');
}

async function triggerDeploy(deployMode) {
  const sftpEnv   = document.getElementById('sel-sftp').value;
  const targetEnv = document.getElementById('sel-target').value;
  const res  = await fetch(API + '?action=deploy', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({sftpEnv, targetEnv, deployMode})
  });
  const data = await res.json();
  if (!res.ok) { toast(data.error||'Deploy failed','err'); return; }
  const modeLabel = deployMode==='gitbuild' ? 'Git Build' : 'Package';
  toast(modeLabel+' deploy started: '+sftpEnv+' → '+targetEnv,'ok');
  clearLogs();
  startStreaming();
  applyStatus({status:'running',sftpEnv,targetEnv,startedAt:new Date().toISOString()});
}

/* ── SSE ── */
function startStreaming() {
  if (evtSource) { evtSource.close(); evtSource=null; }
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',i===0));
  document.querySelectorAll('.tab-panel').forEach((p,i)=>p.classList.toggle('active',i===0));
  evtSource = new EventSource(STREAM);
  evtSource.onmessage = e => {
    if (e.data==='__PING__') return;
    if (e.data==='__DONE__') { evtSource.close(); evtSource=null; refreshStatus(); loadHistory(); return; }
    appendLog(e.data);
  };
  evtSource.onerror = ()=>{ evtSource.close(); evtSource=null; refreshStatus(); };
}

function appendLog(line) {
  const term  = document.getElementById('terminal');
  const empty = term.querySelector('.terminal-empty');
  if (empty) empty.remove();
  const div = document.createElement('div');
  div.className   = 'log-line '+classifyLine(line);
  div.textContent = line;
  term.appendChild(div);
  if (autoScroll) term.scrollTop = term.scrollHeight;
}

function classifyLine(line) {
  const l = line.toLowerCase();
  if (l.includes('fatal')||l.includes('error')||l.includes('[error]')) return 'error';
  if (l.includes('warn'))                                               return 'warn';
  if (l.includes('done')||l.includes('success')||l.includes('complete')) return 'success';
  if (l.includes('=====')||l.includes('deploy target:'))                return 'step';
  if (l.startsWith('[')&&l.includes(']'))                               return 'dim';
  return 'info';
}

function clearLogs() {
  document.getElementById('terminal').innerHTML='<div class="terminal-empty">Log cleared.</div>';
}

/* ── Tomcat ── */
async function loadTomcatPanel() {
  const cfg     = await (await fetch(API+'?action=config')).json();
  const targets = (cfg.deployTargets||[]).filter(t=>t.tomcat);
  const grid    = document.getElementById('tomcat-grid');
  if (!targets.length) { grid.innerHTML='<div style="color:var(--muted);padding:20px">No tomcat config found.</div>'; return; }
  grid.innerHTML = targets.map(t=>`
    <div class="tomcat-card" id="tc-card-${t.name}">
      <div class="tomcat-card-head">
        <span class="tc-name">${t.name}</span>
        <span class="tc-state unknown" id="tc-state-${t.name}">checking…</span>
      </div>
      <div class="tomcat-card-body">
        <div class="tc-url">${t.tomcat.managerUrl||'—'}</div>
        <div class="tc-apps" id="tc-apps-${t.name}">—</div>
        <div class="tc-btns">
          <button class="btn-tc safe"   onclick="tcAction('${t.name}','reload')">↺ Reload App</button>
          <button class="btn-tc safe"   onclick="tcAction('${t.name}','start-app')">▶ Start App</button>
          <button class="btn-tc danger" onclick="tcAction('${t.name}','stop-app')">■ Stop App</button>
          <button class="btn-tc safe"   onclick="tcAction('${t.name}','restart-service')">⟳ Restart Service</button>
          <button class="btn-tc safe"   onclick="tcAction('${t.name}','start-service')">▶ Start Service</button>
          <button class="btn-tc danger" onclick="tcAction('${t.name}','stop-service')">■ Stop Service</button>
        </div>
        <pre class="tc-output" id="tc-out-${t.name}"></pre>
      </div>
    </div>`).join('');
  targets.forEach(t=>refreshTomcatCard(t.name));
}

async function refreshTomcatCard(name) {
  const stEl = document.getElementById('tc-state-'+name);
  const apEl = document.getElementById('tc-apps-'+name);
  if (!stEl) return;
  try {
    const d = await (await fetch(`${API}?action=tomcat-status&target=${encodeURIComponent(name)}`)).json();
    if (d.ok) {
      stEl.textContent='UP'; stEl.className='tc-state up';
      const run=(d.apps||[]).filter(a=>a.state==='running').length;
      apEl.textContent=run+' running / '+(d.apps||[]).length+' total';
    } else {
      stEl.textContent='DOWN'; stEl.className='tc-state down';
      apEl.textContent=d.raw||'unreachable';
    }
  } catch { stEl.textContent='ERROR'; stEl.className='tc-state unknown'; }
}

async function tcAction(name, cmd) {
  const outEl = document.getElementById('tc-out-'+name);
  const btns  = document.querySelectorAll('#tc-card-'+name+' .btn-tc');
  btns.forEach(b=>b.disabled=true);
  outEl.style.display='block'; outEl.textContent='Running: '+cmd+'…';
  try {
    const d = await (await fetch(`${API}?action=tomcat-action&target=${encodeURIComponent(name)}&cmd=${cmd}`,{method:'POST'})).json();
    outEl.textContent=d.raw||(d.ok?'OK':'Failed');
    toast(name+' / '+cmd+': '+(d.ok?'OK':'FAILED'), d.ok?'ok':'err');
    setTimeout(()=>refreshTomcatCard(name),1500);
  } catch(e) { outEl.textContent=String(e); toast(name+': failed','err'); }
  finally { btns.forEach(b=>b.disabled=false); }
}

/* ── Tabs ── */
function switchTab(name,el) {
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('active',p.id==='tab-'+name));
  if (name==='tomcat') loadTomcatPanel();
}

document.addEventListener('DOMContentLoaded',()=>{
  const term = document.getElementById('terminal');
  term.addEventListener('scroll',()=>{
    autoScroll = term.scrollTop+term.clientHeight >= term.scrollHeight-30;
  });
});

/* ── Toast ── */
function toast(msg,type='info') {
  const wrap=document.getElementById('toasts');
  const el=document.createElement('div');
  el.className='toast '+type; el.textContent=msg;
  wrap.appendChild(el);
  requestAnimationFrame(()=>requestAnimationFrame(()=>el.classList.add('show')));
  setTimeout(()=>{ el.classList.remove('show'); setTimeout(()=>el.remove(),400); },3500);
}
</script>
</body>
</html>
