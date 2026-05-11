Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}
document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('reports');
  document.getElementById('topbarActions').innerHTML = `
    <button class="btn btn-ghost" onclick="API.excelLoans()">⬇ Excel Loans</button>
    <button class="btn btn-ghost" onclick="API.excelCollections()">⬇ Excel Overdue</button>
    <button class="btn btn-ghost" onclick="API.excelCustomers()">⬇ Excel Customers</button>

    <input type="date" id="rptFrom" class="form-control filter-ctrl-lg">
    <input type="date" id="rptTo"   class="form-control filter-ctrl-lg">
    <button class="btn btn-ghost" onclick="Toast.success('Report exported')">⬇ Export</button>
  `;
  const now = new Date();
  document.getElementById('rptFrom').value = new Date(now.getFullYear(),now.getMonth(),1).toISOString().split('T')[0];
  document.getElementById('rptTo').value   = now.toISOString().split('T')[0];
  renderTabs();
  loadLoanBreakdown();
});

function renderTabs() {
  document.getElementById('pageContent').innerHTML = `
    <div class="section-header animate-fadeup"><div>
      <h1 class="page-heading">📊 Reports</h1>
      <p class="text-sm text-dim">Portfolio · Branch · Individual · Defaulters · CBK</p>
    </div></div>
    <div class="tabs animate-fadeup stagger-1">
      <button class="tab-btn active" onclick="switchTab(this,'rpt-loans');loadLoanBreakdown()">Loan Breakdown</button>
      <button class="tab-btn" onclick="switchTab(this,'rpt-branches');loadBranchReport()">Branch Performance</button>
      <button class="tab-btn" onclick="switchTab(this,'rpt-defaulters');loadDefaulters()">Defaulters</button>
      <button class="tab-btn" onclick="switchTab(this,'rpt-individual');loadIndividual()">Individual Perf</button>
      <button class="tab-btn" onclick="switchTab(this,'rpt-dormant');loadDormant()">Dormant</button>
      <button class="tab-btn" onclick="switchTab(this,'rpt-leads');loadLeadsReport()">Leads</button>
    </div>
    <div id="rpt-loans"     class="tab-content active"></div>
    <div id="rpt-branches"  class="tab-content"></div>
    <div id="rpt-defaulters"class="tab-content"></div>
    <div id="rpt-individual"class="tab-content"></div>
    <div id="rpt-dormant"   class="tab-content"></div>
    <div id="rpt-leads"     class="tab-content"></div>
  `;
}

async function loadLoanBreakdown() {
  const el = document.getElementById('rpt-loans');
  if(!el) return;
  el.innerHTML = `<div class="skeleton skeleton skeleton-h300"></div>`;
  try {
    const d = await API.reportLoans({from: document.getElementById('rptFrom')?.value, to: document.getElementById('rptTo')?.value});
    const loans = d?.loans || [];
    const t = d?.totals || {};
    el.innerHTML = `
      <div class="kpi-grid kpi-grid kpi-grid-3 animate-fadeup">
        <div class="kpi-card kc-green grad"><div class="kpi-label">Total Principal</div><div class="kpi-value text-2xl">${Fmt.millions(t.total_principal||0)}</div></div>
        <div class="kpi-card kc-blue grad"><div class="kpi-label">Total Collected</div><div class="kpi-value text-2xl">${Fmt.millions(t.total_paid||0)}</div></div>
        <div class="kpi-card kc-red grad"><div class="kpi-label">Outstanding</div><div class="kpi-value text-2xl">${Fmt.millions(t.total_balance||0)}</div></div>
      </div>
      <div class="panel"><div class="panel-body-bare"><table class="data-table">
        <thead><tr><th>Loan ID</th><th>Customer</th><th>Branch</th><th>Principal</th><th>Paid</th><th>Balance</th><th>Status</th></tr></thead>
        <tbody>${loans.map(l=>`<tr>
          <td class="td-mono text-brand">${l.loan_id}</td>
          <td><b>${l.customer_name}</b></td>
          <td>${l.branch_name||'—'}</td>
          <td class="td-mono">${Fmt.currency(l.principal)}</td>
          <td class="td-mono text-brand">${Fmt.currency(l.total_paid)}</td>
          <td class="td-mono" style="color:${parseFloat(l.balance)>0?'var(--gold)':'var(--text3)'}">${Fmt.currency(l.balance)}</td>
          <td>${Badge.status(l.status)}</td>
        </tr>`).join('')||`<tr><td colspan="7">${emptyState('📊','No data','No loans match the filters.')}</td></tr>`}
        </tbody>
      </table></div></div>`;
  } catch (err) {
    console.warn('loadLoanBreakdown failed:', err);
  }
}

