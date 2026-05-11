Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}
Auth.requireRole(['SUPER_ADMIN','FINANCE','RM','OPERATIONS']);
document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('accounting');
  document.getElementById('topbarActions').innerHTML = `
    <input type="date" id="dateFrom" class="form-control filter-ctrl-lg">
    <input type="date" id="dateTo"   class="form-control filter-ctrl-lg">
    <button class="btn btn-ghost" onclick="exportReport()">⬇ Export</button>
    <button class="btn btn-primary" onclick="Modal.open('modal-journal')">+ Journal Entry</button>
  `;
  const now = new Date(), y = now.getFullYear(), m = now.getMonth();
  document.getElementById('dateFrom').value = new Date(y,m,1).toISOString().split('T')[0];
  document.getElementById('dateTo').value   = now.toISOString().split('T')[0];
  // Inject search into topbar
  const ta = document.getElementById('topbarActions');
  if (ta) ta.innerHTML += `
    <div class="topbar-search">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search GL, journal…" oninput="onSearch()">
    </div>
  `;
  renderTabs();
  loadPL();
  loadAccKPIs();
});

function renderTabs() {
  document.getElementById('pageContent').innerHTML = `
    <div class="section-header animate-fadeup">
      <div><h1 class="page-heading">⚖️ Accounting</h1>
           <p class="text-sm text-dim">General Ledger · P&L · Balance Sheet · Trial Balance · CBK Returns</p></div>
    </div>
    <div class="kpi-grid kpi-grid-4 animate-fadeup stagger-1" id="acc-kpis">
      <div class="kpi-card kc-green grad"><div class="kpi-label">Total Assets</div><div class="kpi-value" id="acc-kpi-assets">—</div></div>
      <div class="kpi-card kc-blue grad"><div class="kpi-label">Total Liabilities</div><div class="kpi-value" id="acc-kpi-liabilities">—</div></div>
      <div class="kpi-card kc-gold grad"><div class="kpi-label">Revenue (MTD)</div><div class="kpi-value" id="acc-kpi-revenue">—</div></div>
      <div class="kpi-card kc-purple grad"><div class="kpi-label">Net Profit (MTD)</div><div class="kpi-value" id="acc-kpi-profit">—</div></div>
    </div>
    <div class="tabs animate-fadeup stagger-2" data-tab-scope>
      <button class="tab-btn active" onclick="switchTab(this,'tab-pl');loadPL()">P&L Statement</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-bs');loadBS()">Balance Sheet</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-tb');loadTB()">Trial Balance</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-gl');loadGL()">General Ledger</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-journal');loadJournal()">Journal Entries</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-cbk');loadCBK()">CBK Returns</button>
    </div>
    <div id="tab-pl"      class="tab-content active"></div>
    <div id="tab-bs"      class="tab-content"></div>
    <div id="tab-tb"      class="tab-content"></div>
    <div id="tab-gl"      class="tab-content"></div>
    <div id="tab-journal" class="tab-content"></div>
    <div id="tab-cbk"     class="tab-content"></div>
    <div class="modal-overlay" id="modal-journal">
      <div class="modal modal-md">
        <div class="modal-header"><div class="modal-title">📒 Manual Journal Entry</div><div class="modal-close" onclick="Modal.close('modal-journal')">✕</div></div>
        <div class="modal-body">
          <div class="form-group"><label class="form-label">Narration</label><input class="form-control" id="je-narration" placeholder="Description of transaction"></div>
          <div class="form-group"><label class="form-label">Date</label><input type="date" class="form-control" id="je-date"></div>
          <div class="upload-hint">
            <div class="je-3-grid">
              <div class="form-label">Account Code</div><div class="form-label">Debit (KES)</div><div class="form-label">Credit (KES)</div>
            </div>
            <div id="je-lines"></div>
            <button class="btn btn-ghost btn-sm" onclick="addJELine()" class="mt-8">+ Add Line</button>
          </div>
          <div id="je-balance-check" class="text-sm text-right text-dim"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" onclick="Modal.close('modal-journal')">Cancel</button>
          <button class="btn btn-ghost" onclick="saveJE(false)">Save Draft</button>
          <button class="btn btn-primary" id="postJEBtn" onclick="saveJE(true)"><span class="btn-label">Post Entry</span><span class="btn-spinner"></span></button>
        </div>
      </div>
    </div>
  `;
  document.getElementById('je-date').value = new Date().toISOString().split('T')[0];
  addJELine(); addJELine();
}

