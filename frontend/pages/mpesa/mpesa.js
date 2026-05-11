/**
 * M-Pesa Page — v1.0 (Live Daraja Integration)
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('mpesa');
  setupTopbar();
  loadMpesaTxns();
  loadMpesaKPIs();
});

function setupTopbar() {
  document.getElementById('topbarActions').innerHTML = `
    <div class="topbar-search">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search M-Pesa ref, phone…" oninput="onSearch()">
    </div>
    <select class="filter-ctrl-md" id="typeFilter" onchange="loadTransactions()">
      <option value="">All Types</option>
      <option value="STK_PUSH">STK Push</option>
      <option value="B2C">B2C Disburse</option>
      <option value="C2B">C2B PayBill</option>
    </select>
    <select class="filter-ctrl-md" id="statusFilter" onchange="loadTransactions()">
      <option value="">All Status</option>
      <option value="SUCCESS">Success</option>
      <option value="FAILED">Failed</option>
      <option value="PENDING">Pending</option>
      <option value="UNMATCHED">Unmatched</option>
    </select>
    <span class="badge badge-active" id="api-status">● Checking API…</span>
    <span class="mpesa-api-status d-none d-md-inline">C2B: <code class="mpesa-c2b-url">/api/v1/payments/mpesa/c2b/</code></span>
  `;
  checkApiStatus();
}

async function checkApiStatus() {
  try {
    await API.mpesaTxns({ page_size: 1 });
    const el = document.getElementById('api-status');
    if (el) { el.textContent = '● Daraja Connected'; el.className = 'badge badge-active'; }
  } catch {
    const el = document.getElementById('api-status');
    if (el) { el.textContent = '● Sandbox Mode'; el.className = 'badge badge-pending'; }
  }
}

async function loadMpesaTxns(url) {
  const tbody = document.getElementById('mpesaTbody');
  if (!tbody) return;
  tbody.innerHTML = loadingRows(7, 7);

  const params = {
    status:   document.getElementById('statusFilter')?.value || '',
    txn_type: document.getElementById('typeFilter')?.value   || '',
    ordering: '-initiated_at',
  };

  try {
    const data = url
      ? await fetch(url, { headers: { Authorization: `Bearer ${Auth.getToken()}` } }).then(r => r.json())
      : await API.mpesaTxns(params);
    const txns = data?.results || data || [];

    if (txns.length === 0) { tbody.innerHTML = `<tr><td colspan="7">${emptyState('📱','No transactions yet','B2C disbursements and STK Push collections will appear here.')}</td></tr>`; return; }

    tbody.innerHTML = txns.map(t => `<tr>
      <td class="td-mono text-dim">${Fmt.datetime(t.initiated_at)}</td>
      <td><span class="chip ${t.txn_type==='B2C'?'chip-fa':'chip-cc'}">${t.txn_type}</span></td>
      <td class="td-mono">${t.phone}</td>
      <td class="td-mono ${t.txn_type==='B2C'?'text-red':'text-brand'}">${Fmt.currency(t.amount)}</td>
      <td class="td-mono">${t.mpesa_receipt||'—'}</td>
      <td class="td-mono text-dim">${t.loan_id||'—'}</td>
      <td>${Badge.status(t.status)}</td>
    </tr>`).join('');

    renderPagination('mpesaPagination', data, 'loadMpesaTxns');
  } catch (err) {
    console.warn('loadMpesaTxns failed:', err);
  }
}

async function stkPush() {
  const phone  = document.getElementById('stkPhone')?.value?.trim();
  const amount = document.getElementById('stkAmount')?.value;
  const ref    = document.getElementById('stkRef')?.value?.trim();

  if (!phone || !amount) { Toast.error('Phone number and amount are required'); return; }
  const normPhone = normalizePhone(phone);
  if (!normPhone) { Toast.error('Invalid phone number — use 07XX or 2547XX format'); return; }

  setLoading('stkBtn', true);
  try {
    const res = await API.stkPush({ phone: normPhone, amount: parseFloat(amount), loan_id: ref || 'MANUAL' });
    if (res) {
      Toast.success(`STK Push sent to ${normPhone} — awaiting customer PIN entry`);
      document.getElementById('stkPhone').value  = '';
      document.getElementById('stkAmount').value = '';
      setTimeout(() => loadMpesaTxns(), 3000);
    }
  } catch (err) { console.warn(err); }
  finally { setLoading('stkBtn', false); }
}

async function b2cDisburse() {
  const phone  = document.getElementById('b2cPhone')?.value?.trim();
  const amount = document.getElementById('b2cAmount')?.value;
  const ref    = document.getElementById('b2cRef')?.value?.trim();

  if (!phone || !amount) { Toast.error('Phone number and amount are required'); return; }
  if (!ref) { Toast.error('Loan reference is required for B2C'); return; }
  const normPhone = normalizePhone(phone);
  if (!normPhone) { Toast.error('Invalid phone number'); return; }

  if (!await QL.confirm(`Disburse <b>${Fmt.currency(parseFloat(amount))}</b> to <b>${normPhone}</b>?`, {title:'Confirm Disbursement', okLabel:'Disburse'})) return;

  setLoading('b2cBtn', true);
  try {
    // B2C goes through loan disburse endpoint — find loan first
    const loanSearch = await API.loans({ search: ref });
    const loan = loanSearch?.results?.[0];
    if (!loan) { Toast.error(`Loan "${ref}" not found`); setLoading('b2cBtn', false); return; }
    if (loan.status !== 'APPROVED') { Toast.error(`Loan must be APPROVED to disburse (current: ${loan.status})`); setLoading('b2cBtn', false); return; }

    const res = await API.disburseLoan(loan.id, { method: 'MPESA' });
    if (res) {
      Toast.success(`B2C initiated → ${Fmt.currency(parseFloat(amount))} to ${normPhone}`);
      document.getElementById('b2cPhone').value = '';
      document.getElementById('b2cAmount').value = '';
      document.getElementById('b2cRef').value = '';
      setTimeout(() => loadMpesaTxns(), 2000);
    }
  } catch (err) { console.warn(err); }
  finally { setLoading('b2cBtn', false); }
}

function normalizePhone(p) {
  p = p.replace(/\s+/g, '').replace(/^\+/, '');
  if (/^07\d{8}$/.test(p)) return '254' + p.slice(1);
  if (/^2547\d{8}$/.test(p)) return p;
  if (/^01\d{8}$/.test(p)) return '254' + p.slice(1);
  return null;
}

const onSearch = debounce(() => loadMpesaTxns(), 350);


async function loadMpesaKPIs() {
  try {
    const data = await API.mpesaTxns({ page_size: 200, ordering: '-initiated_at' });
    const txns = data?.results || data || [];
    const success = txns.filter(t => t.status === 'SUCCESS').length;
    const failed  = txns.filter(t => t.status === 'FAILED').length;
    const total   = txns.reduce((s, t) => s + parseFloat(t.amount || 0), 0);
    const stk     = txns.filter(t => t.txn_type === 'STK_PUSH').length;

    const kpiEl = document.createElement('div');
    kpiEl.className = 'kpi-grid kpi-grid-4 animate-fadeup';
    kpiEl.classList.add('mb-20');
    kpiEl.innerHTML = `
      <div class="kpi-card kc-green grad"><div class="kpi-label">Successful</div><div class="kpi-value">${success}</div></div>
      <div class="kpi-card kc-red grad"><div class="kpi-label">Failed</div><div class="kpi-value">${failed}</div></div>
      <div class="kpi-card kc-blue grad"><div class="kpi-label">Total Volume</div><div class="kpi-value">${Fmt.currency(total)}</div></div>
      <div class="kpi-card kc-gold grad"><div class="kpi-label">STK Pushes</div><div class="kpi-value">${stk}</div></div>`;
    document.getElementById('pageContent')?.prepend(kpiEl);
  } catch (err) { console.warn(err); }
}
