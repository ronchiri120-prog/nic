Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}
document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('allocations');
  loadBranchFilter().then(() => loadAllocations());
  document.getElementById('topbarActions').innerHTML = `
    <select class="form-control" id="branchSel" class="filter-ctrl-xl" onchange="loadAllocations()">
      <option value="">All Branches</option>
    </select>
    <button class="btn btn-ghost" onclick="softReshuffle()">🔀 Soft Reshuffle</button>
    <button class="btn btn-danger btn-sm" onclick="hardReshuffle()">⚡ Hard Reshuffle</button>
  `;
});

async function loadBranchFilter() {
  try {
    const d = await API.branches();
    const sel = document.getElementById('branchSel');
    (d?.results||d||[]).forEach(b => { sel.innerHTML += `<option value="${b.id}">${b.name}</option>`; });
  } catch (err) { console.warn(err); }
}

async function loadAllocations() {
  const tbody = document.getElementById('allocTbody');
  if(!tbody) return;
  tbody.innerHTML = loadingRows(7, 7);
  const params = {branch: document.getElementById('branchSel')?.value||'', is_active: true};
  try {
    const d = await API.allocations(params);
    const allocs = d?.results || [];
    document.getElementById('allocCount').textContent = `${d?.count||allocs.length} allocations`;
    tbody.innerHTML = allocs.length ? allocs.map(a => `<tr>
      <td><div class="alloc-agent-cell">${avatarEl(a.agent_name||'?')}<b>${a.agent_name||'—'}</b></div></td>
      <td class="td-mono text-brand">${a.loan_id||'—'}</td>
      <td>${a.customer||'—'}</td>
      <td>${a.branch_name||'—'}</td>
      <td class="td-mono text-dim">${Fmt.date(a.assigned_at)}</td>
      <td>${Badge.status(a.is_active?'ACTIVE':'DORMANT')}</td>
      <td><button class="btn btn-ghost btn-sm" onclick="reassign(${a.loan}, '${a.loan_id||a.loan}')">Reassign</button></td>
    </tr>`).join('') : `<tr><td colspan="7">${emptyState('🔀','No allocations','Run a reshuffle to allocate loans.')}</td></tr>`;
  } catch (err) {
    console.warn('loadAllocations failed:', err);
  }
}

async function softReshuffle() {
  const btn = document.querySelector('[onclick="softReshuffle()"]');
  if (btn) btn.disabled = true;
  const branchId = document.getElementById('branchSel')?.value;
  if(!branchId) { Toast.error('Select a branch first'); return; }
  Toast.warn('Soft reshuffle — allocating unassigned loans…');
  try {
    const r = await API.softReshuffle({branch_id: parseInt(branchId)});
    Toast.success(r?.detail || 'Soft reshuffle complete');
    loadAllocations();
  } catch (err) { console.warn(err); }
}

async function hardReshuffle() {
  if (!await QL.confirm('Hard reshuffle will reassign <b>ALL customers</b>. Continue?', {title:'Hard Reshuffle', okLabel:'Reshuffle', danger:true})) return;
  const branchId = document.getElementById('branchSel')?.value;
  if(!branchId) { Toast.error('Select a branch first'); return; }
  if(!await QL.confirm('Hard reshuffle will reassign <b>ALL active loans</b> across agents. Continue?', {title:'Hard Reshuffle', okLabel:'Reshuffle', danger:true})) return;
  try {
    const r = await API.hardReshuffle({branch_id: parseInt(branchId)});
    Toast.success(r?.detail || 'Hard reshuffle complete');
    loadAllocations();
  } catch (err) { console.warn(err); }
}

async function reassign(allocationId, loanRef) {
  document.getElementById('reassignLoanId').value       = allocationId;
  document.getElementById('reassignLoanRef').textContent = loanRef || allocationId;
  document.getElementById('reassignReason').value       = '';

  // Load officers into selector
  const sel = document.getElementById('reassignAgentSel');
  if (sel) {
    sel.innerHTML = '<option value="">Loading…</option>';
    try {
      const users = await API.users({ role: 'LOAN_OFFICER' });
      const list  = users?.results || users || [];
      sel.innerHTML = '<option value="">Select loan officer…</option>' +
        list.map(u => `<option value="${u.id}">${u.full_name} (${u.branch_name || 'No branch'})</option>`).join('');
    } catch {
      sel.innerHTML = '<option value="">Could not load officers</option>';
    }
  }

  Modal.open('modal-reassign');
}

async function confirmReassign() {
  const allocationId = document.getElementById('reassignLoanId')?.value;
  const agentId      = document.getElementById('reassignAgentSel')?.value;
  const reason       = document.getElementById('reassignReason')?.value.trim();

  if (!agentId) { Toast.error('Select a loan officer'); return; }

  setLoading('confirmReassignBtn', true);
  try {
    const r = await API.createAllocation({ loan: allocationId, loan_officer: agentId, notes: reason });
    if (r) {
      Toast.success('Loan reassigned successfully');
      Modal.close('modal-reassign');
      loadAllocations();
    }
  } catch (err) { console.warn(err); } finally { setLoading('confirmReassignBtn', false); }
}
const onSearch = debounce(() => loadAllocations(), 350);