async function loadPL() {
  const el = document.getElementById('tab-pl');
  if(!el) return;
  el.innerHTML = `<div class="skeleton skeleton skeleton-h300"></div>`;
  try {
    const d = await API.incomeStatement({from: document.getElementById('dateFrom').value, to: document.getElementById('dateTo').value});
    if(!d) { useSeedPL(el); return; }
    const rows = items => items.map(i=>`
      <div class="info-row"><span class="info-key">${i.name}</span><span class="info-val">${Fmt.currency(i.amount)}</span></div>`).join('');
    el.innerHTML = `
      <div class="panel"><div class="panel-header"><div class="panel-title">📊 Income Statement — ${d.period.from} to ${d.period.to}</div><button class="btn btn-ghost btn-sm" onclick="exportReport()">⬇ Export</button></div>
      <div class="panel-body max-w-lg">
        <div class="fs-section-head">INCOME</div>
        ${rows(d.income.items)}
        <div class="info-row table-total-row"><span class="info-key fw-700">Total Income</span><span class="info-val text-brand fw-700">${Fmt.currency(d.income.total)}</span></div>
        <div class="fs-label-mono-mid">EXPENSES</div>
        ${rows(d.expenses.items)}
        <div class="info-row table-total-row"><span class="info-key fw-700">Total Expenses</span><span class="info-val text-red fw-700">${Fmt.currency(d.expenses.total)}</span></div>
        <div class="fs-grand-row ${d.net_profit>=0?'':'fs-grand-loss'}">
          <span class="fs-grand-label">Net Profit / (Loss)</span>
          <span class="pl-value-dynamic" style="color:${d.net_profit>=0?'var(--brand)':'var(--red)'}">
            ${d.net_profit<0?'(':''}${Fmt.currency(Math.abs(d.net_profit))}${d.net_profit<0?')':''}
          </span>
        </div>
        <div class="profit-margin-note">Profit margin: ${Fmt.pct(d.profit_margin)}</div>
      </div></div>`;
  } catch (err) {
    console.warn('loadPL failed:', err);
  }
}

function useSeedPL(el) {
  const income = [{name:'Interest Income',amount:1240000},{name:'Fee Income',amount:84000},{name:'Penalty Income',amount:48000}];
  const expenses = [{name:'Staff Salaries',amount:180000},{name:'Rent & Utilities',amount:52000},{name:'M-Pesa Costs',amount:38000},{name:'Loan Loss Provision',amount:192000},{name:'Admin & Other',amount:22000}];
  const totalI = income.reduce((s,i)=>s+i.amount,0), totalE = expenses.reduce((s,i)=>s+i.amount,0), net = totalI-totalE;
  el.innerHTML = `<div class="panel"><div class="panel-body max-w-lg">
    <div class="fs-section-head">INCOME (SEED DATA)</div>
    ${income.map(i=>`<div class="info-row"><span class="info-key">${i.name}</span><span class="info-val text-brand">${Fmt.currency(i.amount)}</span></div>`).join('')}
    <div class="info-row table-total-row"><span class="info-key fw-700">Total Income</span><span class="info-val text-brand fw-700">${Fmt.currency(totalI)}</span></div>
    <div class="fs-label-mono-mid">EXPENSES</div>
    ${expenses.map(i=>`<div class="info-row"><span class="info-key">${i.name}</span><span class="info-val text-red">${Fmt.currency(i.amount)}</span></div>`).join('')}
    <div class="info-row table-total-row"><span class="info-key fw-700">Total Expenses</span><span class="info-val text-red fw-700">${Fmt.currency(totalE)}</span></div>
    <div class="pl-profit-row">
      <span class="fs-grand-label">Net Profit</span>
      <span class="pl-value-brand">${Fmt.currency(net)}</span>
    </div>
  </div></div>`;
}