async function loadBranchReport() {
  const el = document.getElementById('rpt-branches');
  if(!el) return;
  el.innerHTML = `<div class="skeleton skeleton skeleton-h200"></div>`;
  try {
    const rows = await API.reportBranches();
    if(!rows?.length) {
      el.innerHTML = `<div class="panel"><div class="panel-body-bare">${emptyState('📊','No branch data','No branch performance data available.')}</div></div>`;
      return;
    }
    el.innerHTML = `<div class="panel"><div class="panel-body-bare"><table class="data-table">
      <thead><tr><th>Branch</th><th>Target</th><th>Disbursed</th><th>Total Due</th><th>Collected</th><th>Rate</th><th>Active</th><th>Default</th></tr></thead>
      <tbody>${rows.map(b=>`<tr>
        <td><b>${b.branch}</b></td>
        <td class="td-mono">${Fmt.currency(b.target)}</td>
        <td class="td-mono text-brand">${Fmt.currency(b.disbursed)}</td>
        <td class="td-mono">${Fmt.currency(b.total_due)}</td>
        <td class="td-mono text-brand">${Fmt.currency(b.collected)}</td>
        <td class="td-mono" style="color:${b.collection_rate>=85?'var(--brand)':b.collection_rate>=75?'var(--gold)':'var(--red)'};font-weight:700">${Fmt.pct(b.collection_rate)}</td>
        <td class="td-mono">${b.active_loans}</td>
        <td class="td-mono text-red">${b.defaulted}</td>
      </tr>`).join('')}</tbody>
    </table></div></div>`;
  } catch (err) {
    console.warn('loadBranchReport failed:', err);
    el.innerHTML = `<div class="panel"><div class="panel-body-bare">${emptyState('⚠️','Error','Failed to load branch data.')}</div></div>`;
  }
}

async function loadDefaulters() {
  const el = document.getElementById('rpt-defaulters');
  if(!el) return;
  el.innerHTML = `<div class="skeleton skeleton skeleton-h200"></div>`;
  try {
    const d = await API.reportDefaulters();
    const loans = d?.loans || [];
    el.innerHTML = `<div class="panel">
      <div class="panel-header"><div class="panel-title text-red">⚠️ Defaulters / Overdue</div>
        <span class="badge badge-default">${d?.count||0} accounts — KES ${Fmt.number(d?.total_at_risk||0)} at risk</span>
      </div>
      <div class="panel-body-bare"><table class="data-table">
        <thead><tr><th>Loan ID</th><th>Customer</th><th>Balance</th><th>Due Date</th><th>Officer</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>${loans.map(l=>`<tr>
          <td class="td-mono text-brand">${l.loan_id}</td>
          <td><b>${l.customer_name}</b></td>
          <td class="td-mono text-red">${Fmt.currency(l.balance)}</td>
          <td class="td-mono text-red">${Fmt.date(l.due_date)}</td>
          <td>${l.lo_name||'—'}</td>
          <td>${Badge.status(l.status)}</td>
          <td><button class="btn btn-primary btn-sm" onclick="Toast.success('STK Push sent')">📲</button></td>
        </tr>`).join('')||`<tr><td colspan="7">${emptyState('✓','No defaulters','All loans performing.')}</td></tr>`}
        </tbody>
      </table></div>
    </div>`;
  } catch (err) {
    console.warn('loadDefaulters failed:', err);
  }
}

async function loadIndividual() {
  const el = document.getElementById('rpt-individual');
  if(!el) return;
  el.innerHTML = `<div class="skeleton skeleton skeleton-h200"></div>`;
  try {
    const rows = await API.reportIndividual();
    if(!rows?.length) {
      el.innerHTML = `<div class="panel"><div class="panel-body-bare">${emptyState('📊','No individual data','No officer performance data available.')}</div></div>`;
      return;
    }
    el.innerHTML = `<div class="panel"><div class="panel-body-bare"><table class="data-table">
      <thead><tr><th>Officer</th><th>Branch</th><th>Target</th><th>Disbursed</th><th>Customers</th><th>Collected</th><th>Rate</th></tr></thead>
      <tbody>${rows.map(o=>`<tr>
        <td><div class="d-flex items-center gap-8">${avatarEl(o.officer)}<b>${o.officer}</b></div></td>
        <td>${o.branch||'—'}</td>
        <td class="td-mono">${Fmt.currency(o.disb_target)}</td>
        <td class="td-mono text-brand">${Fmt.currency(o.total_disbursed)}</td>
        <td class="td-mono">${o.active_customers}</td>
        <td class="td-mono text-brand">${Fmt.currency(o.total_paid)}</td>
        <td class="td-mono" style="color:${o.collection_rate>=85?'var(--brand)':o.collection_rate>=75?'var(--gold)':'var(--red)'};font-weight:700">${Fmt.pct(o.collection_rate)}</td>
      </tr>`).join('')}</tbody>
    </table></div></div>`;
  } catch (err) {
    console.warn('loadIndividual failed:', err);
    el.innerHTML = `<div class="panel"><div class="panel-body-bare">${emptyState('⚠️','Error','Failed to load individual data.')}</div></div>`;
  }
}

