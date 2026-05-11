/**
 * Profile — Change password, 2FA setup, view your info
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('profile');
  renderProfile();
});

function renderProfile() {
  const user = Auth.getUser() || {};
  const el   = document.getElementById('pageContent');
  if (!el) return;

  el.innerHTML = `
    <div class="section-header animate-fadeup"><div>
      <h1 class="page-heading">👤 My Profile</h1>
      <p class="text-sm text-dim">View your details · Change password · Set up 2FA</p>
    </div></div>

    <div class="profile-layout">

      <!-- Left: Avatar + info card -->
      <div class="panel animate-fadeup">
        <div class="panel-body text-center">
          <div class="profile-avatar" id="profileAvatar" style="background:\${Auth.avatarColor(user.full_name || \'\')};cursor:pointer;" onclick="document.getElementById('photoUpload').click()">
            ${user.avatar_url ? `<img src="${user.avatar_url}" class="avatar-img" />` : Auth.initials(user.full_name || user.email || '')}
          </div>
          <input type="file" id="photoUpload" accept="image/*" style="display:none" onchange="uploadPhoto(event)">
          <div class="text-xs text-dim mt-4 cursor-pointer text-brand" onclick="document.getElementById('photoUpload').click()">📷 Change Photo</div>
          <div class="profile-name-serif">${user.full_name || 'User'}</div>
          <div class="mono text-dim text-sm mt-4">${user.staff_id || ''}</div>
          <div class="my-10">
            <span class="chip chip-fa text-xs">${(user.role || '').replace(/_/g,' ')}</span>
          </div>
          <div class="info-row"><span class="info-key">Email</span><span class="info-val text-sm">${user.email || '—'}</span></div>
          <div class="info-row"><span class="info-key">Branch</span><span class="info-val text-sm">${user.branch_name || user.branch || '—'}</span></div>
          <div class="mt-16 pt-16 border-top">
            <button class="btn btn-danger btn-sm" onclick="Auth.logout()" class="w-full">⏻ Sign Out</button>
          </div>
        </div>
      </div>

      <!-- Right: Tabs for settings -->
      <div class="animate-fadeup stagger-1">
        <div class="tabs" data-tab-scope class="m-0">
          <button class="tab-btn active" onclick="switchTab(this,'tab-password')">Change Password</button>
          <button class="tab-btn" onclick="switchTab(this,'tab-2fa');check2FAStatus()">Two-Factor Auth (2FA)</button>
          <button class="tab-btn" onclick="switchTab(this,'tab-prefs')">Preferences</button>
        </div>

        <!-- Change Password -->
        <div id="tab-password" class="tab-content active panel tab-panel">
          <div class="panel-body max-w-sm">
            <div class="form-group"><label class="form-label">Current Password</label>
              <input type="password" class="form-control" id="oldPw" placeholder="Enter current password"></div>
            <div class="form-group"><label class="form-label">New Password</label>
              <input type="password" class="form-control" id="newPw" placeholder="Min 8 characters"
                oninput="checkPwStrength(this.value)">
              <div id="pw-strength-bar" class="pw-bar-track">
                <div id="pw-strength-fill" class="pw-bar-fill"></div>
              </div>
              <div id="pw-strength-label" class="text-xs text-dim mt-4"></div>
            </div>
            <div class="form-group"><label class="form-label">Confirm New Password</label>
              <input type="password" class="form-control" id="confirmPw" placeholder="Repeat new password"></div>
            <button class="btn btn-primary" id="changePwBtn" onclick="changePassword()">
              <span class="btn-label">Update Password</span><span class="btn-spinner"></span>
            </button>
          </div>
        </div>

        <!-- 2FA -->
        <div id="tab-2fa" class="tab-content panel tab-panel">
          <div class="panel-body" id="twofa-body">
            <div class="td-loading">Checking 2FA status…</div>
          </div>
        </div>

        <!-- Preferences -->
        <div id="tab-prefs" class="tab-content panel tab-panel">
          <div class="panel-body">
            <div class="form-group">
              <label class="form-label">Theme</label>
              <div class="d-flex gap-10">
                <button class="btn btn-ghost" onclick="setTheme('dark')" id="btn-dark">🌙 Dark</button>
                <button class="btn btn-ghost" onclick="setTheme('light')" id="btn-light">☀️ Light</button>
                <button class="btn btn-ghost" onclick="setTheme('auto')" id="btn-auto">💻 System</button>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">Default Landing Page</label>
              <select class="form-control" id="defaultPage" class="max-w-sm">
                <option value="dashboard">Dashboard</option>
                <option value="loans">Loans</option>
                <option value="customers">Customers</option>
                <option value="collections">Collections</option>
              </select>
            </div>
            <button class="btn btn-primary" onclick="savePrefs()">💾 Save Preferences</button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Highlight current theme
  const theme = localStorage.getItem('ql_theme') || 'dark';
  document.getElementById(`btn-${theme}`)?.classList.add('btn-primary');
}

async function changePassword() {
  const oldPw     = document.getElementById('oldPw')?.value;
  const newPw     = document.getElementById('newPw')?.value;
  const confirmPw = document.getElementById('confirmPw')?.value;
  if (!oldPw || !newPw || !confirmPw) { Toast.error('All fields are required'); return; }
  if (newPw !== confirmPw) { Toast.error('New passwords do not match'); return; }
  if (newPw.length < 8)   { Toast.error('Password must be at least 8 characters'); return; }
  setLoading('changePwBtn', true);
  try {
    const r = await API.changePassword({ old_password: oldPw, new_password: newPw });
    if (r) {
      Toast.success('Password updated successfully — please log in again');
      setTimeout(() => Auth.logout(), 2000);
    }
  } catch (err) { console.warn(err); } finally { setLoading('changePwBtn', false); }
}

function checkPwStrength(pw) {
  const bar   = document.getElementById('pw-strength-fill');
  const label = document.getElementById('pw-strength-label');
  if (!bar) return;
  const checks = [pw.length >= 8, /[A-Z]/.test(pw), /[0-9]/.test(pw), /[^A-Za-z0-9]/.test(pw)];
  const score  = checks.filter(Boolean).length;
  const colors = ['var(--red)','var(--red)','var(--gold)','var(--brand)','var(--brand)'];
  const labels = ['','Weak','Fair','Good','Strong'];
  bar.style.width      = (score * 25) + '%';
  bar.style.background = colors[score];
  label.textContent    = labels[score];
  label.style.color    = colors[score];
}

let _totpSecret = null;

async function check2FAStatus() {
  const body = document.getElementById('twofa-body');
  if (!body) return;
  const user = Auth.getUser() || {};
  if (user.totp_enabled) {
    body.innerHTML = `
      <div class="totp-enabled-box">
        <span class="text-3xl">🔒</span>
        <div><div class="fw-600 text-brand">2FA is enabled</div>
          <div class="text-sm text-dim">Your account is protected with TOTP authentication</div></div>
      </div>
      <button class="btn btn-danger" onclick="disable2FA()">Disable 2FA</button>`;
  } else {
    body.innerHTML = `
      <div class="totp-disabled-box">
        <span class="text-3xl">🔓</span>
        <div><div class="fw-gold">2FA is not enabled</div>
          <div class="text-sm text-dim">Enable two-factor authentication to secure your account</div></div>
      </div>
      <button class="btn btn-primary" onclick="setup2FA()">🔐 Set Up 2FA</button>`;
  }
}

async function setup2FA() {
  const body = document.getElementById('twofa-body');
  body.innerHTML = `<div class="td-loading">Generating QR code…</div>`;
  try {
    const r = await API.totpSetup();
    _totpSecret = r.secret;
    body.innerHTML = `
      <p class="text-md text-dim mb-16">
        1. Open <b>Google Authenticator</b> or <b>Authy</b><br>
        2. Tap <b>+</b> → <b>Scan QR code</b><br>
        3. Enter the 6-digit code below to activate
      </p>
      <div class="text-center mb-16">
        <img src="data:image/png;base64,${r.qr_code}" class="totp-qr">
        <div class="mono text-dim totp-manual-key">
          Manual key: ${r.secret}
        </div>
      </div>
      <div class="form-group max-w-sm">
        <label class="form-label">Enter 6-digit code</label>
        <input class="form-control" id="totpCode" placeholder="000000" maxlength="6"
          class="totp-input"
          oninput="if(this.value.length===6) confirm2FA()">
      </div>
      <button class="btn btn-primary" onclick="confirm2FA()">✓ Activate 2FA</button>`;
    document.getElementById('totpCode')?.focus();
  } catch { body.innerHTML = `<div class="text-red">Failed to generate 2FA setup. Ensure backend is running.</div>`; }
}

async function confirm2FA() {
  const token = document.getElementById('totpCode')?.value;
  if (!token || token.length !== 6) { Toast.error('Enter the 6-digit code from your app'); return; }
  try {
    const r = await API.totpConfirm({ token });
    if (r?.backup_codes) {
      const body = document.getElementById('twofa-body');
      body.innerHTML = `
        <div class="backup-success-box">
          <div class="fw-700 text-brand mb-8">🎉 2FA activated successfully!</div>
          <div class="text-sm text-dim">Save these backup codes — they can be used if you lose your phone. Each code works once only.</div>
        </div>
        <div class="backup-codes-box">
          <div class="form-label mb-8">🔑 Backup Codes (save these now)</div>
          <div class="backup-codes-grid">
            ${r.backup_codes.map(c => `<code class="backup-code-item">${c}</code>`).join('')}
          </div>
        </div>
        <button class="btn btn-ghost" onclick="navigator.clipboard.writeText('${r.backup_codes.join('\\n')}');Toast.success('Codes copied to clipboard')">
          📋 Copy Backup Codes
        </button>`;
      // Update local user cache
      const user = Auth.getUser() || {};
      user.totp_enabled = true;
      localStorage.setItem('ql_user', JSON.stringify(user));
    }
  } catch (err) { console.warn(err); }
}

async function disable2FA() {
  const pw = await QL.prompt('Enter your current password to disable 2FA:', '', {title:'Disable 2FA', placeholder:'Current password', type:'password'});
  if (!pw) return;
  try {
    const r = await API.totpDisable({ password: pw });
    Toast.success('2FA disabled');
    const user = Auth.getUser() || {};
    user.totp_enabled = false;
    localStorage.setItem('ql_user', JSON.stringify(user));
    check2FAStatus();
  } catch (err) { console.warn(err); }
}

function setTheme(theme) {
  localStorage.setItem('ql_theme', theme);
  ['dark','light','auto'].forEach(t => {
    document.getElementById(`btn-${t}`)?.classList.remove('btn-primary');
    document.getElementById(`btn-${t}`)?.classList.add('btn-ghost');
  });
  document.getElementById(`btn-${theme}`)?.classList.add('btn-primary');
  if (theme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  } else if (theme === 'dark') {
    document.documentElement.removeAttribute('data-theme');
  } else {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (!prefersDark) document.documentElement.setAttribute('data-theme', 'light');
  }
  Toast.success(`Theme set to ${theme}`);
}

function savePrefs() {
  const page  = document.getElementById('defaultPage')?.value;
  const theme = localStorage.getItem('ql_theme') || 'dark';
  if (page) localStorage.setItem('ql_default_page', page);
  localStorage.setItem('ql_theme', theme);
  Toast.success('✓ Preferences saved');
  // Apply default page on next login if set
  if (page && page !== 'dashboard') {
    const paths = {
      loans: '/pages/loans/loans.html',
      customers: '/pages/customers/customers.html',
      collections: '/pages/collections/collections.html',
    };
    if (paths[page]) localStorage.setItem('ql_default_path', paths[page]);
  }
}

async function uploadPhoto(event) {
  const file = event.target.files[0];
  if (!file) return;

  // Validate file type and size
  if (!file.type.startsWith('image/')) {
    Toast.error('Please select an image file');
    return;
  }
  if (file.size > 5 * 1024 * 1024) { // 5MB limit
    Toast.error('Image must be less than 5MB');
    return;
  }

  const formData = new FormData();
  formData.append('avatar', file);

  try {
    const response = await fetch('/api/v1/auth/me/avatar/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${Auth.getToken()}`,
      },
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      // Update local user data
      const user = Auth.getUser() || {};
      user.avatar_url = data.avatar_url;
      localStorage.setItem('ql_user', JSON.stringify(user));
      Toast.success('Photo updated successfully');
      renderProfile(); // Re-render to show new photo
    } else {
      Toast.error('Failed to upload photo');
    }
  } catch (err) {
    console.error('Upload error:', err);
    Toast.error('Failed to upload photo');
  }
}

// Profile has no searchable list — search is not applicable
const onSearch = () => {};