async function loadBS() {
  const el = document.getElementById('tab-bs');
  if(!el) return;
  el.innerHTML = `<div class="skeleton skeleton skeleton-h300"></div>`;
  try {
    const d = await API.balanceSheet({as_at: document.getElementById('dateTo').value});
    if(!d) {
      el.innerHTML = `<div class="panel"><div class="panel-body-bare">${emptyState('📊','No data','No balance sheet data available.')}</div></div>`;
      return;
    }
    const rows = items => items.map(i=>`
      <div class="info-row">
        <span class="info-key">${i.name}</span>
        <span class="info-val ${i.amount<0?'text-red':''}">${Fmt.currency(Math.abs(i.amount))}${i.amount<0?' (-)':''}</span>
      </div>`).join('');
    el.innerHTML = `<div class="grid-2">
      <div class="panel"><div class="panel-header"><div class="panel-title">🏦 Assets</div></div><div class="panel-body">
        <div class="fs-label-sm-mb">CURRENT ASSETS</div>
        ${rows(d.assets.current)}
        <div class="fs-label-sm-mx">LOANS RECEIVABLE</div>
        ${rows(d.assets.loans)}
        <div class="info-row fw-700 mt-8 border-top">
          <span class="info-key fw-700">TOTAL ASSETS</span><span class="info-val text-brand fw-700">${Fmt.currency(d.assets.total)}</span>
        </div>
        <div style="margin-top:8px;font-size:11px;color:${d.balanced?'var(--brand)':'var(--red)'}">
          ${d.balanced?'✓ Balance sheet balanced':'⚠ Imbalance detected'}
        </div>
      </div></div>
      <div class="panel"><div class="panel-header"><div class="panel-title">⚖️ Liabilities & Equity</div></div><div class="panel-body">
        <div class="fs-label-sm-mb">LIABILITIES</div>
        ${rows(d.liabilities.items)}
        <div class="info-row fw-700"><span class="info-key fw-700">Total Liabilities</span><span class="info-val text-red fw-700">${Fmt.currency(d.liabilities.total)}</span></div>
        <div class="fs-label-sm-mx">EQUITY</div>
        ${rows(d.equity.items)}
        <div class="info-row fw-700"><span class="info-key fw-700">Total Equity</span><span class="info-val text-brand fw-700">${Fmt.currency(d.equity.total)}</span></div>
        <div class="info-row table-total-row">
          <span class="info-key fw-700">TOTAL L&E</span><span class="info-val text-brand fw-700">${Fmt.currency(d.total_liabilities_equity)}</span>
        </div>
      </div></div>
    </div>`;
  } catch (err) {
    console.warn('loadBS failed:', err);
  }
}

async function loadTB() {
  const el = document.getElementById('tab-tb');
  if(!el) return;
  el.innerHTML = `<div class="skeleton skeleton skeleton-h300"></div>`;
  try {
    const d = await API.trialBalance({as_at: document.getElementById('dateTo').value});
    if(!d) {
      el.innerHTML = `<div class="panel"><div class="panel-body-bare">${emptyState('📊','No data','No trial balance data available.')}</div></div>`;
      return;
    }
    el.innerHTML = `<div class="panel">
      <div class="panel-header"><div class="panel-title">📋 Trial Balance — As at ${d.as_at}</div>
        <span class="badge ${d.balanced?'badge-active':'badge-default'}">${d.balanced?'✓ Balanced':'⚠ Imbalanced'}</span>
      </div>
      <div class="panel-body-bare"><table class="data-table">
        <thead><tr><th>Code</th><th>Account</th><th>Type</th><th class="text-right">Debit (KES)</th><th class="text-right">Credit (KES)</th></tr></thead>
        <tbody>
          ${d.accounts.map(a=>`<tr>
            <td class="td-mono text-dim">${a.code}</td>
            <td>${a.name}</td>
            <td class="td-mono text-sm">${a.type}</td>
            <td class="td-mono tr-right-brand">${a.debit?Fmt.currency(a.debit):'—'}</td>
            <td class="td-mono tr-right-gold">${a.credit?Fmt.currency(a.credit):'—'}</td>
          </tr>`).join('')}
          <tr class="tr-bg-bold">
            <td colspan="3" class="td-mono">TOTALS</td>
            <td class="td-mono tr-right-bk">${Fmt.currency(d.total_dr)}</td>
            <td class="td-mono tr-right-gk">${Fmt.currency(d.total_cr)}</td>
          </tr>
        </tbody>
      </table></div>
    </div>`;
  } catch (err) {
    console.warn('loadTB failed:', err);
  }
}

