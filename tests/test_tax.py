"""Ad-hoc tests for tax loss harvesting and YTD investment income.

Run with:  uv run python tests/test_tax.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db import init_db
from app.queries import get_tax_summary

init_db()

def run():
    t = get_tax_summary()
    failures = []

    def check(label, actual, expected=None, *, minimum=None, maximum=None):
        if expected is not None and actual != expected:
            failures.append(f"FAIL  {label}: expected {expected!r}, got {actual!r}")
        elif minimum is not None and actual < minimum:
            failures.append(f"FAIL  {label}: expected ≥ {minimum}, got {actual!r}")
        elif maximum is not None and actual > maximum:
            failures.append(f"FAIL  {label}: expected ≤ {maximum}, got {actual!r}")
        else:
            tag = f"= {expected!r}" if expected is not None else f"= {actual!r}"
            print(f"  OK  {label} {tag}")

    # ── TLH candidates ────────────────────────────────────────────────────────
    print("\n--- TLH Candidates ---")
    tlh = t["tlh_candidates"]
    tlh_syms = {c["symbol"] for c in tlh}

    # ARKK: 30 shares × ($45 - $120) = -$2,250 unrealized loss
    check("ARKK in TLH candidates", "ARKK" in tlh_syms, True)
    # PLUG: 120 shares × ($2.10 - $20) = -$2,148 unrealized loss
    check("PLUG in TLH candidates", "PLUG" in tlh_syms, True)
    # Profitable holdings (VTI, VXUS, BRK.B) should NOT appear
    for sym in ("VTI", "VXUS", "BRK.B"):
        check(f"{sym} NOT in TLH candidates", sym not in tlh_syms, True)

    arkk_row = next((c for c in tlh if c["symbol"] == "ARKK"), None)
    if arkk_row:
        expected_loss = round(30 * (45.00 - 120.00), 2)   # -2250.00
        check("ARKK unrealized_loss value", arkk_row["unrealized_loss"], expected_loss)

    plug_row = next((c for c in tlh if c["symbol"] == "PLUG"), None)
    if plug_row:
        expected_loss = round(120 * (2.10 - 20.00), 2)    # -2148.00
        check("PLUG unrealized_loss value", plug_row["unrealized_loss"], expected_loss)

    check("tlh_total ≤ -4000", t["tlh_total"], maximum=-4000)

    # ── YTD investment income ─────────────────────────────────────────────────
    print("\n--- YTD Investment Income ---")
    breakdown = {r["category"]: r for r in t["ytd_income_breakdown"]}

    check("Dividends & Interest present", "Dividends & Interest" in breakdown, True)
    check("Capital Gains present",        "Capital Gains" in breakdown, True)

    div_total = breakdown.get("Dividends & Interest", {}).get("total", 0)
    check("Dividends & Interest total", round(div_total, 2), 1820.00)  # 1240 + 580

    cg_total = breakdown.get("Capital Gains", {}).get("total", 0)
    check("Capital Gains total", round(cg_total, 2), 4200.00)

    check("ytd_income_total", round(t["ytd_income_total"], 2), 6020.00)  # 1820 + 4200

    # ── Unrealized total (all brokerage holdings) ─────────────────────────────
    print("\n--- Unrealized Positions ---")
    # Profitable legacy holdings contribute ~+$66k; ARKK (-2250) and PLUG (-2148) drag it down
    check("unrealized_total > 50000", t["unrealized_total"], minimum=50000)
    check("unrealized_total < 80000", t["unrealized_total"], maximum=80000)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    if failures:
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        print(f"All tests passed  ({2 + len(tlh)} TLH candidates, "
              f"${t['ytd_income_total']:,.2f} YTD income, "
              f"${t['unrealized_total']:,.2f} unrealized)")

if __name__ == "__main__":
    run()
