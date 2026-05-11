/**
 * QuickLender Utils — v1.0
 * Formatters, Badge, Toast, Modal, Tabs, Pagination, Forms, Sidebar loader.
 */

// ─── FORMATTERS ───────────────────────────────────────
const Fmt = {
  currency(n, sym = 'KES') {
    if (n == null || n === '') return '—';
    const v = parseFloat(n);
    return isNaN(v) ? '—' : `${sym} ${v.toLocaleString('en-KE', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  },
  number(n)  { return (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString(); },
  pct(n, dec = 1)    { return (n == null || isNaN(n)) ? '—' : `${Number(n).toFixed(dec)}%`; },
  date(d)    { if (!d) return '—'; return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }); },
  datetime(d){ if (!d) return '—'; return new Date(d).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }); },
  relTime(d) {
    if (!d) return '—';
    const diff = Date.now() - new Date(d).getTime();
    const m = Math.floor(diff / 60000);
    if (m < 1)  return 'just now';
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return Fmt.date(d);
  },
  initials(n){ return (n || '?').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase(); },
  millions(n){ return (n == null) ? '—' : `KES ${(n/1e6).toFixed(2)}M`; },
};

// ─── BADGE ────────────────────────────────────────────
const Badge = {
  _STATUS: {
    ACTIVE:'badge-active', Active:'badge-active',
    CLOSED:'badge-closed', Closed:'badge-closed',
    DEFAULT:'badge-default', Default:'badge-default',
    PENDING:'badge-pending', Pending:'badge-pending',
    APPROVED:'badge-approved', Approved:'badge-approved',
    DISBURSED:'badge-disbursed', Disbursed:'badge-disbursed',
    WRITTEN_OFF:'badge-closed', REJECTED:'badge-default', Rejected:'badge-default',
    DORMANT:'badge-pending', BLACKLISTED:'badge-default', DECEASED:'badge-closed',
    SUCCESS:'badge-active', FAILED:'badge-default',
  },
  status(s) {
    return `<span class="badge ${this._STATUS[s] || 'badge-pending'}">${s}</span>`;
  },
  loanType(t) {
    const map = { FA:'chip-fa', CC:'chip-cc', LOGBOOK:'chip-logbook', IDC:'chip-idc', EDC:'chip-edc' };
    return `<span class="chip ${map[t] || 'chip-fa'}">${t}</span>`;
  },
  risk(r) {
    const map = { Low:'badge-active', Medium:'badge-pending', High:'badge-default' };
    return `<span class="badge ${map[r] || 'badge-pending'}">${r}</span>`;
  },
  yesNo(v) {
    return v ? '<span class="badge badge-active">Yes</span>' : '<span class="badge badge-closed">No</span>';
  },
};

// ─── TOAST ────────────────────────────────────────────
const Toast = {
  _el: null,
  _get() {
    if (!this._el) {
      this._el = document.getElementById('toast-container');
      if (!this._el) {
        this._el = document.createElement('div');
        this._el.id = 'toast-container';
        document.body.appendChild(this._el);
      }
    }
    return this._el;
  },
  show(msg, type = 'success', ms = 3500) {
    const icons = { success: '✓', error: '✕', warn: '⚠', info: 'ℹ' };
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.innerHTML = `<span class="toast-icon">${icons[type]||'ℹ'}</span><span class="toast-msg">${msg}</span><span class="toast-close" onclick="this.parentElement.remove()">✕</span>`;
    this._get().appendChild(el);
    setTimeout(() => el?.remove(), ms);
    return el;
  },
  success(msg, ms) { return this.show(msg, 'success', ms); },
  error(msg, ms)   { return this.show(msg, 'error',   ms || 5000); },
  warn(msg, ms)    { return this.show(msg, 'warn',    ms); },
  info(msg, ms)    { return this.show(msg, 'info',    ms); },
};

// ─── MODAL ────────────────────────────────────────────
const Modal = {
  open(id)  { document.getElementById(id)?.classList.add('open'); },
  close(id) { document.getElementById(id)?.classList.remove('open'); },
  closeAll(){ document.querySelectorAll('.modal-overlay.open').forEach(el => el.classList.remove('open')); },
};
document.addEventListener('click', e => { if (e.target.classList.contains('modal-overlay')) Modal.closeAll(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') Modal.closeAll(); });

// ─── TABS ─────────────────────────────────────────────
function switchTab(btn, tabId) {
  const scope = btn.closest('[data-tab-scope]') || document;
  scope.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  scope.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  (scope.querySelector(`#${tabId}`) || document.getElementById(tabId))?.classList.add('active');
}

// ─── PROGRESS BAR ─────────────────────────────────────
function renderProgress(pct, max = 100) {
  const p = Math.min(Math.max(pct || 0, 0), max);
  const col = p >= 85 ? 'pb-green' : p >= 70 ? 'pb-gold' : 'pb-red';
  return `<div class="progress"><div class="progress-bar ${col}" style="width:${(p/max*100).toFixed(1)}%"></div></div>`;
}

// ─── TABLE FILTER ─────────────────────────────────────
function filterTable(input, tbodyId) {
  const q = input.value.toLowerCase();
  document.querySelectorAll(`#${tbodyId} tr`).forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

// ─── AVATAR ───────────────────────────────────────────
function avatarEl(name, size = 'avatar-sm') {
  return `<div class="avatar ${size}" style="background:${Auth.avatarColor(name)}">${Fmt.initials(name)}</div>`;
}

// ─── FORM HELPERS ─────────────────────────────────────
function formData(formId) {
  const form = typeof formId === 'string' ? document.getElementById(formId) : formId;
  if (!form) return {};
  const data = {};
  form.querySelectorAll('[name]').forEach(el => {
    if (!el.name) return;
    if (el.type === 'checkbox') { data[el.name] = el.checked; return; }
    if (el.type === 'file')     { return; }  // handle separately
    if (el.value !== '')        { data[el.name] = el.value; }
  });
  return data;
}

function setLoading(btnId, loading) {
  const btn = typeof btnId === 'string' ? document.getElementById(btnId) : btnId;
  if (!btn) return;
  btn.disabled = loading;
  btn.classList.toggle('loading', loading);
}

function resetForm(formId) {
  const form = typeof formId === 'string' ? document.getElementById(formId) : formId;
  form?.reset();
}

// ─── PAGINATION ───────────────────────────────────────
function renderPagination(containerId, data, onPageFn) {
  const el = document.getElementById(containerId);
  if (!el || !data) return;
  const { count, next, previous } = data;
  if (!next && !previous) { el.innerHTML = ''; return; }
  const pageSize = 25;
  const total = Math.ceil((count || 0) / pageSize);
  el.innerHTML = `
    <div class="d-flex items-center gap-10 px-16 py-12 border-top mono-sm">
      <span class="text-dim mono">${(count||0).toLocaleString()} total records</span>
      <div class="ml-auto d-flex gap-6 items-center">
        ${previous ? `<button class="btn btn-ghost btn-sm" onclick="${onPageFn}('${previous}')">← Prev</button>` : ''}
        <span class="text-dim mono">${total} pages</span>
        ${next ? `<button class="btn btn-ghost btn-sm" onclick="${onPageFn}('${next}')">Next →</button>` : ''}
      </div>
    </div>`;
}

// ─── EMPTY STATE ──────────────────────────────────────
function emptyState(icon, title, subtitle = '') {
  return `<div class="empty-state">
    <div class="empty-state-icon">${icon}</div>
    <h3>${title}</h3>${subtitle ? `<p>${subtitle}</p>` : ''}
  </div>`;
}

// ─── LOADING ROW ──────────────────────────────────────
function loadingRows(cols = 6, rows = 3) {
  return Array(rows).fill(0).map(() =>
    `<tr>${Array(cols).fill(0).map(() =>
      `<td><div class="skel-h14"></div></td>`
    ).join('')}</tr>`
  ).join('');
}

// ─── SIDEBAR LOADER ───────────────────────────────────
// ─── MOBILE SIDEBAR TOGGLE ────────────────────────────────────────────────────
function initMobileSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (!sidebar) return;

  // Inject hamburger into topbar if not there
  const topbarLeft = document.querySelector('.topbar-left');
  if (topbarLeft && !document.getElementById('hamburger-btn')) {
    const btn = document.createElement('button');
    btn.id        = 'hamburger-btn';
    btn.className = 'hamburger';
    btn.setAttribute('aria-label', 'Open menu');
    btn.innerHTML = '<span></span><span></span><span></span>';
    btn.onclick   = toggleMobileSidebar;
    topbarLeft.insertBefore(btn, topbarLeft.firstChild);
  }

  // Inject backdrop if not there
  if (!backdrop) {
    const bd = document.createElement('div');
    bd.id        = 'sidebar-backdrop';
    bd.className = 'sidebar-backdrop';
    bd.onclick   = closeMobileSidebar;
    document.body.appendChild(bd);
  }
}

function toggleMobileSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  sidebar?.classList.toggle('mobile-open');
  backdrop?.classList.toggle('active');
}

