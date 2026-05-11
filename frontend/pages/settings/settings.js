/**
 * Settings — fully live: loan products, fiscal periods, SMS stats, system config
 */
Auth.require();
// API availability guard
if (typeof API === "undefined") {
  document.body.className = "ql-fatal-error";
  document.body.innerHTML =
    '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error("api.js not loaded");
}
Auth.requireRole(["SUPER_ADMIN", "RM", "OPERATIONS"]);

document.addEventListener("DOMContentLoaded", () => {
  loadSidebar("settings");
  document.getElementById("topbarActions").innerHTML =
    `<div class="topbar-search">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search…" oninput="onSearch()">
    </div>
    <button class="btn btn-primary" onclick="saveAllSettings()">💾 Save Changes</button>`;
  renderLayout();
  loadProducts();
  loadFiscalPeriods();
  loadSmsStats();
});

function renderLayout() {
  document.getElementById("pageContent").innerHTML = `
    <div class="section-header animate-fadeup"><div>
      <h1 class="page-heading">⚙️ Settings</h1>
      <p class="text-sm text-dim">Loan products · Fiscal periods · M-Pesa · SMS · System</p>
    </div></div>
    <div class="tabs animate-fadeup stagger-1" data-tab-scope>
      <button class="tab-btn active" onclick="switchTab(this,'tab-products')">Loan Products</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-fiscal');loadFiscalPeriods()">Fiscal Periods</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-mpesa')">M-Pesa</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-sms');loadSmsStats()">SMS / Email</button>
      <button class="tab-btn" onclick="switchTab(this,'tab-system')">System</button>
    </div>
    <div id="tab-products" class="tab-content active">
      <div class="panel">
        <div class="panel-header"><div class="panel-title">💰 Loan Products</div>
          <button class="btn btn-primary btn-sm" onclick="Modal.open('modal-product')">+ Add Product</button>
        </div>
        <div class="panel-body-bare">
          <table class="data-table">
            <thead><tr><th>Name</th><th>Type</th><th>Min</th><th>Max</th><th>Rate</th><th>Tenure</th><th>Penalty</th><th>Status</th><th></th></tr></thead>
            <tbody id="productsTbody"></tbody>
          </table>
        </div>
      </div>
    </div>
    <div id="tab-fiscal" class="tab-content">
      <div class="panel">
        <div class="panel-header"><div class="panel-title">📅 Fiscal Periods</div>
          <button class="btn btn-primary btn-sm" onclick="Modal.open('modal-period')">+ New Period</button>
        </div>
        <div class="panel-body-bare">
          <table class="data-table">
            <thead><tr><th>Period</th><th>Start</th><th>End</th><th>Status</th><th>Closed By</th><th>Actions</th></tr></thead>
            <tbody id="periodsTbody"></tbody>
          </table>
        </div>
      </div>
    </div>
    <div id="tab-mpesa" class="tab-content">
      <div class="panel max-w-md">
        <div class="panel-header"><div class="panel-title">📱 Daraja API</div></div>
        <div class="panel-body">
          <div class="form-group"><label class="form-label">Environment</label>
            <select class="form-control" id="mpesaEnv"><option value="sandbox">Sandbox</option><option value="production">Production</option></select></div>
          <div class="form-grid">
            <div class="form-group"><label class="form-label">Consumer Key</label>
              <input class="form-control" id="mpesaKey" type="password" placeholder="Consumer key"></div>
            <div class="form-group"><label class="form-label">Consumer Secret</label>
              <input class="form-control" id="mpesaSecret" type="password" placeholder="Consumer secret"></div>
            <div class="form-group"><label class="form-label">Shortcode / PayBill</label>
              <input class="form-control" id="mpesaShortcode" value="174379"></div>
            <div class="form-group"><label class="form-label">Passkey</label>
              <input class="form-control" id="mpesaPasskey" type="password" placeholder="Passkey"></div>
          </div>
          <div class="form-group"><label class="form-label">Callback URL</label>
            <input class="form-control" id="mpesaCallback" placeholder="https://yourdomain.co.ke/api/v1/payments/mpesa/callback/"></div>
          <div class="d-flex gap-10 mt-6">
            <button class="btn btn-primary" onclick="saveMpesaConfig()">💾 Save</button>
            <button class="btn btn-ghost" onclick="testDaraja()">⚡ Test Connection</button>
          </div>
          <div id="daraja-status" class="mt-10 text-sm"></div>
        </div>
      </div>
    </div>
    <div id="tab-sms" class="tab-content">
      <div class="panel max-w-lg">
        <div class="panel-header">
          <div class="panel-title">📱 SMS Templates</div>
          <span class="badge badge-pending" id="sms-stats-badge">loading…</span>
        </div>
        <div class="panel-body">
          <div class="kpi-grid kpi-grid kpi-grid-3 animate-fadeup">
            <div class="kpi-card kc-green grad"><div class="kpi-label">Sent (7 days)</div><div class="kpi-value" id="stat-sent">—</div></div>
            <div class="kpi-card kc-red grad"><div class="kpi-label">Failed</div><div class="kpi-value" id="stat-failed">—</div></div>
            <div class="kpi-card kc-blue grad"><div class="kpi-label">Today</div><div class="kpi-value" id="stat-today">—</div></div>
          </div>
          ${[
            {
              id: "tpl-disb",
              label: "Loan Disbursement",
              val: "Dear {name}, your QuickLender loan of KES {amount} ({loan_id}) has been disbursed. Repayment of KES {total} due by {due_date}. Pay via Paybill {shortcode} A/C: {loan_id}. -QuickLender",
            },
            {
              id: "tpl-pay",
              label: "Payment Confirmation",
              val: "Dear {name}, payment of KES {amount} received for loan {loan_id}. Balance: KES {balance}. Thank you! -QuickLender",
            },
            {
              id: "tpl-remind",
              label: "Payment Reminder",
              val: "Dear {name}, your loan {loan_id} of KES {amount} is due on {due_date}. Pay via Paybill {shortcode} A/C: {loan_id}. -QuickLender",
            },
            {
              id: "tpl-overdue",
              label: "Overdue Notice",
              val: "URGENT: Dear {name}, loan {loan_id} is {days} days overdue. Balance: KES {balance}. Call {officer_phone}. -QuickLender",
            },
          ]
            .map(
              (t) => `
            <div class="form-group">
              <div class="d-flex justify-between mb-8">
                <label class="form-label m-0">${t.label}</label>
                <span class="mono text-dim text-xs" id="${t.id}-chars">0 chars</span>
              </div>
              <textarea class="form-control" id="${t.id}" rows="3"
                oninput="document.getElementById('${t.id}-chars').textContent=this.value.length+' chars'">${t.val}</textarea>
            </div>`,
            )
            .join("")}
          <button class="btn btn-primary" onclick="saveTemplates()">💾 Save Templates</button>
        </div>
      </div>
    </div>
    <div id="tab-system" class="tab-content">
      <div class="panel max-w-md">
        <div class="panel-header"><div class="panel-title">🖥️ System Configuration</div></div>
        <div class="panel-body">
          <div class="form-grid">
            <div class="form-group"><label class="form-label">Company Name</label>
              <input class="form-control" value="QuickLender Ltd"></div>
            <div class="form-group"><label class="form-label">System Email</label>
              <input class="form-control" type="email" value="system@quicklender.co.ke"></div>
            <div class="form-group"><label class="form-label">Time Zone</label>
              <select class="form-control"><option>Africa/Nairobi (EAT, UTC+3)</option></select></div>
            <div class="form-group"><label class="form-label">Currency</label>
              <select class="form-control"><option>KES — Kenyan Shilling</option></select></div>
            <div class="form-group"><label class="form-label">Loan Loss Provision (%)</label>
              <input type="number" class="form-control" value="5" step="0.5"></div>
            <div class="form-group"><label class="form-label">Max LTV — Logbook (%)</label>
              <input type="number" class="form-control" value="70"></div>
            <div class="form-group"><label class="form-label">Overdue Grace Period (days)</label>
              <input type="number" class="form-control" value="3"></div>
            <div class="form-group"><label class="form-label">Max Active Loans / Customer</label>
              <input type="number" class="form-control" value="2"></div>
          </div>
          <button class="btn btn-primary" onclick="Toast.success('System configuration saved')">💾 Save</button>
        </div>
      </div>
    </div>

    <!-- Loan Product Modal -->
    <div class="modal-overlay" id="modal-product">
      <div class="modal modal-md">
        <div class="modal-header"><div class="modal-title">💰 Loan Product</div>
          <div class="modal-close" onclick="Modal.close('modal-product')">✕</div></div>
        <div class="modal-body"><form id="productForm">
          <div class="form-group"><label class="form-label">Product Name *</label>
            <input class="form-control" name="name" placeholder="e.g. Salary Advance Premium"></div>
          <div class="form-grid">
            <div class="form-group"><label class="form-label">Type *</label>
              <select class="form-control" name="loan_type">
                <option value="FA">FA — Salary Advance</option><option value="CC">CC — Credit Check</option>
                <option value="LOGBOOK">Logbook</option><option value="IDC">IDC</option><option value="EDC">EDC</option>
              </select></div>
            <div class="form-group"><label class="form-label">Rate (%) *</label>
              <input type="number" class="form-control" name="interest_rate" step="0.01" placeholder="10"></div>
            <div class="form-group"><label class="form-label">Min Amount</label>
              <input type="number" class="form-control" name="min_amount" placeholder="5000"></div>
            <div class="form-group"><label class="form-label">Max Amount</label>
              <input type="number" class="form-control" name="max_amount" placeholder="100000"></div>
            <div class="form-group"><label class="form-label">Tenure (Days)</label>
              <input type="number" class="form-control" name="tenure_days" placeholder="30"></div>
            <div class="form-group"><label class="form-label">Penalty (%/day)</label>
              <input type="number" class="form-control" name="penalty_rate" step="0.1" value="0.5"></div>
          </div>
        </form></div>
        <div class="modal-footer">
          <button class="btn btn-ghost" onclick="Modal.close('modal-product')">Cancel</button>
          <button class="btn btn-primary" id="saveProductBtn" onclick="saveProduct()">
            <span class="btn-label">Save Product</span><span class="btn-spinner"></span></button>
        </div>
      </div>
    </div>

    <!-- Fiscal Period Modal -->
    <div class="modal-overlay" id="modal-period">
      <div class="modal modal-sm">
        <div class="modal-header"><div class="modal-title">📅 New Fiscal Period</div>
          <div class="modal-close" onclick="Modal.close('modal-period')">✕</div></div>
        <div class="modal-body">
          <div class="form-group"><label class="form-label">Name</label>
            <input class="form-control" id="period-name" placeholder="e.g. Q2 2026 — Apr-Jun"></div>
          <div class="form-grid">
            <div class="form-group"><label class="form-label">Start Date</label>
              <input type="date" class="form-control" id="period-start"></div>
            <div class="form-group"><label class="form-label">End Date</label>
              <input type="date" class="form-control" id="period-end"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" onclick="Modal.close('modal-period')">Cancel</button>
          <button class="btn btn-primary" id="savePeriodBtn" onclick="savePeriod()">
            <span class="btn-label">Create</span><span class="btn-spinner"></span></button>
        </div>
      </div>
    </div>
  `;
}