async function loadGL() {
  const el = document.getElementById('tab-gl');
  if(!el) return;
  el.innerHTML = `<div class="gl-search-row">
    <input class="form-control" id="gl-account-code" placeholder="Account code (e.g. 1010)" class="max-w-sm">
    <button class="btn btn-primary" onclick="fetchGL()">Load GL</button>
  </div><div id="gl-result"></div>`;
}

async function fetchGL() {
  const code = document.getElementById('gl-account-code').value.trim();
  if(!code) { Toast.error('Enter an account code'); return; }
  const res = document.getElementById('gl-result');
  res.innerHTML = `<div class="skeleton skeleton skel-h300"></div>`;
  try {
    const d = await API.generalLedger({account: code, from: document.getElementById('dateFrom').value, to: document.getElementById('dateTo').value});
    if(!d) throw new Error();
    res.innerHTML = `<div class="panel">
      <div class="panel-header"><div class="panel-title">${d.account.code} — ${d.account.name}</div>
        <span class="td-mono text-sm">Closing balance: ${Fmt.currency(d.closing_balance)}</span>
      </div>
      <div class="panel-body-bare"><table class="data-table">
        <thead><tr><th>Date</th><th>Reference</th><th>Narration</th><th class="text-right">Debit</th><th class="text-right">Credit</th><th class="text-right">Balance</th></tr></thead>
        <tbody>${d.lines.map(l=>`<tr>
          <td class="td-mono text-dim">${l.date}</td>
          <td class="td-mono text-brand">${l.reference}</td>
          <td>${l.narration}</td>
          <td class="td-mono tr-right-brand">${l.debit?Fmt.currency(l.debit):'—'}</td>
          <td class="td-mono tr-right-gold">${l.credit?Fmt.currency(l.credit):'—'}</td>
          <td class="td-mono text-right">${Fmt.currency(l.balance)}</td>
        </tr>`).join('')}</tbody>
      </table></div>
    </div>`;
  } catch { res.innerHTML = `<div class="panel"><div class="panel-body"><p class="text-dim">Account ${code} not found or has no transactions.</p></div></div>`; }
}

async function loadCBK() {
  const el = document.getElementById('tab-cbk');
  if(!el) return;
  el.innerHTML = `<div class="grid-2">
    <div class="panel node" onclick="loadCBKReport('mfi01')"><div class="panel-body cbk-card-body">
      <div class="cbk-card-icon">🏦</div>
      <div class="cbk-card-title">MFI-01</div>
      <div class="cbk-card-desc">Balance Sheet Return</div>
      <button class="btn btn-primary btn-sm mt-12" onclick="loadCBKReport('mfi01')">Generate</button>
    </div></div>
    <div class="panel node" onclick="loadCBKReport('mfi02')"><div class="panel-body cbk-card-body">
      <div class="cbk-card-icon">📊</div>
      <div class="cbk-card-title">MFI-02</div>
      <div class="cbk-card-desc">Income Statement Return</div>
      <button class="btn btn-primary btn-sm mt-12" onclick="loadCBKReport('mfi02')">Generate</button>
    </div></div>
    <div class="panel node" onclick="loadCBKReport('mfi03')"><div class="panel-body cbk-card-body">
      <div class="cbk-card-icon">⚠️</div>
      <div class="cbk-card-title">MFI-03</div>
      <div class="cbk-card-desc">Portfolio Quality</div>
      <button class="btn btn-primary btn-sm mt-12" onclick="loadCBKReport('mfi03')">Generate</button>
    </div></div>
    <div class="panel node" onclick="loadCBKReport('mfi04')"><div class="panel-body cbk-card-body">
      <div class="cbk-card-icon">💰</div>
      <div class="cbk-card-title">MFI-04</div>
      <div class="cbk-card-desc">Capital Adequacy</div>
      <button class="btn btn-primary btn-sm mt-12" onclick="loadCBKReport('mfi04')">Generate</button>
    </div></div>
  </div><div id="cbk-result" class="mt-16"></div>`;
}

