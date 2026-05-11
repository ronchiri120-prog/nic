/**
 * Groups & Chamas — Group / Chama lending management
 * Create groups · Add members · Apply for group loans · Approve · Disburse
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

let _branches      = [];
let _products      = [];
let _currentGroup  = null;
let _selectedCustomer = null;

document.addEventListener('DOMContentLoaded', async () => {
  loadSidebar('groups');
  await Promise.all([loadBranches(), loadProducts()]);
  loadGroups();
});

// ─── DATA LOADERS ──────────────────────────────────────────────────────────────
async function loadBranches() {
  try {
    const d = await API.branches();
    _branches = d?.results || d || [];
    const sel = document.getElementById('grp-branch');
    if (sel) {
      sel.innerHTML = '<option value="">Select branch…</option>' +
        _branches.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
    }
  } catch (err) { console.warn(err); }
}

async function loadProducts() {
  try {
    const d = await API.loanProducts();
    _products = d?.results || d || [];
    const sel = document.getElementById('gl-product');
    if (sel) {
      sel.innerHTML = '<option value="">Select product…</option>' +
        _products.map(p => `<option value="${p.id}">${p.name} — ${p.interest_rate}%</option>`).join('');
    }
  } catch (err) { console.warn(err); }
}

async function loadGroups(search = '') {
  const el = document.getElementById('pageContent');
  if (!el) return;

  el.innerHTML = `
    <div class="section-header animate-fadeup">
      <div>
        <h1 class="page-heading">👥 Groups &amp; Chamas</h1>
        <p class="text-sm text-dim">Joint liability group lending · Chamas · SACCOs · Self-help groups</p>
      </div>
      <div class="d-flex gap-8">
        <button class="btn btn-ghost" onclick="loadGroupLoans()">💰 Group Loans</button>
      </div>
    </div>
    <div id="groups-kpis" class="kpi-grid kpi-grid-4 animate-fadeup stagger-1">${loadingRows(1, 4)}</div>
    <div class="panel animate-fadeup stagger-2">
      <div class="panel-header">
        <div class="panel-title">Groups Registry</div>
        <span class="badge badge-active" id="groups-count">—</span>
      </div>
      <div id="groups-body" class="panel-body">
        <div class="groups-grid" id="groups-grid">${Array(4).fill('<div class="group-card"><div class="skeleton skel-h52 mb-8"></div><div class="skeleton skel-h18 mb-8"></div><div class="skeleton skel-h18"></div></div>').join('')}</div>
        <div id="groups-pagination"></div>
      </div>
    </div>`;

  try {
    const data = await API.groups({ search });
    const groups = data?.results || data || [];
    const count  = data?.count   ?? groups.length;

    document.getElementById('groups-count').textContent = `${count} groups`;

    // KPI summary
    const active   = groups.filter(g => g.status === 'ACTIVE').length;
    const dormant  = groups.filter(g => g.status === 'DORMANT').length;
    const members  = groups.reduce((s, g) => s + (g.member_count || 0), 0);
    const exposure = groups.reduce((s, g) => s + (parseFloat(g.active_loans_total) || 0), 0);
    document.getElementById('groups-kpis').innerHTML = `
      <div class="kpi-card kc-green grad"><div class="kpi-label">Active Groups</div><div class="kpi-value">${active}</div></div>
      <div class="kpi-card kc-gold grad"><div class="kpi-label">Dormant</div><div class="kpi-value">${dormant}</div></div>
      <div class="kpi-card kc-blue grad"><div class="kpi-label">Total Members</div><div class="kpi-value">${Fmt.number(members)}</div></div>
      <div class="kpi-card kc-red grad"><div class="kpi-label">Active Exposure</div><div class="kpi-value">${Fmt.currency(exposure)}</div></div>`;

    const grid = document.getElementById('groups-grid');
    grid.innerHTML = groups.length
      ? groups.map(g => groupCard(g)).join('')
      : `<div class="grid-col-full">${emptyState('👥', 'No groups yet', 'Create your first group or chama above.')}</div>`;

    renderPagination('groups-pagination', data, 'loadGroups');
  } catch {
    document.getElementById('groups-body').innerHTML =
      `<div class="td-error p-20 text-center">Failed to load groups.</div>`;
  }
}

function groupCard(g) {
  const statusClass = g.status === 'ACTIVE' ? 'badge-active' : g.status === 'DORMANT' ? 'badge-pending' : 'badge-default';
  return `
    <div class="group-card animate-fadeup">
      <div class="group-card-header">
        <div class="flex-1">
          <div class="group-card-id">${g.group_id}</div>
          <div class="group-card-name">${g.name}</div>
          <div class="group-card-branch">📍 ${g.branch_name || g.branch || '—'}</div>
        </div>
        <div class="d-flex flex-col items-end gap-6">
          <span class="badge ${statusClass}">${g.status}</span>
          <span class="chip chip-fa">${(g.group_type || 'CHAMA').replace('_',' ')}</span>
        </div>
      </div>
      <div class="group-card-body">
        <div class="group-stat-row">
          <span class="group-stat-label">Members</span>
          <span class="group-stat-value">${g.member_count || 0} / ${g.max_members || 30}</span>
        </div>
        <div class="group-stat-row">
          <span class="group-stat-label">Active Loans</span>
          <span class="group-stat-value ${g.active_loans_count > 0 ? 'text-brand' : 'text-dim'}">${g.active_loans_count || 0}</span>
        </div>
        <div class="group-stat-row">
          <span class="group-stat-label">Group Fund</span>
          <span class="group-stat-value">${Fmt.currency(g.group_fund || 0)}</span>
        </div>
        <div class="group-stat-row">
          <span class="group-stat-label">Meeting Day</span>
          <span class="group-stat-value text-dim">${g.meeting_day || '—'}</span>
        </div>
      </div>
      <div class="group-card-footer">
        <button class="btn btn-ghost btn-sm" onclick="viewGroup(${g.id})">👁 View</button>
        <button class="btn btn-ghost btn-sm" onclick="openAddMember(${g.id}, '${g.name}')">+ Member</button>
        <button class="btn btn-primary btn-sm" onclick="openGroupLoan(${g.id}, '${g.name}', ${g.member_count || 0})">💰 Loan</button>
      </div>
    </div>`;
}

// ─── GROUP DETAIL ──────────────────────────────────────────────────────────────
async function viewGroup(groupId) {
  _currentGroup = groupId;
  const modal = document.getElementById('modal-view-group');
  if (!modal) return;
  document.getElementById('vg-body').innerHTML = loadingRows(4, 3);
  Modal.open('modal-view-group');

  try {
    const g = await API.group(groupId);
    if (!g) return;

    document.getElementById('vg-title').textContent = `${g.group_id} — ${g.name}`;
    document.getElementById('vg-body').innerHTML = `
      <!-- Info + Members grid -->
      <div class="grid-2 mb-20">
        <div>
          <div class="fs-label-sm mb-8">Group Details</div>
          ${infoRow('ID',        g.group_id)}
          ${infoRow('Branch',    g.branch_name || '—')}
          ${infoRow('Officer',   g.loan_officer_name || '—')}
          ${infoRow('Type',      (g.group_type || 'CHAMA').replace('_',' '))}
          ${infoRow('Status',    g.status)}
          ${infoRow('Meeting',   g.meeting_day || '—')}
          ${infoRow('Fund',      Fmt.currency(g.group_fund || 0))}
        </div>
        <div>
          <div class="d-flex justify-between items-center mb-8">
            <div class="fs-label-sm">Members (${g.member_count || 0} / ${g.max_members})</div>
            <button class="btn btn-ghost btn-sm" onclick="openAddMember(${g.id}, '${g.name}')">+ Add</button>
          </div>
          <div class="member-list" id="vg-members">
            ${(g.memberships || []).map(m => memberRow(m)).join('') || `<div class="text-center text-dim p-20">No members yet</div>`}
          </div>
        </div>
      </div>
      <!-- Group Loans -->
      <div>
        <div class="d-flex justify-between items-center mb-8">
          <div class="fs-label-sm">Group Loans</div>
          <button class="btn btn-primary btn-sm" onclick="openGroupLoan(${g.id}, '${g.name}', ${g.member_count || 0})">+ New Loan</button>
        </div>
        <div id="vg-loans-list">
          ${(g.loans || []).length
            ? (g.loans || []).map(l => groupLoanRow(l)).join('')
            : `<div class="text-center text-dim p-20">No loans yet</div>`}
        </div>
      </div>`;
  } catch {
    document.getElementById('vg-body').innerHTML = `<div class="td-error text-center p-20">Failed to load group details.</div>`;
  }
}

function infoRow(label, value) {
  return `<div class="group-stat-row"><span class="group-stat-label">${label}</span><span class="group-stat-value">${value}</span></div>`;
}

function memberRow(m) {
  const roleClass = m.role === 'CHAIRPERSON' ? 'member-role-chair'
                  : m.role === 'SECRETARY'   ? 'member-role-sec'
                  : m.role === 'TREASURER'   ? 'member-role-tres'
                  : '';
  const initials = (m.customer_name || '?').split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase();
  return `
    <div class="member-row">
      <div class="member-avatar" style="background:${Auth.avatarColor(m.customer_name || '')}">
        ${initials}
      </div>
      <div class="flex-1">
        <div class="member-name">${m.customer_name || '—'}</div>
        <div class="member-sub">${m.customer_phone || ''} · ${m.shares || 1} share(s)</div>
      </div>
      <span class="member-role-badge ${roleClass}">${m.role}</span>
    </div>`;
}

function groupLoanRow(l) {
  const statusClass = l.status === 'ACTIVE' ? 'badge-active' : l.status === 'APPROVED' ? 'badge-approved' : l.status === 'PENDING' ? 'badge-pending' : 'badge-default';
  return `
    <div class="group-loan-row">
      <div class="flex-1">
        <div class="group-loan-id">${l.group_loan_id}</div>
        <div class="group-loan-amount">${Fmt.currency(l.total_amount)}</div>
        <div class="text-sm text-dim">${l.tenure_days}d · ${l.interest_rate}% · ${Fmt.date(l.created_at)}</div>
      </div>
      <div class="d-flex flex-col items-end gap-6">
        <span class="badge ${statusClass}">${l.status}</span>
        <div class="d-flex gap-4">
          ${l.status === 'PENDING'  ? `<button class="btn btn-gold btn-sm" onclick="approveGroupLoan(${l.id})">✓ Approve</button>` : ''}
          ${l.status === 'APPROVED' ? `<button class="btn btn-primary btn-sm" onclick="disburseGroupLoan(${l.id})">↗ Disburse</button>` : ''}
        </div>
      </div>
    </div>`;
}

// ─── GROUP LOANS TAB ──────────────────────────────────────────────────────────
async function loadGroupLoans(search = '') {
  const el = document.getElementById('pageContent');
  if (!el) return;

  el.innerHTML = `
    <div class="section-header animate-fadeup">
      <div>
        <h1 class="page-heading">💰 Group Loans</h1>
        <p class="text-sm text-dim">All group / chama loan applications</p>
      </div>
      <button class="btn btn-ghost" onclick="loadGroups()">← Back to Groups</button>
    </div>
    <div class="panel animate-fadeup stagger-1">
      <div class="panel-header">
        <div class="panel-title">Group Loan Applications</div>
        <div class="d-flex gap-8">
          <select class="filter-ctrl-md" id="glStatusFilter" onchange="loadGroupLoans()">
            <option value="">All Status</option>
            <option value="PENDING">Pending</option>
            <option value="APPROVED">Approved</option>
            <option value="ACTIVE">Active</option>
            <option value="CLOSED">Closed</option>
          </select>
        </div>
      </div>
      <div class="panel-body-bare">
        <table class="data-table">
          <thead><tr>
            <th>Loan ID</th><th>Group</th><th>Amount</th><th>Members</th>
            <th>Rate</th><th>Status</th><th>Applied</th><th>Actions</th>
          </tr></thead>
          <tbody id="gl-tbody">${loadingRows(6, 8)}</tbody>
        </table>
        <div id="gl-pagination"></div>
      </div>
    </div>`;

  try {
    const statusFilter = document.getElementById('glStatusFilter')?.value || '';
    const data  = await API.groupLoans({ status: statusFilter, search });
    const loans = data?.results || data || [];

    document.getElementById('gl-tbody').innerHTML = loans.length
      ? loans.map(l => {
          const sc = l.status === 'ACTIVE' ? 'badge-active' : l.status === 'APPROVED' ? 'badge-approved' : l.status === 'PENDING' ? 'badge-pending' : 'badge-default';
          return `<tr>
            <td class="td-mono text-brand fw-600">${l.group_loan_id}</td>
            <td><b>${l.group_name || '—'}</b><div class="text-sm text-dim">${l.branch_name || ''}</div></td>
            <td class="td-mono">${Fmt.currency(l.total_amount)}</td>
            <td class="text-center">${l.shares_count || 0}</td>
            <td class="td-mono">${l.interest_rate}%</td>
            <td><span class="badge ${sc}">${l.status}</span></td>
            <td class="td-mono text-dim">${Fmt.date(l.created_at)}</td>
            <td class="d-flex gap-4">
              ${l.status === 'PENDING'  ? `<button class="btn btn-gold btn-sm" onclick="approveGroupLoan(${l.id})">✓ Approve</button>` : ''}
              ${l.status === 'APPROVED' ? `<button class="btn btn-primary btn-sm" onclick="disburseGroupLoan(${l.id})">↗ Disburse</button>` : ''}
            </td>
          </tr>`;
        }).join('')
      : `<tr><td colspan="8">${emptyState('💰', 'No group loans', 'Applications will appear here.')}</td></tr>`;

    renderPagination('gl-pagination', data, 'loadGroupLoans');
  } catch {
    document.getElementById('gl-tbody').innerHTML = `<tr><td colspan="8" class="td-error">Failed to load.</td></tr>`;
  }
}

// ─── SAVE GROUP ────────────────────────────────────────────────────────────────
async function saveGroup() {
  const name   = document.getElementById('grp-name')?.value.trim();
  const type   = document.getElementById('grp-type')?.value;
  const branch = document.getElementById('grp-branch')?.value;
  const day    = document.getElementById('grp-day')?.value;
  const desc   = document.getElementById('grp-desc')?.value.trim();

  if (!name || !type || !branch) { Toast.error('Name, type and branch are required'); return; }

  setLoading('saveGroupBtn', true);
  try {
    const g = await API.createGroup({ name, group_type: type, branch, meeting_day: day, notes: desc });
    if (g) {
      Toast.success(`✓ ${g.group_id} — ${g.name} created`);
      Modal.close('modal-new-group');
      document.getElementById('grp-name').value = '';
      document.getElementById('grp-desc').value = '';
      loadGroups();
    }
  } catch (err) { console.warn(err); } finally { setLoading('saveGroupBtn', false); }
}

// ─── ADD MEMBER ────────────────────────────────────────────────────────────────
function openAddMember(groupId, groupName) {
  _currentGroup = groupId;
  _selectedCustomer = null;
  document.getElementById('modal-add-member').dataset.groupId   = groupId;
  document.getElementById('modal-add-member').dataset.groupName = groupName;
  document.querySelector('.modal-title', document.getElementById('modal-add-member'));
  document.getElementById('member-search').value   = '';
  document.getElementById('member-results').innerHTML = '';
  Modal.open('modal-add-member');
}

const searchCustomer = debounce(async (q) => {
  const el = document.getElementById('member-results');
  if (!q || q.length < 2) { if (el) el.innerHTML = ''; return; }
  if (!el) return;
  el.innerHTML = `<div class="text-sm text-dim p-8">Searching…</div>`;
  try {
    const data = await API.customers({ search: q });
    const customers = data?.results || data || [];
    el.innerHTML = customers.length
      ? customers.slice(0, 6).map(c => `
          <div class="customer-result" onclick="selectCustomer(${c.id}, '${c.full_name}', '${c.phone}', '${c.uid}')">
            <div class="member-avatar text-xs" style="background:${Auth.avatarColor(c.full_name)}">
              ${c.full_name.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()}
            </div>
            <div class="flex-1">
              <div class="customer-result-name">${c.full_name}</div>
              <div class="customer-result-meta">${c.uid} · ${c.phone}</div>
            </div>
          </div>`).join('')
      : `<div class="text-sm text-dim p-8">No customers found</div>`;
  } catch { el.innerHTML = `<div class="td-error p-8">Search failed</div>`; }
}, 350);

function selectCustomer(id, name, phone, uid) {
  _selectedCustomer = id;
  const el = document.getElementById('member-results');
  if (el) el.innerHTML = `
    <div class="customer-selected">
      <div>
        <div class="fw-600">${name}</div>
        <div class="mono-xs text-dim">${uid} · ${phone}</div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="_selectedCustomer=null;document.getElementById('member-results').innerHTML='';document.getElementById('member-search').value=''">✕</button>
    </div>`;
  document.getElementById('member-search').value = name;
}

async function addMember() {
  if (!_selectedCustomer) { Toast.error('Select a customer first'); return; }
  const role  = document.getElementById('member-role')?.value || 'MEMBER';
  const share = parseInt(document.getElementById('member-share')?.value || '1');
  const groupId = _currentGroup || document.getElementById('modal-add-member')?.dataset.groupId;
  if (!groupId) { Toast.error('No group selected'); return; }

  setLoading('addMemberBtn', true);
  try {
    const r = await API.addGroupMember(groupId, { customer: _selectedCustomer, role, shares: share });
    if (r) {
      Toast.success(`✓ Member added to group`);
      Modal.close('modal-add-member');
      _selectedCustomer = null;
      loadGroups();
      if (document.getElementById('modal-view-group')?.classList.contains('open')) {
        viewGroup(groupId);
      }
    }
  } catch (err) { console.warn(err); } finally { setLoading('addMemberBtn', false); }
}

// ─── GROUP LOAN APPLICATION ────────────────────────────────────────────────────
let _glGroupId = null;
let _glMemberCount = 0;

function openGroupLoan(groupId, groupName, memberCount) {
  _glGroupId     = groupId;
  _glMemberCount = memberCount;
  document.getElementById('gl-amount').value  = '';
  document.getElementById('gl-purpose').value = '';
  document.getElementById('gl-share-preview').innerHTML = '';
  Modal.open('modal-group-loan');
}

function calcGroupShares() {
  const amount  = parseFloat(document.getElementById('gl-amount')?.value || 0);
  const prodId  = document.getElementById('gl-product')?.value;
  const preview = document.getElementById('gl-share-preview');
  if (!preview) return;

  if (!amount || amount <= 0 || !_glMemberCount) {
    preview.innerHTML = '<div class="text-sm text-dim">Enter amount to see per-member share</div>';
    return;
  }

  const product   = _products.find(p => String(p.id) === String(prodId));
  const rate      = parseFloat(product?.interest_rate || 20);
  const perMember = amount / _glMemberCount;
  const interest  = perMember * (rate / 100);
  const total     = perMember + interest;

  preview.innerHTML = `
    <div class="share-preview-head">Per-member breakdown (${_glMemberCount} members)</div>
    <div class="share-preview-row"><span>Share of principal</span><span class="fw-600">${Fmt.currency(perMember)}</span></div>
    <div class="share-preview-row"><span>Interest (${rate}%)</span><span>${Fmt.currency(interest)}</span></div>
    <div class="share-preview-row border-top pt-6 mt-4">
      <span class="fw-600">Per-member total</span>
      <span class="fw-700 text-brand">${Fmt.currency(total)}</span>
    </div>
    <div class="share-preview-row"><span class="text-dim text-sm">Group total</span><span class="text-dim text-sm">${Fmt.currency(amount + (amount * rate / 100))}</span></div>`;
}

async function applyGroupLoan() {
  const amount  = parseFloat(document.getElementById('gl-amount')?.value || 0);
  const prodId  = document.getElementById('gl-product')?.value;
  const purpose = document.getElementById('gl-purpose')?.value.trim();

  if (!amount || amount <= 0) { Toast.error('Enter a valid loan amount'); return; }
  if (!prodId)                { Toast.error('Select a loan product'); return; }
  if (!_glGroupId)            { Toast.error('No group selected'); return; }

  const product = _products.find(p => String(p.id) === String(prodId));
  setLoading('applyGroupLoanBtn', true);
  try {
    const r = await API.createGroupLoan({
      group:         _glGroupId,
      product:       prodId,
      total_amount:  amount,
      interest_rate: product?.interest_rate || 20,
      tenure_days:   product?.tenure_days   || 30,
      notes:         purpose,
    });
    if (r) {
      Toast.success(`✓ Group loan ${r.group_loan_id} submitted — pending approval`);
      Modal.close('modal-group-loan');
      loadGroups();
    }
  } catch (err) { console.warn(err); } finally { setLoading('applyGroupLoanBtn', false); }
}

// ─── APPROVE / DISBURSE ────────────────────────────────────────────────────────
async function approveGroupLoan(loanId) {
  try {
    const r = await API.approveGroupLoan(loanId);
    if (r) {
      Toast.success(`✓ Group loan approved`);
      if (document.getElementById('modal-view-group')?.classList.contains('open')) {
        viewGroup(_currentGroup);
      } else {
        loadGroupLoans();
      }
    }
  } catch (err) { console.warn(err); }
}

async function disburseGroupLoan(loanId) {
  if (!await QL.confirm('Disburse this group loan?<br><span class="text-sm text-dim">Individual loans will be created for each member.</span>', {title:'Disburse Group Loan', okLabel:'Disburse'})) return;
  try {
    const r = await API.disburseGroupLoan(loanId);
    if (r) {
      Toast.success(`✓ ${r.detail}`);
      if (document.getElementById('modal-view-group')?.classList.contains('open')) {
        viewGroup(_currentGroup);
      } else {
        loadGroupLoans();
      }
    }
  } catch (err) { console.warn(err); }
}

// ─── SEARCH ────────────────────────────────────────────────────────────────────
const onSearch = debounce((el) => {
  const q = el?.value || document.getElementById('searchInput')?.value || '';
  loadGroups(q);
}, 350);

// ─── DELETE GROUP ────────────────────────────────────────────────────────────
async function deleteGroup(id, name) {
  if (!await QL.confirm(
    `Delete group <b>${name}</b>?<br><span class="text-sm text-dim">All members and loan history will be preserved but the group will be removed.</span>`,
    { title: 'Delete Group', okLabel: 'Delete', danger: true }
  )) return;
  try {
    await API.deleteGroup(id);
    Toast.success(`Group "${name}" deleted`);
    loadGroups();
  } catch (err) {
    Toast.error(err?.data?.detail || 'Cannot delete group');
  }
}
