<p align="center">
  <img src="static/logo-finn.svg" alt="finn" width="200">
  <br>
  <strong>finn is your personal finance hub that stays <em>personal</em>.</strong>
</p>
<p>  
  Track your net worth, budget, investments, real estate, tax-loss harvesting, and more — all in a local app and SQLite file so that your financial data never has to leave your computer.
</p>
<p>
  <strong>Open source & local-first. No subscriptions required. No accounts. No ads. No cloud. No AUM fees. No data harvesting.
</p>
<p>
  Just import your transactions, add your accounts, and let finn do the hard work for you.</strong>
</p>

<p><em>Under active development. Expect rough edges, fast iteration, and occasional breaking changes.</em></p>

---

## Features

- **Dashboard** — net worth history chart with 10-year projection, KPI tiles with sparklines, allocation donut, cashflow summary, market ticker strip, and milestone alerts
- **Investments** — holdings by account, allocation vs. target, asset class performance, tax-loss harvesting candidates
- **Accounts** — grouped list with live-computed balances; drill down into transaction history with inline edit; payoff projection for credit and loan accounts
- **Real Estate** — equity, LTV, mortgage amortization schedule, appreciation projection, capex log; link a loan account for live mortgage balance
- **Tax** — unrealized gains/losses, YTD investment income breakdown, TLH candidates (brokerage only)
- **Rebalance** — tax-aware rebalance calculator; new cash input reduces or eliminates required sells
- **Budget** — zero-based monthly planning with editable income/expense plans, actuals, variance, month navigation, copy-month workflow, and an uncategorized transaction inbox
- **Journal** — notes and milestones log; milestones surface as dashboard alerts
- **Multi-portfolio** — switch between named portfolios from the sidebar; each is a separate SQLite file
- **Data management** — full CRUD for all entities; CSV import for holdings (Fidelity/Schwab/Vanguard), transactions (bank exports), and historical snapshots

---

## Prerequisites

- [mise](https://mise.jdx.dev/) — installs the repo's pinned Python, `uv`, `ruff`, and `ty` versions from [mise.toml](mise.toml)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — manages the virtual environment and dependencies once provisioned by mise

If you're using zsh, enable mise in your shell startup so repo-local tools resolve automatically:

```bash
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc
exec zsh
```

---

## Quick start

```bash
git clone https://github.com/jacksonrc/finn.git
cd finn
make setup
make run
```

Your browser opens automatically once the server is ready. A demo dataset loads on first run so the dashboard isn't empty. You'll be prompted for your name the first time — this is used for the dashboard greeting and is stored locally.

Visit `http://localhost:8080/landing` for a public-style product overview page. The app dashboard remains at `/`.

To start on a different port:

```bash
./run.sh 9000
```

A `Makefile` is included for convenience:

| Command | What it does |
|---|---|
| `make setup` | Trust the repo config, install the pinned Python, `uv`, `ruff`, and `ty` via mise, install the repo Git hooks, and sync dependencies |
| `make hooks` | Point Git at the repo's committed hooks in `.githooks/` |
| `make lint` | Run Ruff across the repository |
| `make typecheck` | Run ty across the repository |
| `make check` | Run both linting and type checking |
| `make run` | Start the server |
| `make run PORT=9000` | Start on a custom port |
| `make backup` | Back up all portfolio databases right now |
| `make refresh` | Trigger a price refresh on the running server |

Git hooks are versioned in `.githooks/` and installed by `make setup`.
The pre-commit hook runs `make lint`; the pre-push hook runs `make check`.

---

## Using your own data

1. Go to **Data → Danger Zone** and click **Reset All Data** to clear the demo.
2. Restart the server — the schema is recreated on startup.
3. Add your accounts under **Data → Accounts**.
4. Import holdings, transactions, and historical snapshots via the CSV import cards in each tab, or enter them manually.
5. Use **Budget** to plan any month ahead. Imported transactions without a category land in **Data → Transactions → Uncategorized**, where they can be assigned in bulk.

---

## Backups

finn automatically backs up all portfolio databases to `backups/` on every startup, using SQLite's online backup API (safe with WAL mode and a live server). The 30 most recent backups per portfolio are kept. Run `make backup` to trigger one on demand.

---

## Roadmap

finn already covers the core local-first personal finance workflow: net worth, account balances, budgeting, investments, tax-loss harvesting, rebalancing, real estate, journal notes, CSV imports, multi-portfolio switching, and local backups.

Planned next steps:

- **Stats / Value page** — app opens, daily streak, money tracked, savings and investing totals, tax losses harvested, and estimated advisory fees avoided
- **Testing, linting, and type checking** — expand the static analysis ruleset and add a committed test suite before broader contributor activity
- **Business intelligence** — investigate a future business/bookkeeping area once the existing bookkeeper utility and schema are confirmed

See [TASKS.md](TASKS.md) for the detailed working checklist.

---

## Architecture

Single-process, local-only web app. No build step, no external services required.

| Layer | Stack |
|---|---|
| Server | FastAPI + Uvicorn |
| Database | SQLite (WAL mode) |
| Templates | Jinja2 |
| Frontend | Vanilla JS + Chart.js + Alpine.js |

**Balances are computed live from transactions and holdings** — not from stored snapshots. Snapshots are recorded periodically and used only for the net worth history chart and MoM/YTD comparisons.

**Price data** is fetched from Yahoo Finance via `yfinance`. Prices auto-refresh Mon–Fri at 4:05 PM ET; you can also trigger a manual refresh from the Prices tab. Price refresh will fail silently in air-gapped environments — all other features work fully offline.

---

## CSV import formats

| Import | Location | Format |
|---|---|---|
| Holdings | Data → Holdings | Fidelity, Schwab, or Vanguard export |
| Transactions | Data → Transactions | Standard bank CSV (`date`, `amount`, optional `direction`, optional `category`, `payee`/`merchant`, `description`) |
| Snapshots | Data → Snapshot | `date, net_worth, liquid_cash, invested_total, home_equity, debt_total` |

Transaction categories are optional on import. Rows without a category are saved as `uncategorized` so you can import quickly, then categorize them later in bulk.

---

## Security

finn has no authentication. `./run.sh` binds to `127.0.0.1` (loopback only) — it is not reachable from other machines by default. Do not expose it on a network interface without adding an authentication layer first (e.g. an authenticating reverse proxy).

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