function closeMobileSidebar() {
  document.getElementById('sidebar')?.classList.remove('mobile-open');
  document.getElementById('sidebar-backdrop')?.classList.remove('active');
}

// Role-based nav visibility — called from loadSidebar after HTML is injected

// ─── QL.confirm / QL.prompt — Replace browser dialogs ────────────────────────
// Usage: const ok = await QL.confirm('Delete this?')
// Usage: const val = await QL.prompt('Enter reason:', 'default')
const QL = {
  _overlay: null,

  _ensureOverlay() {
    if (document.getElementById('ql-dialog-overlay')) return;
    const el = document.createElement('div');
    el.id = 'ql-dialog-overlay';
    el.innerHTML = `
      <div class="ql-dialog" id="ql-dialog-box">
        <div class="ql-dialog-icon" id="ql-dialog-icon">⚠️</div>
        <div class="ql-dialog-title" id="ql-dialog-title"></div>
        <div class="ql-dialog-msg" id="ql-dialog-msg"></div>
        <div class="ql-dialog-input-wrap d-none" id="ql-dialog-input-wrap">
          <input class="form-control" id="ql-dialog-input" type="text">
        </div>
        <div class="ql-dialog-footer">
          <button class="btn btn-ghost" id="ql-dialog-cancel">Cancel</button>
          <button class="btn btn-primary" id="ql-dialog-ok">OK</button>
        </div>
      </div>`;
    document.body.appendChild(el);
  },

  confirm(message, { title='Confirm', icon='⚠️', okLabel='Confirm',
                     okClass='btn-primary', danger=false } = {}) {
    this._ensureOverlay();
    return new Promise(resolve => {
      const overlay = document.getElementById('ql-dialog-overlay');
      const titleEl  = document.getElementById('ql-dialog-title');
      const msgEl    = document.getElementById('ql-dialog-msg');
      const iconEl   = document.getElementById('ql-dialog-icon');
      const inputWrap= document.getElementById('ql-dialog-input-wrap');
      const okBtn    = document.getElementById('ql-dialog-ok');
      const cancelBtn= document.getElementById('ql-dialog-cancel');

      titleEl.textContent  = title;
      msgEl.innerHTML      = message;
      iconEl.textContent   = danger ? '🚨' : icon;
      inputWrap.classList.add('d-none');
      okBtn.textContent    = okLabel;
      okBtn.className      = `btn ${danger ? 'btn-danger' : okClass}`;

      overlay.style.display = 'flex';
      okBtn.focus();

      const done = (val) => {
        overlay.style.display = 'none';
        okBtn.onclick = null;
        cancelBtn.onclick = null;
        resolve(val);
      };
      okBtn.onclick     = () => done(true);
      cancelBtn.onclick = () => done(false);
      // Close on overlay click
      overlay.onclick = (e) => { if (e.target === overlay) done(false); };
      // Keyboard
      overlay.onkeydown = (e) => {
        if (e.key === 'Enter') done(true);
        if (e.key === 'Escape') done(false);
      };
    });
  },

  prompt(message, defaultVal='', { title='Input', placeholder='', type='text' } = {}) {
    this._ensureOverlay();
    return new Promise(resolve => {
      const overlay = document.getElementById('ql-dialog-overlay');
      const titleEl  = document.getElementById('ql-dialog-title');
      const msgEl    = document.getElementById('ql-dialog-msg');
      const iconEl   = document.getElementById('ql-dialog-icon');
      const inputWrap= document.getElementById('ql-dialog-input-wrap');
      const inputEl  = document.getElementById('ql-dialog-input');
      const okBtn    = document.getElementById('ql-dialog-ok');
      const cancelBtn= document.getElementById('ql-dialog-cancel');

      titleEl.textContent  = title;
      msgEl.textContent    = message;
      iconEl.textContent   = '✏️';
      inputWrap.classList.remove('d-none');
      inputEl.value        = defaultVal || '';
      inputEl.type         = type;
      inputEl.placeholder  = placeholder;
      okBtn.textContent    = 'OK';
      okBtn.className      = 'btn btn-primary';

      overlay.style.display = 'flex';
      setTimeout(() => inputEl.focus(), 50);

      const done = (val) => {
        overlay.style.display = 'none';
        okBtn.onclick = null;
        cancelBtn.onclick = null;
        resolve(val);
      };
      okBtn.onclick     = () => done(inputEl.value.trim() || null);
      cancelBtn.onclick = () => done(null);
      overlay.onclick   = (e) => { if (e.target === overlay) done(null); };
      inputEl.onkeydown = (e) => {
        if (e.key === 'Enter') done(inputEl.value.trim() || null);
        if (e.key === 'Escape') done(null);
      };
    });
  },
};


