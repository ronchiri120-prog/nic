Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}
document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('applications');
  document.getElementById('topbarActions').innerHTML = `
    <div class="topbar-search">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search…" oninput="onSearch()">
    </div>
    <select class="form-control filter-130" id="appStatusFilter" onchange="loadApplications()">
      <option value="PENDING">Pending</option>
      <option value="APPROVED">Approved</option>
      <option value="REJECTED">Rejected</option>
      <option value="">All</option>
    </select>
    <button class="btn btn-primary" onclick="window.location.href='../loans/loans.html'">+ New Application</button>
  `;
  loadApplications();
});

async function loadApplications() {
  const status = document.getElementById('appStatusFilter')?.value || 'PENDING';
  const search = document.getElementById('searchInput')?.value || '';
  const params = {status, search, ordering: '-created_at'};
  const tbody = document.getElementById('appTbody');
  if(!tbody) return;
  tbody.innerHTML = loadingRows(9, 9);
  try {
    const data = await API.loans(params);
    const apps = data?.results || [];
    document.getElementById('appCount').textContent = `${data?.count||apps.length} applications`;
    tbody.innerHTML = apps.length ? apps.map(a => `<tr>
      <td class="td-mono text-brand">${a.loan_id}</td>
      <td><div class="d-flex items-center gap-8">${avatarEl(a.customer_name||'?')}<b>${a.customer_name||'—'}</b></div></td>
      <td>${Badge.loanType(a.product_type||'FA')}</td>
      <td class="td-mono">${Fmt.currency(a.principal)}</td>
      <td>
        <div class="d-flex items-center gap-8">
          <div class="score-track">
            <div style="height:100%;background:${getCreditColor(a.credit_score)};width:${a.credit_score||0}%"></div>
          </div>
          <span class="mono text-sm">${a.credit_score||'—'}</span>
        </div>
      </td>
      <td>${a.lo_name||'—'}</td>
      <td class="td-mono text-dim">${Fmt.datetime(a.created_at)}</td>
      <td>${Badge.status(a.status)}</td>
      <td>
        <div class="d-flex gap-4">
          ${a.status==='PENDING' && Auth.canApprove() ? `
            <button class="btn btn-primary btn-sm" onclick="runScore(${a.id},'${a.customer}',${a.principal},'${a.loan_id}')">Score</button>
            <button class="btn btn-ghost btn-sm" onclick="approveApp(${a.id},'${a.loan_id}')">✓</button>
            <button class="btn btn-danger btn-sm" onclick="rejectApp(${a.id},'${a.loan_id}')">✕</button>
          ` : ''}
        </div>
      </td>
    </tr>`).join('') : `<tr><td colspan="9">${emptyState('📋','No applications','All caught up.')}</td></tr>`;
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="td-error">Failed to load applications — check connection.</td></tr>`;
  }
}

function getCreditColor(score) {
  if(!score) return 'var(--text3)';
  if(score>=80) return 'var(--brand)';
  if(score>=60) return 'var(--gold)';
  return 'var(--red)';
}

async function runScore(loanId, customerId, amount, ref) {
  try {
    const result = await API.creditScore({customer_id: customerId, loan_amount: amount});
    if(!result) return;
    const color = result.risk_color==='green'?'var(--brand)':result.risk_color==='amber'?'var(--gold)':'var(--red)';
    Toast[result.approved?'success':'warn'](
      `${ref}: Score ${result.score}/100 — ${result.risk_grade} — ${result.recommendation}`
    );
    loadApplications();
  } catch (err) { console.warn(err); }
}

async function approveApp(id, ref) {
  if (!await QL.confirm(`Approve application <b>${ref}</b>?`, {title:'Approve Application', okLabel:'Approve'})) return;
  try {
    await API.approveLoan(id);
    Toast.success(`✓ ${ref} approved`);
    loadApplications();
  } catch (err) {
    Toast.error(err?.data?.detail || `Failed to approve ${ref}`);
  }
}

async function rejectApp(id, ref) {
  const reason = await QL.prompt(`Rejection reason for ${ref}:`, '',
    {title:'Reject Application', placeholder:'e.g. Insufficient income'});
  if (!reason) return;
  try {
    await API.rejectLoan(id, {reason});
    Toast.warn(`${ref} rejected`);
    loadApplications();
  } catch (err) {
    Toast.error(err?.data?.detail || `Failed to reject ${ref}`);
  }
}
const onSearch = debounce(() => loadApplications(), 350);
