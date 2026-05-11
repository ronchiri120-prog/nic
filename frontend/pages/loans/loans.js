/**
 * Loans Page — v1.0 (Full live CRUD)
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

let _products = [];
let _branches = [];
let _customers = [];

document.addEventListener('DOMContentLoaded', async () => {
  loadSidebar('loans');
  await Promise.all([loadProducts(), loadBranches()]);

  // Handle deep-link URL params
  const params = new URLSearchParams(window.location.search);
  const searchQ    = params.get('search');
  const customerId = params.get('customer');
  const openId     = params.get('open');

  if (searchQ) {
    const inp = document.getElementById('searchInput');
    if (inp) inp.value = searchQ;
  }

  loadLoans();

  // Auto-open new loan modal if customer id provided (from customer profile)
  if (customerId) {
    setTimeout(() => {
      const custSel = document.getElementById('loanCustomer');
      if (custSel) {
        custSel.value = customerId;
        Modal.open('modal-new-loan');
      }
    }, 800);
  }

  // Auto-open loan detail if loan id provided
  if (openId) {
    setTimeout(() => viewLoan(parseInt(openId)), 600);
  }
});

// ─── PRODUCTS & BRANCHES (for modals) ─────────────────
async function loadProducts() {
  try {
    const data = await API.loanProducts();
    _products = data?.results || data || [];
    const sel = document.getElementById('loanProduct');
    if (sel) {
      sel.innerHTML = '<option value="">Select product…</option>' +
        _products.map(p => `<option value="${p.id}" data-rate="${p.interest_rate}" data-tenure="${p.tenure_days}">${p.name}</option>`).join('');
    }
  } catch (err) {
    console.warn('loadProducts failed:', err);
  }
}

async function loadBranches() {
  try {
    const data = await API.branches();
    _branches = data?.results || data || [];
    const sels = document.querySelectorAll('select[name="branch"]');
    sels.forEach(sel => {
      sel.innerHTML = '<option value="">Select branch…</option>' +
        _branches.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
    });
  } catch (err) {
    console.warn('loadBranches failed:', err);
  }
}

// ─── LOAN TABLE ───────────────────────────────────────
async function loadLoans(url) {
  const tbody = document.getElementById('loansTbody');
  if (!tbody) return;
  tbody.innerHTML = loadingRows(10, 10);

  const params = {
    status:  document.getElementById('statusFilter')?.value || '',
    search:  document.getElementById('searchInput')?.value || '',
    ordering:'-created_at',
  };

  try {
    const data = url ? await fetch(url, { headers: { Authorization: `Bearer ${Auth.getToken()}` } }).then(r => r.json())
                     : await API.loans(params);
    const loans = data?.results || [];
    const count = data?.count ?? loans.length;

    document.getElementById('loanCount').textContent = `${count.toLocaleString()} loans`;

    tbody.innerHTML = loans.length
      ? loans.map(loanRow).join('')
      : `<tr><td colspan="10">${emptyState('💰', 'No loans found', 'Adjust filters or disburse a new loan.')}</td></tr>`;

    renderPagination('loansPagination', data, 'loadLoans');

    // KPIs from aggregated data
    if (loans.length) {
      const active  = loans.filter(l => l.status === 'ACTIVE').length;
      const def     = loans.filter(l => l.status === 'DEFAULT').length;
      const pending = loans.filter(l => l.status === 'PENDING').length;
      const totalPrincipal = loans.reduce((s, l) => s + parseFloat(l.principal || 0), 0);
      renderLoanKPIs({ active, def, pending, totalPrincipal, total: count });
    }
  } catch {
    tbody.innerHTML = `<tr><td colspan="10" class="td-error">Failed to load loans. Is the backend running?</td></tr>`;
  }
}

function loanRow(l) {
  const canApprove = Auth.canApprove();
  const isVerificationTeam = Auth.isVerificationTeam();
  return `<tr>
    <td class="td-mono text-brand cursor-pointer" onclick="viewLoan(${l.id})">${l.loan_id}</td>
    <td>
      <div class="d-flex items-center gap-6">
        ${avatarEl(l.customer_name || '?', 'avatar-sm')}
        <div><div class="fw-600 text-base">${l.customer_name||'—'}</div>
          <div class="td-mono text-dim text-xs">${l.branch_name||'—'}</div>
        </div>
      </div>
    </td>
    <td class="td-mono">${Fmt.currency(l.principal)}</td>
    <td class="td-mono">${Fmt.currency(l.total_amount)}</td>
    <td class="td-mono text-brand">${Fmt.currency(l.total_paid)}</td>
    <td class="td-mono" style="color:${parseFloat(l.balance)>0?'var(--gold)':'var(--text3)'}">${Fmt.currency(l.balance)}</td>
    <td>${Badge.loanType(l.product_type || l.product_name?.split(' ')[0] || 'FA')}</td>
    <td class="td-mono text-sm">${Fmt.date(l.due_date)}</td>
    <td>${Badge.status(l.status)}</td>
    <td>
      <div class="d-flex gap-4 flex-wrap">
        <button class="btn btn-ghost btn-sm" onclick="viewLoan(${l.id})">View</button>
        ${l.status==='PENDING' && isVerificationTeam ? `<button class="btn btn-primary btn-sm" onclick="verifyLoan(${l.id},'${l.loan_id}')">✓ Verify</button>` : ''}
        ${l.status==='VERIFIED' && canApprove ? `<button class="btn btn-primary btn-sm" onclick="approveLoan(${l.id},'${l.loan_id}')">✓ Approve</button>` : ''}
        ${l.status==='PENDING' && canApprove ? `<button class="btn btn-danger btn-sm" onclick="rejectLoanAction(${l.id},'${l.loan_id}')">✗ Reject</button>` : ''}
        ${l.status==='APPROVED'&& canApprove ? `<button class="btn btn-gold btn-sm" onclick="disburseLoanModal(${l.id},'${l.loan_id}',${l.principal})">⚡ Disburse</button>` : ''}
        ${l.status==='ACTIVE'              ? `<button class="btn btn-ghost btn-sm" onclick="openPayment('${l.loan_id}')">💳 Pay</button>` : ''}
        ${l.status==='ACTIVE' && canApprove? `<button class="btn btn-gold btn-sm" onclick="openRestructure(${l.id},'${l.loan_id}')">↺</button>` : ''}
        ${l.status==='ACTIVE' && canApprove? `<button class="btn btn-danger btn-sm" onclick="markDefault(${l.id},'${l.loan_id}')">⚠</button>` : ''}
      </div>
    </td>
  </tr>`;
}

function renderLoanKPIs({ active, def, pending, totalPrincipal, total }) {
  const el = document.getElementById('loanKPIs');
  if (!el) return;
  el.innerHTML = `
    <div class="kpi-card kc-blue grad"><div class="kpi-label">Active Loans</div><div class="kpi-value text-22">${active}</div><div class="kpi-delta up">of ${total} total</div></div>
    <div class="kpi-card kc-green grad"><div class="kpi-label">Total Principal</div><div class="kpi-value text-2xl">${Fmt.millions(totalPrincipal)}</div></div>
    <div class="kpi-card kc-gold grad"><div class="kpi-label">Pending Approval</div><div class="kpi-value text-22">${pending}</div></div>
    <div class="kpi-card kc-red grad"><div class="kpi-label">Defaulted</div><div class="kpi-value text-22">${def}</div></div>`;
}

// ─── VIEW LOAN DETAIL ─────────────────────────────────
async function viewLoan(id) {
  try {
    const loan = await API.loan(id);
    if (!loan) return;
    const overlay = document.getElementById('modal-loan-detail');
    if (!overlay) return;
    document.getElementById('detail-loan-id').textContent    = loan.loan_id;
    document.getElementById('detail-customer').textContent   = loan.customer_name;
    document.getElementById('detail-product').textContent    = loan.product_name || '—';
    document.getElementById('detail-product-type').textContent = loan.product_type || '—';
    document.getElementById('detail-principal').textContent  = Fmt.currency(loan.principal);
    document.getElementById('detail-interest').textContent   = Fmt.currency(loan.interest_amount);
    document.getElementById('detail-total').textContent      = Fmt.currency(loan.total_amount);
    document.getElementById('detail-paid').textContent       = Fmt.currency(loan.total_paid);
    document.getElementById('detail-balance').textContent    = Fmt.currency(loan.balance);
    document.getElementById('detail-status').innerHTML       = Badge.status(loan.status);
    document.getElementById('detail-due').textContent        = Fmt.date(loan.due_date);
    document.getElementById('detail-officer').textContent    = loan.lo_name || '—';
    Modal.open('modal-loan-detail');
    // Wire document buttons
    document.getElementById('btn-agreement')?.addEventListener('click',  () => API.loanAgreement(loan.id));
    document.getElementById('btn-disb-letter')?.addEventListener('click',() => API.disbursementLetter(loan.id));
    document.getElementById('btn-schedule')?.addEventListener('click',   () => viewSchedule(loan.id, loan.loan_id));
    if (loan.status === 'DEFAULT' || parseFloat(loan.days_overdue||0) > 0) {
      document.getElementById('btn-demand')?.style && (document.getElementById('btn-demand').style.display = 'inline-flex');
      document.getElementById('btn-demand')?.addEventListener('click', () => API.demandLetter(loan.id));
    }
  } catch { Toast.error('Failed to load loan details'); }
}

// ─── VERIFY LOAN ─────────────────────────────────────
async function verifyLoan(id, loanId) {
  if (!await QL.confirm(`Verify loan <b>${loanId}</b>?`, {title:'Verify Loan', okLabel:'Verify', okClass:'btn-primary'})) return;
  try {
    await API.verifyLoan(id);
    Toast.success(`Loan ${loanId} verified ✓`);
    loadLoans();
  } catch { /* error toast already shown by ApiClient */ }
}

