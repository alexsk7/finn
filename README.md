# finctl

A local-first personal finance dashboard. Tracks net worth, investments, accounts, real estate, taxes, and budget — all in a single SQLite database that never leaves your machine.

> **No accounts. No cloud. No subscriptions.** Just run it and point your browser at `localhost:8080`.

---

## Features

- **Dashboard** — net worth history chart with projection overlay, KPI tiles (NW, invested, home equity, cash, debt, and other assets when present), allocation donut, cashflow summary, alerts, market ticker strip
- **Investments** — holdings by account, allocation vs. target, asset class performance, tax-loss harvesting candidates
- **Accounts** — grouped account list with live-computed balances; drill down into transaction history; payoff projection for credit/loan accounts
- **Real Estate** — equity, LTV, mortgage amortization schedule, appreciation projection, capex log; optionally link a loan account for live mortgage balance tracking
- **Tax** — unrealized gains/losses, YTD investment income breakdown, TLH candidates (brokerage accounts only)
- **Budget** — MTD income and expense vs. targets, savings rate
- **Journal** — notes and milestones log; milestone entries surface as dashboard alerts
- **Data management** — full CRUD for all entities; CSV import for holdings (Fidelity/Schwab/Vanguard), transactions (bank exports), and historical snapshots

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — handles the Python environment and dependencies automatically
- Python 3.12+

---

## Quick start

```bash
git clone https://github.com/jacksonrc/finctl.git
cd finctl
./run.sh
```

Your browser opens automatically once the server is ready. A demo dataset loads on first run so the dashboard isn't empty.

To use a different port:

```bash
./run.sh 9000
```

The server auto-reloads on file changes. On first run, `init_db()` creates the schema and `seed_demo()` inserts demo data — both are safe to run repeatedly.

---

## Replacing demo data with your own

1. Go to **Data → Danger Zone** and click **Reset All Data**. This wipes all tables and clears the demo seed flag.
2. Restart the server (`./run.sh`) — the schema is recreated on startup.
3. Add your accounts in **Data → Accounts**.
4. Import holdings, transactions, and historical snapshots via the CSV import cards in each tab, or enter them manually.

---

## Architecture

Single-process, local-only web app. No authentication, no external API dependencies, no build step.

| Layer | Stack |
|---|---|
| Server | FastAPI + Uvicorn |
| Database | SQLite (WAL mode) |
| Templates | Jinja2 |
| Frontend | Vanilla JS + Chart.js + Alpine.js |

**Current account balances are computed live from transactions and holdings**, not from stored snapshots. Snapshots are recorded periodically to build the net worth history chart.

**Price data** is fetched from Yahoo Finance via `yfinance`. Prices auto-refresh Mon–Fri at 4:05 PM ET; you can also trigger a manual refresh from the Prices tab or the dashboard. `yfinance` makes outbound HTTP requests to Yahoo Finance — price refresh will fail silently in air-gapped environments. All other features work offline.

---

## CSV import formats

| Import | Location | Format |
|---|---|---|
| Holdings | Data → Holdings tab | Fidelity, Schwab, or Vanguard export |
| Transactions | Data → Transactions tab | Standard bank CSV (date, description, amount columns) |
| Historical snapshots | Data → Snapshot tab | `date, net_worth, liquid_cash, invested_total, home_equity, debt_total` |

---

## Security note

finctl has **no authentication**. `./run.sh` binds to `127.0.0.1` (loopback only) so it is not reachable from other machines by default. Do not expose it on a public or shared network interface without adding an authentication layer first (e.g., an authenticating reverse proxy).

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