async function loadDormant() {
  const el = document.getElementById('rpt-dormant');
  if(!el) return;
  el.innerHTML = `<div class="skeleton skeleton skeleton-h200"></div>`;
  try {
    const rows = await API.reportDormant();
    el.innerHTML = `<div class="panel"><div class="panel-body-bare"><table class="data-table">
      <thead><tr><th>UID</th><th>Customer</th><th>Phone</th><th>Branch</th><th>Last Active</th><th>Loan Limit</th></tr></thead>
      <tbody>${(rows||[]).map(c=>`<tr>
        <td class="td-mono text-dim">${c.uid}</td>
        <td><b>${c.full_name||`${c.first_name} ${c.last_name}`}</b></td>
        <td class="td-mono">${c.phone}</td>
        <td>${c.branch_name||'—'}</td>
        <td class="td-mono text-dim">${Fmt.date(c.updated_at||c.created_at)}</td>
        <td class="td-mono">${Fmt.currency(c.loan_limit)}</td>
      </tr>`).join('')||`<tr><td colspan="6">${emptyState('✓','No dormant customers')}</td></tr>`}
      </tbody>
    </table></div></div>`;
  } catch (err) {
    console.warn('loadDormant failed:', err);
  }
}

const onSearch = debounce(() => loadLoanBreakdown(), 350);

async function loadLeadsReport() {
  const el = document.getElementById('rpt-leads');
  if (!el) return;
  el.innerHTML = `<div class="skeleton skeleton-h300 mt-16"></div>`;
  try {
    const from = document.getElementById('rptFrom')?.value;
    const to   = document.getElementById('rptTo')?.value;
    const data = await API.leads({ ordering: '-created_at', page_size: 200 });
    const leads = data?.results || data || [];

    const total     = leads.length;
    const converted = leads.filter(l => l.status === 'CONVERTED').length;
    const pipeline  = leads.filter(l => !['CONVERTED','LOST'].includes(l.status)).length;
    const lost      = leads.filter(l => l.status === 'LOST').length;
    const rate      = total > 0 ? ((converted/total)*100).toFixed(1) : 0;

    el.innerHTML = `
      <div class="kpi-grid kpi-grid-4 animate-fadeup mt-16">
        <div class="kpi-card kc-blue grad"><div class="kpi-label">Total Leads</div><div class="kpi-value">${total}</div></div>
        <div class="kpi-card kc-green grad"><div class="kpi-label">Converted</div><div class="kpi-value">${converted}</div></div>
        <div class="kpi-card kc-gold grad"><div class="kpi-label">In Pipeline</div><div class="kpi-value">${pipeline}</div></div>
        <div class="kpi-card kc-teal grad"><div class="kpi-label">Conversion Rate</div><div class="kpi-value">${rate}%</div></div>
      </div>
      <div class="panel mt-16">
        <div class="panel-header"><div class="panel-title">Lead Pipeline Report</div></div>
        <div class="panel-body-bare">
          <table class="data-table">
            <thead><tr><th>Lead ID</th><th>Name</th><th>Phone</th><th>Business</th>
              <th>Sub-market</th><th>Branch</th><th>By</th><th>Status</th><th>Date</th></tr></thead>
            <tbody>
              ${leads.map(l => `<tr>
                <td class="td-mono text-blue">${l.lead_id}</td>
                <td><b>${l.full_name||l.first_name+' '+l.last_name}</b></td>
                <td class="td-mono">${l.phone}</td>
                <td class="text-sm">${l.business_category||'—'}</td>
                <td class="text-sm">${l.submarket||'—'}</td>
                <td class="text-sm text-dim">${l.branch_name||'—'}</td>
                <td class="text-sm text-dim">${l.created_by_name||'—'}</td>
                <td><span class="badge ${l.status==='CONVERTED'?'badge-active':l.status==='LOST'?'badge-default':'badge-pending'}">${l.status}</span></td>
                <td class="td-mono text-dim">${Fmt.date(l.created_at)}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>`;
  } catch {
    el.innerHTML = `<div class="td-error text-center p-20 mt-16">Failed to load leads report.</div>`;
  }
}
