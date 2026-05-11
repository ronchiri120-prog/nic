/**
 * dashboard.js — QuickLender main dashboard
 * All KPIs live from /api/v1/auth/dashboard/stats/
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

// Show access denied toast if redirected from a restricted page
(function() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('access_denied')) {
    setTimeout(() => Toast.error('Access denied — you do not have permission to view that page.'), 500);
    // Clean URL
    history.replaceState({}, '', '/pages/dashboard/dashboard.html');
  }
})();

document.addEventListener('DOMContentLoaded', async () => {
  loadSidebar('dashboard');
  setGreeting();
  await loadDashboard();
});

async function loadDashboard() {
  showSkeletons();
  try {
    const s = await API.dashStats();
    if (s) {
      renderKPIs(s);
      renderRiskBar(s);
    }
    loadRecentActivity();
    loadBranchPerf();
  } catch {
    Toast.error('Could not load dashboard data');
  }
}

function setGreeting() {
  const h = new Date().getHours();
  const greeting = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  const user = Auth.getUser();
  const el = document.getElementById('dash-greeting');
  if (el) el.textContent = `${greeting}, ${user?.full_name?.split(' ')[0] || 'there'} 👋`;
}

function renderKPIs(s) {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

  // Row 1 — Portfolio
  set('kpi-portfolio',   Fmt.millions(s.total_portfolio));
  set('kpi-active',      Fmt.number(s.active_loans));
  set('kpi-pending',     Fmt.number(s.pending_applications));
  set('kpi-default',     Fmt.number(s.defaulted_loans));
  set('kpi-total-loans', Fmt.number(s.total_loans));

  // Row 2 — MTD
  set('kpi-disb',        Fmt.millions(s.mtd_disbursements));
  set('kpi-disb-count',  `${s.mtd_loans_count || 0} loans`);
  set('kpi-coll',        Fmt.millions(s.mtd_collections));
  set('kpi-coll-rate',   `${s.collection_rate || 0}%`);
  set('kpi-new-cust',    Fmt.number(s.new_customers_mtd));
  set('kpi-total-cust',  Fmt.number(s.total_customers));

  // Row 3 — Risk
  set('kpi-par30',       Fmt.millions(s.par30_balance));
  set('kpi-par30-ratio', `PAR 30: ${s.par30_ratio || 0}%`);
  set('kpi-written-off', Fmt.number(s.written_off_mtd));

  // Colour PAR ratio
  const parEl = document.getElementById('kpi-par30-ratio');
  if (parEl) {
    parEl.classList.remove('text-brand','text-gold','text-red');
    if      (s.par30_ratio <= 5)  parEl.classList.add('text-brand');
    else if (s.par30_ratio <= 10) parEl.classList.add('text-gold');
    else                          parEl.classList.add('text-red');
  }
}

function renderRiskBar(s) {
  const el = document.getElementById('risk-bar-fill');
  if (!el) return;
  const pct = Math.min(s.par30_ratio || 0, 100);
  el.style.width = pct + '%';
  el.style.background = pct <= 5 ? 'var(--brand)' : pct <= 10 ? 'var(--gold)' : 'var(--red)';
}

function showSkeletons() {
  const ids = ['kpi-portfolio','kpi-active','kpi-pending','kpi-default','kpi-total-loans',
               'kpi-disb','kpi-coll','kpi-coll-rate','kpi-new-cust','kpi-total-cust',
               'kpi-par30','kpi-par30-ratio'];
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = '—'; });
}

async function loadRecentActivity() {
  try {
    const data = await API.loans({ page_size: 8, ordering: '-created_at' });
    const loans = data?.results || [];
    const el = document.getElementById('recent-loans');
    if (!el) return;
    el.innerHTML = loans.length
      ? loans.map(l => `<tr>
          <td class="td-mono text-brand">${l.loan_id}</td>
          <td><b>${l.customer_name || l.customer}</b></td>
          <td class="td-mono">${Fmt.currency(l.principal)}</td>
          <td>${Badge.status(l.status)}</td>
          <td class="td-mono text-dim">${Fmt.date(l.created_at)}</td>
        </tr>`).join('')
      : `<tr><td colspan="5">${emptyState('📋','No loans yet')}</td></tr>`;
  } catch (err) { console.warn(err); }
}

async function loadBranchPerf() {
  try {
    const data = await API.reportBranches();
    const branches = data?.branches || [];
    const el = document.getElementById('branch-perf');
    if (!el) return;
    el.innerHTML = branches.slice(0, 5).map(b => {
      const rate = b.collection_rate || 0;
      const cls  = rate >= 85 ? 'pb-green' : rate >= 70 ? 'pb-gold' : 'pb-red';
      return `<div class="perf-officer-row">
        <div class="perf-officer-head">
          <div class="perf-officer-identity">
            <div class="perf-officer-name">${b.branch_name}</div>
            <div class="text-dim text-sm">${b.loan_officers || 0} officers</div>
          </div>
          <div class="perf-officer-numbers">
            <span class="td-mono text-sm">${Fmt.millions(b.active_portfolio || 0)}</span>
          </div>
        </div>
        <div class="progress">
          <div class="progress-bar ${cls}" style="width:${Math.min(rate,100)}%"></div>
        </div>
        <div class="perf-progress-sub">${rate}% collection rate · ${b.defaulted || 0} defaults</div>
      </div>`;
    }).join('') || emptyState('🏢', 'No branch data');
  } catch (err) { console.warn(err); }
}
