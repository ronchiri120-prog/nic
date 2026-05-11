/**
 * Leads — Lead origination and customer conversion
 * BA : create leads only
 * RO : create + view detail + convert to customer
 * Admin/BM/HOP/GM : full access
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

const _user    = Auth.getUser();
const _isRO    = ['BDO','LOAN_OFFICER'].includes(_user?.role);
const _isBA    = false; // No longer used
const _isAdmin = ['SUPER_ADMIN','BRANCH_MANAGER','RM','OPERATIONS','IDC','VERIFICATION_TEAM'].includes(_user?.role);
const _canConvert = true;

let _currentLeadId = null;   // lead open in detail panel
let _leadProducts  = [];     // cached loan products

document.addEventListener('DOMContentLoaded', async () => {
  loadSidebar('leads');

  // Topbar — page controls (wireTopbar already put user block in #topbar-system-controls)
  const ta = document.getElementById('topbarActions');
  if (ta) ta.innerHTML = `
    <div class="topbar-search">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search name, phone, ID…" oninput="onSearch()">
    </div>
    <select class="filter-ctrl-md" id="statusFilter" onchange="loadLeads()">
      <option value="">All Status</option>
      <option value="NEW">New</option>
      <option value="CONTACTED">Contacted</option>
      <option value="QUALIFIED">Qualified</option>
      <option value="CONVERTED">Converted</option>
      <option value="LOST">Lost</option>
    </select>
    <button class="btn btn-primary" onclick="openNewLead()">+ New Lead</button>
  `;

  await Promise.all([setupLeadForm(), loadProducts()]);
  loadLeads();
});

// ─── SETUP BRANCH AUTO-FILL ───────────────────────────────────────────────────
async function setupLeadForm() {
  const sel  = document.getElementById('ldBranch');
  const hint = document.getElementById('ldBranchHint');
  if (!sel) return;

  if (_user?.branch_id && (_isRO || _isBA)) {
    sel.innerHTML = `<option value="${_user.branch_id}">${_user.branch || 'Your branch'}</option>`;
    sel.disabled  = true;
    if (hint) hint.innerHTML = `<span class="branch-auto-badge">✓ Auto: ${_user.branch || 'Your branch'}</span>`;
  } else {
    try {
      const d    = await API.branches();
      const list = d?.results || d || [];
      sel.innerHTML = '<option value="">Select branch…</option>' +
        list.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
    } catch (err) { console.warn(err); }
  }
}

// ─── LOAD LOAN PRODUCTS ───────────────────────────────────────────────────────
async function loadProducts() {
  try {
    const d    = await API.loanProducts();
    _leadProducts = d?.results || d || [];
    const sel  = document.getElementById('cvProduct');
    if (sel) {
      sel.innerHTML = '<option value="">Choose product…</option>' +
        _leadProducts.map(p =>
          `<option value="${p.id}" data-min="${p.min_amount}" data-max="${p.max_amount}"
           data-rate="${p.interest_rate}" data-tenure="${p.tenure_days}">${p.name}</option>`
        ).join('');
    }
  } catch (err) { console.warn(err); }
}

function openNewLead() {
  ['ldFirstName','ldLastName','ldPhone','ldNationalId','ldBizLocation','ldNotes','ldSubmarket']
    .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  const gSel = document.getElementById('ldGender');   if (gSel) gSel.value = 'M';
  const sSel = document.getElementById('ldSource');   if (sSel) sSel.value = 'WALK_IN';
  const bSel = document.getElementById('ldBizCategory'); if (bSel) bSel.value = '';
  Modal.open('modal-new-lead');
  setTimeout(() => document.getElementById('ldFirstName')?.focus(), 100);
}

// ─── LOAD LEADS TABLE ─────────────────────────────────────────────────────────
async function loadLeads(url) {
  const el = document.getElementById('pageContent');
  if (!el) return;

  if (!document.getElementById('leadsTbody')) {
    el.innerHTML = `
      <div class="section-header animate-fadeup">
        <div>
          <h1 class="page-heading">🎯 Lead Origination</h1>
          <p class="text-sm text-dim">Capture prospects · Complete profile · Convert to customers</p>
        </div>
      </div>
      <div class="kpi-grid kpi-grid-5 animate-fadeup stagger-1" id="leadsKPIs">
        ${Array(5).fill('<div class="kpi-card"><div class="skeleton skel-h18 mb-8"></div><div class="skeleton skel-h52"></div></div>').join('')}
      </div>
      <div class="panel animate-fadeup stagger-2">
        <div class="panel-header">
          <div class="panel-title">Lead Pipeline</div>
          <span class="badge badge-active" id="leadsCount">—</span>
        </div>
        <div class="panel-body-bare">
          <table class="data-table">
            <thead><tr>
              <th>Lead ID</th>
              <th>Name</th>
              <th>Phone</th>
              <th>Business</th>
              <th>Sub-market</th>
              <th>Branch</th>
              <th>By</th>
              <th>Status</th>
              <th>Date</th>
              <th class="col-action-sm">Detail</th>
            </tr></thead>
            <tbody id="leadsTbody">${loadingRows(8, 10)}</tbody>
          </table>
          <div id="leadsPagination"></div>
        </div>
      </div>`;
  }

  const params = {
    search:   document.getElementById('searchInput')?.value || '',
    status:   document.getElementById('statusFilter')?.value || '',
    ordering: '-created_at',
  };

  try {
    const data  = url
      ? await fetch(url, { headers: { Authorization: `Bearer ${Auth.getToken()}` } }).then(r => r.json())
      : await API.leads(params);
    const leads = data?.results || data || [];
    const count = data?.count ?? leads.length;

    document.getElementById('leadsCount').textContent = `${count} leads`;

    const bySt = s => leads.filter(l => l.status === s).length;
    document.getElementById('leadsKPIs').innerHTML = `
      <div class="kpi-card kc-blue  grad"><div class="kpi-label">Total</div>    <div class="kpi-value">${count}</div></div>
      <div class="kpi-card kc-gold  grad"><div class="kpi-label">New</div>      <div class="kpi-value">${bySt('NEW')}</div></div>
      <div class="kpi-card kc-teal  grad"><div class="kpi-label">Qualified</div><div class="kpi-value">${bySt('QUALIFIED')}</div></div>
      <div class="kpi-card kc-green grad"><div class="kpi-label">Converted</div><div class="kpi-value">${bySt('CONVERTED')}</div></div>
      <div class="kpi-card kc-red   grad"><div class="kpi-label">Lost</div>     <div class="kpi-value">${bySt('LOST')}</div></div>`;

    const tbody = document.getElementById('leadsTbody');
    tbody.innerHTML = leads.length
      ? leads.map(l => leadRow(l)).join('')
      : `<tr><td colspan="10">${emptyState('🎯','No leads yet','Click + New Lead to begin.')}</td></tr>`;

    renderPagination('leadsPagination', data, 'loadLeads');
  } catch (err) {
    const tbody = document.getElementById('leadsTbody');
    if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="td-error">Failed to load leads — check connection.</td></tr>`;
  }
}

function leadRow(l) {
  const sc = {
    NEW:'lead-status-new', CONTACTED:'lead-status-contacted',
    QUALIFIED:'lead-status-qualified', CONVERTED:'lead-status-converted', LOST:'lead-status-lost'
  }[l.status] || 'badge-closed';

  const name = l.full_name || `${l.first_name} ${l.last_name}`;

  // Eye icon always visible; shows view if converted, open detail otherwise
  const eyeBtn = l.status === 'CONVERTED'
    ? `<a class="btn-eye" href="/pages/customers/customers.html?open=${l.customer_id || ''}" title="View Customer">
         👁 <span class="text-xs">Customer</span>
       </a>`
    : `<button class="btn-eye" onclick="openLeadDetail(${l.id})" title="Open lead detail / convert">
         👁 <span class="text-xs">${_canConvert ? 'Detail' : 'View'}</span>
       </button>`;

  return `<tr>
    <td class="td-mono text-blue">${l.lead_id}</td>
    <td>
      <span class="lead-name-link fw-600" onclick="openLeadDetail(${l.id})">${name}</span>
      <div class="text-xs text-dim">${l.gender==='M'?'♂':l.gender==='F'?'♀':'⚧'} ${(l.source||'').replace('_',' ')}</div>
    </td>
    <td><a class="lead-phone-link" href="tel:${l.phone}">${l.phone}</a></td>
    <td class="text-sm">${l.business_category||'—'}</td>
    <td class="text-sm">${l.submarket||'—'}</td>
    <td class="text-sm text-dim">${l.branch_name||'—'}</td>
    <td class="text-sm text-dim">${l.created_by_name||'—'}</td>
    <td><span class="badge ${sc}">${l.status}</span></td>
    <td class="td-mono text-dim">${Fmt.date(l.created_at)}</td>
    <td class="text-center">${eyeBtn}</td>
  </tr>`;
}

// ─── SAVE NEW LEAD ────────────────────────────────────────────────────────────
async function saveLead() {
  const firstName = document.getElementById('ldFirstName')?.value.trim();
  const lastName  = document.getElementById('ldLastName')?.value.trim();
  const phone     = document.getElementById('ldPhone')?.value.trim();
  const submarket = document.getElementById('ldSubmarket')?.value.trim();
  const branchId  = document.getElementById('ldBranch')?.value;

  if (!firstName || !lastName) { Toast.error('First and last name are required'); return; }
  if (!phone)     { Toast.error('Phone number is required'); return; }
  if (!submarket) { Toast.error('Sub-market is required — e.g. Heshima, Town'); return; }
  if (!branchId)  { Toast.error('Branch is required'); return; }

  setLoading('saveLeadBtn', true);
  try {
    const lead = await API.createLead({
      first_name:        firstName,
      last_name:         lastName,
      phone,
      national_id:       document.getElementById('ldNationalId')?.value.trim() || '',
      gender:            document.getElementById('ldGender')?.value || 'M',
      source:            document.getElementById('ldSource')?.value || 'WALK_IN',
      business_category: document.getElementById('ldBizCategory')?.value || '',
      business_location: document.getElementById('ldBizLocation')?.value.trim() || '',
      submarket,
      notes:             document.getElementById('ldNotes')?.value.trim() || '',
      branch:            branchId,
    });
    if (lead) {
      Toast.success(`✓ Lead ${lead.lead_id} — ${lead.full_name || firstName} saved`);
      Modal.close('modal-new-lead');
      loadLeads();
    }
  } catch (err) {
    Toast.error(err?.data?.detail || err?.data?.phone?.[0] || 'Failed to save lead');
  } finally {
    setLoading('saveLeadBtn', false);
  }
}

// ─── OPEN LEAD DETAIL PANEL (eye icon) ────────────────────────────────────────
async function openLeadDetail(id) {
  _currentLeadId = id;

  // Reset tabs to first tab
  document.querySelectorAll('#modal-lead-detail .tab-btn').forEach((b, i) => {
    b.classList.toggle('active', i === 0);
  });
  document.querySelectorAll('#modal-lead-detail .tab-content').forEach((c, i) => {
    c.classList.toggle('active', i === 0);
  });

  Modal.open('modal-lead-detail');

  try {
    const l = await API.lead(id);
    if (!l) { Toast.error('Lead not found'); return; }

    // Header
    const name = l.full_name || `${l.first_name} ${l.last_name}`;
    document.getElementById('leadDetailTitle').textContent = `Lead: ${name}`;
    document.getElementById('leadDetailMeta').textContent =
      `${l.lead_id} · ${l.branch_name || '—'} · Created ${Fmt.date(l.created_at)} by ${l.created_by_name || '—'}`;

    // ── Tab 1: Personal Info ──────────────────────────────────────────────────
    _setVal('cvFirstName',   l.first_name);
    _setVal('cvLastName',    l.last_name);
    _setVal('cvPhone',       l.phone);
    _setVal('cvNationalId',  l.national_id);
    _setVal('cvGender',      l.gender || 'M');
    _setVal('cvMarital',     l.marital_status || '');
    _setVal('cvDob',         l.dob || '');
    _setVal('cvPhone2',      l.phone2 || '');
    _setVal('cvHomeAddress', l.home_address || l.address || '');

    // ── Tab 2: Business ───────────────────────────────────────────────────────
    _setVal('cvBizName',     l.business_name || '');
    _setVal('cvBizCategory', l.business_category || '');
    _setVal('cvBranchDisplay', l.branch_name || _user?.branch || '—');
    _setVal('cvSubmarket',   l.submarket || '');
    _setVal('cvBizLocation', l.business_location || '');
    _setVal('cvIncome',      l.monthly_income || '');

    // ── Tab 3: Guarantor ──────────────────────────────────────────────────────
    _setVal('cvNokName',     l.next_of_kin || '');
    _setVal('cvNokPhone',    l.next_of_kin_phone || '');
    _setVal('cvNokRelation', l.next_of_kin_relation || '');
    _setVal('cvGuarName',    l.guarantor_name || '');
    _setVal('cvGuarPhone',   l.guarantor_phone || '');
    _setVal('cvGuarId',      l.guarantor_id || '');
    _setVal('cvGuarRelation',l.guarantor_relation || '');
    _setVal('cvGuarAddress', l.guarantor_address || '');

    // ── Tab 4: Loan selector ──────────────────────────────────────────────────
    calcLeadAffordability();
    calcLeadLoan();

    // Hide convert button for BA or already-converted leads
    const activateBtn = document.getElementById('activateCustomerBtn');
    if (activateBtn) {
      activateBtn.style.display = (_canConvert && l.status !== 'CONVERTED') ? '' : 'none';
    }
    const saveOnlyBtn = document.getElementById('saveLeadOnlyBtn');
    if (saveOnlyBtn) {
      saveOnlyBtn.style.display = l.status !== 'CONVERTED' ? '' : 'none';
    }
  } catch (err) {
    Toast.error('Failed to load lead details');
  }
}

function _setVal(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  el.value = val ?? '';
}

// ─── AFFORDABILITY HINT ───────────────────────────────────────────────────────
function calcLeadAffordability() {
  const income = parseFloat(document.getElementById('cvIncome')?.value) || 0;
  const hint   = document.getElementById('cvAffordabilityHint');
  const txt    = document.getElementById('cvAffordabilityText');
  if (!hint || !txt) return;
  if (income > 0) {
    const limit = income * 3;
    hint.style.display = '';
    txt.innerHTML = `Based on income of <b>${Fmt.currency(income)}/mo</b>, recommended limit: <b class="text-brand">${Fmt.currency(limit)}</b>`;
  } else {
    hint.style.display = 'none';
  }
}

// ─── LOAN PREVIEW CALCULATOR ──────────────────────────────────────────────────
function calcLeadLoan() {
  const prodId  = document.getElementById('cvProduct')?.value;
  const amount  = parseFloat(document.getElementById('cvAmount')?.value) || 0;
  const preview = document.getElementById('cvLoanPreview');
  const hint    = document.getElementById('cvAmountHint');
  const weeklyWrap = document.getElementById('cvWeeklyWrap');
  if (!preview) return;

  if (!prodId || !amount) { preview.innerHTML = ''; return; }

  const prod = _leadProducts.find(p => String(p.id) === String(prodId));
  if (!prod) return;

  // Check if it's a weekly product (rate denominated per week = rate ≤ 6%)
  const isWeekly = parseFloat(prod.interest_rate) <= 6;
  if (weeklyWrap) weeklyWrap.style.display = isWeekly ? '' : 'none';

  if (hint) {
    hint.textContent = `Min: ${Fmt.currency(prod.min_amount)} · Max: ${Fmt.currency(prod.max_amount)}`;
  }

  let total, interest, schedule;
  if (isWeekly) {
    const weeks   = parseInt(document.querySelector('input[name="cvWeeks"]:checked')?.value || 6);
    const rate    = parseFloat(prod.interest_rate) / 100;
    interest      = amount * rate * weeks;
    total         = amount + interest;
    const weekly  = total / weeks;
    schedule      = `${weeks} weekly payments of <b>${Fmt.currency(weekly)}</b>`;
  } else {
    const rate    = parseFloat(prod.interest_rate) / 100;
    interest      = amount * rate;
    total         = amount + interest;
    const tenure  = prod.tenure_days;
    schedule      = `Due in ${tenure} days`;
  }

  preview.innerHTML = `
    <div class="loan-calc-box animate-fadeup">
      <div class="d-flex justify-between border-bottom pb-8 mb-8">
        <span class="text-dim">Principal</span>
        <span class="fw-600">${Fmt.currency(amount)}</span>
      </div>
      <div class="d-flex justify-between border-bottom pb-8 mb-8">
        <span class="text-dim">Interest (${prod.interest_rate}%${isWeekly ? '/wk' : ''})</span>
        <span>${Fmt.currency(interest)}</span>
      </div>
      <div class="d-flex justify-between fw-700">
        <span>Total Repayable</span>
        <span class="text-brand">${Fmt.currency(total)}</span>
      </div>
      <div class="text-xs text-dim mt-8">📅 ${schedule}</div>
    </div>`;
}

// ─── SAVE LEAD DETAIL (from detail panel) ─────────────────────────────────────
async function saveLeadDetail(action) {
  if (!_currentLeadId) return;

  // Collect all fields from the detail panel
  const payload = {
    first_name:          document.getElementById('cvFirstName')?.value.trim(),
    last_name:           document.getElementById('cvLastName')?.value.trim(),
    phone:               document.getElementById('cvPhone')?.value.trim(),
    national_id:         document.getElementById('cvNationalId')?.value.trim(),
    gender:              document.getElementById('cvGender')?.value,
    marital_status:      document.getElementById('cvMarital')?.value || '',
    dob:                 document.getElementById('cvDob')?.value || null,
    phone2:              document.getElementById('cvPhone2')?.value.trim() || '',
    home_address:        document.getElementById('cvHomeAddress')?.value.trim() || '',
    business_name:       document.getElementById('cvBizName')?.value.trim() || '',
    business_category:   document.getElementById('cvBizCategory')?.value || '',
    submarket:           document.getElementById('cvSubmarket')?.value.trim() || '',
    business_location:   document.getElementById('cvBizLocation')?.value.trim() || '',
    monthly_income:      parseFloat(document.getElementById('cvIncome')?.value) || 0,
    next_of_kin:         document.getElementById('cvNokName')?.value.trim() || '',
    next_of_kin_phone:   document.getElementById('cvNokPhone')?.value.trim() || '',
    next_of_kin_relation:document.getElementById('cvNokRelation')?.value.trim() || '',
    guarantor_name:      document.getElementById('cvGuarName')?.value.trim() || '',
    guarantor_phone:     document.getElementById('cvGuarPhone')?.value.trim() || '',
    guarantor_id:        document.getElementById('cvGuarId')?.value.trim() || '',
    guarantor_relation:  document.getElementById('cvGuarRelation')?.value.trim() || '',
    guarantor_address:   document.getElementById('cvGuarAddress')?.value.trim() || '',
  };

  if (!payload.first_name || !payload.last_name) {
    Toast.error('First and last name are required'); return;
  }
  if (!payload.phone) {
    Toast.error('Phone number is required'); return;
  }

  // Set status based on action
  if (action === 'QUALIFIED') payload.status = 'QUALIFIED';

  const btnId = action === 'CONVERT' ? 'activateCustomerBtn' : 'saveLeadOnlyBtn';
  setLoading(btnId, true);

  try {
    // 1. Update lead with all the detail
    const updated = await API.updateLead(_currentLeadId, payload);
    if (!updated) throw new Error('Lead update failed');

    if (action === 'QUALIFIED') {
      Toast.success(`✓ Lead saved as Qualified — ${payload.first_name} ${payload.last_name}`);
      Modal.close('modal-lead-detail');
      loadLeads();
      return;
    }

    // 2. Convert to customer
    if (!payload.national_id) {
      Toast.error('National ID is required to activate as customer');
      setLoading(btnId, false);
      return;
    }

    const r = await API.convertLead(_currentLeadId);
    if (!r?.customer_id) throw new Error(r?.detail || 'Conversion failed');

    // 3. If product selected, create loan application
    const productId = document.getElementById('cvProduct')?.value;
    const amount    = parseFloat(document.getElementById('cvAmount')?.value) || 0;

    if (productId && amount > 0) {
      const weeks = parseInt(document.querySelector('input[name="cvWeeks"]:checked')?.value || 6);
      try {
        await API.createLoan({
          customer:  r.customer_id,
          product:   productId,
          principal: amount,
          weeks,
          branch:    updated.branch,
        });
        Toast.success(`✓ ${payload.first_name} activated as customer · Loan application created`);
      } catch (lErr) {
        Toast.warn(`✓ Customer created · Loan failed: ${lErr?.data?.detail || 'check loan page'}`);
      }
    } else {
      Toast.success(`✓ ${payload.first_name} ${payload.last_name} activated as customer`);
    }

    Modal.close('modal-lead-detail');
    loadLeads();

    // Redirect to customer profile
    setTimeout(() => {
      window.location.href = `/pages/customers/customers.html?open=${r.customer_id}`;
    }, 1000);

  } catch (err) {
    Toast.error(err?.data?.detail || err?.message || 'Action failed');
  } finally {
    setLoading(btnId, false);
  }
}

// ─── SEARCH ───────────────────────────────────────────────────────────────────
const onSearch = debounce(() => loadLeads(), 350);
