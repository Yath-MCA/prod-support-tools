<%@page contentType="text/html;charset=UTF-8"%>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tomcat Log Console — IMPACT</title>
<style>
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  :root{
    --bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#c9d1d9;--muted:#8b949e;
    --blue:#1f6feb;--blue-h:#388bfd;--red:#da3633;--yellow:#e3b341;--green:#3fb950;
    --orange:#f97316;--purple:#a78bfa;--font-mono:"Cascadia Code","Fira Code",Consolas,monospace;
  }
  html,body{height:100%;background:var(--bg);color:var(--text);
    font-family:-apple-system,"Segoe UI",sans-serif;font-size:13px}
  /* ── Header ── */
  .header{display:flex;align-items:center;gap:12px;padding:0 20px;height:52px;
    background:var(--surface);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10}
  .header .logo{font-size:15px;font-weight:700;color:#fff;white-space:nowrap}
  .header .logo span{color:var(--blue-h)}
  .back-link{font-size:12px;color:var(--muted);text-decoration:none;
    padding:4px 10px;border:1px solid var(--border);border-radius:5px}
  .back-link:hover{color:var(--text);background:#21262d}
  .spacer{flex:1}
  /* ── Toolbar ── */
  .toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;
    padding:12px 20px;background:var(--surface);border-bottom:1px solid var(--border)}
  .field{display:flex;flex-direction:column;gap:3px}
  .field label{font-size:10px;font-weight:600;text-transform:uppercase;
    letter-spacing:.5px;color:var(--muted)}
  select,input[type=text]{background:var(--bg);color:var(--text);
    border:1px solid var(--border);border-radius:5px;padding:5px 8px;
    font-size:12px;outline:none}
  select{min-width:110px;cursor:pointer}
  select:focus,input:focus{border-color:var(--blue)}
  .btn{display:inline-flex;align-items:center;gap:5px;padding:6px 14px;
    border:none;border-radius:5px;font-size:12px;font-weight:600;cursor:pointer}
  .btn-primary{background:var(--blue);color:#fff}
  .btn-primary:hover{background:var(--blue-h)}
  .btn-success{background:#238636;color:#fff}
  .btn-success:hover{background:#2ea043}
  .btn-ghost{background:#21262d;color:var(--text);border:1px solid var(--border)}
  .btn-ghost:hover{background:#30363d}
  .btn-danger{background:#3a1a1a;color:var(--red);border:1px solid #da363344}
  .btn-danger:hover{background:#4a2020}
  .search-wrap{position:relative;flex:1;min-width:160px}
  .search-wrap input{width:100%;padding-left:28px}
  .search-icon{position:absolute;left:8px;top:50%;transform:translateY(-50%);
    color:var(--muted);font-size:13px;pointer-events:none}
  /* ── Status bar ── */
  .statusbar{display:flex;align-items:center;gap:12px;padding:6px 20px;
    background:#010409;border-bottom:1px solid var(--border);font-size:11px;color:var(--muted)}
  .tail-dot{width:7px;height:7px;border-radius:50%;background:var(--muted);flex-shrink:0}
  .tail-dot.live{background:var(--green);animation:blink 1.2s infinite}
  @keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
  /* ── Terminal ── */
  .terminal{height:calc(100vh - 52px - 60px - 36px);overflow-y:auto;
    padding:12px 20px;font-family:var(--font-mono);font-size:12px;
    line-height:1.65;background:#010409}
  .terminal::-webkit-scrollbar{width:6px}
  .terminal::-webkit-scrollbar-thumb{background:#21262d;border-radius:3px}
  /* ── Log line colours ── */
  .ll{white-space:pre-wrap;word-break:break-all;display:block}
  .ll-severe,.ll-fatal  {color:#ff6b6b;font-weight:600}
  .ll-error             {color:var(--red)}
  .ll-warn              {color:var(--yellow)}
  .ll-info              {color:#c9d1d9}
  .ll-debug,.ll-fine    {color:var(--muted)}
  .ll-ping              {display:none}
  .ll-sep               {color:#21262d;border-top:1px solid #21262d;margin:4px 0}
  /* highlighted search match */
  mark{background:#e3b34133;color:var(--yellow);border-radius:2px;padding:0 1px}
  /* ── Level badges ── */
  .level-btn{padding:3px 8px;border-radius:4px;border:1px solid transparent;
    font-size:10px;font-weight:700;cursor:pointer;opacity:.45;transition:opacity .15s}
  .level-btn.active{opacity:1}
  .level-btn.lv-all    {border-color:#30363d;color:var(--text)}
  .level-btn.lv-info   {border-color:#388bfd44;color:var(--blue-h)}
  .level-btn.lv-warn   {border-color:#e3b34144;color:var(--yellow)}
  .level-btn.lv-error  {border-color:#da363344;color:var(--red)}
  .level-btn.lv-severe {border-color:#ff6b6b44;color:#ff6b6b}
  /* ── Toast ── */
  .toast-wrap{position:fixed;bottom:20px;right:20px;display:flex;
    flex-direction:column;gap:6px;z-index:99}
  .toast{padding:8px 14px;border-radius:6px;font-size:12px;font-weight:500;
    opacity:0;transform:translateY(8px);transition:all .25s;border:1px solid transparent}
  .toast.show{opacity:1;transform:translateY(0)}
  .toast.ok {background:#1a3a1a;border-color:#2ea04333;color:var(--green)}
  .toast.err{background:#3a1a1a;border-color:#da363333;color:var(--red)}
  .toast.inf{background:#0d1f38;border-color:#1f6feb33;color:var(--blue-h)}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="logo">⚡ <span>IMPACT</span> Log Console</div>
  <div class="spacer"></div>
  <a href="dashboard.jsp" class="back-link">← Dashboard</a>
</div>

<!-- Toolbar -->
<div class="toolbar">
  <div class="field">
    <label>Server</label>
    <select id="sel-target" onchange="onTargetChange()"></select>
  </div>
  <div class="field">
    <label>Log File</label>
    <select id="sel-file" onchange="onFileChange()">
      <option value="">— select server first —</option>
    </select>
  </div>
  <div class="field">
    <label>Lines</label>
    <select id="sel-lines">
      <option value="100">100</option>
      <option value="500" selected>500</option>
      <option value="1000">1000</option>
      <option value="2000">2000</option>
    </select>
  </div>
  <button class="btn btn-primary" onclick="loadLog()">↺ Load</button>

  <div style="width:1px;background:var(--border);height:28px;margin:0 4px"></div>

  <!-- Level filters -->
  <div style="display:flex;gap:4px;align-items:center">
    <span style="font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px">Level:</span>
    <button class="level-btn lv-all    active" onclick="setLevel('all',this)">ALL</button>
    <button class="level-btn lv-info"          onclick="setLevel('info',this)">INFO</button>
    <button class="level-btn lv-warn"          onclick="setLevel('warn',this)">WARN</button>
    <button class="level-btn lv-error"         onclick="setLevel('error',this)">ERROR</button>
    <button class="level-btn lv-severe"        onclick="setLevel('severe',this)">SEVERE</button>
  </div>

  <div style="width:1px;background:var(--border);height:28px;margin:0 4px"></div>

  <!-- Search -->
  <div class="search-wrap">
    <span class="search-icon">⌕</span>
    <input type="text" id="search" placeholder="Search logs…" oninput="applyFilters()">
  </div>

  <div style="width:1px;background:var(--border);height:28px;margin:0 4px"></div>

  <button class="btn btn-success" id="btn-tail" onclick="toggleTail()">⏵ Live Tail</button>
  <button class="btn btn-ghost" onclick="scrollBottom()">↓ Bottom</button>
  <button class="btn btn-ghost" onclick="clearTerminal()">✕ Clear</button>
</div>

<!-- Status bar -->
<div class="statusbar">
  <div class="tail-dot" id="tail-dot"></div>
  <span id="status-text">Select a server and log file to begin.</span>
  <span style="flex:1"></span>
  <span id="line-count" style="color:var(--muted)"></span>
</div>

<!-- Terminal -->
<div class="terminal" id="terminal">
  <span style="color:var(--muted);font-style:italic">Select a server and log file above, then click Load.</span>
</div>

<div class="toast-wrap" id="toasts"></div>

<script>
const API = 'api.jsp';
let allLines    = [];   // raw loaded lines
let tailSrc     = null; // EventSource
let tailing     = false;
let activeLevel = 'all';
let autoScroll  = true;

/* ── Init ── */
(async function init() {
  const cfg = await (await fetch(API + '?action=config')).json();
  const sel = document.getElementById('sel-target');
  sel.innerHTML = (cfg.deployTargets || [])
    .filter(t => t.tomcat && t.tomcat.logDir)
    .map((t,i) => `<option value="${t.name}" ${i===0?'selected':''}>${t.name}</option>`)
    .join('');
  if (sel.options.length) onTargetChange();
})();

async function onTargetChange() {
  const target = document.getElementById('sel-target').value;
  const res  = await fetch(`${API}?action=tomcat-logfiles&target=${encodeURIComponent(target)}`);
  const data = await res.json();
  const sel  = document.getElementById('sel-file');
  if (!data.ok || !data.files.length) {
    sel.innerHTML = '<option value="">No log files found</option>';
    setStatus('No log files found in: ' + (data.error || '?'));
    return;
  }
  sel.innerHTML = data.files.map(f => {
    const kb = (f.size / 1024).toFixed(0);
    return `<option value="${f.name}">${f.name} (${kb} KB)</option>`;
  }).join('');
  // auto-select catalina.out if present
  const opts = Array.from(sel.options);
  const cat  = opts.find(o => o.value === 'catalina.out');
  if (cat) sel.value = 'catalina.out';
  onFileChange();
}

function onFileChange() {
  stopTail();
}

/* ── Load log ── */
async function loadLog() {
  stopTail();
  const target = document.getElementById('sel-target').value;
  const file   = document.getElementById('sel-file').value;
  const lines  = document.getElementById('sel-lines').value;
  if (!target || !file) { toast('Select a server and file first.','err'); return; }

  setStatus('Loading…');
  clearTerminal();

  const res  = await fetch(`${API}?action=tomcat-logcontent&target=${encodeURIComponent(target)}&file=${encodeURIComponent(file)}&lines=${lines}`);
  const text = await res.text();

  allLines = text.split('\n').filter(l => l.length > 0);
  applyFilters();
  setStatus(`Loaded ${allLines.length} lines from ${file}`);
  scrollBottom();
  toast(`${allLines.length} lines loaded`, 'ok');
}

/* ── Filters ── */
function applyFilters() {
  const term    = document.getElementById('terminal');
  const search  = document.getElementById('search').value.toLowerCase();
  const filtered = allLines.filter(l => {
    if (activeLevel !== 'all' && !matchesLevel(l, activeLevel)) return false;
    if (search && !l.toLowerCase().includes(search)) return false;
    return true;
  });

  term.innerHTML = '';
  filtered.forEach(l => {
    const div = document.createElement('span');
    div.className = 'll ' + classifyLine(l);
    div.innerHTML = search ? highlight(escHtml(l), search) : escHtml(l);
    term.appendChild(div);
    term.appendChild(document.createTextNode('\n'));
  });

  document.getElementById('line-count').textContent =
    filtered.length + (search || activeLevel!=='all' ? ` / ${allLines.length} total` : '') + ' lines';

  if (autoScroll) scrollBottom();
}

function matchesLevel(line, level) {
  const l = line.toLowerCase();
  switch (level) {
    case 'info':   return l.includes(' info ') || l.includes('[info]');
    case 'warn':   return l.includes(' warning') || l.includes(' warn ') || l.includes('[warn]');
    case 'error':  return l.includes(' severe') || l.includes(' error') || l.includes('[error]');
    case 'severe': return l.includes(' severe') || l.includes('[severe]');
    default:       return true;
  }
}

function classifyLine(line) {
  const l = line.toLowerCase();
  if (l.includes(' severe') || l.includes('fatal'))   return 'll-severe';
  if (l.includes(' error') || l.includes('[error]'))  return 'll-error';
  if (l.includes(' warning') || l.includes(' warn ')) return 'll-warn';
  if (l.includes(' info ') || l.includes('[info]'))   return 'll-info';
  if (l.includes(' fine ') || l.includes(' debug'))   return 'll-debug';
  return 'll-info';
}

function setLevel(level, btn) {
  activeLevel = level;
  document.querySelectorAll('.level-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}

/* ── Live Tail ── */
function toggleTail() {
  if (tailing) stopTail();
  else         startTail();
}

function startTail() {
  const target = document.getElementById('sel-target').value;
  const file   = document.getElementById('sel-file').value;
  if (!target || !file) { toast('Select a server and file first.', 'err'); return; }

  tailing = true;
  autoScroll = true;
  document.getElementById('btn-tail').textContent  = '⏹ Stop Tail';
  document.getElementById('btn-tail').className    = 'btn btn-danger';
  document.getElementById('tail-dot').className    = 'tail-dot live';
  setStatus('Live tail — ' + file);

  tailSrc = new EventSource(`log-tail.jsp?target=${encodeURIComponent(target)}&file=${encodeURIComponent(file)}`);
  tailSrc.onmessage = e => {
    if (e.data === '__PING__' || e.data === '__DONE__') return;
    allLines.push(e.data);
    if (allLines.length > 5000) allLines.shift(); // cap buffer
    appendTailLine(e.data);
  };
  tailSrc.onerror = () => { stopTail(); toast('Tail connection lost.', 'err'); };
  toast('Live tail started — ' + file, 'ok');
}

function stopTail() {
  if (tailSrc) { tailSrc.close(); tailSrc = null; }
  tailing = false;
  document.getElementById('btn-tail').textContent = '⏵ Live Tail';
  document.getElementById('btn-tail').className   = 'btn btn-success';
  document.getElementById('tail-dot').className   = 'tail-dot';
  if (tailing === false && allLines.length) setStatus('Tail stopped. ' + allLines.length + ' lines in buffer.');
}

function appendTailLine(line) {
  const search = document.getElementById('search').value.toLowerCase();
  if (activeLevel !== 'all' && !matchesLevel(line, activeLevel)) return;
  if (search && !line.toLowerCase().includes(search)) return;

  const term = document.getElementById('terminal');
  const empty = term.querySelector('span[style]');
  if (empty && empty.style.fontStyle === 'italic') term.innerHTML = '';

  const span = document.createElement('span');
  span.className = 'll ' + classifyLine(line);
  span.innerHTML = search ? highlight(escHtml(line), search) : escHtml(line);
  term.appendChild(span);
  term.appendChild(document.createTextNode('\n'));
  if (autoScroll) scrollBottom();

  const cnt = parseInt(document.getElementById('line-count').textContent) || 0;
  document.getElementById('line-count').textContent = (cnt + 1) + ' lines';
}

/* ── Helpers ── */
function scrollBottom() {
  const t = document.getElementById('terminal');
  t.scrollTop = t.scrollHeight;
}

function clearTerminal() {
  document.getElementById('terminal').innerHTML =
    '<span style="color:var(--muted);font-style:italic">Log cleared.</span>';
  allLines = [];
  document.getElementById('line-count').textContent = '';
}

function setStatus(msg) {
  document.getElementById('status-text').textContent = msg;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function highlight(html, term) {
  if (!term) return html;
  const re = new RegExp('(' + term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + ')', 'gi');
  return html.replace(re, '<mark>$1</mark>');
}

function toast(msg, type='inf') {
  const wrap = document.getElementById('toasts');
  const el   = document.createElement('div');
  el.className = 'toast ' + type; el.textContent = msg;
  wrap.appendChild(el);
  requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('show')));
  setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }, 3000);
}

/* Auto-scroll detection */
document.getElementById('terminal').addEventListener('scroll', () => {
  const t = document.getElementById('terminal');
  autoScroll = t.scrollTop + t.clientHeight >= t.scrollHeight - 40;
});
</script>
</body>
</html>
