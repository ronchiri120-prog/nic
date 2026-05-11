/**
 * Branches — Regions, Branches, Submarkets management
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}
Auth.requireRole(['SUPER_ADMIN','RM','BRANCH_MANAGER','OPERATIONS','BDO']);

document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('branches');
  // Inject search into topbar
  const _ta = document.getElementById('topbarActions');
  if (_ta && !_ta.querySelector('#searchInput')) {
    _ta.innerHTML = `<div class="topbar-search">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search…" oninput="onSearch()">
    </div>` + _ta.innerHTML;
  }
  renderLayout();
  loadAll();
});

function renderLayout() {
  document.getElementById('topbarActions').innerHTML = `
    <button class="btn btn-ghost" onclick="Modal.open('modal-new-region')">+ Region</button>
    <button class="btn btn-primary" onclick="Modal.open('modal-new-branch')">+ Branch</button>
  `;
  document.getElementById('pageContent').innerHTML = `
    <div class="section-header animate-fadeup"><div>
      <h1 class="page-heading">🏢 Branch Network</h1>
      <p class="text-sm text-dim">Regions · Branches · Submarkets</p>
    </div></div>
    <div class="kpi-grid animate-fadeup stagger-1 kpi-grid kpi-grid-4 animate-fadeup">
      <div class="kpi-card kc-blue grad"><div class="kpi-label">Regions</div><div class="kpi-value" id="kpi-regions">—</div></div>
      <div class="kpi-card kc-green grad"><div class="kpi-label">Branches</div><div class="kpi-value" id="kpi-branches">—</div></div>
      <div class="kpi-card kc-gold grad"><div class="kpi-label">Total Staff</div><div class="kpi-value" id="kpi-staff">—</div></div>
      <div class="kpi-card kc-red grad"><div class="kpi-label">Active Loans</div><div class="kpi-value" id="kpi-loans">—</div></div>
    </div>
    <div class="tabs animate-fadeup stagger-2" data-tab-scope>
      <button class="tab-btn active" onclick="switchTab(this,'tab-regions')">Regions</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-branches')">All Branches</button>
    </div>
    <div id="tab-regions"  class="tab-content active"><div id="regions-grid"></div></div>
    <div id="tab-branches" class="tab-content"><div id="branches-table"></div></div>

    <!-- Region Modal -->
    <div class="modal-overlay" id="modal-new-region">
      <div class="modal modal-sm">
        <div class="modal-header"><div class="modal-title">🗺️ New Region</div>
          <div class="modal-close" onclick="Modal.close('modal-new-region')">✕</div></div>
        <div class="modal-body">
          <div class="form-group"><label class="form-label">Region Name *</label>
            <input class="form-control" id="reg-name" placeholder="e.g. Nairobi North"></div>
          <div class="form-group"><label class="form-label">Region Code *</label>
            <input class="form-control" id="reg-code" placeholder="e.g. NBI-N" class="uppercase" maxlength="10"></div>
          <div class="form-group"><label class="form-label">Region Manager</label>
            <select class="form-control" id="reg-manager">
              <option value="">No manager assigned</option>
            </select></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" onclick="Modal.close('modal-new-region')">Cancel</button>
          <button class="btn btn-primary" id="saveRegionBtn" onclick="saveRegion()">
            <span class="btn-label">Create Region</span><span class="btn-spinner"></span></button>
        </div>
      </div>
    </div>

    <!-- Branch Modal -->
    <div class="modal-overlay" id="modal-new-branch">
      <div class="modal modal-md">
        <div class="modal-header"><div class="modal-title">🏢 New Branch</div>
          <div class="modal-close" onclick="Modal.close('modal-new-branch')">✕</div></div>
        <div class="modal-body">
          <div class="form-grid">
            <div class="form-group"><label class="form-label">Branch Name *</label>
              <input class="form-control" id="br-name" placeholder="e.g. Westlands Branch"></div>
            <div class="form-group"><label class="form-label">Branch Code *</label>
              <input class="form-control" id="br-code" placeholder="WLD" class="uppercase" maxlength="10"></div>
            <div class="form-group"><label class="form-label">Branch Type *</label>
              <select class="form-control" id="br-type">
                <option value="BRANCH">Regular Branch</option>
                <option value="HQ">Headquarters (HQ)</option>
              </select></div>
            <div class="form-group"><label class="form-label">Region *</label>
              <select class="form-control" id="br-region">
                <option value="">Select region…</option>
              </select></div>
            <div class="form-group"><label class="form-label">Sub-market</label>
              <input class="form-control" id="br-submarket" placeholder="e.g. Westlands CBD"></div>
            <div class="form-group"><label class="form-label">Disbursement Target (KES)</label>
              <input type="number" class="form-control" id="br-target" placeholder="2000000"></div>
            <div class="form-group"><label class="form-label">Phone</label>
              <input class="form-control" id="br-phone" placeholder="07XX XXX XXX"></div>
          </div>
          <div class="form-group"><label class="form-label">Address</label>
            <textarea class="form-control" id="br-address" rows="2" placeholder="Physical address"></textarea></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" onclick="Modal.close('modal-new-branch')">Cancel</button>
          <button class="btn btn-primary" id="saveBranchBtn" onclick="saveBranch()">
            <span class="btn-label">Create Branch</span><span class="btn-spinner"></span></button>
        </div>
      </div>
    </div>
  `;
}

async function loadAll() {
  try {
    const [regData, brData, perfData, usersData] = await Promise.all([
      API.regions().catch(() => null),
      API.branches(),
      API.reportBranches().catch(() => null),
      API.users().catch(() => null),
    ]);

    const regions  = regData?.results || regData || [];
    const branches = brData?.results  || brData  || [];
    const users    = usersData?.results || usersData || [];
    const perfMap  = {};
    if (Array.isArray(perfData)) perfData.forEach(p => { perfMap[p.branch] = p; });

    // KPIs
    setText('kpi-regions',  regions.length);
    setText('kpi-branches', branches.length);
    setText('kpi-staff',    branches.reduce((s, b) => s + (b.staff_count || 0), 0));
    setText('kpi-loans',    branches.reduce((s, b) => s + (b.active_loans || 0), 0));

    // Populate manager select in region modal
    const mgrSel = document.getElementById('reg-manager');
    if (mgrSel) {
      mgrSel.innerHTML = '<option value="">No manager assigned</option>' +
        users.filter(u => u.role === 'BRANCH_MANAGER' || u.role === 'RM' || u.role === 'SUPER_ADMIN')
          .map(u => `<option value="${u.id}">${u.full_name || u.username} (${u.role})</option>`).join('');
    }

    // Populate region select in branch modal
    const sel = document.getElementById('br-region');
    if (sel) {
      sel.innerHTML = '<option value="">Select region…</option>' +
        regions.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
    }

    // Regions tab — cards grouping branches
    const regGrid = document.getElementById('regions-grid');
    if (regions.length) {
      regGrid.innerHTML = `<div class="grid-2 mt-16">` +
        regions.map(r => {
          const rBranches = branches.filter(b => b.region === r.id || b.region_name === r.name);
          return `<div class="panel">
            <div class="panel-header">
              <div>
                <div class="fw-700 text-lg">${r.name}</div>
                <div class="mono text-dim text-xs">${r.code}</div>
                ${r.manager_name ? `<div class="text-dim text-xs">👤 ${r.manager_name}</div>` : ''}
              </div>
              <span class="badge badge-active">${r.branches_count || rBranches.length} branches</span>
            </div>
            <div class="panel-body">
              ${rBranches.length ? rBranches.map(b => {
                const perf = perfMap[b.name] || {};
                const rate = perf.collection_rate || 0;
                return `<div class="branch-card-row">
                  <div>
                    <div class="fw-600 text-base">${b.name}</div>
                    <div class="mono text-dim text-xs">${b.submarket || b.code}</div>
                  </div>
                  <div class="d-flex items-center gap-8">
                    ${rate ? `<span class="mono" style="font-size:11px;color:${rate>=85?'var(--brand)':rate>=75?'var(--gold)':'var(--red)'}">${Fmt.pct(rate)}</span>` : ''}
                    <span class="badge ${b.is_active?'badge-active':'badge-closed'} text-9">
                      ${b.is_active?'Active':'Inactive'}
                    </span>
                  </div>
                </div>`;
              }).join('') : '<p class="text-dim text-sm">No branches in this region</p>'}
            </div>
          </div>`;
        }).join('') + `</div>`;
    } else {
      regGrid.innerHTML = `<div class="mt-20">${emptyState('🗺️', 'No regions yet', 'Create a region first, then add branches to it.')}</div>`;
    }

    // Branches tab — full table
    const brTable = document.getElementById('branches-table');
    brTable.innerHTML = `<div class="panel mt-16">
      <div class="panel-body-bare">
        <table class="data-table">
          <thead><tr><th>Branch</th><th>Code</th><th>Type</th><th>Region</th><th>Sub-market</th>
            <th>Target</th><th>Staff</th><th>Active Loans</th><th>Rate</th><th>Status</th><th></th>
          </tr></thead>
          <tbody>${branches.map(b => {
            const perf = perfMap[b.name] || {};
            const rate = perf.collection_rate || 0;
            const isHQ = b.branch_type === 'HQ';
            return `<tr>
              <td><b>${b.name}</b>${isHQ ? ' <span class="chip chip-fa text-xs">HQ</span>' : ''}</td>
              <td class="mono text-dim">${b.code}</td>
              <td>${isHQ ? '<span class="chip chip-fa text-xs">HQ</span>' : '<span class="text-dim text-xs">Branch</span>'}</td>
              <td>${b.region_name || '—'}</td>
              <td class="mono text-dim">${b.submarket || '—'}</td>
              <td class="mono">${Fmt.currency(b.disb_target)}</td>
              <td class="mono">${b.staff_count || 0}</td>
              <td class="mono">${b.active_loans || 0}</td>
              <td class="mono" style="color:${rate>=85?'var(--brand)':rate>=75?'var(--gold)':'var(--red)'}">
                ${rate ? Fmt.pct(rate) : '—'}
              </td>
              <td>${Badge.status(b.is_active ? 'ACTIVE' : 'DORMANT')}</td>
              <td class="d-flex gap-4"><button class="btn btn-ghost btn-sm" onclick="editBranch(${b.id})">✏️ Edit</button><button class="btn btn-danger btn-sm" onclick="deleteBranch(${b.id},'${b.name}')">✕</button></td>
            </tr>`;
          }).join('')}</tbody>
        </table>
      </div>
    </div>`;

  } catch(e) {
    console.error(e);
    Toast.error('Failed to load branch data');
  }
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

async function saveRegion() {
  const name = document.getElementById('reg-name')?.value.trim();
  const code = document.getElementById('reg-code')?.value.trim().toUpperCase();
  const manager = document.getElementById('reg-manager')?.value;
  if (!name || !code) { Toast.error('Name and code required'); return; }
  setLoading('saveRegionBtn', true);
  try {
    const payload = { name, code };
    if (manager) payload.manager = parseInt(manager);
    const r = await API.createRegion(payload);
    if (r) {
      Toast.success(`Region "${r.name}" created`);
      Modal.close('modal-new-region');
      document.getElementById('reg-name').value = '';
      document.getElementById('reg-code').value = '';
      document.getElementById('reg-manager').value = '';
      loadAll();
    }
  } catch (err) { console.warn(err); } finally { setLoading('saveRegionBtn', false); }
}

async function saveBranch() {
  const name      = document.getElementById('br-name')?.value.trim();
  const code      = document.getElementById('br-code')?.value.trim().toUpperCase();
  const type      = document.getElementById('br-type')?.value;
  const region    = document.getElementById('br-region')?.value;
  const submarket = document.getElementById('br-submarket')?.value.trim();
  const target    = document.getElementById('br-target')?.value;
  const phone     = document.getElementById('br-phone')?.value.trim();
  const address   = document.getElementById('br-address')?.value.trim();
  if (!name || !code) { Toast.error('Name and code required'); return; }
  setLoading('saveBranchBtn', true);
  try {
    const b = await API.createBranch({
      name, code, branch_type: type, submarket, address, phone,
      ...(region ? { region: parseInt(region) } : {}),
      ...(target ? { disb_target: parseFloat(target) } : {}),
    });
    if (b) {
      Toast.success(`Branch "${b.name}" (${b.code}) created`);
      Modal.close('modal-new-branch');
      loadAll();
    }
  } catch (err) { console.warn(err); } finally { setLoading('saveBranchBtn', false); }
}

const onSearch = debounce(() => {
  const q = document.getElementById('searchInput')?.value || '';
  loadAll(q);
}, 300);

// ─── EDIT BRANCH ──────────────────────────────────────────────────────────────
async function editBranch(id) {
  try {
    const b = await API.branch(id);
    if (!b) { Toast.error('Could not load branch'); return; }

    // Populate the edit-branch modal
    document.getElementById('editBranchId').value        = id;
    document.getElementById('editBranchName').value      = b.name || '';
    document.getElementById('editBranchPhone').value     = b.phone || '';
    document.getElementById('editBranchAddress').value   = b.address || '';
    document.getElementById('editBranchSubmarket').value = b.submarket || '';
    document.getElementById('editBranchTarget').value    = b.disb_target || '';
    Modal.open('modal-edit-branch');
  } catch (err) {
    Toast.error('Could not load branch details');
  }
}

async function saveEditBranch() {
  const id = document.getElementById('editBranchId')?.value;
  if (!id) return;
  const payload = {
    name:        document.getElementById('editBranchName')?.value.trim(),
    phone:       document.getElementById('editBranchPhone')?.value.trim(),
    address:     document.getElementById('editBranchAddress')?.value.trim(),
    submarket:   document.getElementById('editBranchSubmarket')?.value.trim(),
    disb_target: parseFloat(document.getElementById('editBranchTarget')?.value) || 0,
  };
  if (!payload.name) { Toast.error('Branch name is required'); return; }
  setLoading('saveBranchEditBtn', true);
  try {
    const updated = await API.updateBranch(id, payload);
    if (updated) {
      Toast.success(`✓ ${updated.name} updated`);
      Modal.close('modal-edit-branch');
      loadAll();
    }
  } catch (err) {
    Toast.error(err?.data?.detail || 'Update failed');
  } finally { setLoading('saveBranchEditBtn', false); }
}

// ─── DELETE BRANCH / REGION ───────────────────────────────────────────────────
async function deleteBranch(id, name) {
  if (!await QL.confirm(
    `Delete branch <b>${name}</b>?<br><span class="text-sm text-dim">This cannot be undone. All linked customers/loans must be reassigned first.</span>`,
    { title: 'Delete Branch', okLabel: 'Delete', danger: true }
  )) return;
  try {
    await API.deleteBranch(id);
    Toast.success(`Branch "${name}" deleted`);
    loadAll();
  } catch (err) {
    Toast.error(err?.data?.detail || 'Cannot delete — linked customers or loans exist');
  }
}

async function deleteRegion(id, name) {
  if (!await QL.confirm(
    `Delete region <b>${name}</b>?<br><span class="text-sm text-dim">All branches in this region must be reassigned first.</span>`,
    { title: 'Delete Region', okLabel: 'Delete', danger: true }
  )) return;
  try {
    await API.deleteRegion(id);
    Toast.success(`Region "${name}" deleted`);
    loadAll();
  } catch (err) {
    Toast.error(err?.data?.detail || 'Cannot delete — linked branches exist');
  }
}