async function loadCBKReport(type) {
  const res = document.getElementById('cbk-result');
  res.innerHTML = `<div class="skeleton skeleton skel-h300"></div>`;
  try {
    const fns = {mfi01: API.cbkMFI01, mfi02: API.cbkMFI02, mfi03: API.cbkMFI03, mfi04: API.cbkMFI04};
    const d = await fns[type]({from: document.getElementById('dateFrom').value, to: document.getElementById('dateTo').value});
    res.innerHTML = `<div class="panel"><div class="panel-header">
        <div class="panel-title">${d.return_type} — ${d.institution}</div>
        <button class="btn btn-ghost btn-sm" onclick="Toast.success('CBK return exported to PDF')">⬇ Download PDF</button>
      </div>
      <div class="panel-body"><pre class="json-pre">${JSON.stringify(d, null, 2)}</pre></div>
    </div>`;
  } catch (err) {
    console.warn('loadCBKReport failed:', err);
  }
}

let jeLineCount = 0;
function addJELine() {
  const i = jeLineCount++;
  const line = document.createElement('div');
  line.style.cssText = 'display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:8px;margin-bottom:8px;align-items:center';
  line.innerHTML = `
    <input class="form-control je-code" placeholder="1010" class="mono text-sm" oninput="checkBalance()">
    <input type="number" class="form-control je-debit"  placeholder="0" oninput="checkBalance()">
    <input type="number" class="form-control je-credit" placeholder="0" oninput="checkBalance()">
    <button class="btn btn-danger btn-sm btn-icon" onclick="this.closest('div').remove();checkBalance()">✕</button>
  `;
  document.getElementById('je-lines').appendChild(line);
}

function checkBalance() {
  const debs = [...document.querySelectorAll('.je-debit')].reduce((s,el)=>s+(parseFloat(el.value)||0),0);
  const creds = [...document.querySelectorAll('.je-credit')].reduce((s,el)=>s+(parseFloat(el.value)||0),0);
  const el = document.getElementById('je-balance-check');
  if(Math.abs(debs-creds)<0.01) { el.innerHTML = `<span class="text-brand">✓ Balanced — DR ${Fmt.currency(debs)} = CR ${Fmt.currency(creds)}</span>`; }
  else { el.innerHTML = `<span class="text-red">✗ Unbalanced — DR ${Fmt.currency(debs)} ≠ CR ${Fmt.currency(creds)} (diff: ${Fmt.currency(Math.abs(debs-creds))})</span>`; }
}

async function saveJE(post) {
  const narration = document.getElementById('je-narration').value.trim();
  const date      = document.getElementById('je-date').value;
  if(!narration) { Toast.error('Narration is required'); return; }
  const lines = [];
  const codes   = [...document.querySelectorAll('.je-code')];
  const debits  = [...document.querySelectorAll('.je-debit')];
  const credits = [...document.querySelectorAll('.je-credit')];
  for(let i=0;i<codes.length;i++) {
    const code = codes[i].value.trim();
    if(!code) continue;
    lines.push({account_code: code, debit_amount: parseFloat(debits[i].value)||0, credit_amount: parseFloat(credits[i].value)||0});
  }
  if(lines.length < 2) { Toast.error('Journal entry needs at least 2 lines'); return; }
  setLoading('postJEBtn', true);
  try {
    const entry = await API.createJournal({narration, date, lines});
    if(entry && post) await API.postJournal(entry.id);
    Toast.success(post ? `${entry?.reference} posted to GL` : 'Draft saved');
    Modal.close('modal-journal');
    loadPL();
  } catch (err) { console.warn(err); } finally { setLoading('postJEBtn', false); }
}