function _applyNavPermissions() {
  const user = Auth.getUser();
  if (!user) return;
  const role = user.role || '';

  // ── Permission sets ──────────────────────────────────────────────────────
  const ADMIN_LEVEL = ['SUPER_ADMIN', 'RM'];
  const MANAGEMENT  = [...ADMIN_LEVEL, 'BRANCH_MANAGER', 'OPERATIONS'];
  const FIELD_OPS   = ['LOAN_OFFICER', 'IDC', 'BDO'];
  const COLLECTIONS_TEAM = [
    'COLLECTIONS', 'COLLECTIONS_MGR', 'EXTERNAL_DEBT_COLLECTOR', 'FIELD_AGENT'
  ];
  const MARKETING_TEAM = ['CC_MANAGER', 'CALL_CENTRE', 'BDO'];
  const FINANCE_TEAM   = ['FINANCE', 'PAYMENT_OFFICER', 'DISBURSEMENT_OFFICER'];

  // ── Page → allowed roles  (empty = ALL) ──────────────────────────────────
  const PAGE_ROLES = {
    // ── Full access ───────────────────────────────────────────────────────────
    // SUPER_ADMIN, RM, OPERATIONS: all pages (empty array = no restriction)
    dashboard:     [],
    leads:         [],
    reference:     [],

    // ── Customers: all operational roles ─────────────────────────────────────
    customers:    ['SUPER_ADMIN','BRANCH_MANAGER','LOAN_OFFICER','IDC',
                   'BDO','RM','OPERATIONS',
                   'COLLECTIONS','COLLECTIONS_MGR',
                   'EXTERNAL_DEBT_COLLECTOR','FIELD_AGENT','FINANCE',
                   'PAYMENT_OFFICER','DISBURSEMENT_OFFICER','CC_MANAGER',
                   'CALL_CENTRE','FA_MANAGER','VERIFICATION_TEAM'],

    // ── Loans: all operational roles ────────────────────────────────────────────
    loans:        ['SUPER_ADMIN','BRANCH_MANAGER','LOAN_OFFICER','IDC',
                   'BDO','RM','OPERATIONS','FINANCE','VERIFICATION_TEAM'],

    // ── Applications: approvers & originators ────────────────────────────────
    applications: ['SUPER_ADMIN','BRANCH_MANAGER','LOAN_OFFICER','IDC',
                   'BDO','RM','OPERATIONS','VERIFICATION_TEAM'],

    // ── CRM: collections & operational roles ─────────────────────────────────
    crm:          ['SUPER_ADMIN','BRANCH_MANAGER','LOAN_OFFICER','IDC',
                   'BDO','RM','OPERATIONS',
                   'COLLECTIONS','COLLECTIONS_MGR',
                   'EXTERNAL_DEBT_COLLECTOR','FIELD_AGENT','VERIFICATION_TEAM'],

    // ── Payments: finance & collections ──────────────────────────────────────
    payments:     ['SUPER_ADMIN','BRANCH_MANAGER','LOAN_OFFICER','IDC',
                   'BDO','RM','OPERATIONS',
                   'COLLECTIONS','COLLECTIONS_MGR',
                   'EXTERNAL_DEBT_COLLECTOR','FIELD_AGENT','FINANCE',
                   'PAYMENT_OFFICER','DISBURSEMENT_OFFICER','VERIFICATION_TEAM'],

    // ── Collections: collections team + management ───────────────────────────
    collections:  ['SUPER_ADMIN','BRANCH_MANAGER','RM','OPERATIONS',
                   'LOAN_OFFICER','IDC','BDO',
                   'COLLECTIONS','COLLECTIONS_MGR',
                   'EXTERNAL_DEBT_COLLECTOR','FIELD_AGENT','VERIFICATION_TEAM'],

    // ── Notifications: all operational roles ─────────────────────────────────────
    notifications:['SUPER_ADMIN','BRANCH_MANAGER','LOAN_OFFICER','IDC',
                   'BDO','RM','OPERATIONS','VERIFICATION_TEAM'],

    // ── M-Pesa: TECH, RM, OPERATIONS only ──────────────────────────────────────
    mpesa:        ['SUPER_ADMIN','TECH','RM','OPERATIONS'],

    // ── Accounting: TECH, RM, OPERATIONS only ───────────────────────────────────
    accounting:   ['SUPER_ADMIN','TECH','RM','OPERATIONS'],

    // ── Branches: TECH, RM, OPERATIONS only ────────────────────────────────────
    branches:     ['SUPER_ADMIN','TECH','RM','OPERATIONS'],

    // ── Allocations: management + field ──────────────────────────────────────
    allocations:  ['SUPER_ADMIN','BRANCH_MANAGER','RM','OPERATIONS','VERIFICATION_TEAM'],

    // ── Assets: TECH, RM, OPERATIONS only ─────────────────────────────────────
    assets:       ['SUPER_ADMIN','TECH','RM','OPERATIONS'],

    // ── Groups/Chamas: TECH, RM, OPERATIONS only ───────────────────────────────
    groups:       ['SUPER_ADMIN','TECH','RM','OPERATIONS'],

    // ── Reports: management + field supervisors ───────────────────────────────
    reports:      ['SUPER_ADMIN','BRANCH_MANAGER','LOAN_OFFICER','IDC',
                   'RM','OPERATIONS','FINANCE','BDO','CC_MANAGER',
                   'VERIFICATION_TEAM'],

    // ── Performance: management + field ──────────────────────────────────────
    performance:  ['SUPER_ADMIN','BRANCH_MANAGER','LOAN_OFFICER','IDC',
                   'RM','OPERATIONS','VERIFICATION_TEAM'],

    // ── Staff & Settings: TECH, RM, OPERATIONS only ──────────────────────────
    staff:        ['SUPER_ADMIN','TECH','RM','OPERATIONS'],
    settings:     ['SUPER_ADMIN','RM','OPERATIONS'],
  };

  // Apply: hide nav items the current role cannot access
  document.querySelectorAll('.nav-item[data-page]').forEach(el => {
    const page    = el.getAttribute('data-page');
    const allowed = PAGE_ROLES[page];
    if (!allowed) return;                    // empty = all roles allowed
    if (allowed.length && !allowed.includes(role)) {
      el.style.display = 'none';
    }
  });

  // Also hide group labels that have no visible children
  document.querySelectorAll('.nav-group-label').forEach(label => {
    let sibling = label.nextElementSibling;
    let anyVisible = false;
    while (sibling && !sibling.classList.contains('nav-group-label')) {
      if (sibling.style.display !== 'none' && sibling.classList.contains('nav-item')) {
        anyVisible = true; break;
      }
      sibling = sibling.nextElementSibling;
    }
    if (!anyVisible) label.style.display = 'none';
  });
}