// ─── APPROVE LOAN ─────────────────────────────────────
async function approveLoan(id, loanId) {
  if (!await QL.confirm(`Approve loan <b>${loanId}</b>?`, {title:'Approve Loan', okLabel:'Approve', okClass:'btn-primary'})) return;
  try {
    await API.approveLoan(id);
    Toast.success(`Loan ${loanId} approved ✓`);
    loadLoans();
  } catch { /* error toast already shown by ApiClient */ }
}

// ─── DISBURSE MODAL ───────────────────────────────────
function disburseLoanModal(id, loanId, principal) {
  document.getElementById('disbLoanId').value      = id;
  document.getElementById('disbLoanRef').textContent = loanId;
  document.getElementById('disbAmount').textContent  = Fmt.currency(principal);
  Modal.open('modal-disburse');
}

async function confirmDisburse() {
  const id     = document.getElementById('disbLoanId').value;
  const method = document.getElementById('disbMethod').value;
  setLoading('disbBtn', true);
  try {
    const res = await API.disburseLoan(id, { method });
    Toast.success(`Loan disbursed via ${method} ✓${res?.due_date ? ' · Due: ' + Fmt.date(res.due_date) : ''}`);
    Modal.close('modal-disburse');
    loadLoans();
  } catch (err) { console.warn(err); }
  finally { setLoading('disbBtn', false); }
}

