Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

let _selectedLoans = new Set();

document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('collections');
  document.getElementById('topbarActions').innerHTML = `
    <select class="filter-ctrl-lg" id="branchFilter" onchange="loadCollections()">
      <option value="">All Branches</option>
    </select>
    <select class="filter-ctrl-md" id="ageFilter" onchange="loadCollections()">
      <option value="">All Ages</option>
      <option value="1">1–30 days</option>
      <option value="31">31–60 days</option>
      <option value="61">61–90 days</option>
      <option value="90">90+ days</option>
    </select>
    <button class="btn btn-ghost" id="bulkSMSBtn" onclick="doBulkSMS()" class="d-none">📱 SMS Selected</button>
    <button class="btn btn-ghost" id="bulkCallBtn" onclick="doBulkSTK()" class="d-none">📲 STK Selected</button>
    <button class="btn btn-ghost" onclick="API.excelCollections()">⬇ Excel</button>
  `;
  loadBranchOptions();
  loadCollections();
});

async function loadBranchOptions() {
  try {
    const data = await API.branches();
    const sel  = document.getElementById('branchFilter');
    if (!sel) return;
    (data?.results || data || []).forEach(b => {
      sel.innerHTML += `<option value="${b.id}">${b.name}</option>`;
    });
  } catch (err) { console.warn(err); }
}

async function loadCollections() {
  const tbody = document.getElementById('collTbody');
  if (!tbody) return;
  _selectedLoans.clear();
  updateBulkButtons();
  tbody.innerHTML = loadingRows(11, 9);

  try {
    const d = await API.reportDefaulters();
    const loans = (d?.loans || []).filter(l => {
      const age = document.getElementById('ageFilter')?.value;
      const days = l.days_overdue || 0;
      if (!age) return true;
      if (age === '1')  return days >= 1  && days <= 30;
      if (age === '31') return days >= 31 && days <= 60;
      if (age === '61') return days >= 61 && days <= 90;
      if (age === '90') return days > 90;
      return true;
    });

    document.getElementById('collCount').textContent = `${loans.length} accounts`;
    const atRisk = document.getElementById('kpi-coll-at-risk');
    if (atRisk) atRisk.textContent = Fmt.millions(d?.total_at_risk || 0);

    tbody.innerHTML = loans.length ? loans.map(l => `<tr id="row-${l.id}">
      <td>
        <input type="checkbox" class="coll-checkbox" data-id="${l.id}"
          data-phone="${l.customer_phone||''}" data-loan="${l.loan_id}"
          data-balance="${l.balance}"
          onchange="toggleSelect(${l.id}, this)">
      </td>
      <td class="td-mono text-brand">${l.loan_id}</td>
      <td><b>${l.customer_name}</b></td>
      <td class="td-mono">${l.customer_phone || '—'}</td>
      <td class="td-mono text-red">${Fmt.currency(l.balance)}</td>
      <td class="td-mono days-od-${getDayClass(l.days_overdue||0)}">${l.days_overdue||0}d</td>
      <td class="td-mono text-dim">${l.due_date ? Fmt.date(l.due_date) : '—'}</td>
      <td>${l.lo_name || '—'}</td>
      <td>${Badge.status(l.status)}</td>
      <td>
        <div class="coll-actions">
          <button class="btn btn-ghost btn-sm" title="Log call"
            onclick="logCall('${l.loan_id}','${l.customer_name}')">📞</button>
          <button class="btn btn-primary btn-sm" title="STK Push"
            onclick="stkPush('${l.loan_id}','${l.customer_phone||''}',${l.balance})">📲</button>
          <button class="btn btn-gold btn-sm" title="Restructure"
            onclick="restructure('${l.id}','${l.loan_id}')">↺</button>
          <button class="btn btn-ghost btn-sm" title="Demand letter"
            onclick="API.demandLetter(${l.id})">📄</button>
        </div>
      </td>
    </tr>`).join('')
    : `<tr><td colspan="10">${emptyState('✓', 'No overdue loans', 'All accounts performing!')}</td></tr>`;

    // Header checkbox for select-all
    const thead = tbody.closest('table')?.querySelector('thead tr');
    if (thead && !thead.querySelector('.select-all-chk')) {
      thead.prepend(Object.assign(document.createElement('th'), {innerHTML:
        '<input type="checkbox" class="select-all-chk" onchange="toggleAll(this)">'
      }));
    }
  } catch (err) {
    console.warn('loadCollections failed:', err);
  }
}

function getDayClass(days) {
  if (days > 30) return 'high';
  if (days > 14) return 'mid';
  return 'low';
}

function toggleSelect(id, cb) {
  if (cb.checked) _selectedLoans.add(id);
  else _selectedLoans.delete(id);
  updateBulkButtons();
}

function toggleAll(masterCb) {
  document.querySelectorAll('.coll-checkbox').forEach(cb => {
    cb.checked = masterCb.checked;
    const id = parseInt(cb.dataset.id);
    if (masterCb.checked) _selectedLoans.add(id);
    else _selectedLoans.delete(id);
  });
  updateBulkButtons();
}

