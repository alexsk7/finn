<p align="center">
  <img src="static/logo-finn.svg" alt="finn" width="260">
</p>

<p align="center">
  A local-first personal finance dashboard.<br>
  Net worth, investments, accounts, real estate, taxes, and budget — in a single SQLite file that never leaves your machine.
</p>

<p align="center">
  <strong>No accounts. No cloud. No subscriptions.</strong>
</p>

---

## Features

- **Dashboard** — net worth history chart with 10-year projection, KPI tiles with sparklines, allocation donut, cashflow summary, market ticker strip, and milestone alerts
- **Investments** — holdings by account, allocation vs. target, asset class performance, tax-loss harvesting candidates
- **Accounts** — grouped list with live-computed balances; drill down into transaction history with inline edit; payoff projection for credit and loan accounts
- **Real Estate** — equity, LTV, mortgage amortization schedule, appreciation projection, capex log; link a loan account for live mortgage balance
- **Tax** — unrealized gains/losses, YTD investment income breakdown, TLH candidates (brokerage only)
- **Rebalance** — tax-aware rebalance calculator; new cash input reduces or eliminates required sells
- **Budget** — MTD income and expense vs. targets, savings rate
- **Journal** — notes and milestones log; milestones surface as dashboard alerts
- **Multi-portfolio** — switch between named portfolios from the sidebar; each is a separate SQLite file
- **Data management** — full CRUD for all entities; CSV import for holdings (Fidelity/Schwab/Vanguard), transactions (bank exports), and historical snapshots

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — manages the Python environment and all dependencies
- Python 3.12+

---

## Quick start

```bash
git clone https://github.com/jacksonrc/finn.git
cd finn
./run.sh
```

Your browser opens automatically once the server is ready. A demo dataset loads on first run so the dashboard isn't empty. You'll be prompted for your name the first time — this is used for the dashboard greeting and is stored locally.

To start on a different port:

```bash
./run.sh 9000
```

A `Makefile` is included for convenience:

| Command | What it does |
|---|---|
| `make run` | Start the server |
| `make run PORT=9000` | Start on a custom port |
| `make backup` | Back up all portfolio databases right now |
| `make refresh` | Trigger a price refresh on the running server |

---

## Using your own data

1. Go to **Data → Danger Zone** and click **Reset All Data** to clear the demo.
2. Restart the server — the schema is recreated on startup.
3. Add your accounts under **Data → Accounts**.
4. Import holdings, transactions, and historical snapshots via the CSV import cards in each tab, or enter them manually.

---

## Backups

finn automatically backs up all portfolio databases to `backups/` on every startup, using SQLite's online backup API (safe with WAL mode and a live server). The 30 most recent backups per portfolio are kept. Run `make backup` to trigger one on demand.

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
| Transactions | Data → Transactions | Standard bank CSV (date, description, amount) |
| Snapshots | Data → Snapshot | `date, net_worth, liquid_cash, invested_total, home_equity, debt_total` |

---

## Security

finn has no authentication. `./run.sh` binds to `127.0.0.1` (loopback only) — it is not reachable from other machines by default. Do not expose it on a network interface without adding an authentication layer first (e.g. an authenticating reverse proxy).

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