async function loadProducts() {
  const tbody = document.getElementById("productsTbody");
  if (!tbody) return;
  tbody.innerHTML = loadingRows(9, 3);
  try {
    const data = await API.loanProducts();
    const prods = data?.results || data || [];
    tbody.innerHTML = prods.length
      ? prods
          .map(
            (p) => `<tr>
          <td><b>${p.name}</b></td>
          <td>${Badge.loanType(p.loan_type)}</td>
          <td class="td-mono"><input type="number" class="inline-edit" value="${p.min_amount}" 
            onchange="quickUpdateProduct(${p.id}, 'min_amount', this.value)" style="width:80px"></td>
          <td class="td-mono"><input type="number" class="inline-edit" value="${p.max_amount}" 
            onchange="quickUpdateProduct(${p.id}, 'max_amount', this.value)" style="width:100px"></td>
          <td class="td-mono c-platinum"><input type="number" step="0.1" class="inline-edit" value="${p.interest_rate}" 
            onchange="quickUpdateProduct(${p.id}, 'interest_rate', this.value)" style="width:60px">%</td>
          <td class="td-mono c-gold-dark">${p.rate_gold || 18}%</td>
          <td class="td-mono">${p.rate_silver || 20}%</td>
          <td class="td-mono text-red">${p.rate_arrears || 21}%</td>
          <td class="td-mono">${Fmt.currency(p.first_loan_fee || 500)}</td>
          <td class="td-mono">${Fmt.currency(p.repeat_loan_fee || 300)}</td>
          <td class="td-mono"><input type="number" class="inline-edit" value="${p.tenure_days}" 
            onchange="quickUpdateProduct(${p.id}, 'tenure_days', this.value)" style="width:60px">d</td>
          <td>${Badge.status(p.is_active ? "ACTIVE" : "DORMANT")}</td>
          <td>
            <button class="btn btn-ghost btn-sm" onclick="editProduct(${p.id})">✏️ Edit</button>
            <button class="btn btn-danger btn-sm" onclick="deleteProduct(${p.id}, '${p.name}')">✕</button>
          </td>
        </tr>`,
          )
          .join("")
      : `<tr><td colspan="13">${emptyState("💰", "No products", "Add a product below.")}</td></tr>`;
  } catch (err) {
    if (tbody)
      tbody.innerHTML = `<tr><td colspan="13" class="td-error">Failed to load products.</td></tr>`;
  }
}
async function saveProduct() {
  const data = formData("productForm");
  if (!data.name || !data.interest_rate) {
    Toast.error("Name and rate required");
    return;
  }
  const editId = document.getElementById("editProductId")?.value;
  setLoading("saveProdBtn", true);
  try {
    let p;
    if (editId) {
      p = await API.updateProduct(editId, data);
      Toast.success(`"${p.name}" updated`);
    } else {
      p = await API.createProduct(data);
      Toast.success(`"${p.name}" created`);
    }
    if (p) {
      Modal.close("modal-product");
      resetForm("productForm");
      document.getElementById("editProductId").value = "";
      loadProducts();
    }
  } catch (err) {
    console.warn(err);
    Toast.error(err?.data?.detail || "Save failed");
  } finally {
    setLoading("saveProdBtn", false);
  }
}