async function loadSidebar(activePage) {
  const SIDEBAR_HTML = `<!-- QuickLender Sidebar — injected via loadSidebar() -->
<nav class="sidebar" id="sidebar">
  <div class="sidebar-brand">
    <div class="brand-icon">⚡</div>
    <div>
      <div class="brand-name">Quick<span>Lender</span></div>
      <div class="brand-ver">v3.0 · LMS</div>
    </div>
  </div>

  <div class="sidebar-nav">
    <div class="nav-group-label">Core</div>
    <a class="nav-item" data-page="dashboard"    href="/pages/dashboard/dashboard.html">
      <span class="nav-icon">⬡</span> Dashboard
    </a>
    <a class="nav-item" data-page="leads" href="/pages/leads/leads.html">
      <span class="nav-icon">🎯</span> Leads
    </a>
    <a class="nav-item" data-page="reference" href="/pages/reference/reference.html">
      <span class="nav-icon">🔎</span> Reference Check
      <span class="nav-badge gold" id="nav-badge-ref" class="d-none">!</span>
    </a>
    <a class="nav-item" data-page="customers"    href="/pages/customers/customers.html">
      <span class="nav-icon">👤</span> Customers
    </a>
    <a class="nav-item" data-page="loans"        href="/pages/loans/loans.html">
      <span class="nav-icon">💰</span> Loans
    </a>
    <a class="nav-item" data-page="applications" href="/pages/applications/applications.html">
      <span class="nav-icon">📋</span> Applications
      <span class="nav-badge red" id="nav-badge-apps">—</span>
    </a>

    <div class="nav-group-label">Finance</div>
    <a class="nav-item" data-page="payments"     href="/pages/payments/payments.html">
      <span class="nav-icon">💳</span> Payments
    </a>
    <a class="nav-item" data-page="mpesa"        href="/pages/mpesa/mpesa.html" data-roles="TECH,RM,OPERATIONS">
      <span class="nav-icon">📱</span> M-Pesa
    </a>
    <a class="nav-item" data-page="accounting"   href="/pages/accounting/accounting.html" data-roles="TECH,RM,OPERATIONS">
      <span class="nav-icon">⚖️</span> Accounting
    </a>

    <div class="nav-group-label">Collections</div>
    <a class="nav-item" data-page="crm"          href="/pages/crm/crm.html">
      <span class="nav-icon">📋</span> CRM
    </a>
    <a class="nav-item" data-page="collections"  href="/pages/collections/collections.html">
      <span class="nav-icon">�</span> Collections
    </a>

    <div class="nav-group-label">Operations</div>
    <a class="nav-item" data-page="branches"     href="/pages/branches/branches.html" data-roles="TECH,RM,OPERATIONS">
      <span class="nav-icon">🏢</span> Branches
    </a>
    <a class="nav-item" data-page="allocations"  href="/pages/allocations/allocations.html">
      <span class="nav-icon">�</span> Allocations
    </a>
    <a class="nav-item" data-page="assets"       href="/pages/assets/assets.html" data-roles="TECH,RM,OPERATIONS">
      <span class="nav-icon">🚗</span> Asset Finance
    </a>

    <div class="nav-group-label">Analytics</div>
    <a class="nav-item" data-page="groups" href="/pages/groups/groups.html" data-roles="TECH,RM,OPERATIONS">
      <span class="nav-icon">👥</span> Groups & Chamas
    </a>
    <a class="nav-item" data-page="reports"      href="/pages/reports/reports.html">
      <span class="nav-icon">📊</span> Reports
    </a>
    <a class="nav-item" data-page="performance"  href="/pages/performance/performance.html">
      <span class="nav-icon">🎯</span> Performance
    </a>

    <div class="nav-group-label">System</div>
    <a class="nav-item" data-page="notifications" href="/pages/notifications/notifications.html">
      <span class="nav-icon">🔔</span> Notifications
      <span class="nav-badge" id="nav-badge-notif" class="d-none"></span>
    </a>
    <a class="nav-item" data-page="staff"        href="/pages/staff/staff.html" data-roles="TECH,RM,OPERATIONS">
      <span class="nav-icon">👥</span> Staff & Roles
    </a>
    <a class="nav-item" data-page="settings"     href="/pages/settings/settings.html">
      <span class="nav-icon">⚙️</span> Settings
    </a>
  </div>

  <!-- User block + logout -->
  <div class="sidebar-footer" id="sidebar-user">
    <div class="user-avatar" id="user-avatar-initials">—</div>
    <div class="flex-1 min-w-0">
      <div class="user-name" id="sidebar-user-name">Loading…</div>
      <div class="user-role" id="sidebar-user-role">—</div>
    </div>
    <button class="logout-btn" onclick="Auth.logout()" title="Sign out (logout)">⏻</button>
  </div>
</nav>
`;

  try {
    const mount = document.getElementById('sidebar-mount');
    if (!mount) return;

    mount.innerHTML = SIDEBAR_HTML;

    // Populate user info from stored JWT payload
    const user = Auth.getUser();
    if (user) {
      const nameEl = document.getElementById('sidebar-user-name');
      const roleEl = document.getElementById('sidebar-user-role');
      const avEl   = document.getElementById('user-avatar-initials');
      if (nameEl) nameEl.textContent = user.full_name || user.email || '—';
      if (roleEl) roleEl.textContent = (user.role || '').replace(/_/g, ' ');
      if (avEl) {
        avEl.textContent       = Auth.initials(user.full_name || user.email || '');
        avEl.style.background  = Auth.avatarColor(user.full_name || '');
      }
    }

    // Highlight the current page in the nav
    if (activePage) {
      document.querySelectorAll(`.nav-item[data-page="${activePage}"]`)
        .forEach(el => el.classList.add('active'));
    } else {
      // Auto-detect from URL if activePage not passed
      const page = window.location.pathname.split('/').filter(Boolean).slice(-1)[0]?.replace('.html','');
      if (page) {
        document.querySelectorAll(`.nav-item[data-page="${page}"]`)
          .forEach(el => el.classList.add('active'));
      }
    }

    // Apply role-based nav visibility
    _applyNavPermissions();

    wireTopbar();
    initMobileSidebar();

    // Load live counts into nav badges
    _updateNavBadges();

  } catch (e) {
    console.warn('Sidebar init failed:', e);
  }
}

