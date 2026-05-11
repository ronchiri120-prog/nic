/**
 * QuickLender API Client
 * Auto-detects base URL, handles JWT auth, refresh, pagination, errors.
 */

// ─── BASE URL ─────────────────────────────────────────
const API_BASE = (() => {
  // When served by Django (http/https) — always use relative path
  // Works on any port: 8000, 80, 443, etc.
  if (window.location.protocol.startsWith('http')) return '/api/v1';
  // Fallback for file:// direct open (dev only)
  return 'http://localhost:8000/api/v1';
})();

// ─── CLIENT CLASS ─────────────────────────────────────
class ApiClient {
  constructor() { this.base = API_BASE; }

  _headers() {
    const token = Auth.getToken();
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  async _request(method, endpoint, body = null, params = {}) {
    let url = this.base + endpoint;
    if (params && Object.keys(params).length) {
      const clean = Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== '' && v != null)
      );
      if (Object.keys(clean).length) url += '?' + new URLSearchParams(clean);
    }
    const opts = { method, headers: this._headers() };
    if (body && method !== 'GET') opts.body = JSON.stringify(body);

    // Auth endpoints never need the refresh-token retry logic
    const isAuthEndpoint = endpoint.startsWith('/auth/login') ||
                           endpoint.startsWith('/auth/token');

    try {
      const resp = await fetch(url, opts);

      // ── 401 handling ──────────────────────────────────────────────────
      if (resp.status === 401 && !isAuthEndpoint) {
        // JWT expired on a protected endpoint — try refresh once
        const refresh = Auth.getRefresh();
        if (refresh) {
          const rr = await fetch(this.base + '/auth/token/refresh/', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ refresh }),
          });
          if (rr.ok) {
            const { access } = await rr.json();
            // Use auth.js key so Auth.getToken() stays in sync
            localStorage.setItem(Auth.TOKEN_KEY, access);
            opts.headers.Authorization = `Bearer ${access}`;
            const retry = await fetch(url, opts);
            if (!retry.ok) {
              const errData = await retry.json().catch(() => ({}));
              throw { status: retry.status, data: errData };
            }
            return retry.status === 204 ? null : await retry.json();
          } else {
            // Refresh token is invalid — log out
            Auth.logout();
            return null;
          }
        } else {
          // No refresh token — session ended, redirect to login
          Auth.logout();
          return null;
        }
      }

      // ── Non-200 responses ─────────────────────────────────────────────
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
        // Auth endpoints: let the caller (login.js) show the error — no Toast
        if (!isAuthEndpoint && typeof Toast !== 'undefined') {
          const msg = err.detail || err.non_field_errors?.[0] || err.message || `Error ${resp.status}`;
          if (resp.status !== 404) Toast.error(msg);
        }
        throw { status: resp.status, data: err };
      }

      return resp.status === 204 ? null : await resp.json();

    } catch (err) {
      if (err.status !== undefined) throw err;  // already a formatted error object
      // Network / fetch failure
      if (!isAuthEndpoint && typeof Toast !== 'undefined') {
        Toast.error('Network error — check your connection');
      }
      throw { status: 0, data: { detail: 'Cannot reach server. Is the backend running?' }, networkError: true };
    }
  }

  get(ep, p)   { return this._request('GET',    ep, null, p); }
  post(ep, d)  { return this._request('POST',   ep, d);       }
  patch(ep, d) { return this._request('PATCH',  ep, d);       }
  put(ep, d)   { return this._request('PUT',    ep, d);       }
  del(ep)      { return this._request('DELETE', ep);          }
}

const Api = new ApiClient();