async function quickUpdateProduct(id, field, value) {
  try {
    const p = await API.updateProduct(id, { [field]: value });
    Toast.success(`Updated ${field}`);
    loadProducts();
  } catch (err) {
    console.warn(err);
    Toast.error(err?.data?.detail || "Update failed");
    loadProducts(); // Reload to revert if failed
  }
}

async function loadFiscalPeriods() {
  const tbody = document.getElementById("periodsTbody");
  if (!tbody) return;
  tbody.innerHTML = loadingRows(6, 2);
  try {
    const data = await API.fiscalPeriods();
    const periods = data?.results || data || [];
    tbody.innerHTML = periods.length
      ? periods
          .map(
            (p) => `<tr>
          <td><b>${p.name}</b></td>
          <td class="td-mono">${Fmt.date(p.start_date)}</td>
          <td class="td-mono">${Fmt.date(p.end_date)}</td>
          <td>${Badge.status(p.status === "OPEN" ? "ACTIVE" : "CLOSED")}</td>
          <td>${p.closed_by_name || "—"}</td>
          <td>${
            p.status === "OPEN"
              ? `<button class="btn btn-danger btn-sm" onclick="closePeriod(${p.id},'${p.name}')">Lock Period</button>`
              : `<span class="mono text-dim">${Fmt.date(p.closed_at)}</span>`
          }
          </td>
        </tr>`,
          )
          .join("")
      : `<tr><td colspan="6">${emptyState("📅", "No periods", "Create your first fiscal period.")}</td></tr>`;
  } catch (err) {
    console.warn("loadFiscalPeriods failed:", err);
  }
}

