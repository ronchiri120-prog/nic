Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}
Auth.requireRole(['SUPER_ADMIN','BRANCH_MANAGER','RM','OPERATIONS','IDC','LOAN_OFFICER','PAYMENT_OFFICER']);

document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('notifications');
  document.getElementById('topbarActions').innerHTML += `
    <button class="btn btn-ghost" onclick="Modal.open('modal-send-sms')">📱 Send SMS</button>
  `;
  renderLayout();
  loadStats();
  loadSMSLogs();
});

function renderLayout() {
  document.getElementById('pageContent').innerHTML = `
    <div class="section-header animate-fadeup"><div>
      <h1 class="page-heading">🔔 Notifications</h1>
      <p class="text-sm text-dim">SMS delivery logs · Email history · Send manual messages</p>
    </div></div>

    <!-- Stats bar -->
    <div class="kpi-grid animate-fadeup stagger-1 kpi-grid kpi-grid-4 animate-fadeup" id="notif-stats">
      <div class="kpi-card kc-green grad"><div class="kpi-label">SMS Sent (7d)</div><div class="kpi-value" id="stat-sent">—</div></div>
      <div class="kpi-card kc-red grad"><div class="kpi-label">SMS Failed</div><div class="kpi-value" id="stat-failed">—</div></div>
      <div class="kpi-card kc-blue grad"><div class="kpi-label">Today</div><div class="kpi-value" id="stat-today">—</div></div>
      <div class="kpi-card kc-gold grad"><div class="kpi-label">Email Sent (7d)</div><div class="kpi-value" id="stat-email">—</div></div>
    </div>

    <div class="tabs animate-fadeup stagger-2">
      <button class="tab-btn active" onclick="switchTab(this,'tab-sms');loadSMSLogs()">SMS Log</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-email');loadEmailLogs()">Email Log</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-send')">Manual Send</button>
    </div>

    <!-- SMS Log -->
    <div id="tab-sms" class="tab-content active">
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">📱 SMS Delivery Log</div>
          <div class="d-flex gap-8">
            <select class="form-control filter-ctrl-md" id="smsStatusFilter" onchange="loadSMSLogs()">
              <option value="">All Status</option>
              <option value="SENT">Sent</option>
              <option value="FAILED">Failed</option>
              <option value="PENDING">Pending</option>
            </select>
            <select class="form-control filter-ctrl-xl" id="smsTemplateFilter" onchange="loadSMSLogs()">
              <option value="">All Templates</option>
              <option value="DISBURSEMENT">Disbursement</option>
              <option value="PAYMENT_CONFIRM">Payment</option>
              <option value="PAYMENT_REMINDER">Reminder</option>
              <option value="OVERDUE_1">Overdue</option>
              <option value="APPROVAL">Approval</option>
              <option value="REJECTION">Rejection</option>
              <option value="CUSTOM">Custom</option>
            </select>
          </div>
        </div>
        <div class="panel-body-bare">
          <table class="data-table">
            <thead><tr>
              <th>Time</th><th>Recipient</th><th>Customer</th><th>Template</th>
              <th>Message Preview</th><th>Status</th><th>Cost</th><th>Action</th>
            </tr></thead>
            <tbody id="smsTbody"></tbody>
          </table>
          <div id="smsPagination"></div>
        </div>
      </div>
    </div>

    <!-- Email Log -->
    <div id="tab-email" class="tab-content">
      <div class="panel">
        <div class="panel-header"><div class="panel-title">📧 Email Delivery Log</div></div>
        <div class="panel-body-bare">
          <table class="data-table">
            <thead><tr><th>Time</th><th>Recipient</th><th>Subject</th><th>Status</th></tr></thead>
            <tbody id="emailTbody"></tbody>
          </table>
          <div id="emailPagination"></div>
        </div>
      </div>
    </div>

    <!-- Manual Send -->
    <div id="tab-send" class="tab-content">
      <div class="notif-send-grid">
        <div class="panel">
          <div class="panel-header"><div class="panel-title">📱 Send SMS</div></div>
          <div class="panel-body">
            <div class="form-group"><label class="form-label">Phone Number *</label>
              <input class="form-control" id="manualPhone" placeholder="07XX XXX XXX"></div>
            <div class="form-group"><label class="form-label">Loan Reference (optional)</label>
              <input class="form-control" id="manualLoanId" placeholder="QL-L0001"></div>
            <div class="form-group"><label class="form-label">Message *</label>
              <textarea class="form-control" id="manualMsg" rows="4"
                placeholder="Type your message…" oninput="document.getElementById('sms-char-count').textContent=this.value.length+' chars'"></textarea>
              <div class="sms-char-counter" id="sms-char-count">0 chars</div>
            </div>
            <button class="btn btn-primary" id="sendSMSBtn" onclick="sendManualSMS()">
              <span class="btn-label">📱 Send SMS</span><span class="btn-spinner"></span>
            </button>
          </div>
        </div>
        <div class="panel">
          <div class="panel-header"><div class="panel-title">📊 Delivery Summary</div></div>
          <div class="panel-body">
            <div class="text-sm text-dim mb-16">
              Africa's Talking integration status
            </div>
            <div id="at-status"></div>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function loadStats() {
  try {
    const s = await API.notifStats();
    if (!s) return;
    const sent   = (s.sms?.SENT || 0) + (s.sms?.DELIVERED || 0);
    const failed = s.failed_sms_total || 0;
    const today  = s.sms_total_today  || 0;
    const email  = (s.email?.SENT     || 0);
    ['stat-sent','stat-failed','stat-today','stat-email'].forEach((id, i) => {
      const el = document.getElementById(id);
      if (el) el.textContent = Fmt.number([sent, failed, today, email][i]);
    });
    // AT status
    const atEl = document.getElementById('at-status');
    if (atEl) atEl.innerHTML = `
      <div class="info-row"><span class="info-key">Mode</span>
        <span class="info-val">${sent > 0 && !window.location.hostname.includes('localhost') ? 'Live (Africa\'s Talking)' : 'Dev mode (console)'}</span></div>
      <div class="info-row"><span class="info-key">Sent (7d)</span><span class="info-val text-brand">${sent}</span></div>
      <div class="info-row"><span class="info-key">Failed</span><span class="info-val ${failed>0?'text-red':''}">${failed}</span></div>
      <div class="info-row"><span class="info-key">Today</span><span class="info-val">${today}</span></div>`;
  } catch (err) { console.warn(err); }
}

async function loadSMSLogs(url) {
  const tbody = document.getElementById('smsTbody');
  if (!tbody) return;
  tbody.innerHTML = loadingRows(8, 4);
  const params = {
    status:   document.getElementById('smsStatusFilter')?.value   || '',
    template: document.getElementById('smsTemplateFilter')?.value || '',
    search:   document.getElementById('searchInput')?.value       || '',
  };
  try {
    const data = url
      ? await fetch(url, { headers: { Authorization: `Bearer ${Auth.getToken()}` } }).then(r => r.json())
      : await API.smsLogs(params);
    const logs = data?.results || [];
    tbody.innerHTML = logs.length ? logs.map(s => `<tr>
      <td class="td-mono text-dim">${Fmt.datetime(s.created_at)}</td>
      <td class="td-mono">${s.recipient}</td>
      <td>${s.customer_name || '—'}</td>
      <td><span class="chip chip-fa text-9">${s.template}</span></td>
      <td class="sms-preview"
          title="${s.message}">${s.message?.substring(0, 60)}…</td>
      <td>
        <span class="badge ${s.status==='SENT'||s.status==='DELIVERED'?'badge-active':s.status==='FAILED'?'badge-default':'badge-pending'}">
          ${s.status}
        </span>
      </td>
      <td class="td-mono text-dim">${s.at_cost || '—'}</td>
      <td>${s.status === 'FAILED'
        ? `<button class="btn btn-ghost btn-sm" onclick="retrySMS(${s.id})">Retry</button>`
        : ''}
      </td>
    </tr>`).join('') : `<tr><td colspan="8">${emptyState('📱', 'No SMS logs', 'SMS messages will appear here after being sent.')}</td></tr>`;
    renderPagination('smsPagination', data, 'loadSMSLogs');
  } catch { tbody.innerHTML = `<tr><td colspan="8" class="td-error">Failed to load</td></tr>`; }
}

async function loadEmailLogs(url) {
  const tbody = document.getElementById('emailTbody');
  if (!tbody) return;
  tbody.innerHTML = loadingRows(4, 3);
  try {
    const data = url
      ? await fetch(url, { headers: { Authorization: `Bearer ${Auth.getToken()}` } }).then(r => r.json())
      : await API.emailLogs();
    const logs = data?.results || [];
    tbody.innerHTML = logs.length ? logs.map(e => `<tr>
      <td class="td-mono text-dim">${Fmt.datetime(e.created_at)}</td>
      <td class="td-mono">${e.recipient}</td>
      <td class="text-sm">${e.subject}</td>
      <td><span class="badge ${e.status==='SENT'?'badge-active':'badge-default'}">${e.status}</span></td>
    </tr>`).join('') : `<tr><td colspan="4">${emptyState('📧', 'No email logs')}</td></tr>`;
    renderPagination('emailPagination', data, 'loadEmailLogs');
  } catch { tbody.innerHTML = `<tr><td colspan="4" class="td-error">Failed to load</td></tr>`; }
}

async function sendManualSMS() {
  const phone   = document.getElementById('manualPhone')?.value.trim();
  const message = document.getElementById('manualMsg')?.value.trim();
  const loanId  = document.getElementById('manualLoanId')?.value.trim();
  if (!phone || !message) { Toast.error('Phone and message are required'); return; }
  setLoading('sendSMSBtn', true);
  try {
    const r = await API.sendSMS({ phone, message, loan_id: loanId || undefined });
    if (r?.success) {
      Toast.success(`SMS sent to ${phone} ✓${r.dev_mode ? ' (dev mode)' : ''}`);
      document.getElementById('manualMsg').value   = '';
      document.getElementById('manualPhone').value = '';
      document.getElementById('sms-char-count').textContent = '0 chars';
      loadSMSLogs();
      loadStats();
    } else {
      Toast.error(`SMS failed: ${r?.error || 'unknown error'}`);
    }
  } catch (err) { console.warn(err); } finally { setLoading('sendSMSBtn', false); }
}

async function retrySMS(id) {
  try {
    const r = await Api.post(`/notifications/sms/${id}/retry/`);
    Toast[r?.success ? 'success' : 'error'](r?.success ? 'SMS retried successfully' : `Retry failed: ${r?.error}`);
    loadSMSLogs();
  } catch (err) { console.warn(err); }
}

const onSearch = debounce(() => loadSMSLogs(), 350);
