/**
 * Reference Check Page
 * Cross-branch customer lookup by National ID or Phone number.
 * Must be run BEFORE registering any new customer or approving any loan.
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('reference');
  document.getElementById('refInput').focus();
});

async function runCheck() {
  const q = document.getElementById('refInput').value.trim();
  if (!q || q.length < 4) {
    Toast.error('Enter at least 4 characters — National ID or phone number');
    return;
  }

  const btn    = document.getElementById('refBtn');
  const result = document.getElementById('refResult');
  btn.disabled     = true;
  btn.textContent  = 'Checking…';
  result.innerHTML = renderSearching(q);

  try {
    const data = await API.customerReference(q);
    if (!data) throw new Error('No response');
    renderResult(data, q);
  } catch (err) {
    result.innerHTML = `
      <div class="ref-result-card">
        <div class="ref-result-body text-center p-40">
          <div class="icon-lg">⚠️</div>
          <div class="text-red fw-600">Reference check failed</div>
          <div class="text-dim text-sm mt-6">
            ${err?.data?.detail || 'Backend may be offline. Try again or contact your administrator.'}
          </div>
        </div>
      </div>`;
  } finally {
    btn.disabled    = false;
    btn.textContent = 'Check';
  }
}

function renderSearching(q) {
  return `
    <div class="ref-result-card">
      <div class="ref-result-body text-center p-40">
        <div class="icon-spin">⏳</div>
        <div class="text-dim text-14">Searching all branches for <b class="text-brand mono">${q}</b>…</div>
      </div>
    </div>`;
}

function renderResult(data, q) {
  const result = document.getElementById('refResult');

  // ── NOT FOUND ──────────────────────────────────────────────────────────────
  if (!data.found) {
    result.innerHTML = `
      <div class="ref-result-card border-brand">
        <div class="ref-result-body">
          <div class="flag-info">
            <span>✅</span>
            <div>
              <div>No existing customer found with ID/phone matching <b class="mono">${q}</b></div>
              <div class="fw-400 mt-4">Safe to register as a new customer.</div>
            </div>
          </div>
          <div class="ref-safe-actions text-center mt-16">
            <button class="btn btn-primary"
              onclick="window.location.href='../customers/customers.html'">
              + Register New Customer
            </button>
          </div>
        </div>
      </div>`;
    return;
  }

  // ── FLAGS ──────────────────────────────────────────────────────────────────
  const flagsHtml = (data.flags || []).map(f => {
    const isDanger   = f.startsWith('BLACKLISTED') || f.startsWith('WARNING');
    const isExposure = f.startsWith('ACTIVE EXPOSURE');
    const cls = isDanger ? 'ref-flag-danger' : isExposure ? 'ref-flag-warn' : 'ref-flag-info';
    const icon= isDanger ? '🚫' : isExposure ? '⚠️' : 'ℹ️';
    return `<div class="ref-flag ${cls}"><span>${icon}</span><div>${f}</div></div>`;
  }).join('');

  // ── CUSTOMER CARDS ─────────────────────────────────────────────────────────
  const cardsHtml = data.customers.map(c => {
    const isBlacklisted = c.status === 'BLACKLISTED';
    const loans = c.active_loans || [];
    const totalExposure = c.total_exposure || 0;
    const kycscore = c.kyc_score || 0;

    return `
      <div class="ref-result-card" style="${isBlacklisted ? 'border-color:var(--red)' : ''}">
        <div class="ref-result-header">
          <div class="avatar avatar-lg" style="background:${Auth.avatarColor(c.full_name)};border-radius:10px;font-size:16px">
            ${Auth.initials(c.full_name)}
          </div>
          <div class="flex-1">
            <div class="ref-customer-name">
              ${c.full_name}
            </div>
            <div class="ref-customer-meta">
              <span class="mono text-dim text-sm">${c.uid}</span>
              <span class="mono text-dim text-sm">ID: ${c.national_id}</span>
              <span class="mono text-dim text-sm">📱 ${c.phone}</span>
            </div>
          </div>
          <div class="d-flex flex-col items-end gap-6">
            ${Badge.status(c.status)}
            ${data.count > 1 ? `<span class="badge badge-default text-9">MULTI-PROFILE</span>` : ''}
          </div>
        </div>

        <div class="ref-result-body">
          <!-- KYC completeness bar -->
          <div class="kyc-bar-wrap mb-16">
            <span class="text-sm text-dim text-sm text-dim" >KYC Completeness</span>
            <div class="flex-1">
              <div class="kyc-bar-track">
                <div style="height:100%;border-radius:4px;width:${kycscore}%;
                  background:${kycscore>=80?'var(--brand)':kycscore>=60?'var(--gold)':'var(--red)'}"></div>
              </div>
            </div>
            <span class="kyc-score-label" style="color:${kycscore>=80?'var(--brand)':kycscore>=60?'var(--gold)':'var(--red)'}">
              ${kycscore}%
            </span>
          </div>

          <div class="ref-info-grid">
            <div>
              <div class="form-label">Branch</div>
              <div class="fw-600">${c.branch_name || '—'}</div>
              <div class="text-sm text-dim">${c.region_name || ''}</div>
            </div>
            <div>
              <div class="form-label">Loan Officer</div>
              <div class="fw-600">${c.lo_name || '—'}</div>
            </div>
            <div>
              <div class="form-label">Loan Limit</div>
              <div class="fw-600 text-brand">${Fmt.currency(c.loan_limit)}</div>
            </div>
            <div>
              <div class="form-label">Credit Score</div>
              <div style="font-weight:600;color:${(c.credit_score||0)>=65?'var(--brand)':(c.credit_score||0)>=45?'var(--gold)':'var(--red)'}"
                   title="0=no data, 80+=low risk">
                ${c.credit_score || '—'}
                ${c.credit_score ? ` / 100` : ''}
              </div>
            </div>
          </div>

          <!-- Active loans -->
          ${loans.length ? `
            <div class="form-label mb-8">
              Active Loan Exposure — Total: <span class="text-red fw-700">${Fmt.currency(totalExposure)}</span>
            </div>
            <div class="mb-12">
              ${loans.map(l => `
                <span class="loan-pill">
                  <span class="loan-pill-id">${l.loan_id}</span>
                  <span class="loan-pill-amt">${Fmt.currency(l.balance)}</span>
                  <span class="loan-pill-br">${l.branch}</span>
                  <span class="badge ${l.status==='DEFAULT'?'badge-default':l.status==='ACTIVE'?'badge-active':'badge-approved'} badge-xs">${l.status}</span>
                </span>`).join('')}
            </div>
          ` : `<div class="text-sm text-brand mb-12">✓ No active loan exposure</div>`}

          ${isBlacklisted && c.blacklist_reason ? `
            <div class="flag-danger mb-12">
              <span>🚫</span><div><b>Blacklisted:</b> ${c.blacklist_reason}</div>
            </div>
          ` : ''}

          <!-- Action buttons -->
          <div class="ref-action-bar">
            <button class="btn btn-primary btn-sm"
              onclick="window.location.href='../customers/customers.html'">
              👤 View Full Profile
            </button>
            ${!isBlacklisted && loans.length === 0 ? `
              <button class="btn btn-ghost btn-sm"
                onclick="window.location.href='../loans/loans.html'">
                💰 Create Loan
              </button>` : ''}
            <button class="btn btn-ghost btn-sm"
              onclick="printResult('${c.uid}','${c.full_name}')">
              🖨 Print Result
            </button>
          </div>
        </div>
      </div>`;
  }).join('');

  result.innerHTML = `
    <div class="ref-results-head">
      <div>
        <span class="ref-results-query">Results for </span>
        <span class="mono text-brand text-md">${q}</span>
        <span class="badge ${data.count > 1 ? 'badge-default' : 'badge-active'} ml-8">
          ${data.count} record${data.count !== 1 ? 's' : ''} found
        </span>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="clearResult()">✕ Clear</button>
    </div>
    ${flagsHtml}
    ${cardsHtml}
  `;
}

function clearResult() {
  document.getElementById('refResult').innerHTML = '';
  document.getElementById('refInput').value = '';
  document.getElementById('refInput').focus();
}

function printResult(uid, name) {
  window.print();
}

// Allow pressing Enter in search
document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && document.activeElement.id === 'refInput') {
    runCheck();
  }
});

// Spin animation for loading
const style = document.createElement('style');
style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
document.head.appendChild(style);
