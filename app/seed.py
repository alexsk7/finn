"""Seed demo data so the dashboard has something to render on first run."""

from .db import get_conn


def seed_demo() -> None:
    with get_conn() as conn:
        flag = conn.execute(
            "SELECT value FROM app_flags WHERE key='demo_seeded'"
        ).fetchone()
        if flag:
            return  # seeded before, or user explicitly reset

        # Migration: existing DB has data but predates app_flags table
        if conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] > 0:
            conn.execute("INSERT OR IGNORE INTO app_flags (key,value) VALUES ('demo_seeded','1')")
            return

        conn.executescript("""
            INSERT INTO accounts (name, institution, type) VALUES
                ('Primary Checking',    'Chase',      'checking'),
                ('High-Yield Savings',  'Marcus',     'savings'),
                ('Taxable Brokerage',   'Fidelity',   'brokerage'),
                ('401(k)',              'Fidelity',   'retirement_401k'),
                ('Roth IRA',            'Fidelity',   'retirement_ira'),
                ('Traditional IRA',     'Fidelity',   'retirement_ira'),
                ('HSA',                 'HealthEquity',      'hsa'),
                ('Auto Loan',           'Chase',      'loan'),
                ('Mortgage',           'Rocket',      'loan');

            INSERT INTO real_estate (name, estimated_value, mortgage_balance, purchase_price, purchase_date) VALUES
                ('Primary Residence', 620000, 410000, 480000, '2020-06-15');

            INSERT INTO allocation_targets (asset_class, target_pct) VALUES
                ('us_equity',          60),
                ('intl_equity',        20),
                ('bond',               10),
                ('real_estate_fund',    5),
                ('cash_equiv',          4),
                ('other',               1);

            INSERT INTO prices (symbol, price) VALUES
                ('VTI',   270.12),
                ('VXUS',  62.44),
                ('BND',   72.18),
                ('VNQ',   85.30),
                ('SGOV',  100.25),
                ('BRK.B', 458.77);

            INSERT INTO holdings (account_id, symbol, name, asset_class, shares, cost_basis) VALUES
                (3, 'VTI',   'Vanguard Total Stock Market ETF', 'us_equity',      420,  220.00),
                (3, 'VXUS',  'Vanguard Total International',    'intl_equity',    310,   55.20),
                (3, 'BRK.B', 'Berkshire Hathaway',              'us_equity',       45,  390.00),
                (4, 'VTI',   'Vanguard Total Stock Market ETF', 'us_equity',      680,  185.00),
                (4, 'BND',   'Vanguard Total Bond Market ETF',  'bond',           520,   78.50),
                (4, 'VXUS',  'Vanguard Total International',    'intl_equity',    200,   52.00),
                (5, 'VTI',   'Vanguard Total Stock Market ETF', 'us_equity',      210,  190.00),
                (5, 'VXUS',  'Vanguard Total International',    'intl_equity',     90,   56.00),
                (6, 'SGOV',  'iShares 0-3 Month Treasury',      'cash_equiv',     180,  100.10),
                (6, 'VNQ',   'Vanguard Real Estate ETF',         'real_estate_fund', 40,  95.00);
        """)

        # seed 24 monthly snapshots
        conn.execute("""
            INSERT INTO snapshots (snapshot_date, net_worth, liquid_cash, invested_total, home_equity, debt_total) VALUES
                ('2024-05-01', 720000,  32000, 478000, 210000, 410000),
                ('2024-06-01', 738000,  33500, 492000, 211500, 409000),
                ('2024-07-01', 751000,  31000, 508000, 212000, 408000),
                ('2024-08-01', 744000,  34500, 496000, 213500, 407000),
                ('2024-09-01', 762000,  36000, 512000, 214000, 406000),
                ('2024-10-01', 780000,  38000, 527000, 215000, 405000),
                ('2024-11-01', 801000,  35500, 549000, 216500, 404000),
                ('2024-12-01', 819000,  40000, 562000, 217000, 403000),
                ('2025-01-01', 835000,  42000, 573000, 218000, 402000),
                ('2025-02-01', 848000,  39000, 588000, 219000, 401000),
                ('2025-03-01', 831000,  41000, 568000, 220000, 400000),
                ('2025-04-01', 856000,  43500, 590000, 221000, 399000),
                ('2025-05-01', 871000,  44000, 604000, 222000, 398000),
                ('2025-06-01', 889000,  46500, 618000, 223000, 397000),
                ('2025-07-01', 902000,  48000, 630000, 224000, 396000),
                ('2025-08-01', 915000,  45000, 645000, 225000, 395000),
                ('2025-09-01', 928000,  47500, 655000, 226000, 394000),
                ('2025-10-01', 942000,  49000, 666000, 227000, 393000),
                ('2025-11-01', 958000,  51000, 678000, 228000, 392000),
                ('2025-12-01', 971000,  53000, 689000, 229000, 391000),
                ('2026-01-01', 985000,  55000, 700000, 230000, 390000),
                ('2026-02-01', 999000,  57500, 712000, 231000, 389000),
                ('2026-03-01',1012000,  58000, 723000, 232000, 388000),
                ('2026-04-01',1028000,  60000, 735000, 233000, 387000)
        """)

        conn.executescript("""
            INSERT INTO transactions (txn_date, account_id, amount, direction, category, description, recurring) VALUES
                -- ── Primary Checking (1) ──────────────────────────────────────────────────
                -- January 2026
                ('2026-01-01', 1,  9800.00, 'income',  'Salary',        'Paycheck',                      1),
                ('2026-01-15', 1,  9800.00, 'income',  'Salary',        'Paycheck',                      1),
                ('2026-01-01', 1,  2450.00, 'expense', 'Housing',       'Mortgage payment',               1),
                ('2026-01-02', 1,   192.00, 'expense', 'Utilities',     'Electric + gas',                 1),
                ('2026-01-02', 1,    85.00, 'expense', 'Subscriptions', 'Internet',                       1),
                ('2026-01-04', 1,   634.00, 'expense', 'Groceries',     'Whole Foods + Trader Joe''s',    0),
                ('2026-01-05', 1,  3500.00, 'expense', 'Investments',   '401k contribution',              1),
                ('2026-01-08', 1,   265.00, 'expense', 'Dining',        'Restaurants',                    0),
                ('2026-01-11', 1,   128.00, 'expense', 'Transport',     'Gas + parking',                  0),
                ('2026-01-12', 1,    95.00, 'expense', 'Subscriptions', 'Streaming + software',           1),
                ('2026-01-18', 1,   380.00, 'expense', 'Shopping',      'Amazon + clothing',              0),
                ('2026-01-21', 1,   155.00, 'expense', 'Health',        'Prescriptions + copays',         0),
                ('2026-01-24', 1,   110.00, 'expense', 'Entertainment', 'Concert tickets',                0),
                -- February 2026
                ('2026-02-01', 1,  9800.00, 'income',  'Salary',        'Paycheck',                      1),
                ('2026-02-15', 1,  9800.00, 'income',  'Salary',        'Paycheck',                      1),
                ('2026-02-28', 1,   850.00, 'income',  'Side Income',   'Freelance project',              0),
                ('2026-02-01', 1,  2450.00, 'expense', 'Housing',       'Mortgage payment',               1),
                ('2026-02-02', 1,   178.00, 'expense', 'Utilities',     'Electric + gas',                 1),
                ('2026-02-02', 1,    85.00, 'expense', 'Subscriptions', 'Internet',                       1),
                ('2026-02-04', 1,   598.00, 'expense', 'Groceries',     'Whole Foods',                    0),
                ('2026-02-05', 1,  3500.00, 'expense', 'Investments',   '401k contribution',              1),
                ('2026-02-09', 1,   195.00, 'expense', 'Dining',        'Restaurants',                    0),
                ('2026-02-12', 1,   142.00, 'expense', 'Transport',     'Gas + tolls',                    0),
                ('2026-02-12', 1,    95.00, 'expense', 'Subscriptions', 'Streaming + software',           1),
                ('2026-02-14', 1,   520.00, 'expense', 'Shopping',      'Valentine''s gifts + Amazon',    0),
                ('2026-02-19', 1,    80.00, 'expense', 'Health',        'Gym membership',                 1),
                ('2026-02-24', 1,    95.00, 'expense', 'Entertainment', 'Movies + events',                0),
                -- March 2026
                ('2026-03-01', 1,  9800.00, 'income',  'Salary',        'Paycheck',                      1),
                ('2026-03-15', 1,  9800.00, 'income',  'Salary',        'Paycheck',                      1),
                ('2026-03-01', 1,  2450.00, 'expense', 'Housing',       'Mortgage payment',               1),
                ('2026-03-02', 1,   201.00, 'expense', 'Utilities',     'Electric + gas + water',         1),
                ('2026-03-02', 1,    85.00, 'expense', 'Subscriptions', 'Internet',                       1),
                ('2026-03-04', 1,   672.00, 'expense', 'Groceries',     'Whole Foods + Costco',           0),
                ('2026-03-05', 1,  3500.00, 'expense', 'Investments',   '401k contribution',              1),
                ('2026-03-08', 1,   310.00, 'expense', 'Dining',        'Restaurants',                    0),
                ('2026-03-10', 1,   155.00, 'expense', 'Transport',     'Gas + parking + Uber',           0),
                ('2026-03-12', 1,    95.00, 'expense', 'Subscriptions', 'Streaming + software',           1),
                ('2026-03-16', 1,   290.00, 'expense', 'Shopping',      'Amazon + Target',                0),
                ('2026-03-20', 1,   220.00, 'expense', 'Health',        'Dental visit + prescriptions',   0),
                ('2026-03-22', 1,   130.00, 'expense', 'Entertainment', 'Sports tickets',                 0),
                -- April 2026
                ('2026-04-01', 1,  9800.00, 'income',  'Salary',        'Paycheck',                      1),
                ('2026-04-15', 1,  9800.00, 'income',  'Salary',        'Paycheck',                      1),
                ('2026-04-01', 1,  2450.00, 'expense', 'Housing',       'Mortgage payment',               1),
                ('2026-04-01', 1,   180.00, 'expense', 'Utilities',     'Electric + gas',                 1),
                ('2026-04-01', 1,    85.00, 'expense', 'Subscriptions', 'Internet',                       1),
                ('2026-04-03', 1,   620.00, 'expense', 'Groceries',     'Whole Foods',                    0),
                ('2026-04-05', 1,  3500.00, 'expense', 'Investments',   '401k contribution',              1),
                ('2026-04-08', 1,   240.00, 'expense', 'Dining',        'Restaurants',                    0),
                ('2026-04-10', 1,   145.00, 'expense', 'Transport',     'Gas + parking',                  0),
                ('2026-04-12', 1,    95.00, 'expense', 'Subscriptions', 'Software + streaming',           1),
                ('2026-04-14', 1,   310.00, 'expense', 'Shopping',      'Amazon + clothing',              0),
                ('2026-04-18', 1,   180.00, 'expense', 'Health',        'Prescriptions + copays',         0),

                -- ── High-Yield Savings (2) ────────────────────────────────────────────────
                ('2026-01-31', 2,   108.42, 'income',  'Interest',      'Monthly interest',               1),
                ('2026-02-28', 2,   110.15, 'income',  'Interest',      'Monthly interest',               1),
                ('2026-03-31', 2,   112.88, 'income',  'Interest',      'Monthly interest',               1),
                ('2026-04-23', 2,   113.50, 'income',  'Interest',      'Monthly interest',               1),

                -- ── Taxable Brokerage (3) ─────────────────────────────────────────────────
                ('2026-01-15', 3,   486.24, 'income',  'Dividends',     'VTI quarterly dividend',         0),
                ('2026-01-15', 3,   124.00, 'income',  'Dividends',     'VXUS quarterly dividend',        0),
                ('2026-04-15', 3,   491.40, 'income',  'Dividends',     'VTI quarterly dividend',         0),
                ('2026-04-15', 3,   126.20, 'income',  'Dividends',     'VXUS quarterly dividend',        0),
                ('2026-04-15', 3,    67.50, 'income',  'Dividends',     'BRK.B special dividend',         0),

                -- ── 401(k) (4) ───────────────────────────────────────────────────────────
                ('2026-01-05', 4,  3500.00, 'income',  'Retirement',    'Employee contribution',          1),
                ('2026-01-05', 4,  1750.00, 'income',  'Retirement',    'Employer match (50%)',           1),
                ('2026-02-05', 4,  3500.00, 'income',  'Retirement',    'Employee contribution',          1),
                ('2026-02-05', 4,  1750.00, 'income',  'Retirement',    'Employer match (50%)',           1),
                ('2026-03-05', 4,  3500.00, 'income',  'Retirement',    'Employee contribution',          1),
                ('2026-03-05', 4,  1750.00, 'income',  'Retirement',    'Employer match (50%)',           1),
                ('2026-04-05', 4,  3500.00, 'income',  'Retirement',    'Employee contribution',          1),
                ('2026-04-05', 4,  1750.00, 'income',  'Retirement',    'Employer match (50%)',           1),

                -- ── Roth IRA (5) ─────────────────────────────────────────────────────────
                ('2026-01-02', 5,  7000.00, 'income',  'Retirement',    '2026 Roth IRA max contribution', 0),

                -- ── HSA (6) ──────────────────────────────────────────────────────────────
                ('2026-01-05', 6,   300.00, 'income',  'HSA',           'Payroll HSA contribution',       1),
                ('2026-01-28', 6,    85.00, 'expense', 'Health',        'Prescription reimbursement',     0),
                ('2026-02-05', 6,   300.00, 'income',  'HSA',           'Payroll HSA contribution',       1),
                ('2026-02-20', 6,   220.00, 'expense', 'Health',        'Eye exam + glasses',             0),
                ('2026-03-05', 6,   300.00, 'income',  'HSA',           'Payroll HSA contribution',       1),
                ('2026-03-18', 6,   145.00, 'expense', 'Health',        'Specialist copay',               0),
                ('2026-04-05', 6,   300.00, 'income',  'HSA',           'Payroll HSA contribution',       1),
                ('2026-04-17', 6,    65.00, 'expense', 'Health',        'Prescriptions',                  0);

            INSERT INTO budget_categories (name, monthly_target, direction) VALUES
                ('Salary',       19600, 'income'),
                ('Side Income',   1000, 'income'),
                ('Housing',       2450, 'expense'),
                ('Utilities',      300, 'expense'),
                ('Groceries',      700, 'expense'),
                ('Dining',         300, 'expense'),
                ('Transport',      200, 'expense'),
                ('Health',         200, 'expense'),
                ('Subscriptions',  100, 'expense'),
                ('Shopping',       400, 'expense'),
                ('Investments',   3500, 'expense'),
                ('Entertainment',  150, 'expense');

            INSERT OR IGNORE INTO budget_months(month) VALUES (strftime('%Y-%m','now'));

            INSERT OR IGNORE INTO budget_month_items(month, category_id, planned_amount)
            SELECT strftime('%Y-%m','now'), id, monthly_target
            FROM budget_categories;

            INSERT INTO journal_entries (entry_date, title, body, tags, is_milestone, milestone_value) VALUES
                ('2024-11-01', 'Hit $800k net worth',
                 'Crossed $800k for the first time. Markets have been strong, kept DCAing through the dip in August.',
                 'milestone,net-worth', 1, 800000),
                ('2025-03-15', 'Rebalanced portfolio',
                 'Sold some VTI in taxable to buy VXUS — international allocation had drifted to 14%, target is 20%. No big tax hit since cost basis is low.',
                 'rebalance,tax', 0, NULL),
                ('2025-06-01', 'Refinanced mortgage consideration',
                 'Rates dropped slightly. Ran the numbers — break-even on closing costs is 3.1 years. Decided to hold for now and revisit if we see another 50bps drop.',
                 'mortgage,real-estate', 0, NULL),
                ('2026-01-10', 'New year allocation review',
                 'Bumped bond target from 8% to 10% as we get closer to a potential home upgrade in 3-4 years. Shifted 2% from US equity.',
                 'allocation,bonds', 0, NULL),
                ('2026-04-01', 'Crossed $1M milestone',
                 'Net worth officially over $1M this month. Home equity + investment portfolio carried most of the growth. Next goal: $1.5M.',
                 'milestone,net-worth', 1, 1028000);

            INSERT OR IGNORE INTO app_flags (key, value) VALUES ('demo_seeded', '1');
        """)
