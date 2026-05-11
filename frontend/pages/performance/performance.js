Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}
document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('performance');
  // Inject search into topbar
  const ta = document.getElementById('topbarActions');
  if (ta) ta.innerHTML = `
    <div class="topbar-search">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search officer name…" oninput="onSearch()">
    </div>
  `;
  loadPerformance();
});

async function loadPerformance() {
  const el = document.getElementById('pageContent');
  try {
    const [individual, branches] = await Promise.all([
      API.reportIndividual().catch(() => null),
      API.reportBranches().catch(() => null),
    ]);
    const officers  = individual || [];
    const branchPerf = branches || [];

    el.innerHTML = `
      <div class="section-header animate-fadeup"><div>
        <h1 class="page-heading">🎯 Performance Tracker</h1>
        <p class="text-sm text-dim">Targets vs actuals — staff & branches</p>
      </div></div>
      <div class="kpi-grid animate-fadeup stagger-1 kpi-grid kpi-grid-4 animate-fadeup">
        <div class="kpi-card kc-green grad"><div class="kpi-label">Avg Collection Rate</div>
          <div class="kpi-value">${officers.length?Fmt.pct(officers.reduce((s,o)=>s+o.collection_rate,0)/officers.length):'—'}</div></div>
        <div class="kpi-card kc-blue grad"><div class="kpi-label">Top Performer</div>
          <div class="kpi-value text-14">${officers.sort((a,b)=>b.collection_rate-a.collection_rate)[0]?.officer.split(' ')[0]||'—'}</div></div>
        <div class="kpi-card kc-gold grad"><div class="kpi-label">Active Officers</div>
          <div class="kpi-value">${officers.length}</div></div>
        <div class="kpi-card kc-red grad"><div class="kpi-label">Below Target</div>
          <div class="kpi-value">${officers.filter(o=>o.collection_rate<80).length}</div></div>
      </div>

      <div class="panel animate-fadeup stagger-2 mb-24">
        <div class="panel-header"><div class="panel-title">🎯 Officer Disbursement vs Target</div></div>
        <div class="panel-body">
          ${officers.map(o => {
            const rate = Math.min(o.disb_rate||0, 100);
            return `<div class="mb-16">
              <div class="perf-officer-head">
                <div class="perf-officer-identity">${avatarEl(o.officer)}<div>
                  <div class="perf-officer-name">${o.officer}</div>
                  <div class="perf-officer-sub">${o.role?.replace(/_/g,' ')} · ${o.branch||'—'}</div>
                </div></div>
                <div class="d-flex items-center gap-12">
                  <span class="mono text-sm text-dim">${Fmt.currency(o.total_disbursed)} / ${Fmt.currency(o.disb_target)}</span>
                  <span class="badge ${rate>=100?'badge-active':rate>=80?'badge-approved':'badge-pending'}">${Fmt.pct(rate,0)}</span>
                </div>
              </div>
              ${renderProgress(rate)}
            </div>`;
          }).join('') || '<p class="text-dim text-md">No performance data — ensure backend is running</p>'}
        </div>
      </div>

      ${branchPerf.length ? `<div class="panel animate-fadeup stagger-3">
        <div class="panel-header"><div class="panel-title">🏢 Branch Collection Performance</div></div>
        <div class="panel-body">
          ${branchPerf.map(b => {
            const rate = b.collection_rate || 0;
            return `<div class="mb-16">
              <div class="d-flex justify-between mb-8">
                <span class="text-sm fw-600">${b.branch}</span>
                <span class="mono text-sm" style="color:${rate>=85?'var(--brand)':rate>=75?'var(--gold)':'var(--red)'}">${Fmt.pct(rate)}</span>
              </div>
              ${renderProgress(rate)}
              <div class="perf-progress-sub">
                ${Fmt.currency(b.collected)} collected / ${Fmt.currency(b.total_due)} due
              </div>
            </div>`;
          }).join('')}
        </div>
      </div>` : ''}
    `;
  } catch (err) {
    console.warn('loadPerformance failed:', err);
  }
}

const onSearch = debounce(() => {
  const q = document.getElementById('searchInput')?.value || '';
  loadPerformance(q);
}, 300);