async function _updateNavBadges() {
  try {
    // Pending applications count
    const apps = await API.loans({ status: 'PENDING' }).catch(() => null);
    const badgeApps = document.getElementById('nav-badge-apps');
    if (badgeApps) {
      const n = apps?.count ?? 0;
      badgeApps.textContent = n > 0 ? n : '';
      badgeApps.style.display = n > 0 ? 'inline-flex' : 'none';
    }

    // Unread notifications count
    const stats = await API.notifStats().catch(() => null);
    const badgeNotif = document.getElementById('nav-badge-notif');
    if (badgeNotif) {
      const n = stats?.failed_sms_total ?? 0;
      badgeNotif.textContent = n > 0 ? n : '';
      badgeNotif.style.display = n > 0 ? 'inline-flex' : 'none';
    }
  } catch {}
}

// ─── LOAN CALC ────────────────────────────────────────
function calcLoanTotals(principal, rate) {
  const p = parseFloat(principal) || 0;
  const r = parseFloat(rate) || 0;
  const interest = p * (r / 100);
  return { principal: p, interest, total: p + interest };
}

// ─── DEBOUNCE ─────────────────────────────────────────
function debounce(fn, ms = 350) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ─── DATE HELPERS ─────────────────────────────────────
function todayISO() { return new Date().toISOString().split('T')[0]; }
function addDays(days, from = new Date()) {
  const d = new Date(from);
  d.setDate(d.getDate() + days);
  return d.toISOString().split('T')[0];
}

