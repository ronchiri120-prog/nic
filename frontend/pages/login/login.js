/**
 * Login Page
 */
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}

// Already logged in? go straight to dashboard
if (Auth.isLoggedIn()) {
  window.location.href = _dashboardPath();
}

const form     = document.getElementById('loginForm');
const emailEl  = document.getElementById('email');
const pwEl     = document.getElementById('password');
const loginBtn = document.getElementById('loginBtn');
const loginErr = document.getElementById('loginError');

// ─── SUBMIT ───────────────────────────────────────────
function _dashboardPath() {
  if (window.location.protocol === 'file:') return '../dashboard/dashboard.html';
  return '/pages/dashboard/dashboard.html';
}

form.addEventListener('submit', async e => {
  e.preventDefault();
  clearErrors();

  const email    = emailEl.value.trim();
  const password = pwEl.value;
  let valid = true;

  if (!email) {
    fieldErr('email-error', 'Email is required');
    emailEl.classList.add('error'); valid = false;
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    fieldErr('email-error', 'Enter a valid email address');
    emailEl.classList.add('error'); valid = false;
  }
  if (!password) {
    fieldErr('password-error', 'Password is required');
    pwEl.classList.add('error'); valid = false;
  }
  if (!valid) return;

  setBusy(true);

  try {
    const data = await API.login({ email, password });

    if (!data) {
      showErr('No response from server — check your connection.');
      return;
    }

    // 2FA required?
    if (data.requires_2fa) {
      _tempJWT = data.temp_jwt;
      show2FAStep();
      return;
    }

    // Success — save tokens and redirect
    Auth.save(data);
    loginBtn.querySelector('.btn-label').textContent = '✓ Redirecting…';
    const defaultPath = localStorage.getItem('ql_default_path') || _dashboardPath();
    setTimeout(() => { window.location.href = defaultPath; }, 450);

  } catch (err) {
    // api.js always throws { status, data: { detail } } — never swallows auth errors now
    const msg = _extractError(err);
    showErr(msg);
  } finally {
    setBusy(false);
  }
});

function _extractError(err) {
  // Network / server unreachable
  if (err?.networkError || err?.status === 0) {
    return 'Cannot reach the server. Make sure the backend is running on port 8000.';
  }
  // Rate-limited / locked out
  if (err?.status === 429) {
    return err?.data?.detail || 'Account locked after too many attempts. Try again in 15 minutes.';
  }
  // Server returned a JSON error body — show the exact message
  const d = err?.data;
  if (d?.detail)                return d.detail;
  if (d?.non_field_errors?.[0]) return d.non_field_errors[0];
  if (d?.email?.[0])            return d.email[0];
  if (d?.password?.[0])         return d.password[0];
  // HTTP error without body
  if (err?.status === 401) return 'Incorrect email or password.';
  if (err?.status === 400) return 'Invalid request — check your input.';
  if (err?.status >= 500)  return `Server error (${err.status}) — contact support.`;
  // Plain JS Error
  if (err?.message)        return err.message;
  return 'Login failed — please try again.';
}

// ─── HELPERS ──────────────────────────────────────────
function setBusy(loading) {
  loginBtn.disabled = loading;
  loginBtn.classList.toggle('loading', loading);
}

function clearErrors() {
  document.querySelectorAll('.field-error').forEach(el => el.textContent = '');
  document.querySelectorAll('.form-input').forEach(el => el.classList.remove('error'));
  loginErr.classList.remove('show');
  loginErr.textContent = '';
}

function fieldErr(id, msg) {
  const el = document.getElementById(id);
  if (el) el.textContent = msg;
}

function showErr(msg) {
  loginErr.textContent = msg;
  loginErr.classList.add('show');
  const card = document.querySelector('.login-card');
  if (card) {
    card.style.animation = 'none';
    requestAnimationFrame(() => { card.style.animation = 'shake 0.4s ease'; });
  }
}

function togglePw() {
  const isText = pwEl.type === 'text';
  pwEl.type = isText ? 'password' : 'text';
  document.getElementById('pw-icon').textContent = isText ? '👁' : '🙈';
}

