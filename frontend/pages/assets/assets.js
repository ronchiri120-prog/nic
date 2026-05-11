Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}
document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('assets');
  document.getElementById('topbarActions').innerHTML = `
    <div class="topbar-search">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search…" oninput="onSearch()">
    </div>
    <select class="form-control" id="assetCatFilter" class="filter-ctrl-lg" onchange="loadAssets()">
      <option value="">All Types</option>
      <option value="VEHICLE">Motor Vehicle</option>
      <option value="MOTORCYCLE">Motorcycle</option>
      <option value="LAND">Land/Property</option>
      <option value="OTHER">Other</option>
    </select>
    <button class="btn btn-ghost" onclick="exportAssets()">⬇ Export</button>
    <button class="btn btn-primary" onclick="Modal.open('modal-new-asset')">+ Register Asset</button>
  `;
  loadAssets();
});

async function loadAssets() {
  // Load KPIs first
  try {
    const all = await API.assets({ page_size: 1000 });
    const items = all?.results || all || [];
    const total     = items.length;
    const active    = items.filter(a => a.status === 'ACTIVE').length;
    const totalVal  = items.reduce((s, a) => s + parseFloat(a.current_value || a.estimated_value || 0), 0);
    const avgLTV    = items.length ? items.reduce((s, a) => s + parseFloat(a.ltv_ratio || 0), 0) / items.length : 0;
    const kpis = document.getElementById('asset-kpis');
    if (!kpis) {
      const kpiEl = document.createElement('div');
      kpiEl.id = 'asset-kpis';
      kpiEl.className = 'kpi-grid kpi-grid-4 animate-fadeup';
      kpiEl.classList.add('mb-20');
      kpiEl.innerHTML = `
        <div class="kpi-card kc-blue grad"><div class="kpi-label">Total Assets</div><div class="kpi-value">${total}</div></div>
        <div class="kpi-card kc-green grad"><div class="kpi-label">Active</div><div class="kpi-value">${active}</div></div>
        <div class="kpi-card kc-gold grad"><div class="kpi-label">Total Value</div><div class="kpi-value">${Fmt.currency(totalVal)}</div></div>
        <div class="kpi-card kc-purple grad"><div class="kpi-label">Avg LTV</div><div class="kpi-value">${Fmt.pct(avgLTV)}</div></div>`;
      document.getElementById('pageContent')?.prepend(kpiEl);
    }
  } catch (err) {
    const tb = document.getElementById('assetsTbody');
    if (tb) tb.innerHTML = `<tr><td colspan="9" class="td-error">Failed to load assets</td></tr>`;
  }

  const tbody = document.getElementById('assetTbody');
  if(!tbody) return;
  tbody.innerHTML = loadingRows(8, 8);
  const params = {
    category: document.getElementById('assetCatFilter')?.value || '',
    search:   document.getElementById('searchInput')?.value || '',
  };
  try {
    const d = await API.assets(params);
    const assets = d?.results || [];
    document.getElementById('assetCount').textContent = `${d?.count||assets.length} assets`;
    tbody.innerHTML = assets.length ? assets.map(a => `<tr>
      <td class="td-mono text-brand">${a.asset_id}</td>
      <td><b>${a.customer_name||'—'}</b></td>
      <td>${a.category}</td>
      <td>${[a.make, a.model, a.year].filter(Boolean).join(' ') || '—'}</td>
      <td class="td-mono">${a.reg_number||'—'}</td>
      <td class="td-mono text-brand">${Fmt.currency(a.valuation)}</td>
      <td class="td-mono ${(a.ltv||0)>70?'text-red':'text-brand'}">${a.ltv||0}%</td>
      <td class="td-mono text-dim">${a.loan_id||'—'}</td>
      <td class="td-mono text-dim">${Fmt.date(a.valued_at)}</td>
      <td>${Badge.status(a.is_active?'ACTIVE':'DORMANT')}</td>
    </tr>`).join('') : `<tr><td colspan="10">${emptyState('🚗','No assets registered','Register a logbook or land title.')}</td></tr>`;
  } catch { tbody.innerHTML = `<tr><td colspan="10" class="text-center text-red p-20">Failed to load</td></tr>`; }
}

async function saveAsset() {
  const data = formData('newAssetForm');
  if(!data.customer||!data.valuation||!data.category) { Toast.error('Customer, category, and valuation required'); return; }
  setLoading('saveAssetBtn', true);
  try {
    const a = await API.createAsset(data);
    if(a) { Toast.success(`Asset ${a.asset_id} registered`); Modal.close('modal-new-asset'); loadAssets(); }
  } catch (err) { console.warn(err); } finally { setLoading('saveAssetBtn', false); }
}

const onSearch = debounce(() => loadAssets(), 350);

// Update asset status
async function deactivateAsset(id, ref) {
  if (!await QL.confirm(`Deactivate asset <b>${ref}</b>?`, {title:'Deactivate Asset', okLabel:'Deactivate', danger:true})) return;
  try {
    await API.updateAsset(id, { is_active: false });
    Toast.success(`Asset ${ref} deactivated`);
    loadAssets();
  } catch (err) { console.warn(err); }
}

// Quick valuation update
async function updateValuation(id, ref) {
  const val = await QL.prompt(`New valuation for ${ref} (KES):`, '', {title:'Update Valuation', placeholder:'e.g. 1500000', type:'number'});
  if (!val || isNaN(val)) return;
  try {
    await API.updateAsset(id, { valuation: parseFloat(val) });
    Toast.success(`Valuation updated to ${Fmt.currency(parseFloat(val))}`);
    loadAssets();
  } catch (err) { console.warn(err); }
}

// Download asset register as CSV
function exportAssets() {
  const b = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
  window.open(`${b}/api/v1/assets/export/`, '_blank');
  Toast.success('Asset register downloading…');
}
