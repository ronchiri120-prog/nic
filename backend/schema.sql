-- ═══════════════════════════════════════════════════════════════════════════════
--  QuickLender — Complete Database Schema (Phase 1–5)
--  All 17 tables + indexes + views
--  Run: psql -U postgres -d quicklender_db -f schema.sql
--  OR:  python manage.py migrate  (preferred — uses Django migrations)
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- For fuzzy search

-- ─── 1. Branches ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_regions (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(80)  NOT NULL,
    code         VARCHAR(10)  UNIQUE NOT NULL,
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ql_branches (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(120) NOT NULL,
    code         VARCHAR(10)  UNIQUE NOT NULL,
    region_id    INT          REFERENCES ql_regions(id),
    manager_id   INT,                            -- FK to ql_users added below
    disb_target  NUMERIC(14,2) DEFAULT 0,
    phone        VARCHAR(20),
    address      TEXT,
    is_active    BOOLEAN      DEFAULT TRUE,
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

-- ─── 2. Users ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_users (
    id                  SERIAL PRIMARY KEY,
    staff_id            VARCHAR(20) UNIQUE,
    email               VARCHAR(254) UNIQUE NOT NULL,
    full_name           VARCHAR(120) NOT NULL,
    phone               VARCHAR(20),
    role                VARCHAR(20) NOT NULL DEFAULT 'LOAN_OFFICER',
    branch_id           INT         REFERENCES ql_branches(id),
    is_active           BOOLEAN     DEFAULT TRUE,
    is_staff            BOOLEAN     DEFAULT FALSE,
    is_superuser        BOOLEAN     DEFAULT FALSE,
    password            VARCHAR(128) NOT NULL,
    disbursement_target NUMERIC(14,2) DEFAULT 0,
    last_login          TIMESTAMPTZ,
    date_joined         TIMESTAMPTZ  DEFAULT NOW(),
    -- 2FA
    totp_secret         VARCHAR(64),
    totp_enabled        BOOLEAN     DEFAULT FALSE,
    totp_backup_codes   JSONB       DEFAULT '[]'
);

ALTER TABLE ql_branches ADD CONSTRAINT fk_branch_manager
    FOREIGN KEY (manager_id) REFERENCES ql_users(id) DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE IF NOT EXISTS ql_audit_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INT         REFERENCES ql_users(id) ON DELETE SET NULL,
    action      VARCHAR(200) NOT NULL,
    model_name  VARCHAR(80),
    object_id   VARCHAR(40),
    details     JSONB       DEFAULT '{}',
    ip_address  VARCHAR(45),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 3. Customers ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_customers (
    id               SERIAL PRIMARY KEY,
    uid              VARCHAR(20) UNIQUE NOT NULL,
    first_name       VARCHAR(80)  NOT NULL,
    last_name        VARCHAR(80)  NOT NULL,
    national_id      VARCHAR(500) NOT NULL,      -- encrypted
    phone            VARCHAR(500),               -- encrypted
    email            VARCHAR(500),               -- encrypted
    dob              DATE,
    gender           CHAR(1),
    address          TEXT,
    branch_id        INT         REFERENCES ql_branches(id),
    loan_officer_id  INT         REFERENCES ql_users(id) ON DELETE SET NULL,
    employer         VARCHAR(150),
    employment_type  VARCHAR(50),
    monthly_income   NUMERIC(14,2) DEFAULT 0,
    loan_limit       NUMERIC(14,2) DEFAULT 50000,
    credit_score     INT,
    guarantor_name   VARCHAR(120),
    guarantor_phone  VARCHAR(500), -- encrypted
    guarantor_id     VARCHAR(500), -- encrypted
    id_front         VARCHAR(400),
    id_back          VARCHAR(400),
    status           VARCHAR(15)  DEFAULT 'ACTIVE',
    is_active        BOOLEAN      DEFAULT TRUE,
    notes            TEXT,
    created_at       TIMESTAMPTZ  DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ql_kyc_documents (
    id           SERIAL PRIMARY KEY,
    customer_id  INT         NOT NULL REFERENCES ql_customers(id) ON DELETE CASCADE,
    category     VARCHAR(20) NOT NULL,
    s3_key       VARCHAR(400) NOT NULL,
    filename     VARCHAR(200) NOT NULL,
    content_type VARCHAR(50)  NOT NULL,
    file_size    INT          DEFAULT 0,
    status       VARCHAR(10)  DEFAULT 'PENDING',
    reviewed_by_id INT        REFERENCES ql_users(id) ON DELETE SET NULL,
    notes        TEXT,
    uploaded_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ─── 4. Loan Products ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_loan_products (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(120) NOT NULL,
    loan_type      VARCHAR(10)  NOT NULL,
    min_amount     NUMERIC(14,2) NOT NULL,
    max_amount     NUMERIC(14,2) NOT NULL,
    interest_rate  NUMERIC(5,2)  NOT NULL,
    tenure_days    INT           NOT NULL,
    penalty_rate   NUMERIC(5,2)  DEFAULT 0.5,
    is_active      BOOLEAN       DEFAULT TRUE,
    created_at     TIMESTAMPTZ   DEFAULT NOW()
);

-- ─── 5. Loans ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_loans (
    id                  SERIAL PRIMARY KEY,
    loan_id             VARCHAR(20)   UNIQUE NOT NULL,
    customer_id         INT           NOT NULL REFERENCES ql_customers(id),
    product_id          INT           REFERENCES ql_loan_products(id),
    branch_id           INT           REFERENCES ql_branches(id),
    loan_officer_id     INT           REFERENCES ql_users(id) ON DELETE SET NULL,
    approved_by_id      INT           REFERENCES ql_users(id) ON DELETE SET NULL,
    principal           NUMERIC(14,2) NOT NULL,
    interest_rate       NUMERIC(5,2)  NOT NULL,
    interest_amount     NUMERIC(14,2) DEFAULT 0,
    initiation_fee      NUMERIC(14,2) DEFAULT 0,
    penalty_amount      NUMERIC(14,2) DEFAULT 0,
    total_amount        NUMERIC(14,2) DEFAULT 0,
    total_paid          NUMERIC(14,2) DEFAULT 0,
    balance             NUMERIC(14,2) DEFAULT 0,
    tenure_days         INT           NOT NULL DEFAULT 30,
    status              VARCHAR(15)   DEFAULT 'PENDING',
    disbursement_method VARCHAR(10)   DEFAULT 'MPESA',
    application_mode    VARCHAR(10)   DEFAULT 'OFFLINE',
    rejection_reason    TEXT,
    notes               TEXT,
    disbursed_at        TIMESTAMPTZ,
    due_date            DATE,
    closed_at           TIMESTAMPTZ,
    approved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ   DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ql_repayment_schedules (
    id              SERIAL PRIMARY KEY,
    loan_id         INT NOT NULL REFERENCES ql_loans(id) ON DELETE CASCADE,
    installment_no  INT NOT NULL,
    due_date        DATE NOT NULL,
    principal_due   NUMERIC(14,2) NOT NULL,
    interest_due    NUMERIC(14,2) NOT NULL,
    total_due       NUMERIC(14,2) NOT NULL,
    paid_amount     NUMERIC(14,2) DEFAULT 0,
    status          VARCHAR(10) DEFAULT 'PENDING',
    paid_at         TIMESTAMPTZ,
    UNIQUE (loan_id, installment_no)
);

-- ─── 6. Payments ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_payments (
    id              SERIAL PRIMARY KEY,
    ref             VARCHAR(20) UNIQUE NOT NULL,
    loan_id         INT         NOT NULL REFERENCES ql_loans(id),
    recorded_by_id  INT         REFERENCES ql_users(id) ON DELETE SET NULL,
    amount          NUMERIC(14,2) NOT NULL,
    method          VARCHAR(10) NOT NULL DEFAULT 'MPESA',
    payment_type    VARCHAR(12) DEFAULT 'PARTIAL',
    mpesa_ref       VARCHAR(30),
    phone           VARCHAR(20),
    notes           TEXT,
    paid_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ql_mpesa_transactions (
    id               SERIAL PRIMARY KEY,
    txn_type         VARCHAR(5)   NOT NULL,
    phone            VARCHAR(20)  NOT NULL,
    amount           NUMERIC(14,2) NOT NULL,
    loan_id          INT          REFERENCES ql_loans(id) ON DELETE SET NULL,
    mpesa_receipt    VARCHAR(30),
    conversation_id  VARCHAR(80),
    originator_id    VARCHAR(80),
    status           VARCHAR(10)  DEFAULT 'PENDING',
    result_code      INT,
    result_desc      TEXT,
    initiated_at     TIMESTAMPTZ  DEFAULT NOW(),
    completed_at     TIMESTAMPTZ
);

-- ─── 7. Allocations ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_allocations (
    id           SERIAL PRIMARY KEY,
    loan_id      INT         NOT NULL REFERENCES ql_loans(id) ON DELETE CASCADE,
    agent_id     INT         NOT NULL REFERENCES ql_users(id) ON DELETE CASCADE,
    branch_id    INT         REFERENCES ql_branches(id),
    assigned_at  TIMESTAMPTZ DEFAULT NOW(),
    is_active    BOOLEAN     DEFAULT TRUE,
    UNIQUE (loan_id, agent_id)
);

-- ─── 8. Assets ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_assets (
    id           SERIAL PRIMARY KEY,
    asset_id     VARCHAR(20) UNIQUE NOT NULL,
    customer_id  INT         NOT NULL REFERENCES ql_customers(id),
    loan_id      INT         REFERENCES ql_loans(id) ON DELETE SET NULL,
    category     VARCHAR(15) NOT NULL DEFAULT 'VEHICLE',
    make         VARCHAR(60),
    model        VARCHAR(60),
    year         INT,
    reg_number   VARCHAR(20),
    logbook_no   VARCHAR(40),
    engine_no    VARCHAR(40),
    chassis_no   VARCHAR(40),
    valuation    NUMERIC(14,2) NOT NULL,
    ltv          NUMERIC(5,2),
    valued_by    VARCHAR(120),
    valued_at    DATE,
    is_active    BOOLEAN     DEFAULT TRUE,
    notes        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 9. Notifications ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_sms_logs (
    id              SERIAL PRIMARY KEY,
    recipient       VARCHAR(20)  NOT NULL,
    customer_id     INT          REFERENCES ql_customers(id) ON DELETE SET NULL,
    loan_id         INT          REFERENCES ql_loans(id) ON DELETE SET NULL,
    template        VARCHAR(30)  DEFAULT 'CUSTOM',
    message         TEXT         NOT NULL,
    status          VARCHAR(12)  DEFAULT 'PENDING',
    at_message_id   VARCHAR(80),
    at_cost         VARCHAR(20),
    failure_reason  TEXT,
    sent_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ql_email_logs (
    id           SERIAL PRIMARY KEY,
    recipient    VARCHAR(254) NOT NULL,
    subject      VARCHAR(200) NOT NULL,
    body_text    TEXT         NOT NULL,
    status       VARCHAR(10)  DEFAULT 'PENDING',
    error        TEXT,
    sent_at      TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

-- ─── 10. Accounting / GL ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_fiscal_periods (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(50)  NOT NULL,
    start_date   DATE         NOT NULL,
    end_date     DATE         NOT NULL,
    status       VARCHAR(8)   DEFAULT 'OPEN',
    closed_by_id INT          REFERENCES ql_users(id) ON DELETE SET NULL,
    closed_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ql_gl_accounts (
    id           SERIAL PRIMARY KEY,
    code         VARCHAR(10)  UNIQUE NOT NULL,
    name         VARCHAR(120) NOT NULL,
    account_type VARCHAR(12)  NOT NULL,
    parent_id    INT          REFERENCES ql_gl_accounts(id) ON DELETE SET NULL,
    description  TEXT,
    is_active    BOOLEAN      DEFAULT TRUE,
    is_control   BOOLEAN      DEFAULT FALSE,
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ql_journal_entries (
    id           SERIAL PRIMARY KEY,
    reference    VARCHAR(30)  UNIQUE NOT NULL,
    narration    VARCHAR(255) NOT NULL,
    date         DATE         NOT NULL,
    status       VARCHAR(12)  DEFAULT 'DRAFT',
    source_type  VARCHAR(40),
    source_id    INT,
    reversal_of_id INT        REFERENCES ql_journal_entries(id) ON DELETE SET NULL,
    created_by_id  INT        REFERENCES ql_users(id) ON DELETE SET NULL,
    posted_at    TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ql_journal_lines (
    id             SERIAL PRIMARY KEY,
    entry_id       INT           NOT NULL REFERENCES ql_journal_entries(id) ON DELETE CASCADE,
    account_id     INT           NOT NULL REFERENCES ql_gl_accounts(id) ON DELETE RESTRICT,
    debit_amount   NUMERIC(16,2) DEFAULT 0,
    credit_amount  NUMERIC(16,2) DEFAULT 0,
    description    VARCHAR(200),
    branch_id      INT           REFERENCES ql_branches(id) ON DELETE SET NULL
);

-- ─── 11. Group / Chama Loans ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ql_loan_groups (
    id                SERIAL PRIMARY KEY,
    group_id          VARCHAR(20) UNIQUE NOT NULL,
    name              VARCHAR(120) NOT NULL,
    branch_id         INT         REFERENCES ql_branches(id),
    loan_officer_id   INT         REFERENCES ql_users(id) ON DELETE SET NULL,
    chairperson_id    INT         REFERENCES ql_customers(id) ON DELETE SET NULL,
    secretary_id      INT         REFERENCES ql_customers(id) ON DELETE SET NULL,
    status            VARCHAR(12) DEFAULT 'ACTIVE',
    meeting_day       VARCHAR(20),
    meeting_location  TEXT,
    max_members       INT         DEFAULT 30,
    group_fund        NUMERIC(14,2) DEFAULT 0,
    notes             TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ql_group_memberships (
    id           SERIAL PRIMARY KEY,
    group_id     INT NOT NULL REFERENCES ql_loan_groups(id) ON DELETE CASCADE,
    customer_id  INT NOT NULL REFERENCES ql_customers(id) ON DELETE CASCADE,
    role         VARCHAR(14) DEFAULT 'MEMBER',
    joined_at    TIMESTAMPTZ DEFAULT NOW(),
    is_active    BOOLEAN     DEFAULT TRUE,
    shares       INT         DEFAULT 1,
    UNIQUE (group_id, customer_id)
);

CREATE TABLE IF NOT EXISTS ql_group_loans (
    group_loan_id  VARCHAR(20)   UNIQUE NOT NULL,
    id             SERIAL PRIMARY KEY,
    group_id       INT           NOT NULL REFERENCES ql_loan_groups(id),
    product_id     INT           REFERENCES ql_loan_products(id),
    total_amount   NUMERIC(14,2) NOT NULL,
    interest_rate  NUMERIC(5,2)  NOT NULL,
    tenure_days    INT           NOT NULL,
    status         VARCHAR(12)   DEFAULT 'PENDING',
    approved_by_id INT           REFERENCES ql_users(id) ON DELETE SET NULL,
    approved_at    TIMESTAMPTZ,
    disbursed_at   TIMESTAMPTZ,
    due_date       DATE,
    notes          TEXT,
    created_at     TIMESTAMPTZ   DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ql_group_loan_shares (
    id                SERIAL PRIMARY KEY,
    group_loan_id     INT           NOT NULL REFERENCES ql_group_loans(id) ON DELETE CASCADE,
    member_id         INT           NOT NULL REFERENCES ql_group_memberships(id),
    amount            NUMERIC(14,2) NOT NULL,
    total_due         NUMERIC(14,2) NOT NULL,
    total_paid        NUMERIC(14,2) DEFAULT 0,
    balance           NUMERIC(14,2) DEFAULT 0,
    individual_loan_id INT          REFERENCES ql_loans(id) ON DELETE SET NULL UNIQUE
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_loans_customer    ON ql_loans(customer_id);
CREATE INDEX IF NOT EXISTS idx_loans_status      ON ql_loans(status);
CREATE INDEX IF NOT EXISTS idx_loans_due_date    ON ql_loans(due_date);
CREATE INDEX IF NOT EXISTS idx_loans_branch      ON ql_loans(branch_id);
CREATE INDEX IF NOT EXISTS idx_loans_officer     ON ql_loans(loan_officer_id);
CREATE INDEX IF NOT EXISTS idx_payments_loan     ON ql_payments(loan_id);
CREATE INDEX IF NOT EXISTS idx_payments_paid_at  ON ql_payments(paid_at DESC);
CREATE INDEX IF NOT EXISTS idx_customers_uid     ON ql_customers(uid);
CREATE INDEX IF NOT EXISTS idx_customers_status  ON ql_customers(status);
CREATE INDEX IF NOT EXISTS idx_customers_branch  ON ql_customers(branch_id);
CREATE INDEX IF NOT EXISTS idx_sms_status        ON ql_sms_logs(status);
CREATE INDEX IF NOT EXISTS idx_sms_created       ON ql_sms_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_je_date           ON ql_journal_entries(date DESC);
CREATE INDEX IF NOT EXISTS idx_je_status         ON ql_journal_entries(status);
CREATE INDEX IF NOT EXISTS idx_jl_account        ON ql_journal_lines(account_id);
CREATE INDEX IF NOT EXISTS idx_jl_entry          ON ql_journal_lines(entry_id);
CREATE INDEX IF NOT EXISTS idx_mpesa_status      ON ql_mpesa_transactions(status);
CREATE INDEX IF NOT EXISTS idx_allocations_agent ON ql_allocations(agent_id);
-- Trigram for fast fuzzy customer search
CREATE INDEX IF NOT EXISTS idx_customer_name_trgm ON ql_customers
    USING gin ((first_name || ' ' || last_name) gin_trgm_ops);

-- ═══════════════════════════════════════════════════════════════════════════════
-- USEFUL VIEWS
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW ql_portfolio_summary AS
SELECT
    b.name                                          AS branch,
    COUNT(l.id)                                     AS total_loans,
    COUNT(l.id) FILTER (WHERE l.status = 'ACTIVE')  AS active_loans,
    COUNT(l.id) FILTER (WHERE l.status = 'DEFAULT') AS defaulted_loans,
    COALESCE(SUM(l.principal) FILTER (WHERE l.status = 'ACTIVE'),0)  AS portfolio_gross,
    COALESCE(SUM(l.balance)   FILTER (WHERE l.status = 'ACTIVE'),0)  AS portfolio_net,
    COALESCE(SUM(l.total_paid),0)                   AS total_collected
FROM ql_loans l
JOIN ql_branches b ON l.branch_id = b.id
GROUP BY b.id, b.name;

CREATE OR REPLACE VIEW ql_par_buckets AS
SELECT
    COUNT(*) FILTER (WHERE CURRENT_DATE - due_date BETWEEN 1  AND 30)  AS par_1_30,
    COUNT(*) FILTER (WHERE CURRENT_DATE - due_date BETWEEN 31 AND 60)  AS par_31_60,
    COUNT(*) FILTER (WHERE CURRENT_DATE - due_date BETWEEN 61 AND 90)  AS par_61_90,
    COUNT(*) FILTER (WHERE CURRENT_DATE - due_date > 90)               AS par_over_90,
    COALESCE(SUM(balance) FILTER (WHERE CURRENT_DATE - due_date BETWEEN 1  AND 30), 0) AS par_1_30_bal,
    COALESCE(SUM(balance) FILTER (WHERE CURRENT_DATE - due_date BETWEEN 31 AND 60), 0) AS par_31_60_bal,
    COALESCE(SUM(balance) FILTER (WHERE CURRENT_DATE - due_date BETWEEN 61 AND 90), 0) AS par_61_90_bal,
    COALESCE(SUM(balance) FILTER (WHERE CURRENT_DATE - due_date > 90), 0)               AS par_over_90_bal
FROM ql_loans
WHERE status IN ('ACTIVE', 'DEFAULT') AND due_date < CURRENT_DATE;

CREATE OR REPLACE VIEW ql_officer_performance AS
SELECT
    u.full_name,
    u.role,
    b.name                                           AS branch,
    u.disbursement_target                            AS disb_target,
    COUNT(l.id) FILTER (WHERE l.status = 'ACTIVE')  AS active_customers,
    COALESCE(SUM(l.principal) FILTER (WHERE l.disbursed_at >= date_trunc('month', NOW())), 0) AS total_disbursed,
    COALESCE(SUM(p.amount),0)                        AS total_paid
FROM ql_users u
LEFT JOIN ql_branches b ON u.branch_id = b.id
LEFT JOIN ql_loans l    ON l.loan_officer_id = u.id
LEFT JOIN ql_payments p ON p.loan_id = l.id AND p.paid_at >= date_trunc('month', NOW())
WHERE u.role IN ('LOAN_OFFICER','CREDIT_OFFICER','COLLECTIONS')
GROUP BY u.id, u.full_name, u.role, b.name, u.disbursement_target;