// ─── NEW LOAN MODAL ───────────────────────────────────
function calcLoanPreview() {
  const p = parseFloat(document.getElementById('loanPrincipal')?.value) || 0;
  const r = parseFloat(document.getElementById('loanRate')?.value) || 0;
  const t = calcLoanTotals(p, r);
  document.getElementById('sum-principal').textContent = Fmt.currency(t.principal);
  document.getElementById('sum-interest').textContent  = Fmt.currency(t.interest);
  document.getElementById('sum-total').textContent     = Fmt.currency(t.total);
  const tenure = parseInt(document.getElementById('loanTenure')?.value) || 30;
  const el = document.getElementById('loanDueDate');
  if (el) el.value = addDays(tenure);
}

function onProductChange() {
  const sel = document.getElementById('loanProduct');
  const opt = sel?.selectedOptions[0];
  if (!opt?.value) return;
  
  const productName = opt.text;
  const biasharaWeeksGroup = document.getElementById('biasharaWeeksGroup');
  
  // Show week selector for BIASHARA product
  if (productName.includes('BIASHARA')) {
    biasharaWeeksGroup.style.display = 'block';
    // Set default to 4 weeks
    document.getElementById('biasharaWeeks').value = '4';
    onBiasharaWeekChange();
  } else {
    biasharaWeeksGroup.style.display = 'none';
    document.getElementById('loanRate').value   = opt.dataset.rate   || '';
    document.getElementById('loanTenure').value = opt.dataset.tenure || '';
    calcLoanPreview();
  }
}