function fillDemo() {
  emailEl.value = 'admin@quicklender.co.ke';
  pwEl.value    = 'QuickLender@2026';
  clearErrors();
}

function showForgot(e) {
  e.preventDefault();
  const card = document.querySelector('.login-card');
  if (!card) return;

  if (document.getElementById('forgot-mode')) {
    document.getElementById('forgot-mode').remove();
    return;
  }

  const panel = document.createElement('div');
  panel.id = 'forgot-mode';
  panel.innerHTML = `
    <div class="mb-16">
      <div class="fw-700 mb-8">🔑 Reset Password</div>
      <div class="text-sm text-dim mb-16">Enter your email and we'll send a reset link.</div>
      <input class="form-input w-full" id="resetEmail" type="email" placeholder="your@email.co.ke">
      <button class="btn btn-primary w-full mt-12" id="sendResetBtn" onclick="sendReset()">
        <span class="btn-label">Send Reset Link</span><span class="btn-spinner"></span>
      </button>
      <button class="btn btn-ghost w-full mt-8" onclick="showForgot(event)">← Back to Login</button>
    </div>`;
  card.appendChild(panel);
  document.getElementById('resetEmail')?.focus();
}

async function sendReset() {
  const email = document.getElementById('resetEmail')?.value.trim();
  if (!email) { showErr('Enter your email address'); return; }
  setLoading('sendResetBtn', true);
  try {
    const r = await API.passwordReset({ email });
    if (r) {
      document.getElementById('forgot-mode').innerHTML = `
        <div class="text-center">
          <div class="icon-lg">📧</div>
          <div class="fw-600 mb-8">Check your email</div>
          <div class="text-sm text-dim mb-16">${r.detail || 'Reset link sent.'}</div>
          <button class="btn btn-ghost w-full" onclick="showForgot(event)">← Back to Login</button>
        </div>`;
    }
  } catch (err) {
    showErr(_extractError(err));
  } finally {
    setLoading('sendResetBtn', false);
  }
}

// Clear errors when user types
[emailEl, pwEl].forEach(el => el?.addEventListener('input', () => {
  el.classList.remove('error');
  clearErrors();
}));

// Shake keyframe (injected once)
const _shakeStyle = document.createElement('style');
_shakeStyle.textContent = `@keyframes shake{0%,100%{transform:translateX(0)}20%{transform:translateX(-8px)}40%{transform:translateX(8px)}60%{transform:translateX(-5px)}80%{transform:translateX(5px)}}`;
document.head.appendChild(_shakeStyle);

// ─── 2FA STEP ─────────────────────────────────────────
let _tempJWT = null;

function show2FAStep() {
  const card = document.querySelector('.login-card');
  if (!card) return;

  // Remove login form, show OTP input
  const existing = document.getElementById('twofa-step');
  if (existing) { document.getElementById('otpInput')?.focus(); return; }

  const div = document.createElement('div');
  div.id = 'twofa-step';
  div.className = 'mt-20 pt-20 border-top';
  div.innerHTML = `
    <div class="fw-700 mb-8">🔐 Two-Factor Authentication</div>
    <div class="text-sm text-dim mb-16">Enter the 6-digit code from your authenticator app.</div>
    <input id="otpInput" type="text" inputmode="numeric" maxlength="6"
      class="form-input w-full text-center otp-input" placeholder="000000"
      oninput="if(this.value.length===6) verify2FA()">
    <button class="btn btn-primary w-full mt-12" id="verifyBtn" onclick="verify2FA()">
      <span class="btn-label">Verify Code</span><span class="btn-spinner"></span>
    </button>
    <p class="text-sm text-dim text-center mt-10">Lost your phone? Enter a backup code.</p>`;
  card.appendChild(div);
  setTimeout(() => document.getElementById('otpInput')?.focus(), 100);
}

async function verify2FA() {
  const token = document.getElementById('otpInput')?.value.trim();
  if (!token) return;
  setLoading('verifyBtn', true);
  try {
    const data = await API.totpVerify({ token, temp_jwt: _tempJWT });
    if (data?.access) {
      Auth.save(data);
      window.location.href = _dashboardPath();
    }
  } catch (err) {
    showErr(_extractError(err));
    setLoading('verifyBtn', false);
  }
}
