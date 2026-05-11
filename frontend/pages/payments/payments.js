/**
 * Payments Page — v1.0 (Live CRUD)
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('payments');
  // Check URL param for pre-filled loan
  const params = new URLSearchParams(window.location.search);
  const loan = params.get('loan');
  if (loan) {
    const loanInput = document.getElementById('payLoanId');
    if (loanInput) {
      loanInput.value = loan;
    }
    // Wait for modal to be available before opening
    setTimeout(() => {
      const modal = document.getElementById('modal-record-payment');
      if (modal) {
        Modal.open('modal-record-payment');
      }
    }, 100);
  }
  loadPayments();
});

async function loadPayments(url) {
  const tbody = document.getElementById('payTbody');
  if (!tbody) return;
  tbody.innerHTML = loadingRows(8, 8);

  const params = {
    method:  document.getElementById('methodFilter')?.value || '',
    search:  document.getElementById('searchInput')?.value  || '',
    ordering:'-paid_at',
  };

  try {
    const data = url
      ? await fetch(url, { headers: { Authorization: `Bearer ${Auth.getToken()}` } }).then(r => r.json())
      : await API.payments(params);
    const pays = data?.results || [];
    const count = data?.count ?? pays.length;

    document.getElementById('payCount').textContent = `${count.toLocaleString()} payments`;

    // Today's total
    const today = todayISO();
    const todayPays = pays.filter(p => p.paid_at?.startsWith(today));
    const todayTotal = todayPays.reduce((s, p) => s + parseFloat(p.amount || 0), 0);
    const el = document.querySelector('#kpi-today-collected');
    if (el) el.textContent = Fmt.currency(todayTotal);

    tbody.innerHTML = pays.length
      ? pays.map(p => `<tr>
          <td class="td-mono text-brand">${p.ref}</td>
          <td><b>${p.customer_name||'—'}</b></td>
          <td class="td-mono">${p.loan_id||'—'}</td>
          <td class="td-mono text-brand">${Fmt.currency(p.amount)}</td>
          <td><span class="chip ${p.method==='MPESA'?'chip-fa':p.method==='BANK'?'chip-cc':'chip-idc'}">${p.method}</span></td>
          <td class="td-mono text-dim">${p.mpesa_ref||'—'}</td>
          <td class="td-mono text-dim">${Fmt.datetime(p.paid_at)}</td>
          <td>${Badge.status(p.payment_type==='FULL'?'CLOSED':p.payment_type==='PARTIAL'?'ACTIVE':'PENDING')}</td>
          <td>${p.is_reversed
            ? '<span class="badge badge-default">Reversed</span>'
            : (Auth.hasRole('SUPER_ADMIN','BRANCH_MANAGER','HOP','GM')
              ? `<button class="btn btn-ghost btn-sm text-red" onclick="reversePayment(${p.id},'${p.ref}')">↩ Reverse</button>`
              : '')
          }</td>
        </tr>`).join('')
      : `<tr><td colspan="8">${emptyState('💳', 'No payments found', 'Record a payment to get started.')}</td></tr>`;

    renderPagination('payPagination', data, 'loadPayments');
  } catch {
    tbody.innerHTML = `<tr><td colspan="8" class="td-error">Failed to load payments.</td></tr>`;
  }
}

async function recordPayment() {
  const data = formData('paymentForm');
  if (!data.loan_id || !data.amount || !data.method) {
    Toast.error('Loan ID, amount, and method are required'); return;
  }
  // Need to resolve loan_id string to pk — try to look it up
  setLoading('recordPayBtn', true);
  try {
    // Search for the loan by loan_id
    const loanSearch = await API.loans({ search: data.loan_id });
    const loan = loanSearch?.results?.[0];
    if (!loan) { Toast.error(`Loan "${data.loan_id}" not found`); setLoading('recordPayBtn', false); return; }

    const payment = await API.createPayment({
      loan:         loan.id,
      amount:       parseFloat(data.amount),
      method:       data.method,
      payment_type: data.payment_type || 'PARTIAL',
      mpesa_ref:    data.mpesa_ref || '',
      notes:        data.notes || '',
    });
    if (payment) {
      Toast.success(`Payment ${payment.ref} recorded — balance updated`);
      Modal.close('modal-record-payment');
      resetForm('paymentForm');
      loadPayments();
    }
  } catch (err) { console.warn(err); }
  finally { setLoading('recordPayBtn', false); }
}

const onSearch = debounce(() => loadPayments(), 350);


// ─── PRIVILEGED PAYMENT UPLOAD ────────────────────────────────────────────────
async function submitUploadPayment() {
  const fileInput = document.getElementById('up-csv-file') || document.getElementById('uploadFile');
  if (!fileInput?.files?.length) { Toast.error('Select a file to upload'); return; }
  // Determine which tab is active
  const bulkEl = document.getElementById('up-bulk');
  const isBulk = bulkEl?.classList.contains('active');

  setLoading('uploadPayBtn', true);
  try {
    if (isBulk) {
      const file = document.getElementById('up-csv-file')?.files[0];
      if (!file) { Toast.error('Please select a CSV file'); return; }
      const form = new FormData();
      form.append('file', file);
      const resp = await fetch(
        (window.location.port === '3000' ? '' : 'http://localhost:8000') + '/api/v1/payments/bulk-upload/',
        { method: 'POST', headers: { Authorization: `Bearer ${Auth.getToken()}` }, body: form }
      );
      const result = await resp.json();
      Toast[result.errors > 0 ? 'warn' : 'success'](
        `✓ ${result.created} payments uploaded${result.errors > 0 ? `, ${result.errors} errors` : ''}`
      );
      if (result.error_detail?.length) {
        console.warn('Bulk upload errors:', result.error_detail);
      }
      Modal.close('modal-upload-payment');
      loadPayments();
    } else {
      const loanId  = document.getElementById('up-loan-id')?.value.trim();
      const amount  = document.getElementById('up-amount')?.value;
      const method  = document.getElementById('up-method')?.value;
      const date    = document.getElementById('up-date')?.value || null;
      const mpesaRef= document.getElementById('up-mpesa-ref')?.value.trim();
      const notes   = document.getElementById('up-notes')?.value.trim();

      if (!loanId || !amount) { Toast.error('Loan ID and amount are required'); return; }

      const r = await API.uploadPayment({
        loan_id: loanId, amount: parseFloat(amount),
        method, date, mpesa_ref: mpesaRef, notes,
      });
      if (r) {
        Toast.success(`✓ ${r.payment_ref} posted to ${r.loan_id} — Balance: ${Fmt.currency(r.new_balance)}`);
        Modal.close('modal-upload-payment');
        // Reset form
        ['up-loan-id','up-amount','up-mpesa-ref','up-notes'].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.value = '';
        });
        loadPayments();
      }
    }
  } catch (err) {
    Toast.error(err?.data?.detail || 'Upload failed');
  } finally {
    setLoading('uploadPayBtn', false);
  }
}


// ─── PAYMENT REVERSAL ────────────────────────────────────────────────────────
async function reversePayment(id, ref) {
  const reason = await QL.prompt(`Reason for reversing payment <b>${ref}</b>:`, '', {title:'Reverse Payment', placeholder:'e.g. Incorrect amount, duplicate'});
  if (!reason || !reason.trim()) return;
  try {
    const r = await API.reversePayment(id, { reason: reason.trim() });
    if (r) {
      Toast.success(`✓ ${r.detail}`);
      loadPayments();
    }
  } catch (err) {
    Toast.error(err?.data?.detail || 'Reversal failed');
  }
}
