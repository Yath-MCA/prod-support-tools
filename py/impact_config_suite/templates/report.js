/* HTML Compare Report JavaScript */

var fm = [], fi = -1;
var mainRows = [], delmergeRows = [], currentDelmergeIndex = 0;
var delmergeSection = null, delmergeTable = null;
var mainTable = null;

// Main report filtering
function af() {
  var t = (document.getElementById('tf').value || '').toLowerCase(),
      s = document.getElementById('sf').value,
      p = document.getElementById('pf').value,
      v = 0;
  mainRows.forEach(function(r) {
    var ok = ((!t || r.textContent.toLowerCase().includes(t)) &&
              (!s || r.dataset.status === s) &&
              (!p || (r.dataset.parent || '').includes(p)));
    r.style.display = ok ? '' : 'none';
    if(ok) v++;
  });
  document.getElementById('rc').textContent = v + ' rows';
}

// Build dropdowns from unique statuses
function bd() {
  var ss = document.getElementById('sf'),
      ps = document.getElementById('pf'),
      sv = new Set(),
      pv = new Set();
  mainRows.forEach(function(r) {
    if(r.dataset.status) sv.add(r.dataset.status);
    if(r.dataset.parent && r.dataset.parent !== '—') pv.add(r.dataset.parent);
  });
  [...sv].sort().forEach(function(s) {
    var o = document.createElement('option');
    o.value = s;
    o.textContent = s;
    ss.appendChild(o);
  });
  [...pv].sort().forEach(function(s) {
    var o = document.createElement('option');
    o.value = s;
    o.textContent = s;
    ps.appendChild(o);
  });
  document.getElementById('rc').textContent = mainRows.length + ' rows';
}

// Find in visible rows
function df() {
  var q = (document.getElementById('fi').value || '').toLowerCase();
  if(!q) {
    cf();
    return;
  }
  fm = [];
  fi = -1;
  mainRows.forEach(function(r) {
    if(r.style.display !== 'none' && r.textContent.toLowerCase().includes(q))
      fm.push(r);
  });
  document.getElementById('fc').textContent = fm.length + ' found';
  if(fm.length) {
    fi = 0;
    sm();
  }
}

// Scroll match into view
function sm() {
  fm.forEach(function(r) {
    r.classList.remove('ring');
  });
  if(fi >= 0 && fi < fm.length) {
    fm[fi].classList.add('ring');
    fm[fi].scrollIntoView({block:'center', behavior:'smooth'});
  }
}

function fn() {
  if(!fm.length) return;
  fi = (fi + 1) % fm.length;
  sm();
}

function fp() {
  if(!fm.length) return;
  fi = (fi - 1 + fm.length) % fm.length;
  sm();
}

function cf() {
  document.getElementById('fi').value = '';
  fm = [];
  fi = -1;
  document.getElementById('fc').textContent = '';
  mainRows.forEach(function(r) {
    r.classList.remove('ring');
  });
}

// Delmerge navigation
function getVisibleDelmergeRows() {
  return delmergeRows.filter(function(r) {
    return r.style.display !== 'none';
  });
}

function focusDelmergeRow(anchor) {
  delmergeRows.forEach(function(r) {
    var match = !anchor || r.dataset.anchor === anchor;
    r.style.display = match ? '' : 'none';
    r.classList.toggle('focused', match);
    if(match) r.scrollIntoView({block:'center', behavior:'smooth'});
  });
}

function gotoDelmergeRow(idx) {
  var rows = getVisibleDelmergeRows();
  if(!rows.length) return;
  if(idx < 0) idx = 0;
  if(idx >= rows.length) idx = rows.length - 1;
  currentDelmergeIndex = idx;
  focusDelmergeRow(rows[idx].dataset.anchor || '');
}

function gotoDelmergePrev() {
  gotoDelmergeRow(currentDelmergeIndex - 1);
}

function gotoDelmergeNext() {
  gotoDelmergeRow(currentDelmergeIndex + 1);
}

// Toggle styles
function toggleDelmergeDel(mode) {
  if(delmergeSection)
    delmergeSection.classList[mode === 'hide' ? 'add' : 'remove']('hide-del');
}

function toggleHtmlView(mode) {
  if(mainTable) {
    mainTable.querySelectorAll('.html-preview').forEach(function(el) {
      el.style.display = mode === 'preview' ? 'block' : 'none';
    });
    mainTable.querySelectorAll('.html-raw').forEach(function(el) {
      el.style.display = mode === 'preview' ? 'none' : 'block';
    });
  }
}

function toggleHtmlViewDelmerge(mode) {
  if(delmergeTable) {
    delmergeTable.querySelectorAll('.html-preview').forEach(function(el) {
      el.style.display = mode === 'preview' ? 'block' : 'none';
    });
    delmergeTable.querySelectorAll('.html-raw').forEach(function(el) {
      el.style.display = mode === 'preview' ? 'none' : 'block';
    });
  }
}

// Bind events
function bindMainReportClicks() {
  mainRows.forEach(function(r) {
    r.addEventListener('dblclick', function() {
      var anchor = r.dataset.anchor || '';
      if(delmergeTable) {
        focusDelmergeRow(anchor);
      }
    });
  });
}

// Initialize on load
function initReport() {
  mainTable = document.getElementById('main-report-table');
  delmergeTable = document.getElementById('delmerge-table');
  delmergeSection = document.getElementById('delmerge-section');
  if(mainTable) mainRows = [].slice.call(mainTable.querySelectorAll('tbody tr'));
  if(delmergeTable) delmergeRows = [].slice.call(delmergeTable.querySelectorAll('tbody tr'));
  bd();
  bindMainReportClicks();
}

window.onload = initReport;