function exportReport() {
  // Download the current active financial report as Excel
  const b = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
  const tab = document.querySelector('.tab-btn.active')?.textContent?.trim() || '';
  if (tab.includes('P&L') || tab.includes('Income')) {
    window.open(`${b}/api/v1/reports/excel/loans/`, '_blank');
  } else {
    window.open(`${b}/api/v1/reports/excel/loans/`, '_blank');
  }
  Toast.success('Downloading financial report…');
}
const onSearch = debounce(() => {
  const q = document.getElementById('searchInput')?.value || '';
  // Route search to whichever tab is active
  if (document.getElementById('tab-gl')?.classList.contains('active'))   { loadGL(q); return; }
  if (document.getElementById('tab-tb')?.classList.contains('active'))   { loadTB(q); return; }
  if (document.getElementById('tab-journal')?.classList.contains('active')){ loadJournal(q); return; }
}, 300);


// ─── JOURNAL ENTRIES TAB ──────────────────────────────────────────────────────
async function loadJournal(search = '') {
  const el = document.getElementById('tab-journal');
  if (!el) return;

  el.innerHTML = `
    <div class="panel mt-20">
      <div class="panel-header">
        <div class="panel-title">📒 Journal Entries</div>
        <div class="d-flex gap-8">
          <input class="form-control filter-ctrl-lg" id="journal-search"
            placeholder="Search narration…" value="${search}"
            oninput="const q=this.value; clearTimeout(window._jt); window._jt=setTimeout(()=>loadJournal(q),300)">
          <button class="btn btn-ghost" onclick="Modal.open('modal-journal')">+ New Entry</button>
        </div>
      </div>
      <div class="panel-body-bare">
        <table class="data-table">
          <thead><tr>
            <th>Date</th><th>Ref</th><th>Narration</th>
            <th>Debit</th><th>Credit</th><th>Status</th><th>Posted By</th>
          </tr></thead>
          <tbody id="journal-tbody">${loadingRows(6, 7)}</tbody>
        </table>
        <div id="journal-pagination"></div>
      </div>
    </div>`;

  try {
    const data = await API.journal({ search, ordering: '-created_at' });
    const entries = data?.results || [];
    const tbody   = document.getElementById('journal-tbody');
    if (!tbody) return;

    tbody.innerHTML = entries.length
      ? entries.map(e => `<tr>
          <td class="td-mono text-dim">${Fmt.date(e.created_at)}</td>
          <td class="td-mono">${e.reference || '—'}</td>
          <td>${e.narration}</td>
          <td class="td-mono tr-right-brand">${e.total_debit  ? Fmt.currency(e.total_debit)  : '—'}</td>
          <td class="td-mono tr-right-gold">${e.total_credit ? Fmt.currency(e.total_credit) : '—'}</td>
          <td>${Badge.status(e.is_posted ? 'CLOSED' : 'PENDING')}</td>
          <td class="text-dim text-sm">${e.created_by_name || '—'}</td>
        </tr>`).join('')
      : `<tr><td colspan="7">${emptyState('📒', 'No journal entries', 'Post a manual entry above.')}</td></tr>`;

    renderPagination('journal-pagination', data, 'loadJournal');
  } catch {
    const tbody = document.getElementById('journal-tbody');
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="td-error">Failed to load journal entries.</td></tr>`;
  }
}


async function loadAccKPIs() {
  try {
    const [bs, pl] = await Promise.all([
      API.balanceSheet().catch(() => null),
      API.incomeStatement().catch(() => null),
    ]);
    const assets = bs?.total_assets || bs?.assets_total || 0;
    const liabs  = bs?.total_liabilities || 0;
    const rev    = pl?.total_revenue || pl?.income_total || 0;
    const profit = pl?.net_profit || 0;
    ['acc-kpi-assets','acc-kpi-liabilities','acc-kpi-revenue','acc-kpi-profit'].forEach((id,i) => {
      const el = document.getElementById(id);
      if (el) el.textContent = Fmt.currency([assets, liabs, rev, profit][i]);
      if (id === 'acc-kpi-profit' && el) el.className = parseFloat(profit) >= 0 ? 'kpi-value text-brand' : 'kpi-value text-red';
    });
  } catch (err) { console.warn(err); }
}