function onBiasharaWeekChange() {
  const weeks = parseInt(document.getElementById('biasharaWeeks')?.value) || 4;
  const days = weeks * 7; // Convert weeks to days
  
  // BIASHARA interest calculation: 20% base + 5% per additional week
  const baseRate = 20;
  const additionalWeeks = weeks - 4;
  const interestRate = baseRate + (additionalWeeks * 5);
  
  document.getElementById('loanRate').value = interestRate;
  document.getElementById('loanTenure').value = days;
  calcLoanPreview();
}

async function disburseLoan() {
  const data = formData('newLoanForm');
  if (!data.customer || !data.product || !data.principal) {
    Toast.error('Customer, product, and principal are required'); return;
  }
  setLoading('disburseLoanBtn', true);
  try {
    const loan = await API.createLoan({
      customer:            data.customer,
      product:             data.product,
      principal:           parseFloat(data.principal),
      interest_rate:       parseFloat(data.interest_rate || 0),
      tenure_days:         parseInt(data.tenure_days || 30),
      disbursement_method: data.disbursement_method || 'MPESA',
      application_mode:    'OFFLINE',
    });
    if (loan) {
      Toast.success(`Loan ${loan.loan_id} created — pending approval`);
      Modal.close('modal-new-loan');
      resetForm('newLoanForm');
      loadLoans();
    }
  } catch (err) { console.warn(err); Toast.error(err?.message || 'Failed to create loan'); }
  finally { setLoading('disburseLoanBtn', false); }
}

// ─── PAY SHORTCUT ─────────────────────────────────────
function openPayment(loanId) {
  window.location.href = `../payments/payments.html?loan=${loanId}`;
}

// ─── SEARCH ───────────────────────────────────────────
const onSearch = debounce(() => loadLoans(), 350);

// Payment recording when called from loans page (not payments page)
async function recordPaymentFromLoans() {
  const data = formData('paymentForm');
  if (!data.loan_id || !data.amount) { Toast.error('Loan ID and amount are required'); return; }
  setLoading('recordPayBtn', true);
  try {
    const loanSearch = await API.loans({ search: data.loan_id });
    const loan = loanSearch?.results?.[0];
    if (!loan) { Toast.error(`Loan "${data.loan_id}" not found`); setLoading('recordPayBtn', false); return; }
    const payment = await API.createPayment({
      loan: loan.id, amount: parseFloat(data.amount),
      method: data.method, payment_type: data.payment_type||'PARTIAL', mpesa_ref: data.mpesa_ref||'',
    });
    if (payment) {
      Toast.success(`Payment ${payment.ref} recorded — balance updated`);
      Modal.close('modal-record-payment');
      resetForm('paymentForm');
      loadLoans();
    }
  } catch (err) { console.warn(err); }
  finally { setLoading('recordPayBtn', false); }
}