function updateBulkButtons() {
  const n = _selectedLoans.size;
  const smsBtn  = document.getElementById('bulkSMSBtn');
  const callBtn = document.getElementById('bulkCallBtn');
  if (smsBtn)  { smsBtn.style.display  = n > 0 ? '' : 'none'; smsBtn.textContent  = `📱 SMS (${n})`; }
  if (callBtn) { callBtn.style.display = n > 0 ? '' : 'none'; callBtn.textContent = `📲 STK (${n})`; }
}

async function stkPush(loanId, phone, balance) {
  if (!phone) { Toast.error('No phone number'); return; }
  if (!await QL.confirm(`Send STK Push to <b>${phone}</b><br>Loan: <b>${loanId}</b> · Amount: <b>${Fmt.currency(balance)}</b>`, {title:'Confirm STK Push', okLabel:'Send STK'})) return;
  try {
    await API.stkPush({ phone, amount: Math.ceil(balance), loan_id: loanId });
    Toast.success(`STK Push sent to ${phone}`);
  } catch (err) { console.warn(err); }
}

async function doBulkSTK() {
  const btn = document.getElementById('bulkCallBtn');
  if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }
  if (!_selectedLoans.size) return;
  const checkboxes = document.querySelectorAll('.coll-checkbox:checked');
  let sent = 0;
  for (const cb of checkboxes) {
    if (!cb.dataset.phone) continue;
    try {
      await API.stkPush({
        phone: cb.dataset.phone,
        amount: Math.ceil(parseFloat(cb.dataset.balance)),
        loan_id: cb.dataset.loan
      });
      sent++;
    } catch (err) { console.warn(err); }
  }
  Toast.success(`STK Push sent to ${sent}/${_selectedLoans.size} accounts`);
}

async function doBulkSMS() {
  if (!_selectedLoans.size) { Toast.error('Select at least one account first'); return; }
  if (!await QL.confirm(
    `Send SMS reminders to <b>${_selectedLoans.size}</b> selected accounts?`,
    {title:'Bulk SMS', okLabel:'Send SMS'}
  )) return;
  const btn = document.getElementById('bulkSMSBtn');
  if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }
  let sent = 0, failed = 0;
  for (const loanId of _selectedLoans) {
    try {
      await API.sendSMS({ loan_id: loanId, type: 'PAYMENT_REMINDER' });
      sent++;
    } catch { failed++; }
  }
  if (btn) { btn.disabled = false; btn.textContent = '📩 Bulk SMS'; }
  if (sent > 0)    Toast.success(`✓ ${sent} SMS reminder${sent>1?'s':''} sent`);
  if (failed > 0)  Toast.error(`${failed} failed to send`);
  _selectedLoans.clear();
  updateBulkButtons();
}

async function logCall(loanId, name) {
  const note = await QL.prompt(
    `Log call outcome for <b>${name}</b> (${loanId}):`,
    '', { title: 'Log Call', placeholder: 'e.g. Customer promised to pay Friday' }
  );
  if (!note) return;
  // Post a CRM note via notifications SMS log endpoint
  try {
    await API.sendSMS({ phone: '', message: `[CALL NOTE] ${loanId}: ${note}`, note_only: true });
  } catch {}
  Toast.success(`📞 Call logged — ${name}: "${note.slice(0, 40)}…"`);
}

async function restructure(id, loanId) {
  const action = await QL.prompt(
    `<b>${loanId}</b> — Choose restructure action:<br>
     <span class="text-sm text-dim">1 = Extend tenure &nbsp;|&nbsp; 2 = Reduce rate &nbsp;|&nbsp; 3 = Write-off</span>`,
    '', { title: 'Restructure Loan', placeholder: 'Enter 1, 2 or 3' }
  );
  if (!action) return;
  const map = { '1': 'EXTEND_TENURE', '2': 'REDUCE_RATE', '3': 'WRITE_OFF' };
  const actionCode = map[action.trim()];
  if (!actionCode) { Toast.error('Invalid — enter 1, 2 or 3'); return; }

  const reason = await QL.prompt('Reason for restructuring:', '', {
    title: 'Restructure Reason', placeholder: 'e.g. Customer facing hardship'
  }) || '';

  let extra = {};
  if (actionCode === 'EXTEND_TENURE') {
    const days = await QL.prompt('New tenure (days):', '60', { title: 'New Tenure', type: 'number' });
    extra.new_tenure_days = parseInt(days || '60');
  }
  if (actionCode === 'REDUCE_RATE') {
    const rate = await QL.prompt('New interest rate (%):', '10', { title: 'New Rate', type: 'number' });
    extra.new_rate = parseFloat(rate || '10');
  }
  if (actionCode === 'WRITE_OFF') {
    const amt = await QL.prompt('Write-off amount (KES):', '0', { title: 'Write-off Amount', type: 'number' });
    extra.writeoff_amount = parseFloat(amt || '0');
  }

  try {
    const r = await API.restructureLoan(id, { action: actionCode, reason, ...extra });
    if (r) { Toast.success(`✓ ${loanId} restructured`); loadCollections(); }
  } catch (err) {
    Toast.error(err?.data?.detail || 'Restructure failed');
  }
}

const onSearch = debounce(() => loadCollections(), 350);
