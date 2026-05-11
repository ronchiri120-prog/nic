/**
 * QuickLender Auth — v1.0
 * JWT storage, refresh, role guards, path-aware redirects.
 */

const Auth = {
  TOKEN_KEY:   'ql_access',
  REFRESH_KEY: 'ql_refresh',
  USER_KEY:    'ql_user',

  getToken()  { return localStorage.getItem(this.TOKEN_KEY); },
  getRefresh(){ return localStorage.getItem(this.REFRESH_KEY); },
  getUser()   {
    try { return JSON.parse(localStorage.getItem(this.USER_KEY)); }
    catch { return null; }
  },

  save(data) {
    localStorage.setItem(this.TOKEN_KEY,   data.access);
    localStorage.setItem(this.REFRESH_KEY, data.refresh);
    localStorage.setItem(this.USER_KEY,    JSON.stringify(data.user));
  },

  clear() {
    [this.TOKEN_KEY, this.REFRESH_KEY, this.USER_KEY].forEach(k =>
      localStorage.removeItem(k)
    );
  },

  isLoggedIn() { return !!this.getToken(); },

  _loginPath() {
    // Use absolute path — works whether served by Django or opened directly
    // When opened from disk: file:// URLs need relative path
    if (window.location.protocol === 'file:') {
      const depth = window.location.pathname.split('/').filter(Boolean).length;
      const up = '../'.repeat(Math.max(depth - 1, 1));
      return up + 'login/login.html';
    }
    // Served by Django / web server — use absolute path
    return '/pages/login/login.html';
  },

  require() {
    if (!this.isLoggedIn()) {
      window.location.href = this._loginPath();
    }
  },

  // Guard a page to specific roles — call at top of page JS
  // Usage: Auth.requireRole(['SUPER_ADMIN','GM','HOP'])
  requireRole(allowedRoles) {
    if (!this.isLoggedIn()) {
      window.location.href = this._loginPath();
      return;
    }
    const user = this.getUser();
    if (allowedRoles.length && !allowedRoles.includes(user?.role)) {
      // Redirect to dashboard with access-denied toast
      window.location.href = '/pages/dashboard/dashboard.html?access_denied=1';
    }
  },

  async refreshToken() {
    const refresh = this.getRefresh();
    if (!refresh) return false;
    try {
      const base = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
      const resp = await fetch(`${base}/api/v1/auth/token/refresh/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ refresh }),
      });
      if (!resp.ok) return false;
      const data = await resp.json();
      localStorage.setItem(this.TOKEN_KEY, data.access);
      if (data.refresh) localStorage.setItem(this.REFRESH_KEY, data.refresh);
      return true;
    } catch { return false; }
  },

  logout() {
    const refresh = this.getRefresh();
    const token   = this.getToken();
    const base    = window.location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
    if (refresh && token) {
      fetch(`${base}/api/v1/auth/logout/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body:    JSON.stringify({ refresh }),
      }).catch(() => {});
    }
    this.clear();
    window.location.href = this._loginPath();
  },

  hasRole(...roles) {
    const u = this.getUser();
    return u && roles.includes(u.role);
  },

  canApprove() {
    return this.hasRole('SUPER_ADMIN', 'BRANCH_MANAGER', 'RM', 'OPERATIONS');
  },

  isVerificationTeam() {
    return this.hasRole('VERIFICATION_TEAM');
  },

  canEditCustomer() {
    return this.hasRole('SUPER_ADMIN', 'COLLECTIONS_MGR', 'COLLECTIONS', 'OPERATIONS', 'TECH');
  },

  isSuperAdmin() { return this.hasRole('SUPER_ADMIN'); },

  initials(name = '') {
    return (name || 'U').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
  },

  avatarColor(name = '') {
    const palette = ['#0098A1','#5b8def','#f0b429','#a78bfa','#f06060','#06b6d4','#fb923c'];
    let h = 0;
    for (const c of (name || '')) h += c.charCodeAt(0);
    return palette[h % palette.length];
  },
};

// Apply saved theme on page load
(function() {
  const theme = localStorage.getItem('ql_theme') || 'dark';
  if (theme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  } else if (theme === 'auto') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (!prefersDark) document.documentElement.setAttribute('data-theme', 'light');
  }
  // Dark is default — no attribute needed
})();
