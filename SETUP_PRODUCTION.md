# QuickLender — Production Setup Guide

This guide walks you through going live with **real data**. Do NOT run `seed_demo_data`.

---

## Step 1 — Environment

```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit with your real values
nano backend/.env
```

### Required credentials

| Key | Where to get it |
|-----|----------------|
| `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DB_PASSWORD` | Set a strong password for PostgreSQL |
| `MPESA_CONSUMER_KEY` | [developer.safaricom.co.ke](https://developer.safaricom.co.ke) → Create App |
| `MPESA_CONSUMER_SECRET` | Same as above |
| `MPESA_SHORTCODE` | Your PayBill number (sandbox: `174379`) |
| `MPESA_PASSKEY` | From Daraja portal |
| `MPESA_CALLBACK_URL` | Your live server URL + `/api/v1/payments/mpesa/callback/` |
| `AT_API_KEY` | [africastalking.com](https://africastalking.com) → SMS → API Key |
| `AT_USERNAME` | Your Africa's Talking username (sandbox: `sandbox`) |
| `EMAIL_HOST_PASSWORD` | Gmail App Password (16 characters) |
| `FIELD_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

---

## Step 2 — Database

```bash
# Apply all migrations (creates all 20+ tables)
python manage.py migrate

# Set up for real data (creates admin, GL accounts, fiscal period)
python manage.py setup_real_data
```

You will be prompted for:
- Admin email (e.g. `admin@yourcompany.co.ke`)
- Admin full name
- Admin password (use a strong password — you can change it after login)

---

## Step 3 — First login setup order

After logging in as admin, follow this order:

### 3.1 — Regions & Branches
1. **Branches** → **+ Region** — add your regions (e.g. Nairobi, Mombasa, Western)
2. **Branches** → **+ Branch** — add each branch, assign to region + submarket

### 3.2 — Staff
3. **Staff & Roles** → **+ Add Staff Member** — create your loan officers, branch managers
   - Each staff member gets a welcome email with temporary password
   - Assign them to their branch

### 3.3 — Loan Products
4. **Settings** → **Loan Products** → **+ Add Product**
   - Configure each product: FA, CC, Logbook, IDC, EDC
   - Set interest rate, minimum/maximum amounts, tenure, penalty rate

### 3.4 — M-Pesa (optional but recommended)
5. **Settings** → **M-Pesa** → enter Daraja credentials → **Test Connection**

### 3.5 — SMS Templates
6. **Settings** → **SMS** → review and customise message templates

---

## Step 4 — Registering your first customer

> ⚠️ **Always run Reference Check before registering any customer**

1. **Reference Check** (sidebar, 2nd item) → search by National ID or phone
2. If no record found: **+ Register New Customer**
3. Complete all 6 sections of the KYC form:
   - Personal Identity (ID, gender, DOB, marital status)
   - Contact (phone, address, county, sub-county)
   - Employment (type, employer, income, net salary → auto-sets loan limit)
   - Next of Kin (required for compliance)
   - Guarantor (strongly recommended)
   - Branch assignment (branch + loan officer)
4. KYC completeness bar must reach **≥ 80%** before loan approval

---

## Step 5 — First loan

1. **Customers** → find customer → **Loan**  
   *or* **Loans** → **+ New Application**
2. Select product, enter principal
3. System runs **Credit Score** automatically (0–100, grade A–E)
4. Branch Manager / Credit Officer reviews and **Approves** or **Rejects**
5. On approval → **Disburse** → M-Pesa B2C sends funds directly to customer
6. Customer repays via:
   - M-Pesa PayBill `{shortcode}` → Account Number = Loan ID
   - Loan Officer records manual cash/bank payment

---

## Step 6 — Daily operations

| Time | Automatic task |
|------|---------------|
| 08:00 EAT | SMS reminders sent to customers due in 1, 3, 7 days |
| 09:00 EAT | Penalty engine — daily penalties applied to overdue loans |
| Every 15 min | M-Pesa STK push reconciliation |
| Monday 07:00 | Weekly portfolio report emailed to branch managers |

---

## Duplicate prevention

The system **enforces uniqueness across all branches**:

- **National ID** — cannot be registered twice system-wide
- **Phone number** — normalised (07XX → 254XX) before checking; duplicate blocked
- **Reference Check** — shows all profiles for an ID/phone including active loan exposure
- If a customer tries to borrow from two branches simultaneously, the system flags it

---

## CBK Reporting

**Accounting** → **CBK Returns** → generate MFI-01 through MFI-04 on demand

---

## Two-Factor Authentication

Staff can enable 2FA from their **Profile** page:
1. Profile → **Two-Factor Auth** → **Set Up 2FA**
2. Scan QR code with Google Authenticator or Authy
3. Enter 6-digit code to activate
4. Save the 10 backup codes securely

Once enabled, login requires: password + 6-digit TOTP code

---

## Support

- Health check: `https://yourdomain.co.ke/health/`
- API docs: `https://yourdomain.co.ke/api/docs/`
- Logs: `/var/log/quicklender/quicklender.log`