async function savePeriod() {
  const name = document.getElementById("period-name")?.value.trim();
  const start = document.getElementById("period-start")?.value;
  const end = document.getElementById("period-end")?.value;
  if (!name || !start || !end) {
    Toast.error("All fields required");
    return;
  }
  setLoading("savePeriodBtn", true);
  try {
    const p = await Api.post("/accounting/periods/", {
      name,
      start_date: start,
      end_date: end,
    });
    if (p) {
      Toast.success(`Period "${p.name}" created`);
      Modal.close("modal-period");
      loadFiscalPeriods();
    }
  } catch (err) {
    console.warn(err);
  } finally {
    setLoading("savePeriodBtn", false);
  }
}

async function closePeriod(id, name) {
  if (
    !(await QL.confirm(
      `Lock period <b>${name}</b>?<br><span class='text-sm text-dim'>This cannot be undone.</span>`,
      { title: "Lock Period", okLabel: "Lock", danger: true },
    ))
  )
    return;
  try {
    await Api.post(`/accounting/periods/${id}/close/`);
    Toast.success(`Period "${name}" locked`);
    loadFiscalPeriods();
  } catch (err) {
    console.warn(err);
  }
}

async function loadSmsStats() {
  try {
    const s = await API.notifStats();
    if (!s) return;
    const sent = (s.sms?.SENT || 0) + (s.sms?.DELIVERED || 0);
    const failed = s.failed_sms_total || 0;
    const today = s.sms_total_today || 0;
    const el = (id) => document.getElementById(id);
    if (el("stat-sent")) el("stat-sent").textContent = Fmt.number(sent);
    if (el("stat-failed")) el("stat-failed").textContent = Fmt.number(failed);
    if (el("stat-today")) el("stat-today").textContent = Fmt.number(today);
    const badge = document.getElementById("sms-stats-badge");
    if (badge) {
      badge.textContent = `${sent} sent · ${failed} failed`;
      badge.className = `badge ${failed > 10 ? "badge-default" : "badge-active"}`;
    }
  } catch (err) {
    console.warn("loadSmsStats failed:", err);
  }
}