// ─── LOAN SCHEDULE ────────────────────────────────────────────────────────────
async function viewSchedule(loanId, loanRef) {
  try {
    const data = await API.loanSchedule(loanId);
    if (!data) return;
    const rows = data.schedule || [];
    const today = new Date().toISOString().split('T')[0];
    const html = `
      <div class="panel schedule-wrap">
        <div class="panel-header">
          <div>
            <div class="panel-title">📅 Repayment Schedule — ${loanRef}</div>
            <div class="text-sm text-dim">
              Principal: ${Fmt.currency(data.principal)} · Total: ${Fmt.currency(data.total_amount)} · ${data.tenure_days}d
            </div>
          </div>
        </div>
        <div class="panel-body-bare">
          <table class="data-table">
            <thead><tr>
              <th>#</th><th>Due Date</th><th>Principal</th><th>Interest</th>
              <th>Total Due</th><th>Paid</th><th>Balance</th><th>Status</th>
            </tr></thead>
            <tbody>${rows.map(r => {
              const isPast    = r.due_date < today && r.status === 'PENDING';
              const isCurrent = r.due_date >= today && r.status === 'PENDING';
              return `<tr style="${isPast?'background:rgba(240,96,96,0.05)':isCurrent?'background:rgba(34,211,160,0.05)':''}">
                <td class="mono text-dim">${r.installment}</td>
                <td class="mono ${isPast?'text-red':''}">${Fmt.date(r.due_date)}</td>
                <td class="mono">—</td>
                <td class="mono">—</td>
                <td class="mono">${Fmt.currency(r.amount_due)}</td>
                <td class="mono text-brand">${r.amount_paid > 0 ? Fmt.currency(r.amount_paid) : '—'}</td>
                <td class="mono ${r.balance>0?'text-red':''}">${Fmt.currency(r.balance)}</td>
                <td>${Badge.status(r.status==='PAID'?'CLOSED':r.status==='PENDING'&&r.due_date<today?'DEFAULT':'ACTIVE')}</td>
              </tr>`;
            }).join('')}
            </tbody>
          </table>
        </div>
      </div>`;
    // Show in detail modal body
    const body = document.querySelector('#modal-loan-detail .modal-body');
    if (body) body.innerHTML = html;
  } catch { Toast.error('Could not load schedule'); }
}


// ─── REJECT LOAN ──────────────────────────────────────────────────────────────
async function rejectLoanAction(id, loanId) {
  const reason = await QL.prompt('Enter rejection reason:', '', {title:`Reject ${loanId}`, placeholder:'e.g. Insufficient income'});
  if (!reason?.trim()) return;
  try {
    const r = await API.rejectLoan(id, { reason });
    if (r) {
      Toast.success(`${loanId} rejected`);
      loadLoans();
      Modal.close('modal-loan-detail');
    }
  } catch (err) { console.warn(err); }
}

// ─── MARK DEFAULT ─────────────────────────────────────────────────────────────
async function markDefault(id, loanId) {
  if (!await QL.confirm(`Mark <b>${loanId}</b> as DEFAULT?<br><span class='text-sm text-dim'>This will trigger the penalty engine and collections workflow.</span>`, {title:'Mark as Default', okLabel:'Mark Default', danger:true})) return;
  try {
    const r = await API.defaultLoan(id);
    if (r) {
      Toast.warn(`${loanId} marked as default`);
      loadLoans();
      Modal.close('modal-loan-detail');
    }
  } catch (err) { console.warn(err); }
}

// ─── RESTRUCTURE MODAL ────────────────────────────────────────────────────────
let _restructureId = null;
function openRestructure(id, loanId) {
  _restructureId = id;
  document.getElementById('restr-loan-label').textContent = loanId;
  Modal.open('modal-restructure');
}