// ─── TOPBAR WIRING ────────────────────────────────────────────────────────────
function wireTopbar() {
  const user = Auth.getUser();
  if (!user) return;

  // Use dedicated system controls slot so page-specific topbarActions
  // never overwrite notif bell + user avatar
  const topbarRight = document.querySelector('.topbar-right');
  if (!topbarRight) return;

  // Remove any previously injected system controls (idempotent)
  document.getElementById('topbar-system-controls')?.remove();

  // Create a persistent system controls wrapper appended to topbar-right
  const sysWrapper = document.createElement('div');
  sysWrapper.id    = 'topbar-system-controls';
  sysWrapper.style = 'display:flex;align-items:center;gap:6px;margin-left:auto;flex-shrink:0';
  topbarRight.appendChild(sysWrapper);

  // Inject notification bell into system wrapper
  const notifWrapper = document.createElement('div');
  notifWrapper.style.position = 'relative';
  notifWrapper.innerHTML = `
    <div class="notif-btn" id="notifBtn" onclick="toggleNotifDropdown(event)" title="Notifications">
      🔔<span class="notif-dot" id="notifDot"></span>
    </div>
    <div class="notif-dropdown" id="notifDropdown">
      <div class="notif-dropdown-header">
        <span>Notifications</span>
        <span class="text-sm text-dim cursor-pointer" onclick="markAllRead()">Mark all read</span>
      </div>
      <div class="notif-list" id="notifList">
        <div class="p-20 text-center text-dim text-sm">Loading…</div>
      </div>
    </div>
  `;

  // Inject user avatar+dropdown (at end of topbar-right)
  const userWrapper = document.createElement('div');
  userWrapper.style.position = 'relative';
  const initials = Auth.initials(user.full_name || user.email || '');
  const color    = Auth.avatarColor(user.full_name || '');
  const roleTxt  = (user.role || '').replace(/_/g, ' ');
  userWrapper.innerHTML = `
    <div class="topbar-user" id="topbarUserBtn" onclick="toggleUserDropdown(event)">
      <div class="topbar-avatar" style="background:${color}">${initials}</div>
      <div class="topbar-user-info">
        <div class="topbar-user-name">${(user.full_name || user.email || '').split(' ')[0]}</div>
        <div class="topbar-user-role">${roleTxt}</div>
      </div>
      <span class="text-xs text-dim ml-4">▾</span>
    </div>
    <div class="user-dropdown" id="userDropdown">
      <div class="user-dropdown-header">
        <div class="user-dropdown-name">${user.full_name || user.email}</div>
        <div class="user-dropdown-email">${user.email}</div>
      </div>
      <a href="/pages/profile/profile.html" class="user-dropdown-item">👤 My Profile</a>
      <a href="/pages/settings/settings.html"   class="user-dropdown-item">⚙️ Settings</a>
      <div class="user-dropdown-divider"></div>
      <button class="user-dropdown-item danger" onclick="Auth.logout()">⏻ Sign Out</button>
    </div>
  `;

  // Insert into the persistent system wrapper, not topbarRight directly
  sysWrapper.appendChild(notifWrapper);
  sysWrapper.appendChild(userWrapper);

  // Load notifications
  loadNotifBadge();

  // Close dropdowns on outside click
  document.addEventListener('click', (e) => {
    if (!notifWrapper.contains(e.target))  document.getElementById('notifDropdown')?.classList.remove('open');
    if (!userWrapper.contains(e.target))   document.getElementById('userDropdown')?.classList.remove('open');
  });
}

