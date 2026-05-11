/**
 * Customers — Full KYC registration, cross-branch reference, profile viewer
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

let _allBranches = [];
let _allOfficers = [];

document.addEventListener('DOMContentLoaded', async () => {
  loadSidebar('customers');

  // Handle ?open=<id> from lead conversion redirect
  const params = new URLSearchParams(window.location.search);
  const openId = params.get('open');
  const openUid = params.get('uid');
  document.getElementById('topbarActions').innerHTML = `
    <div class="topbar-search">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search name, ID, phone…" oninput="onSearch(this)">
    </div>
    <select class="form-control filter-150" id="branchFilter" onchange="loadCustomers()">
      <option value="">All Branches</option>
    </select>
    <select class="form-control filter-110" id="statusFilter" onchange="loadCustomers()">
      <option value="">All Status</option>
      <option value="ACTIVE">Active</option>
      <option value="DORMANT">Dormant</option>
      <option value="BLACKLISTED">Blacklisted</option>
    </select>
    <button class="btn btn-ghost" onclick="window.location.href='/pages/reference/reference.html'">🔎 Ref Check</button>
    <button class="btn btn-ghost" onclick="API.exportCustomers()">⬇ Export</button>
    <button class="btn btn-primary" onclick="window.location.href='/pages/leads/leads.html'"
      title="Customers must be converted from Leads">🎯 + New Lead</button>
  `;
  await Promise.all([loadBranchOptions(), loadOfficerOptions()]);
  loadCustomers();

  // Auto-open customer profile if redirected from leads
  if (openId || openUid) {
    setTimeout(async () => {
      if (openId) {
        viewCustomer(parseInt(openId));
      } else if (openUid) {
        try {
          const d = await API.customers({ search: openUid });
          const c = (d?.results || d || [])[0];
          if (c) viewCustomer(c.id);
        } catch {}
      }
    }, 600);
  }
});

async function loadBranchOptions() {
  try {
    const d = await API.branches();
    _allBranches = d?.results || d || [];
    const sel = document.getElementById('custBranchSel');
    if (sel) {
      sel.innerHTML = '<option value="">Select branch…</option>' +
        _allBranches.map(b => `<option value="${b.id}">${b.name}${b.submarket ? ' — ' + b.submarket : ''}</option>`).join('');
    }
    // Also populate filter
    const filt = document.getElementById('branchFilter');
    if (filt) {
      filt.innerHTML = '<option value="">All Branches</option>' +
        _allBranches.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
    }
  } catch (err) {
    console.warn('loadBranchOptions failed:', err);
  }
}

async function loadOfficerOptions(branchId = null) {
  try {
    const params = branchId ? { branch: branchId, role: 'LOAN_OFFICER' } : { role: 'LOAN_OFFICER' };
    const d = await API.users(params);
    _allOfficers = d?.results || d || [];
    const sel = document.getElementById('custLOSel');
    if (sel) {
      sel.innerHTML = _allOfficers.length
        ? '<option value="">Select officer…</option>' + _allOfficers.map(u => `<option value="${u.id}">${u.full_name}</option>`).join('')
        : '<option value="">No officers in this branch</option>';
    }
  } catch (err) {
    console.warn('loadOfficerOptions failed:', err);
  }
}

async function loadOfficersForBranch(branchId) {
  if (!branchId) return;
  await loadOfficerOptions(branchId);
}

async function loadCustomers(url) {
  const tbody = document.getElementById('custTbody');
  if (!tbody) return;
  tbody.innerHTML = loadingRows(8, 9);

  const params = {
    status: document.getElementById('statusFilter')?.value || '',
    branch: document.getElementById('branchFilter')?.value || '',
    search: document.getElementById('searchInput')?.value  || '',
    ordering: '-created_at',
  };

  try {
    const data = url
      ? await fetch(url, { headers: { Authorization: `Bearer ${Auth.getToken()}` } }).then(r => r.json())
      : await API.customers(params);

    const custs = data?.results || [];
    const count = data?.count ?? custs.length;

    document.getElementById('custCount').textContent = `${count.toLocaleString()} customers`;

    // KPI cards
    const active  = custs.filter(c => c.status === 'ACTIVE').length;
    const dormant = custs.filter(c => c.status === 'DORMANT').length;
    const blk     = custs.filter(c => c.status === 'BLACKLISTED').length;
    document.getElementById('custKPIs').innerHTML = `
      <div class="kpi-card kc-green grad"><div class="kpi-label">Total</div><div class="kpi-value text-22">${count.toLocaleString()}</div></div>
      <div class="kpi-card kc-blue grad"><div class="kpi-label">Active</div><div class="kpi-value text-22">${active}</div></div>
      <div class="kpi-card kc-gold grad"><div class="kpi-label">Dormant</div><div class="kpi-value text-22">${dormant}</div></div>
      <div class="kpi-card kc-red grad"><div class="kpi-label">Blacklisted</div><div class="kpi-value text-22">${blk}</div></div>`;

    tbody.innerHTML = custs.length
      ? custs.map(c => {
          const kyc = c.kyc_score || 0;
          const photoUrl = c.photo || null;
          const idFrontUrl = c.id_front || null;
          return `<tr>
            <td class="td-mono text-dim">${c.uid}</td>
            <td>
              <div class="cust-name-cell">
                ${photoUrl 
                  ? `<img src="${photoUrl}" class="avatar-sm" alt="${c.full_name}" onclick="viewImage('${photoUrl}')" style="cursor:pointer" title="Click to view photo">`
                  : avatarEl(c.full_name || `${c.first_name} ${c.last_name}`, 'avatar-sm')
                }
                <div>
                  <div class="fw-600">${c.full_name || `${c.first_name} ${c.last_name}`}</div>
                  <div class="td-mono text-dim text-xs">${c.phone || ''}</div>
                </div>
              </div>
            </td>
            <td class="td-mono">${c.national_id}</td>
            <td class="td-mono">${c.phone || '—'}</td>
            <td>${c.branch_name || '—'}</td>
            <td class="td-mono">${Fmt.currency(c.loan_limit)}</td>
            <td>${tierBadge(c.tier)}</td>
            <td>${Badge.status(c.status)}</td>
            <td>
              <div class="d-flex gap-4">
                <button class="btn btn-ghost" onclick="viewCustomer(${c.id})">View</button>
                ${idFrontUrl ? `<button class="btn btn-ghost" onclick="viewImage('${idFrontUrl}')" title="View ID">🆔</button>` : ''}
                ${c.status !== 'BLACKLISTED' ? `<button class="btn btn-primary" onclick="newLoanFor(${c.id})">Loan</button>` : ''}
              </div>
            </td>
          </tr>`;
        }).join('')
      : `<tr><td colspan="9">${emptyState('👥', 'No customers found', 'Register a new customer — run Reference Check first.')}</td></tr>`;

    renderPagination('custPagination', data, 'loadCustomers');
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="9" class="td-error">
      Failed to load customers — ${e?.message || 'check backend connection'}
    </td></tr>`;
  }
}

let currentCustomerId = null;
let _currentCustomerData = null;

// Make phone/ID numbers clickable links
function phoneLink(p) {
  if (!p) return '—';
  return `<a href="tel:${p}" class="mono text-blue">${p}</a>`;
}
function idLink(id, custId) {
  if (!id) return '—';
  return `<span class="mono text-brand cursor-pointer" onclick="Modal.close('modal-customer-detail');setTimeout(()=>viewCustomer(${custId}),200)">${id}</span>`;
}

function viewImage(url) {
  if (!url) return;
  // Create a simple modal to view the image
  const modal = document.createElement('div');
  modal.className = 'modal-overlay open';
  modal.innerHTML = `
    <div class="modal modal-lg">
      <div class="modal-header">
        <div class="modal-title">📷 Image View</div>
        <div class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</div>
      </div>
      <div class="modal-body" style="text-align:center">
        <img src="${url}" style="max-width:100%; max-height:500px; object-fit:contain;" alt="Customer document">
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">Close</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });
}

async function viewCustomer(id) {
  currentCustomerId = id;
  const panel = document.getElementById('customerDetailPanel');
  if (!panel) return;
  panel.innerHTML = '<div class="p-32-center">Loading profile…</div>';
  Modal.open('modal-customer-detail');

  try {
    const [cust, loans] = await Promise.all([API.customer(id), API.customerLoans(id)]);
    if (!cust) { panel.innerHTML = '<div class="td-error">Failed to load customer</div>'; return; }
    _currentCustomerData = cust;

    const kyc      = calcKYCScore(cust);
    const activeLoan = (loans||[]).find(l => l.status === 'ACTIVE');
    const canEdit = Auth.canEditCustomer();
    const hasActiveLoan = !!activeLoan;

    // Update modal footer buttons
    const newLoanBtn = document.getElementById('detailNewLoanBtn');
    if (newLoanBtn) {
      newLoanBtn.textContent = '💰 New Loan';
      newLoanBtn.onclick = () => newLoanFor(id);
    }

    panel.innerHTML = `
      <!-- ── Header ─────────────────────────────────────────────── -->
      <div class="cust-profile-header">
        ${avatarEl(cust.full_name || cust.first_name, 'avatar-lg')}
        <div class="flex-1">
          <div class="font-serif text-2xl fw-700">
            <a href="/pages/customers/customers.html?open=${cust.id}" class="text-brand link-no-underline">${cust.full_name}</a>
          </div>
          <div class="d-flex gap-12 flex-wrap mt-4 text-sm text-dim">
            <span class="mono">${cust.uid}</span>
            <span>ID: <a class="mono text-blue" onclick="navigator.clipboard?.writeText('${cust.national_id}')" title="Copy">${cust.national_id}</a></span>
            <a href="tel:${cust.phone}" class="mono text-blue">${cust.phone}</a>
          </div>
          <div class="d-flex items-center gap-8 mt-6">
            ${Badge.status(cust.status)}
            ${tierBadge(cust.tier)}
            ${cust.credit_score ? `<span class="mono text-sm text-brand">Score: ${cust.credit_score}/100</span>` : ''}
          </div>
        </div>
        <!-- KYC ring -->
        <div class="text-center flex-shrink-0">
          <svg viewBox="0 0 64 64" class="kyc-ring-svg">
            <circle cx="32" cy="32" r="26" fill="none" stroke="var(--surface3)" stroke-width="8"/>
            <circle cx="32" cy="32" r="26" fill="none"
              stroke="${kyc>=80?'#0098A1':kyc>=60?'#f0b429':'#f06060'}"
              stroke-width="8" stroke-dasharray="${kyc*1.633} 163.3" stroke-linecap="round"/>
          </svg>
          <div class="kyc-ring-label">KYC ${kyc}%</div>
        </div>
      </div>

      <!-- ── Guarantor Preview ─────────────────────────────────────── -->
      ${cust.guarantor_name || cust.guarantor_id_front || cust.guarantor_passport ? `
      <div class="panel mb-16">
        <div class="panel-header"><div class="panel-title">🤝 Guarantor</div></div>
        <div class="panel-body">
          <div class="d-flex gap-16 items-start">
            ${cust.guarantor_passport 
              ? `<img src="${cust.guarantor_passport}" class="avatar-lg">` 
              : `<div class="avatar-lg bg-surface3 d-flex items-center justify-center"><span class="text-2xl">👤</span></div>`}
            <div class="flex-1">
              <div class="fw-600 text-lg">${cust.guarantor_name || '—'}</div>
              <div class="d-flex gap-12 flex-wrap mt-4 text-sm text-dim">
                ${cust.guarantor_id ? `<span>ID: <a class="mono text-blue" onclick="navigator.clipboard?.writeText('${cust.guarantor_id}')" title="Copy">${cust.guarantor_id}</a></span>` : ''}
                ${cust.guarantor_phone ? `<a href="tel:${cust.guarantor_phone}" class="mono text-blue">${cust.guarantor_phone}</a>` : ''}
              </div>
              <div class="d-flex gap-8 mt-6">
                ${cust.guarantor_id_front ? `<span class="text-xs text-brand">✓ ID Front</span>` : ''}
                ${cust.guarantor_id_back ? `<span class="text-xs text-brand">✓ ID Back</span>` : ''}
                ${cust.guarantor_passport ? `<span class="text-xs text-brand">✓ Photo</span>` : ''}
              </div>
            </div>
          </div>
        </div>
      </div>` : ''}

      <!-- ── Tabs ────────────────────────────────────────────────── -->
      <div class="cust-profile-body" data-tab-scope>
        <div class="tabs">
          <button class="tab-btn active" onclick="switchTab(this,'cp-loans')">💰 Loans</button>
          <button class="tab-btn" onclick="switchTab(this,'cp-personal')">👤 Profile</button>
          <button class="tab-btn" onclick="switchTab(this,'cp-business')">🏪 Business</button>
          <button class="tab-btn" onclick="switchTab(this,'cp-guarantor')">🤝 Guarantor</button>
          <button class="tab-btn" onclick="switchTab(this,'cp-crm')">📋 CRM</button>
          <button class="tab-btn" onclick="switchTab(this,'cp-afford')">📊 Affordability</button>
          <button class="tab-btn ${hasActiveLoan && !canEdit ? 'disabled' : ''}" 
                onclick="${hasActiveLoan && !canEdit ? '' : `switchTab(this,'cp-edit')`}"
                ${hasActiveLoan && !canEdit ? 'disabled title="Customer has active loan - cannot edit"' : ''}>✏️ Edit</button>
        </div>

        <!-- ── LOANS TAB ───────────────────────────────────────── -->
        <div id="cp-loans" class="tab-content active">
          ${activeLoan ? `
          <div class="panel mb-16">
            <div class="panel-header"><div class="panel-title">Active Loan</div>${Badge.status('ACTIVE')}</div>
            <div class="panel-body">
              <div class="loan-amounts-grid">
                <div class="loan-amount-cell">
                  <div class="loan-amount-label">Loan ID</div>
                  <div class="mono text-brand fw-700">${activeLoan.loan_id}</div>
                </div>
                <div class="loan-amount-cell">
                  <div class="loan-amount-label">Principal</div>
                  <div class="loan-amount-value">${Fmt.currency(activeLoan.principal)}</div>
                </div>
                <div class="loan-amount-cell">
                  <div class="loan-amount-label">Total Balance</div>
                  <div class="loan-amount-value text-red">${Fmt.currency(activeLoan.balance)}</div>
                </div>
                <div class="loan-amount-cell">
                  <div class="loan-amount-label">Amount Paid</div>
                  <div class="loan-amount-value text-brand">${Fmt.currency(activeLoan.total_paid)}</div>
                </div>
              </div>
              <div class="form-grid mt-16">
                <div><div class="form-label">M-Pesa Disburse Code</div>
                  <div class="mono text-blue">${activeLoan.mpesa_disburse_code || activeLoan.transcode || '—'}</div></div>
                <div><div class="form-label">Disbursement Date</div>
                  <div class="mono">${Fmt.date(activeLoan.disbursed_at)}</div></div>
                <div><div class="form-label">Last Due Date</div>
                  <div class="mono text-red">${Fmt.date(activeLoan.due_date)}</div></div>
                <div><div class="form-label">Weekly Instalment</div>
                  <div class="mono">${activeLoan.weekly_installment ? Fmt.currency(activeLoan.weekly_installment)+'/wk' : '—'}</div></div>
              </div>
            </div>
          </div>` : '<div class="alert alert-info mb-16"><span>ℹ️</span><div>No active loan. Use the New Loan button to apply.</div></div>'}

          <div class="panel">
            <div class="panel-header"><div class="panel-title">Loan History</div></div>
            <div class="panel-body-bare">
              <table class="data-table">
                <thead><tr>
                  <th>Loan ID</th><th>Principal</th><th>Paid</th><th>Balance</th>
                  <th>Status</th><th>Disbursed</th><th>Due</th>
                </tr></thead>
                <tbody>${(loans||[]).length
                  ? loans.map(l => `<tr>
                      <td><a class="mono text-brand cursor-pointer fw-600"
                        onclick="window.location.href='/pages/loans/loans.html?search=${l.loan_id}'">${l.loan_id}</a></td>
                      <td class="mono">${Fmt.currency(l.principal)}</td>
                      <td class="mono text-brand">${Fmt.currency(l.total_paid)}</td>
                      <td class="mono ${parseFloat(l.balance)>0?'text-gold':'text-dim'}">${Fmt.currency(l.balance)}</td>
                      <td>${Badge.status(l.status)}</td>
                      <td class="mono text-dim">${Fmt.date(l.disbursed_at)}</td>
                      <td class="mono text-dim">${Fmt.date(l.due_date)}</td>
                    </tr>`).join('')
                  : '<tr><td colspan="7" class="text-center text-dim p-16">No loan history</td></tr>'}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- ── PERSONAL TAB ─────────────────────────────────────── -->
        <div id="cp-personal" class="tab-content">
          <div class="form-grid">
            <div><div class="form-label">Gender</div><div>${cust.gender==='M'?'♂ Male':cust.gender==='F'?'♀ Female':'Other'}</div></div>
            <div><div class="form-label">Date of Birth</div><div class="mono">${Fmt.date(cust.dob)}</div></div>
            <div><div class="form-label">Marital Status</div><div>${cust.marital_status||'—'}</div></div>
            <div><div class="form-label">Dependants</div><div>${cust.dependants??'—'}</div></div>
            <div><div class="form-label">Phone</div><div>${phoneLink(cust.phone)}</div></div>
            <div><div class="form-label">Alt Phone</div><div>${phoneLink(cust.phone2)}</div></div>
            <div><div class="form-label">Email</div><div>${cust.email||'—'}</div></div>
            <div><div class="form-label">County</div><div>${cust.county||'—'}</div></div>
            <div><div class="form-label">Sub-County</div><div>${cust.sub_county||'—'}</div></div>
            <div><div class="form-label">Village / Estate</div><div>${cust.village||'—'}</div></div>
          </div>
          <div class="form-label mt-12">Home Address</div>
          <div class="text-md">${cust.home_address||cust.address||'—'}</div>
          <div class="form-label mt-12">Branch</div>
          <div class="text-md">${cust.branch_name||'—'}</div>
          
          <div class="nok-section-label mt-16">KYC DOCUMENTS</div>
          <div class="d-flex gap-12 flex-wrap">
            ${cust.id_front
              ? `<div class="text-center"><div class="text-xs text-dim mb-4">ID Front</div>
                 <img src="${cust.id_front}" class="doc-preview-lg"></div>` : ''}
            ${cust.id_back
              ? `<div class="text-center"><div class="text-xs text-dim mb-4">ID Back</div>
                 <img src="${cust.id_back}" class="doc-preview-lg"></div>` : ''}
            ${cust.photo
              ? `<div class="text-center"><div class="text-xs text-dim mb-4">Passport Photo</div>
                 <img src="${cust.photo}" class="doc-preview-sm"></div>` : ''}
            ${!cust.id_front&&!cust.id_back&&!cust.photo
              ? '<div class="text-dim text-sm">No KYC documents uploaded yet. Use the Edit tab to upload.</div>' : ''}
          </div>
        </div>

        <!-- ── BUSINESS TAB ─────────────────────────────────────── -->
        <div id="cp-business" class="tab-content">
          <div class="form-grid">
            <div><div class="form-label">Business Name</div><div class="fw-600">${cust.business_name||'—'}</div></div>
            <div><div class="form-label">Category</div><div>${cust.business_category||'—'}</div></div>
            <div><div class="form-label">Location</div><div>${cust.business_location||'—'}</div></div>
            ${cust.geo_lat?`<div><div class="form-label">Geo Location</div><div class="mono text-sm">${cust.geo_lat}, ${cust.geo_lng}</div></div>`:''}
          </div>
          <div class="form-label mt-12">Business Address</div>
          <div class="text-md mb-16">${cust.business_address||'—'}</div>
          <div class="d-flex gap-8 mt-8">
            <button class="btn btn-ghost btn-sm" onclick="API.customerStatement(${cust.id})">📄 Statement</button>
            <button class="btn btn-ghost btn-sm" onclick="API.demandLetter(${activeLoan?.id||0})" ${!activeLoan?'disabled':''}>⚠️ Demand Letter</button>
          </div>
        </div>

        <!-- ── GUARANTOR TAB ────────────────────────────────────── -->
        <div id="cp-guarantor" class="tab-content">
          <div class="nok-section-label">NEXT OF KIN</div>
          <div class="form-grid">
            <div><div class="form-label">Name</div><div class="fw-600">${cust.next_of_kin||'—'}</div></div>
            <div><div class="form-label">Phone</div><div>${phoneLink(cust.next_of_kin_phone)}</div></div>
            <div><div class="form-label">Relationship</div><div>${cust.next_of_kin_relation||'—'}</div></div>
          </div>
          <div class="nok-section-label-mid">GUARANTOR</div>
          <div class="form-grid">
            <div><div class="form-label">Full Name</div><div class="fw-600">${cust.guarantor_name||'—'}</div></div>
            <div><div class="form-label">Phone</div><div>${phoneLink(cust.guarantor_phone)}</div></div>
            <div><div class="form-label">National ID</div><div class="mono">${cust.guarantor_id||'—'}</div></div>
            <div><div class="form-label">Relationship</div><div>${cust.guarantor_relation||'—'}</div></div>
          </div>
          <div class="form-label mt-16">Guarantor Home / Business Address</div>
          <div class="text-md mb-8">${cust.guarantor_address||cust.guarantor_business_address||'—'}</div>
          <div class="nok-section-label-mid">GUARANTOR DOCUMENTS</div>
          <div class="d-flex gap-12 flex-wrap">
            ${cust.guarantor_id_front
              ? `<div class="text-center"><div class="text-xs text-dim mb-4">ID Front</div>
                 <img src="${cust.guarantor_id_front}" class="doc-preview-lg"></div>` : ''}
            ${cust.guarantor_id_back
              ? `<div class="text-center"><div class="text-xs text-dim mb-4">ID Back</div>
                 <img src="${cust.guarantor_id_back}" class="doc-preview-lg"></div>` : ''}
            ${cust.guarantor_passport
              ? `<div class="text-center"><div class="text-xs text-dim mb-4">Passport Photo</div>
                 <img src="${cust.guarantor_passport}" class="doc-preview-sm"></div>` : ''}
            ${!cust.guarantor_id_front&&!cust.guarantor_id_back&&!cust.guarantor_passport
              ? '<div class="text-dim text-sm">No guarantor documents uploaded yet. Use the Edit tab to upload.</div>' : ''}
          </div>
          ${cust.documents && cust.documents.length > 0 && cust.documents.some(d => d.category === 'GUARANTOR_ID')
            ? `<div class="mt-12"><div class="text-xs text-dim mb-4">Guarantor Documents (KYC System)</div>
               <div class="d-flex gap-12 flex-wrap">
                 ${cust.documents.filter(d => d.category === 'GUARANTOR_ID').map(d => 
                   `<div class="text-center">
                      <a href="${d.download_url}" target="_blank" class="btn btn-ghost btn-sm">📄 ${d.filename}</a>
                    </div>`
                 ).join('')}
               </div></div>` : ''}
        </div>

        <!-- ── CRM TAB ──────────────────────────────────────────── -->
        <div id="cp-crm" class="tab-content">
          <div class="panel mb-16">
            <div class="panel-header"><div class="panel-title">📱 Send Message</div></div>
            <div class="panel-body">
              <div class="form-group">
                <label class="form-label">Message</label>
                <textarea class="form-control" id="crmMsg" rows="3"
                  placeholder="Type a message to send to ${cust.full_name}…"></textarea>
              </div>
              <button class="btn btn-primary btn-sm" onclick="sendCRMMessage(${cust.id},'${cust.phone}')">
                📱 Send SMS
              </button>
            </div>
          </div>
          <div class="panel">
            <div class="panel-header"><div class="panel-title">Loan Tracking</div></div>
            <div class="panel-body">
              <div class="form-grid">
                <div><div class="form-label">Customer Since</div><div class="mono">${Fmt.date(cust.created_at)}</div></div>
                <div><div class="form-label">Total Loans Taken</div><div class="mono">${(loans||[]).length}</div></div>
                <div><div class="form-label">Total Paid</div><div class="mono text-brand">${Fmt.currency((loans||[]).reduce((s,l)=>s+parseFloat(l.total_paid||0),0))}</div></div>
                <div><div class="form-label">Loan Officer</div><div>${cust.loan_officer_name||'—'}</div></div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── AFFORDABILITY TAB ────────────────────────────────── -->
        <div id="cp-afford" class="tab-content">
          <div class="panel">
            <div class="panel-header"><div class="panel-title">📊 Affordability Analysis</div></div>
            <div class="panel-body">
              <div class="form-grid mb-16">
                <div><div class="form-label">Monthly Income</div><div class="mono text-brand fw-700">${Fmt.currency(cust.monthly_income)}</div></div>
                <div><div class="form-label">Net Salary</div><div class="mono">${Fmt.currency(cust.net_salary)}</div></div>
                <div><div class="form-label">Loan Limit (3× net)</div><div class="mono text-brand fw-700">${Fmt.currency(cust.loan_limit)}</div></div>
                <div><div class="form-label">Tier</div><div>${tierBadge(cust.tier)}</div></div>
              </div>
              <div class="progress mb-8">
                <div class="progress-bar pb-green"
                  style="width:${Math.min(100,parseFloat(activeLoan?.balance||0)/Math.max(1,parseFloat(cust.loan_limit))*100).toFixed(0)}%">
                </div>
              </div>
              <div class="text-xs text-dim">Active debt vs loan limit</div>
              <div class="alert alert-info mt-16">
                <span>ℹ️</span>
                <div>
                  <b>First-time limit:</b> KES 5,000 · <b>Rate:</b> 20%/month (5%/week)<br>
                  <b>Repayment:</b> 4, 6 or 8 weeks · Limit adjustable by HOP/Admin/GM/BDM
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── EDIT TAB ─────────────────────────────────────────── -->
        <div id="cp-edit" class="tab-content">
          <div class="form-grid">
            <div class="form-group"><label class="form-label">First Name</label>
              <input class="form-control" id="ed-first-name" value="${cust.first_name||''}"></div>
            <div class="form-group"><label class="form-label">Last Name</label>
              <input class="form-control" id="ed-last-name" value="${cust.last_name||''}"></div>
            <div class="form-group"><label class="form-label">Phone</label>
              <input class="form-control" id="ed-phone" value="${cust.phone||''}"></div>
            <div class="form-group"><label class="form-label">National ID</label>
              <input class="form-control" id="ed-nid" value="${cust.national_id||''}"></div>
            <div class="form-group"><label class="form-label">Gender</label>
              <select class="form-control" id="ed-gender">
                <option value="M" ${cust.gender==='M'?'selected':''}>Male</option>
                <option value="F" ${cust.gender==='F'?'selected':''}>Female</option>
                <option value="O" ${cust.gender==='O'?'selected':''}>Other</option>
              </select></div>
            <div class="form-group"><label class="form-label">Marital Status</label>
              <select class="form-control" id="ed-marital">
                ${['SINGLE','MARRIED','DIVORCED','WIDOWED'].map(m=>
                  `<option value="${m}" ${cust.marital_status===m?'selected':''}>${m[0]+m.slice(1).toLowerCase()}</option>`).join('')}
              </select></div>
            <div class="form-group"><label class="form-label">Business Name</label>
              <input class="form-control" id="ed-biz-name" value="${cust.business_name||''}"></div>
            <div class="form-group"><label class="form-label">Business Category</label>
              <input class="form-control" id="ed-biz-cat" value="${cust.business_category||''}"></div>
          </div>
          <div class="form-group"><label class="form-label">Business Address</label>
            <textarea class="form-control" id="ed-biz-addr" rows="2">${cust.business_address||''}</textarea></div>
          <div class="form-group"><label class="form-label">Home Address</label>
            <textarea class="form-control" id="ed-home-addr" rows="2">${cust.home_address||''}</textarea></div>
          <div class="form-group"><label class="form-label">Business Location / Sub-market</label>
            <input class="form-control" id="ed-biz-loc" value="${cust.business_location||''}"></div>
          <div class="form-grid">
            <div class="form-group"><label class="form-label">Geo Lat</label>
              <input class="form-control" id="ed-lat" value="${cust.geo_lat||''}" placeholder="e.g. -1.2921">
            </div>
            <div class="form-group"><label class="form-label">Geo Lng</label>
              <input class="form-control" id="ed-lng" value="${cust.geo_lng||''}" placeholder="e.g. 36.8219">
            </div>
          </div>
          <button class="btn btn-ghost btn-sm mb-16" onclick="captureGeoLocation()">📍 Capture GPS Location</button>

          <div class="nok-section-label">KYC DOCUMENT UPLOADS</div>
          <div class="form-grid mt-12">
            <div class="form-group"><label class="form-label">ID Front</label>
              <input type="file" class="form-control" id="up-id-front" accept="image/*"></div>
            <div class="form-group"><label class="form-label">ID Back</label>
              <input type="file" class="form-control" id="up-id-back" accept="image/*"></div>
            <div class="form-group"><label class="form-label">Passport Photo</label>
              <input type="file" class="form-control" id="up-passport" accept="image/*"></div>
          </div>
          <div class="nok-section-label-mid">GUARANTOR DOCUMENTS</div>
          <div class="form-grid">
            <div class="form-group"><label class="form-label">Guarantor ID Front</label>
              <input type="file" class="form-control" id="up-guar-front" accept="image/*"></div>
            <div class="form-group"><label class="form-label">Guarantor ID Back</label>
              <input type="file" class="form-control" id="up-guar-back" accept="image/*"></div>
            <div class="form-group"><label class="form-label">Guarantor Passport</label>
              <input type="file" class="form-control" id="up-guar-passport" accept="image/*"></div>
          </div>
          <div class="d-flex gap-8 mt-16">
            <button class="btn btn-primary" onclick="saveCustomerEdit(${cust.id})">
              💾 Save Changes
            </button>
            <button class="btn btn-danger btn-sm" onclick="blacklistCustomer(${cust.id},'${cust.full_name}')">
              🚫 Blacklist
            </button>
          </div>
        </div>
      </div>`;
  } catch(e) {
    panel.innerHTML = '<div class="td-error text-center p-20">Failed to load customer profile</div>';
  }
}

async function saveCustomerEdit(id) {
  const first = document.getElementById('ed-first-name')?.value.trim();
  const last  = document.getElementById('ed-last-name')?.value.trim();
  const phone = document.getElementById('ed-phone')?.value.trim();
  if (!first || !last) { Toast.error('First and last name are required'); return; }
  if (!phone)          { Toast.error('Phone number is required'); return; }
  
  // Create FormData to handle file uploads
  const formData = new FormData();
  formData.append('first_name', document.getElementById('ed-first-name')?.value.trim());
  formData.append('last_name', document.getElementById('ed-last-name')?.value.trim());
  formData.append('phone', document.getElementById('ed-phone')?.value.trim());
  formData.append('national_id', document.getElementById('ed-nid')?.value.trim());
  formData.append('gender', document.getElementById('ed-gender')?.value);
  formData.append('marital_status', document.getElementById('ed-marital')?.value);
  formData.append('business_name', document.getElementById('ed-biz-name')?.value.trim());
  formData.append('business_category', document.getElementById('ed-biz-cat')?.value.trim());
  formData.append('business_address', document.getElementById('ed-biz-addr')?.value.trim());
  formData.append('home_address', document.getElementById('ed-home-addr')?.value.trim());
  formData.append('business_location', document.getElementById('ed-biz-loc')?.value.trim());
  formData.append('geo_lat', document.getElementById('ed-lat')?.value || null);
  formData.append('geo_lng', document.getElementById('ed-lng')?.value || null);
  
  // Add file uploads
  const idFront = document.getElementById('up-id-front')?.files[0];
  const idBack = document.getElementById('up-id-back')?.files[0];
  const passport = document.getElementById('up-passport')?.files[0];
  const guarFront = document.getElementById('up-guar-front')?.files[0];
  const guarBack = document.getElementById('up-guar-back')?.files[0];
  const guarPassport = document.getElementById('up-guar-passport')?.files[0];
  
  if (idFront) formData.append('id_front', idFront);
  if (idBack) formData.append('id_back', idBack);
  if (passport) formData.append('photo', passport);
  if (guarFront) formData.append('guarantor_id_front', guarFront);
  if (guarBack) formData.append('guarantor_id_back', guarBack);
  if (guarPassport) formData.append('guarantor_passport', guarPassport);
  
  try {
    const token = Auth.getToken();
    const response = await fetch(`/api/v1/customers/${id}/`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });
    
    if (response.ok) {
      Toast.success('✓ Customer profile saved');
      viewCustomer(id); // Reload tabs
      loadCustomers();
    } else {
      const error = await response.json();
      Toast.error(error.detail || 'Save failed');
    }
  } catch(err) {
    Toast.error(err?.data?.detail || 'Save failed');
  }
}

function captureGeoLocation() {
  if (!navigator.geolocation) { Toast.warn('Geolocation not supported on this device'); return; }
  navigator.geolocation.getCurrentPosition(
    pos => {
      const lat = pos.coords.latitude.toFixed(6);
      const lng = pos.coords.longitude.toFixed(6);
      const latEl = document.getElementById('ed-lat');
      const lngEl = document.getElementById('ed-lng');
      if (latEl) latEl.value = lat;
      if (lngEl) lngEl.value = lng;
      Toast.success(`📍 Location captured: ${lat}, ${lng}`);
    },
    () => Toast.error('Could not get GPS location — check browser permissions')
  );
}

async function sendCRMMessage(custId, phone) {
  const msg = document.getElementById('crmMsg')?.value.trim();
  if (!msg) { Toast.error('Enter a message first'); return; }
  try {
    await API.sendSMS({ phone, message: msg, customer: custId });
    Toast.success('✓ SMS sent');
    document.getElementById('crmMsg').value = '';
  } catch(err) {
    Toast.error(err?.data?.detail || 'SMS failed');
  }
}

function calcKYCScore(c) {
  const checks = [
    !!c.national_id, !!c.phone, !!c.dob, !!c.gender, !!c.address, !!c.county,
    !!c.employer, !!c.monthly_income, !!c.next_of_kin, !!c.next_of_kin_phone,
    !!c.guarantor_name, !!c.guarantor_phone, !!c.id_front, !!c.id_back, !!c.photo,
  ];
  return Math.round(checks.filter(Boolean).length / checks.length * 100);
}

// ── KYC live completeness meter ────────────────────────────────────────────────
function updateKYC() {
  const form = document.getElementById('newCustomerForm');
  if (!form) return;
  const fields = ['first_name','last_name','national_id','gender','dob',
                  'phone','address','county','employment_type','employer',
                  'monthly_income','next_of_kin','next_of_kin_phone',
                  'guarantor_name','guarantor_phone'];
  const filled = fields.filter(f => {
    const el = form.elements[f];
    return el && el.value && el.value.trim();
  }).length;
  const pct = Math.round(filled / fields.length * 100);
  const bar = document.getElementById('kyc-bar');
  const label = document.getElementById('kyc-pct');
  if (bar)   { bar.style.width = pct + '%'; bar.style.background = pct>=80?'var(--brand)':pct>=60?'var(--gold)':'var(--red)'; }
  if (label) label.textContent = pct + '%';
}

function calcAffordability() {
  const net = parseFloat(document.querySelector('[name="net_salary"]')?.value) || 0;
  const limit = net * 3;
  const field = document.getElementById('loanLimitField');
  if (field && limit > 0) field.value = limit;
}

function openNewCustomer() {
  Modal.open('modal-new-customer');
  updateKYC();
}

function runRefCheck() {
  const idInput = document.querySelector('[name="national_id"]')?.value.trim();
  const phone   = document.querySelector('[name="phone"]')?.value.trim();
  const q       = idInput || phone;
  if (q) {
    window.open(`../reference/reference.html?q=${encodeURIComponent(q)}`, '_blank');
  } else {
    window.open('../reference/reference.html', '_blank');
  }
}

async function saveCustomer() {
  const form = document.getElementById('newCustomerForm');
  if (!form) return;
  const data = formData('newCustomerForm');

  // Client-side required fields
  const required = ['first_name','last_name','national_id','phone','branch','loan_officer'];
  const missing = required.filter(f => !data[f]);
  if (missing.length) {
    Toast.error(`Required fields missing: ${missing.join(', ')}`);
    return;
  }

  setLoading('saveCustomerBtn', true);
  try {
    const cust = await API.createCustomer(data);
    if (cust) {
      Toast.success(`✓ ${cust.full_name} registered (${cust.uid}) — KYC ${cust.kyc_score || 0}%`);
      Modal.close('modal-new-customer');
      form.reset();
      updateKYC();
      loadCustomers();
    }
  } catch(err) {
    // Show field-specific validation errors
    if (err?.data && typeof err.data === 'object') {
      const msgs = Object.entries(err.data).map(([k,v]) =>
        `${k.replace(/_/g,' ')}: ${Array.isArray(v)?v[0]:v}`
      ).join('\n');
      Toast.error(msgs, 8000);
    }
  } finally { setLoading('saveCustomerBtn', false); }
}

async function blacklistCustomer(id, name) {
  const reason = await QL.prompt(`Blacklist reason for ${name}:`, '', {title:'Blacklist Customer', placeholder:'Enter reason…'});
  if (!reason) return;
  try {
    await API.blacklistCust(id, { reason });
    Toast.success(`${name} blacklisted`);
    Modal.close('modal-customer-detail');
    loadCustomers();
  } catch (err) { console.warn(err); }
}

function newLoanFor(id) {
  window.location.href = `../loans/loans.html?customer=${id}`;
}

function exportCSV() { API.exportCustomers(); }
const onSearch = debounce(() => loadCustomers(), 350);


// ─── TIER BADGE ───────────────────────────────────────────────────────────────
function tierBadge(tier) {
  const styles = {
    PLATINUM: 'background:linear-gradient(135deg,#e8e0ff,#c8b8ff);color:#4c1d95;border:1px solid #a78bfa',
    GOLD:     'background:linear-gradient(135deg,#fef9c3,#fde68a);color:#92400e;border:1px solid #fbbf24',
    SILVER:   'background:var(--surface2);color:var(--text2);border:1px solid var(--border)',
  };
  const icons = { PLATINUM: '💎', GOLD: '🥇', SILVER: '🥈' };
  const s = styles[tier] || styles.SILVER;
  const icon = icons[tier] || '🥈';
  return `<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 8px;
    border-radius:20px;font-size:10px;font-weight:700;${s}">
    ${icon} ${tier || 'SILVER'}
  </span>`;
}