async function saveMpesaConfig() {
  // Settings are in .env — show instruction and test connection
  const env = document.getElementById("mpesaEnv")?.value;
  const key = document.getElementById("mpesaKey")?.value.trim();
  const secret = document.getElementById("mpesaSecret")?.value.trim();
  const shortcode = document.getElementById("mpesaShortcode")?.value.trim();
  const passkey = document.getElementById("mpesaPasskey")?.value.trim();
  const callback = document.getElementById("mpesaCallback")?.value.trim();

  if (key || secret) {
    Toast.warn(
      "⚠️ Credentials must be set in the .env file and the server restarted. Testing current config…",
    );
  }
  await testDaraja();
}

async function testDaraja() {
  const el = document.getElementById("daraja-status");
  if (el)
    el.innerHTML =
      '<span class="text-dim">⏳ Testing Daraja connection…</span>';
  try {
    const r = await API.mpesaTestToken();
    if (r?.status === "success") {
      if (el)
        el.innerHTML = `<span class="text-brand fw-600">✓ ${r.detail}</span>
        <span class="text-dim text-sm ml-8">Env: ${r.env} · Shortcode: ${r.shortcode}</span>`;
    } else {
      if (el)
        el.innerHTML = `<span class="text-red fw-600">✗ ${r?.detail || "Connection failed"}</span>`;
    }
  } catch (err) {
    const msg = err?.data?.detail || "Cannot reach server";
    if (el) el.innerHTML = `<span class="text-red fw-600">✗ ${msg}</span>`;
  }
}