function toggleNotifDropdown(e) {
  e.stopPropagation();
  const dd = document.getElementById('notifDropdown');
  const wasOpen = dd.classList.contains('open');
  document.getElementById('userDropdown')?.classList.remove('open');
  if (!wasOpen) {
    dd.classList.add('open');
    loadNotifications();
  } else {
    dd.classList.remove('open');
  }
}

function toggleUserDropdown(e) {
  e.stopPropagation();
  document.getElementById('notifDropdown')?.classList.remove('open');
  document.getElementById('userDropdown')?.classList.toggle('open');
}

async function loadNotifBadge() {
  try {
    const s = await API.notifStats?.();
    const failed = s?.failed_sms_total || 0;
    const dot = document.getElementById('notifDot');
    if (dot && failed > 0) dot.classList.add('active');
  } catch {}
}

const _notifColors = {
  PENDING: 'var(--gold)', APPROVED: 'var(--brand)',
  DEFAULT: 'var(--red)',  DISBURSED: 'var(--blue)',
};

async function loadNotifications() {
  const list = document.getElementById('notifList');
  if (!list) return;
  try {
    const [smsData, loanData] = await Promise.all([
      API.smsLogs?.({page_size: 8}),
      API.loans?.({status: 'PENDING', page_size: 5}),
    ]);
    const smsList  = smsData?.results || [];
    const loanList = loanData?.results || [];
    const items = [];

    loanList.forEach(l => items.push({
      icon: '📋', title: `Pending: ${l.loan_id} — ${l.customer_name}`,
      meta: `KES ${(+l.principal).toLocaleString()} · ${Fmt.date(l.created_at)}`,
      color: 'var(--gold)',
    }));
    smsList.forEach(s => items.push({
      icon: s.status === 'FAILED' ? '❌' : '📱',
      title: `SMS ${s.status} → ${s.recipient}`,
      meta: s.template + ' · ' + Fmt.relTime(s.created_at),
      color: s.status === 'FAILED' ? 'var(--red)' : 'var(--brand)',
    }));

    list.innerHTML = items.length ? items.map(n => `
      <div class="notif-item">
        <div class="d-flex gap-10 items-start">
          <div class="notif-item-dot" style="background:${n.color};margin-top:5px"></div>
          <div>
            <div class="notif-item-title">${n.icon} ${n.title}</div>
            <div class="notif-item-meta">${n.meta}</div>
          </div>
        </div>
      </div>`).join('')
    : '<div class="p-20 text-center text-dim text-sm">No recent notifications</div>';
  } catch {
    list.innerHTML = '<div class="p-16 text-center text-dim text-sm">Unable to load</div>';
  }
}

function markAllRead() {
  const dot = document.getElementById('notifDot');
  if (dot) dot.classList.remove('active');
  Toast.success('All notifications marked as read');
  document.getElementById('notifDropdown')?.classList.remove('open');
}