async function confirmRestructure() {
  if (!_restructureId) return;
  const action       = document.getElementById('restr-action')?.value;
  const reason       = document.getElementById('restr-reason')?.value?.trim();
  const tenureDays   = parseInt(document.getElementById('restr-tenure')?.value || '0');
  const newRate      = parseFloat(document.getElementById('restr-rate')?.value || '0');
  const writeoffAmt  = parseFloat(document.getElementById('restr-writeoff')?.value || '0');

  if (!reason) { Toast.error('Reason is required'); return; }

  const payload = { action, reason };
  if (action === 'EXTEND_TENURE' && tenureDays) payload.new_tenure_days = tenureDays;
  if (action === 'REDUCE_RATE'   && newRate)    payload.new_rate = newRate;
  if (action === 'WRITE_OFF'     && writeoffAmt)payload.writeoff_amount = writeoffAmt;

  setLoading('confirmRestrBtn', true);
  try {
    const r = await API.restructureLoan(_restructureId, payload);
    if (r) {
      Toast.success(`Loan restructured: ${action}`);
      Modal.close('modal-restructure');
      loadLoans();
    }
  } catch (err) { console.warn(err); } finally { setLoading('confirmRestrBtn', false); }
}

function onRestrActionChange() {
  const v = document.getElementById('restr-action')?.value;
  document.getElementById('restr-tenure-row').style.display  = v === 'EXTEND_TENURE' ? '' : 'none';
  document.getElementById('restr-rate-row').style.display    = v === 'REDUCE_RATE'   ? '' : 'none';
  document.getElementById('restr-writeoff-row').style.display= v === 'WRITE_OFF'    ? '' : 'none';
}

// ─── CREDIT SCORE PREVIEW ─────────────────────────────────────────────────────
async function previewCreditScore(customerId, loanId) {
  try {
    const r = await API.creditScore({ customer_id: customerId });
    if (!r) return;
    const color = r.score >= 65 ? 'var(--brand)' : r.score >= 45 ? 'var(--gold)' : 'var(--red)';
    Toast.success(
      `Credit Score: ${r.score}/100 — Grade ${r.grade}`,
      { duration: 4000 }
    );
    const el = document.getElementById(`score-${loanId}`);
    if (el) {
      el.textContent = `${r.score} ${r.grade}`;
      el.style.color = color;
    }
  } catch (err) { console.warn(err); }
}


// ─── WEEKLY LOAN CALCULATOR ───────────────────────────────────────────────────
function calcWeeklyLoan() {
  const principal = parseFloat(document.getElementById('wkPrincipal')?.value || 0);
  const weeks     = parseInt(document.getElementById('wkWeeks')?.value || 4);
  const rate      = 5.0; // 5% per week = 20% per month

  if (!principal || principal <= 0) return;

  const interest       = principal * (rate / 100) * weeks;
  const total          = principal + interest;
  const weeklyInstall  = total / weeks;

  const preview = document.getElementById('wkPreview');
  if (!preview) return;

  preview.innerHTML = `
    <div class="loan-calc-box">
      <div class="share-preview-head">Weekly Repayment Plan</div>
      <div class="share-preview-row"><span>Principal</span><span class="fw-600">${Fmt.currency(principal)}</span></div>
      <div class="share-preview-row"><span>Interest (${rate}%/wk × ${weeks} wks)</span><span>${Fmt.currency(interest)}</span></div>
      <div class="share-preview-row border-top pt-6 mt-4">
        <span class="fw-700">Total Repayable</span>
        <span class="fw-700 text-brand">${Fmt.currency(total)}</span>
      </div>
      <div class="share-preview-row">
        <span class="fw-700">Weekly Instalment</span>
        <span class="fw-700 text-green">${Fmt.currency(weeklyInstall)}</span>
      </div>
      <div class="text-xs text-dim mt-8">
        ${weeks} weekly payments of ${Fmt.currency(weeklyInstall)} · First payment 7 days after disbursement
      </div>
    </div>`;
}

