/* ============================================================
   MediCore HMS v2 — medicore.js
   Features: session caching, skeleton loaders, live search,
             pagination, optimistic UI, CSRF, alert system
   ============================================================ */

window.HMS = (function () {

  /* ── Session cache (avoids re-fetch on every page) ── */
  var _sessionCache = null;
  try {
    var cached = sessionStorage.getItem('hms_session');
    if (cached) _sessionCache = JSON.parse(cached);
  } catch (_) {}

  /* ── CSRF token ── */
  var _csrf = document.cookie.split(';').reduce(function(t, c) {
    var parts = c.trim().split('=');
    return parts[0] === 'csrf_token' ? decodeURIComponent(parts[1]) : t;
  }, '');

  /* ── API ── */
  function _handleResponse(r) {
    if (r.status === 401) { sessionStorage.removeItem('hms_session'); window.location.href = '/login'; throw new Error('Unauthorized'); }
    if (r.status === 429) { showAlert('Too many requests. Please wait a moment.', 'warning'); throw new Error('Rate limited'); }
    return r.json();
  }

  function apiGet(url) {
    return fetch(url, { credentials: 'same-origin' }).then(_handleResponse);
  }

  function apiPost(url, data) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _csrf },
      body: JSON.stringify(data || {})
    }).then(_handleResponse);
  }

  /* ── Alert system ── */
  function showAlert(message, type, duration) {
    type     = type     || 'info';
    duration = duration || 5000;
    var icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    var container = document.getElementById('alertContainer');
    if (!container) return;

    var div = document.createElement('div');
    div.className = 'alert alert-' + type;
    div.innerHTML =
      '<span class="alert-icon">' + (icons[type] || 'ℹ') + '</span>' +
      '<span style="flex:1;">' + message + '</span>' +
      '<button class="alert-dismiss" onclick="this.parentNode.remove()">×</button>';
    container.appendChild(div);
    if (duration > 0) {
      setTimeout(function() { if (div.parentNode) { div.style.opacity='0'; div.style.transition='opacity .3s'; setTimeout(function(){ if(div.parentNode) div.remove(); }, 300); } }, duration);
    }
  }

  /* ── Skeleton helpers ── */
  function skeletonRows(cols, rows) {
    rows = rows || 5;
    var widths = ['w-full','w-3-4','w-1-2','w-1-4'];
    var ths = Array(cols).fill('<th></th>').join('');
    var tds = Array(cols).fill(0).map(function(_, i) {
      return '<td><div class="skeleton skeleton-text ' + widths[i % 4] + '"></div></td>';
    }).join('');
    var bodyRows = Array(rows).fill('<tr>' + tds + '</tr>').join('');
    return '<div class="table-container"><table class="data-table"><thead><tr>' + ths + '</tr></thead><tbody>' + bodyRows + '</tbody></table></div>';
  }

  function skeletonStats(count) {
    return Array(count).fill('<div class="skeleton skeleton-card"></div>').join('');
  }

  /* ── Status badge ── */
  function statusBadge(status) {
    if (!status) return '<span class="badge badge-slate">—</span>';
    return '<span class="badge badge-' + status + '">' + status + '</span>';
  }

  /* ── Debounce ── */
  function debounce(fn, delay) {
    var timer;
    return function() {
      var args = arguments, ctx = this;
      clearTimeout(timer);
      timer = setTimeout(function() { fn.apply(ctx, args); }, delay);
    };
  }

  /* ── Pagination renderer ── */
  function renderPagination(pagination, onPageChange) {
    if (!pagination || pagination.total_pages <= 1) return '';
    var p = pagination;
    var info = 'Showing ' + ((p.page - 1) * p.per_page + 1) + '–' +
               Math.min(p.page * p.per_page, p.total) + ' of ' + p.total;

    var prevBtn = '<button class="page-btn" ' + (!p.has_prev ? 'disabled' : '') +
                  ' onclick="(' + onPageChange.toString() + ')(' + (p.page - 1) + ')">‹</button>';
    var nextBtn = '<button class="page-btn" ' + (!p.has_next ? 'disabled' : '') +
                  ' onclick="(' + onPageChange.toString() + ')(' + (p.page + 1) + ')">›</button>';

    var pages = '';
    var start = Math.max(1, p.page - 2);
    var end   = Math.min(p.total_pages, p.page + 2);
    if (start > 1)              pages += '<button class="page-btn" onclick="(' + onPageChange.toString() + ')(1)">1</button>' + (start > 2 ? '<span style="padding:0 4px;color:var(--text-muted)">…</span>' : '');
    for (var i = start; i <= end; i++) {
      pages += '<button class="page-btn' + (i === p.page ? ' active' : '') + '" onclick="(' + onPageChange.toString() + ')(' + i + ')">' + i + '</button>';
    }
    if (end < p.total_pages) pages += (end < p.total_pages - 1 ? '<span style="padding:0 4px;color:var(--text-muted)">…</span>' : '') + '<button class="page-btn" onclick="(' + onPageChange.toString() + ')(' + p.total_pages + ')">' + p.total_pages + '</button>';

    return '<div class="pagination"><span class="pagination-info">' + info + '</span><div class="pagination-controls">' + prevBtn + pages + nextBtn + '</div></div>';
  }

  /* ── Sidebar nav builder ── */
  function buildNav(role) {
    var path = window.location.pathname;
    var sections = [{ label: 'Main', items: [{ href:'/dashboard', icon:'⊞', text:'Dashboard' }] }];

    if (['ADMIN','DOCTOR','RECEPTIONIST'].indexOf(role) !== -1) {
      var pi = [{ href:'/patients', icon:'👥', text:'Patients' }];
      if (['ADMIN','RECEPTIONIST'].indexOf(role) !== -1) pi.push({ href:'/register-patient', icon:'➕', text:'Register Patient' });
      sections.push({ label: 'Patients', items: pi });

      var si = [{ href:'/appointments', icon:'📅', text:'Appointments' }];
      if (['ADMIN','RECEPTIONIST'].indexOf(role) !== -1) si.push({ href:'/appointments/schedule', icon:'🗓', text:'Schedule' });
      sections.push({ label: 'Scheduling', items: si });
    }
    if (['ADMIN','DOCTOR'].indexOf(role) !== -1)
      sections.push({ label: 'Medical', items: [{ href:'/medical-records/add', icon:'📝', text:'Add Record' }] });
    if (['ADMIN','BILLING'].indexOf(role) !== -1)
      sections.push({ label: 'Finance', items: [{ href:'/billing', icon:'💰', text:'Billing' }] });
    if (role === 'ADMIN')
      sections.push({ label: 'Admin', items: [{ href:'/admin/users', icon:'👤', text:'Users' }, { href:'/admin/audit-log', icon:'📋', text:'Audit Log' }] });
    sections.push({ label: 'Account', items: [{ href:'/change-password', icon:'🔐', text:'Change Password' }] });

    return sections.map(function(s) {
      return '<div class="nav-section-label">' + s.label + '</div>' +
        s.items.map(function(item) {
          var isActive = path === item.href || path.startsWith(item.href + '/');
          return '<a href="' + item.href + '" class="nav-link' + (isActive ? ' active' : '') + '"><span class="nav-icon">' + item.icon + '</span>' + item.text + '</a>';
        }).join('');
    }).join('');
  }

  /* ── Logout ── */
  function doLogout() {
    sessionStorage.removeItem('hms_session');
    fetch('/api/logout', { credentials: 'same-origin' }).finally(function() { window.location.href = '/login'; });
  }

  /* ── Sidebar toggle ── */
  function _initSidebar() {
    var btn = document.getElementById('hamburgerBtn');
    var sb  = document.getElementById('sidebar');
    var bd  = document.getElementById('sidebarBackdrop');
    if (!btn || !sb || !bd) return;
    function open()  { sb.classList.add('open');    bd.classList.add('open');    btn.setAttribute('aria-expanded','true');  document.body.style.overflow='hidden'; }
    function close() { sb.classList.remove('open'); bd.classList.remove('open'); btn.setAttribute('aria-expanded','false'); document.body.style.overflow=''; }
    btn.addEventListener('click', function() { sb.classList.contains('open') ? close() : open(); });
    bd.addEventListener('click', close);
    sb.querySelectorAll('.nav-link, .logout-btn').forEach(function(l) { l.addEventListener('click', function() { if (window.innerWidth <= 768) close(); }); });
  }

  /* ── Init ── */
  function init() {
    _initSidebar();

    var setUser = function(u) {
      var el = function(id) { return document.getElementById(id); };
      if (el('userAvatar')) el('userAvatar').textContent = (u.full_name || 'U')[0].toUpperCase();
      if (el('userName'))   el('userName').textContent   = u.full_name || u.username;
      if (el('userRole'))   { el('userRole').textContent = u.role; el('userRole').className = 'role-pill role-' + u.role; }
      if (el('sidebarNav')) el('sidebarNav').innerHTML   = buildNav(u.role);
      window._hmsUser = u;
      if (typeof window.onHMSReady === 'function') window.onHMSReady(u);
    };

    // Use cache for instant sidebar render
    if (_sessionCache) { setUser(_sessionCache); }

    apiGet('/api/session').then(function(data) {
      if (!data.ok || !data.user) { sessionStorage.removeItem('hms_session'); window.location.href = '/login'; return; }
      try { sessionStorage.setItem('hms_session', JSON.stringify(data.user)); } catch(_) {}
      _sessionCache = data.user;
      setUser(data.user);
    }).catch(function() { window.location.href = '/login'; });
  }

  /* ── Live search builder ── */
  function setupLiveSearch(inputId, fetchFn) {
    var input = document.getElementById(inputId);
    if (!input) return;
    var debouncedFetch = debounce(function() { fetchFn(input.value.trim()); }, 300);
    input.addEventListener('input', debouncedFetch);
  }

  return {
    init:              init,
    api:               { get: apiGet, post: apiPost },
    showAlert:         showAlert,
    statusBadge:       statusBadge,
    skeletonRows:      skeletonRows,
    skeletonStats:     skeletonStats,
    renderPagination:  renderPagination,
    setupLiveSearch:   setupLiveSearch,
    debounce:          debounce,
    doLogout:          doLogout,
  };
})();

window.doLogout = function() { HMS.doLogout(); };
