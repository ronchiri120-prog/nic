/**
 * Staff & Roles Page — v1.0 (Live)
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}
Auth.requireRole(['SUPER_ADMIN','BRANCH_MANAGER','RM','OPERATIONS']);

// Permission Matrix
const PERMS = [
  { m: 'Dashboard', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'Full', ba: 'View', coll_mgr: 'Full', mkt: 'View', hop: 'Full', acc: 'View' },
  { m: 'Customers', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'Full', ba: 'Full', coll_mgr: 'Full', mkt: 'Full', hop: 'View', acc: 'View' },
  { m: 'Loans', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'Full', ba: 'View', coll_mgr: 'Full', mkt: 'View', hop: 'View', acc: 'View' },
  { m: 'Payments', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'Full', ba: 'Full', coll_mgr: 'Full', mkt: 'View', hop: 'View', acc: 'Full' },
  { m: 'Branches', sa: 'Full', rm: 'Full', bm: 'Own', ro: 'View', ba: 'View', coll_mgr: 'View', mkt: 'View', hop: 'View', acc: 'View' },
  { m: 'Staff', sa: 'Full', rm: 'Region', bm: 'Own', ro: 'View', ba: 'View', coll_mgr: 'View', mkt: 'View', hop: 'Full', acc: 'View' },
  { m: 'Reports', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'View', ba: 'View', coll_mgr: 'Full', mkt: 'View', hop: 'Full', acc: 'Full' },
  { m: 'Accounting', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'View', ba: 'View', coll_mgr: 'View', mkt: 'View', hop: 'View', acc: 'Full' },
  { m: 'Settings', sa: 'Full', rm: 'View', bm: 'View', ro: 'None', ba: 'None', coll_mgr: 'None', mkt: 'None', hop: 'Full', acc: 'View' },
  { m: 'Leads', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'Full', ba: 'View', coll_mgr: 'Full', mkt: 'Full', hop: 'View', acc: 'View' },
  { m: 'Applications', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'Full', ba: 'View', coll_mgr: 'Full', mkt: 'View', hop: 'View', acc: 'View' },
  { m: 'Collections', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'Full', ba: 'View', coll_mgr: 'Full', mkt: 'View', hop: 'View', acc: 'Full' },
  { m: 'Notifications', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'Full', ba: 'View', coll_mgr: 'Full', mkt: 'View', hop: 'View', acc: 'View' },
  { m: 'Reference Check', sa: 'Full', rm: 'Full', bm: 'Full', ro: 'Full', ba: 'View', coll_mgr: 'Full', mkt: 'View', hop: 'View', acc: 'View' },
];

document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('staff');
  // Inject search into topbar
  const _ta = document.getElementById('topbarActions');
  if (_ta && !_ta.querySelector('#searchInput')) {
    _ta.innerHTML = `<div class="topbar-search">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search…" oninput="onSearch()">
    </div>` + _ta.innerHTML;
  }
  setupTopbar();
  loadStaff();
  loadBranchOptions();
  loadRegionOptions();
  renderPermissions();
});

function setupTopbar() {
  document.getElementById('topbarActions').innerHTML =
    `<button class="btn btn-ghost" onclick="refreshStaff()">↺ Refresh</button>
    <button class="btn btn-primary" onclick="Modal.open('modal-new-staff')">+ Add Staff Member</button>`;
}

async function loadStaff(url) {
  const tbody = document.getElementById('staffTbody');
  if (!tbody) return;
  tbody.innerHTML = loadingRows(8, 8);

  const params = { search: document.getElementById('searchInput')?.value || '' };

  try {
    const data = url
      ? await fetch(url, { headers: { Authorization: `Bearer ${Auth.getToken()}` } }).then(r => r.json())
      : await API.users(params);
    const users = data?.results || [];
    const count = data?.count ?? users.length;

    tbody.innerHTML = users.length
      ? users.map(u => `<tr>
          <td class="td-mono text-dim">${u.staff_id||'—'}</td>
          <td><div class="d-flex items-center gap-8">${avatarEl(u.full_name||u.email,'avatar-sm')}<b>${u.full_name||u.email}</b></div></td>
          <td><span class="chip chip-fa text-xs tracking-wide">${(u.role||'').replace(/_/g,' ')}</span></td>
          <td>${u.branch_name||'—'}</td>
          <td>${u.region_name||'—'}</td>
          <td class="td-mono text-dim">${u.email}</td>
          <td>${Badge.status(u.is_active?'ACTIVE':'DORMANT')}</td>
          <td class="td-mono text-dim">${Fmt.relTime(u.last_login)}</td>
          <td>
            <div class="d-flex gap-4">
              <button class="btn btn-ghost btn-sm" onclick="editStaff(${u.id},'${u.full_name}')">✏️ Edit</button>
              <button class="btn btn-ghost btn-sm" onclick="resetPw(${u.id},'${u.full_name}')">🔑 Reset PW</button>
              ${Auth.isSuperAdmin() ? `<button class="btn btn-danger btn-sm" onclick="deleteStaff(${u.id},'${u.full_name}')">✕</button>` : ''}
            </div>
          </td>
        </tr>`).join('')
      : `<tr><td colspan="9">${emptyState('👥','No staff found','Add a staff member to get started.')}</td></tr>`;

    renderPagination('staffPagination', data, 'loadStaff');
  } catch (err) {
    console.warn('loadStaff failed:', err);
  }
}

function renderPermissions() {
  const tbody = document.getElementById('permsTbody');
  if (!tbody) return;
  if (typeof PERMS === 'undefined') {
    tbody.innerHTML = `<tr><td colspan="11">${emptyState('⚠️','Not configured','Permission matrix not defined.')}</td></tr>`;
    return;
  }
  tbody.innerHTML = PERMS.map(p =>
    `<tr>
      <td><b>${p.m}</b></td>
      <td>${p.sa}</td>
      <td>${p.rm}</td>
      <td>${p.bm}</td>
      <td>${p.ro}</td>
      <td>${p.ba}</td>
      <td>${p.coll_mgr}</td>
      <td>${p.mkt}</td>
      <td>${p.hop}</td>
      <td>${p.acc}</td>
    </tr>`
  ).join('');
}

async function saveStaff() {
  const data = formData('newStaffForm');
  if (!data.full_name || !data.email || !data.role || !data.password) {
    Toast.error('Name, email, role, and password are required'); return;
  }
  setLoading('saveStaffBtn', true);
  try {
    const user = await API.createUser(data);
    if (user) {
      Toast.success(`${user.full_name} added — welcome email sent`);
      Modal.close('modal-new-staff');
      resetForm('newStaffForm');
      loadStaff();
    }
  } catch (err) { console.warn(err); }
  finally { setLoading('saveStaffBtn', false); }
}

// ─── EDIT STAFF ──────────────────────────────────────────────────────────────
async function editStaff(id, name) {
  try {
    const u = await API.users({ search: '' }).then(d =>
      (d?.results || []).find(x => x.id === id)
    );
    if (!u) { Toast.error('Could not load staff record'); return; }

    document.getElementById('editStaffId').value      = u.id;
    document.getElementById('editStaffName').value    = u.full_name || '';
    document.getElementById('editStaffEmail').value   = u.email || '';
    document.getElementById('editStaffRole').value    = u.role || 'LOAN_OFFICER';
    document.getElementById('editStaffPhone').value   = u.phone || '';
    document.getElementById('editStaffTarget').value  = u.disbursement_target || '';
    document.getElementById('editStaffActive').value  = String(u.is_active !== false);
    document.getElementById('editStaffPw').value      = '';

    // Populate branch selector
    const branchSel = document.getElementById('editStaffBranch');
    if (branchSel) {
      branchSel.innerHTML = '<option value="">No branch</option>';
      const branches = await API.branches().catch(() => null);
      (branches?.results || branches || []).forEach(b => {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = b.name;
        if (b.id === u.branch) opt.selected = true;
        branchSel.appendChild(opt);
      });
    }

    // Populate region selector
    const regionSel = document.getElementById('editStaffRegion');
    if (regionSel) {
      regionSel.innerHTML = '<option value="">No region assigned</option>';
      const regions = await API.regions().catch(() => null);
      (regions?.results || regions || []).forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.id;
        opt.textContent = r.name;
        if (r.id === u.region) opt.selected = true;
        regionSel.appendChild(opt);
      });
    }

    // Deactivate button label
    const deBtn = document.getElementById('deactivateStaffBtn');
    if (deBtn) deBtn.querySelector('.btn-label').textContent =
      u.is_active !== false ? 'Deactivate' : 'Reactivate';

    Modal.open('modal-edit-staff');
  } catch (err) {
    Toast.error('Failed to load staff details');
  }
}

async function updateStaff() {
  const id     = document.getElementById('editStaffId')?.value;
  const name   = document.getElementById('editStaffName')?.value.trim();
  const email  = document.getElementById('editStaffEmail')?.value.trim();
  const role   = document.getElementById('editStaffRole')?.value;
  const branch = document.getElementById('editStaffBranch')?.value || null;
  const region = document.getElementById('editStaffRegion')?.value || null;
  const phone  = document.getElementById('editStaffPhone')?.value.trim();
  const target = document.getElementById('editStaffTarget')?.value;
  const pw     = document.getElementById('editStaffPw')?.value;
  const active = document.getElementById('editStaffActive')?.value === 'true';

  if (!name || !email) { Toast.error('Name and email are required'); return; }

  const payload = { full_name: name, email, role, phone,
                    is_active: active, disbursement_target: target || null };
  if (branch) payload.branch = parseInt(branch);
  if (region) payload.region = parseInt(region);
  if (pw)     payload.password = pw;

  setLoading('updateStaffBtn', true);
  try {
    const u = await API.updateUser(id, payload);
    if (u) {
      Toast.success(`${u.full_name} updated successfully`);
      Modal.close('modal-edit-staff');
      loadStaff();
    }
  } catch (err) { console.warn(err); } finally { setLoading('updateStaffBtn', false); }
}

async function toggleStaffActive() {
  const id     = document.getElementById('editStaffId')?.value;
  const active = document.getElementById('editStaffActive')?.value === 'true';
  const newVal = !active;
  setLoading('deactivateStaffBtn', true);
  try {
    const u = await API.updateUser(id, { is_active: newVal });
    if (u) {
      Toast.success(`${u.full_name} ${newVal ? 'reactivated' : 'deactivated'}`);
      Modal.close('modal-edit-staff');
      loadStaff();
    }
  } catch (err) { console.warn(err); } finally { setLoading('deactivateStaffBtn', false); }
}

// ─── RESET PASSWORD ───────────────────────────────────────────────────────────
function resetPw(id, name) {
  document.getElementById('resetPwStaffId').value   = id;
  document.getElementById('resetPwStaffName').textContent = name;
  document.getElementById('newStaffPw').value        = '';
  document.getElementById('confirmStaffPw').value    = '';
  Modal.open('modal-reset-pw');
}

async function saveResetPw() {
  const id  = document.getElementById('resetPwStaffId')?.value;
  const pw  = document.getElementById('newStaffPw')?.value;
  const pw2 = document.getElementById('confirmStaffPw')?.value;

  if (!pw || pw.length < 8) { Toast.error('Password must be at least 8 characters'); return; }
  if (pw !== pw2)           { Toast.error('Passwords do not match'); return; }

  setLoading('saveNewPwBtn', true);
  try {
    const u = await API.updateUser(id, { password: pw });
    if (u) {
      Toast.success(`Password reset for ${u.full_name}`);
      Modal.close('modal-reset-pw');
    }
  } catch (err) { console.warn(err); } finally { setLoading('saveNewPwBtn', false); }
}
const onSearch = debounce(() => loadStaff(), 350);

// Load branches for the staff form
async function loadBranchOptions() {
  try {
    const d = await API.branches();
    const sel = document.getElementById('staffBranchSel');
    if (!sel) return;
    (d?.results || d || []).forEach(b => {
      sel.innerHTML += `<option value="${b.id}">${b.name}</option>`;
    });
  } catch (err) { console.warn(err); }
}

// Load regions for the staff form
async function loadRegionOptions() {
  try {
    const d = await API.regions();
    const sel = document.getElementById('staffRegionSel');
    if (!sel) return;
    (d?.results || d || []).forEach(r => {
      sel.innerHTML += `<option value="${r.id}">${r.name}</option>`;
    });
  } catch (err) { console.warn(err); }
}

// Delete staff user
async function deleteStaff(id, name) {
  if (!await QL.confirm(`Remove <b>${name}</b> from the system?<br><span class='text-sm text-dim'>This cannot be undone.</span>`, {title:'Remove Staff', okLabel:'Remove', danger:true})) return;
  try {
    await API.deleteUser(id);
    Toast.success(`${name} removed`);
    loadStaff();
  } catch (err) { console.warn(err); }
}

// Reload button
function refreshStaff() { loadStaff(); }