function toggleWeeklyLoan(checked) {
  const fields = document.getElementById('weeklyFields');
  if (fields) fields.classList.toggle('d-none', !checked);
  // When weekly is selected, lock tenure to match weeks selection
  if (checked) {
    calcWeeklyLoan();
    // Restrict principal to first-time limit
    const principalInput = document.getElementById('wkPrincipal');
    if (principalInput && !principalInput.value) principalInput.focus();
  }
}

// ─── CUSTOMER LIVE SEARCH (new loan modal) ────────────────────────────────────
let _selectedCustomerId = null;

const searchLoanCustomer = debounce(async (q) => {
  const resultEl = document.getElementById('loanCustomerResults');
  if (!resultEl) return;
  if (!q || q.length < 2) { resultEl.innerHTML = ''; return; }

  resultEl.innerHTML = '<div class="text-sm text-dim p-8">Searching…</div>';
  try {
    const data = await API.customers({ search: q, status: 'ACTIVE' });
    const list = data?.results || data || [];
    if (!list.length) {
      resultEl.innerHTML = '<div class="text-sm text-dim p-8">No active customers found. <a href="/pages/leads/leads.html" class="text-brand">Convert a lead first →</a></div>';
      return;
    }
    resultEl.innerHTML = list.slice(0, 6).map(c => `
      <div class="customer-result" onclick="selectLoanCustomer(${c.id},'${c.full_name}','${c.uid}','${c.phone}',${c.loan_limit||0})">
        <div class="member-avatar text-xs" style="background:${Auth.avatarColor(c.full_name)}">
          ${Auth.initials(c.full_name)}
        </div>
        <div class="flex-1">
          <div class="fw-600">${c.full_name}</div>
          <div class="mono-xs text-dim">${c.uid} · ${c.phone} · Limit: ${Fmt.currency(c.loan_limit)}</div>
        </div>
      </div>`).join('');
  } catch {
    resultEl.innerHTML = '<div class="td-error p-8">Search failed</div>';
  }
}, 350);

function selectLoanCustomer(id, name, uid, phone, limit) {
  _selectedCustomerId = id;
  const inp = document.getElementById('loanCustomer');
  const res = document.getElementById('loanCustomerResults');
  const sel = document.getElementById('loanCustomerSelected');

  if (inp) inp.value = name;
  if (res) res.innerHTML = '';
  if (sel) sel.innerHTML = `
    <div class="customer-selected">
      <div>
        <div class="fw-600">${name}</div>
        <div class="mono-xs text-dim">${uid} · ${phone} · Limit: ${Fmt.currency(limit)}</div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="_selectedCustomerId=null;
        document.getElementById('loanCustomer').value='';
        document.getElementById('loanCustomerSelected').innerHTML=''">✕</button>
    </div>`;

  // Update loan limit hint
  const limitHint = document.getElementById('loanLimitHint');
  if (limitHint) limitHint.textContent = `Customer limit: ${Fmt.currency(limit)}`;

  // Fetch full customer details to auto-populate form
  fetchCustomerDetails(id);
}

async function fetchCustomerDetails(customerId) {
  try {
    const data = await API.customer(customerId);
    if (!data) return;

    // Auto-populate customer details
    const phoneInput = document.getElementById('loanPhone');
    const branchInput = document.getElementById('loanBranch');
    if (phoneInput && data.phone) phoneInput.value = data.phone;
    if (branchInput && data.branch) branchInput.value = data.branch;

    // Auto-select default product if set
    if (data.default_product) {
      const productSelect = document.getElementById('loanProduct');
      if (productSelect) {
        productSelect.value = data.default_product;
        onProductChange(); // Trigger product change to update rates
      }
    }
  } catch (err) {
    console.warn('Failed to fetch customer details:', err);
  }
}