async function saveTemplates() {
  const payload = {
    sms_payment_received:
      document.getElementById("tplPaymentReceived")?.value?.trim() || "",
    sms_loan_approved:
      document.getElementById("tplLoanApproved")?.value?.trim() || "",
    sms_loan_overdue:
      document.getElementById("tplLoanOverdue")?.value?.trim() || "",
    sms_custom: document.getElementById("tplCustom")?.value?.trim() || "",
  };
  setLoading("saveTemplatesBtn", true);
  try {
    // Store templates in localStorage (they're used client-side when sending manual SMS)
    localStorage.setItem("ql_sms_templates", JSON.stringify(payload));
    Toast.success("✓ SMS templates saved");
  } catch {
    Toast.error("Failed to save templates");
  } finally {
    setLoading("saveTemplatesBtn", false);
  }
}
async function saveAllSettings() {
  await testDaraja();
  Toast.success(
    "Settings verified. Update your .env file for any credential changes.",
  );
}
const onSearch = debounce(() => {
  const q = document.getElementById("searchInput")?.value || "";
  loadProducts(q);
}, 300);

// ─── PRODUCT CRUD ────────────────────────────────────────────────────────────
async function editProduct(id) {
  try {
    // Get product details from the API
    const products = await API.loanProducts();
    const p = (products?.results || products || []).find((x) => x.id === id);
    if (!p) {
      Toast.error("Product not found");
      return;
    }

    // Populate the new-product form fields
    const setVal = (sel, val) => {
      const el = document.getElementById(sel);
      if (el) el.value = val ?? "";
    };
    setVal("prodName", p.name);
    setVal("prodType", p.loan_type);
    setVal("prodMin", p.min_amount);
    setVal("prodMax", p.max_amount);
    setVal("prodRate", p.interest_rate);
    setVal("prodTenure", p.tenure_days);
    setVal("prodPenalty", p.penalty_rate);
    setVal("prodFirstFee", p.first_loan_fee);
    setVal("prodRepeatFee", p.repeat_loan_fee);
    // Store ID for update
    const hiddenId = document.getElementById("editProductId");
    if (hiddenId) hiddenId.value = id;
    else {
      // Create hidden field
      const inp = document.createElement("input");
      inp.type = "hidden";
      inp.id = "editProductId";
      inp.value = id;
      document.getElementById("prodName")?.closest("form")?.appendChild(inp);
    }
    // Update save button label
    const saveBtn = document.getElementById("saveProdBtn");
    if (saveBtn)
      saveBtn.querySelector(".btn-label").textContent = "Update Product";
    Modal.open("modal-new-product");
    Toast.success("Product loaded — make changes and save");
  } catch {
    Toast.error("Could not load product details");
  }
}

async function deleteProduct(id, name) {
  if (
    !(await QL.confirm(
      `Delete product <b>${name}</b>?<br><span class='text-sm text-dim'>This cannot be undone.</span>`,
      { title: "Delete Product", okLabel: "Delete", danger: true },
    ))
  )
    return;
  try {
    // Products can't be deleted if loans exist — backend will reject
    await Api.del(`/loans/products/${id}/`);
    Toast.success(`Product "${name}" deleted`);
    loadProducts();
  } catch (err) {
    Toast.error(
      err?.data?.detail ||
        "Cannot delete — loans may be linked to this product",
    );
  }
}