// ─── ENDPOINT MAP ─────────────────────────────────────
const API = {
  // ── Auth ──────────────────────────────────────────────────
  login:              d     => Api.post('/auth/login/', d),
  logout:             d     => Api.post('/auth/logout/', d),
  me:                 ()    => Api.get('/auth/me/'),
  refreshToken:       d     => Api.post('/auth/token/refresh/', d),
  changePassword:     d     => Api.post('/auth/change-password/', d),
  dashStats:          ()    => Api.get('/auth/dashboard/stats/'),

  // ── Staff / Users ─────────────────────────────────────────
  users:              p     => Api.get('/auth/users/', p),
  createUser:         d     => Api.post('/auth/users/', d),
  updateUser:         (id,d)=> Api.patch(`/auth/users/${id}/`, d),
  deleteUser:         id    => Api.del(`/auth/users/${id}/`),
  auditLogs:          p     => Api.get('/auth/audit-logs/', p),

  // ── Password Reset ────────────────────────────────────────────
  passwordReset:        d => Api.post('/auth/password-reset/', d),
  passwordResetConfirm: d => Api.post('/auth/password-reset/confirm/', d),

  // ── TOTP / 2FA ────────────────────────────────────────────
  totpSetup:          ()    => Api.get('/auth/totp/setup/'),
  totpConfirm:        d     => Api.post('/auth/totp/confirm/', d),
  totpDisable:        d     => Api.post('/auth/totp/disable/', d),
  totpVerify:         d     => Api.post('/auth/totp/verify/', d),

  // ── Leads ──────────────────────────────────────────────────────
  leads:              p     => Api.get('/customers/leads/', p),
  lead:               id    => Api.get(`/customers/leads/${id}/`),
  createLead:         d     => Api.post('/customers/leads/', d),
  updateLead:         (id,d)=> Api.patch(`/customers/leads/${id}/`, d),
  convertLead:        id    => Api.post(`/customers/leads/${id}/convert/`),

  // ── Customers ─────────────────────────────────────────────
  customers:          p     => Api.get('/customers/', p),
  customer:           id    => Api.get(`/customers/${id}/`),
  createCustomer:     d     => Api.post('/customers/', d),
  updateCustomer:     (id,d)=> Api.patch(`/customers/${id}/`, d),
  customerLoans:      id    => Api.get(`/customers/${id}/loan-history/`),
  blacklistCust:      (id,d)=> Api.post(`/customers/${id}/blacklist/`, d),
  customerReference:  q     => Api.get(`/customers/reference/?q=${encodeURIComponent(q)}`),

  // ── Loans ─────────────────────────────────────────────────
  loanProducts:       ()    => Api.get('/loans/products/'),
  createProduct:      d     => Api.post('/loans/products/', d),
  updateProduct:      (id,d)=> Api.patch(`/loans/products/${id}/`, d),
  loans:              p     => Api.get('/loans/', p),
  loan:               id    => Api.get(`/loans/${id}/`),
  createLoan:         d     => Api.post('/loans/', d),
  updateLoan:         (id,d)=> Api.patch(`/loans/${id}/`, d),
  verifyLoan:         id    => Api.post(`/loans/${id}/verify/`),
  approveLoan:        id    => Api.post(`/loans/${id}/approve/`),
  rejectLoan:         (id,d)=> Api.post(`/loans/${id}/reject/`, d),
  disburseLoan:       (id,d)=> Api.post(`/loans/${id}/disburse/`, d),
  defaultLoan:        id    => Api.post(`/loans/${id}/mark-default/`),
  creditScore:        d     => Api.post('/loans/credit-score/', d),
  restructureLoan:    (id,d)=> Api.post(`/loans/${id}/restructure/`, d),
  loanSchedule:       id    => Api.get(`/documents/loans/${id}/schedule/`),
  generateSchedule:   (id,d)=> Api.post(`/documents/loans/${id}/schedule/`, d),

  // ── Payments ──────────────────────────────────────────────
  payments:           p     => Api.get('/payments/', p),
  payment:            id    => Api.get(`/payments/${id}/`),
  createPayment:      d     => Api.post('/payments/', d),
  stkPush:            d     => Api.post('/payments/mpesa/stk-push/', d),
  mpesaTxns:          p     => Api.get('/payments/mpesa/transactions/', p),
  mpesaTestToken:     ()    => Api.get('/payments/mpesa/test-token/'),

  // ── Branches + Regions ────────────────────────────────────
  regions:            ()    => Api.get('/branches/regions/'),
  createRegion:       d     => Api.post('/branches/regions/', d),
  submarkets:         p     => Api.get('/branches/submarkets/', p),
  branches:           p     => Api.get('/branches/', p),
  branch:             id    => Api.get(`/branches/${id}/`),
  createBranch:       d     => Api.post('/branches/', d),
  updateBranch:       (id,d)=> Api.patch(`/branches/${id}/`, d),
  deleteBranch:       id    => Api.del(`/branches/${id}/`),
  deleteRegion:       id    => Api.del(`/branches/regions/${id}/`),

  // ── Reports ───────────────────────────────────────────────
  reportLoans:        p     => Api.get('/reports/loans-breakdown/', p),
  reportBranches:     ()    => Api.get('/reports/branch-performance/'),
  reportIndividual:   ()    => Api.get('/reports/individual-performance/'),
  reportDefaulters:   ()    => Api.get('/reports/defaulters/'),
  reportDormant:      ()    => Api.get('/reports/dormant-customers/'),

  // ── CBK Reports ───────────────────────────────────────────
  cbkMFI01:           p     => Api.get('/reports/cbk/mfi-01/', p),
  cbkMFI02:           p     => Api.get('/reports/cbk/mfi-02/', p),
  cbkMFI03:           p     => Api.get('/reports/cbk/mfi-03/', p),
  cbkMFI04:           ()    => Api.get('/reports/cbk/mfi-04/'),

  // ── Excel Exports ─────────────────────────────────────────
  excelLoans: (p) => {
    const b = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
    window.open(`${b}/api/v1/reports/excel/loans/${p ? '?' + new URLSearchParams(p) : ''}`, '_blank');
  },
  excelCollections: () => {
    const b = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
    window.open(`${b}/api/v1/reports/excel/collections/`, '_blank');
  },
  excelCustomers: () => {
    const b = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
    window.open(`${b}/api/v1/reports/excel/customers/`, '_blank');
  },

  // ── CRM ───────────────────────────────────────────────────────
  crmInteractions:  (p)    => Api.get('/crm/interactions/', p),
  crmInteraction:   (id)   => Api.get(`/crm/interactions/${id}/`),
  createCRM:        d      => Api.post('/crm/interactions/', d),
  updateCRM:        (id,d) => Api.patch(`/crm/interactions/${id}/`, d),
  deleteCRM:        id     => Api.del(`/crm/interactions/${id}/`),
  crmByCustomer:    (id)   => Api.get(`/crm/interactions/by_customer/?customer_id=${id}`),
  crmPTPToday:      ()    => Api.get('/crm/interactions/ptp_today/'),
  crmFollowUps:     ()    => Api.get('/crm/interactions/follow_ups/'),

  // ── Document Generation ───────────────────────────────────
  customerStatement: (id, p) => {
    const b  = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
    const qs = p ? '?' + new URLSearchParams(p) : '';
    window.open(`${b}/api/v1/documents/customers/${id}/statement/${qs}`, '_blank');
  },
  loanAgreement: (id) => {
    const b = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
    window.open(`${b}/api/v1/documents/loans/${id}/agreement/`, '_blank');
  },
  disbursementLetter: (id) => {
    const b = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
    window.open(`${b}/api/v1/documents/loans/${id}/disbursement-letter/`, '_blank');
  },
  demandLetter: (id) => {
    const b = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
    window.open(`${b}/api/v1/documents/loans/${id}/demand-letter/`, '_blank');
  },

  // ── Privileged Payment Upload ─────────────────────────────────────────
  uploadPayment:      d     => Api.post('/payments/upload/', d),
  bulkUploadPayments: d     => Api.post('/payments/bulk-upload/', d),
  reversePayment:     (id,d)=> Api.post(`/payments/${id}/reverse/`, d),
  customerTier:       id    => Api.get(`/customers/${id}/tier/`),
  setCustomerTier:    (id,d)=> Api.post(`/customers/${id}/tier/`, d),

  // ── CSV Exports ───────────────────────────────────────────
  exportCustomers: () => {
    const b = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
    window.open(`${b}/api/v1/customers/export/`, '_blank');
  },
  exportLoans: () => {
    const b = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
    window.open(`${b}/api/v1/loans/export/`, '_blank');
  },

  // ── Allocations ───────────────────────────────────────────
  allocations:        p     => Api.get('/allocations/', p),
  createAllocation:   d     => Api.post('/allocations/', d),
  softReshuffle:      d     => Api.post('/allocations/soft-reshuffle/', d),
  hardReshuffle:      d     => Api.post('/allocations/hard-reshuffle/', d),

  // ── Assets ────────────────────────────────────────────────
  assets:             p     => Api.get('/assets/', p),
  asset:              id    => Api.get(`/assets/${id}/`),
  createAsset:        d     => Api.post('/assets/', d),
  updateAsset:        (id,d)=> Api.patch(`/assets/${id}/`, d),

  // ── Accounting GL ─────────────────────────────────────────
  glAccounts:         p     => Api.get('/accounting/accounts/', p),
  journal:            p     => Api.get('/accounting/journal/', p),
  createJournal:      d     => Api.post('/accounting/journal/', d),
  postJournal:        id    => Api.post(`/accounting/journal/${id}/post/`),
  deleteJournal:      id    => Api.del(`/accounting/journal/${id}/`),
  reverseJournal:     (id,d)=> Api.post(`/accounting/journal/${id}/reverse/`, d),
  incomeStatement:    p     => Api.get('/accounting/reports/income-statement/', p),
  balanceSheet:       p     => Api.get('/accounting/reports/balance-sheet/', p),
  trialBalance:       p     => Api.get('/accounting/reports/trial-balance/', p),
  generalLedger:      p     => Api.get('/accounting/reports/general-ledger/', p),
  fiscalPeriods:      ()    => Api.get('/accounting/periods/'),

  // ── Groups / Chama ────────────────────────────────────────
  groups:             p     => Api.get('/groups/', p),
  createGroup:        d     => Api.post('/groups/', d),
  group:              id    => Api.get(`/groups/${id}/`),
  addGroupMember:     (id,d)=> Api.post(`/groups/${id}/members/`, d),
  groupLoans:         p     => Api.get('/groups/loans/', p),
  deleteGroup:        id    => Api.del(`/groups/${id}/`),
  createGroupLoan:    d     => Api.post('/groups/loans/', d),
  approveGroupLoan:   id    => Api.post(`/groups/loans/${id}/approve/`),
  disburseGroupLoan:  id    => Api.post(`/groups/loans/${id}/disburse/`),

  // ── Notifications ─────────────────────────────────────────
  smsLogs:            p     => Api.get('/notifications/sms/', p),
  emailLogs:          p     => Api.get('/notifications/email/', p),
  notifStats:         ()    => Api.get('/notifications/stats/'),
  sendSMS:            d     => Api.post('/notifications/sms/send/', d),
};

// ── Ensure global availability ──────────────────────────────────────────────
if (typeof window !== 'undefined') {
  window.API = API;
  window.Api = Api;
}
