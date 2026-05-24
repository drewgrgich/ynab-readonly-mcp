#!/usr/bin/env python3
"""
Debt payoff projection (avalanche or snowball) with minimum payments,
monthly interest accrual, a cash floor, payment rollover, and one-time events.

This is a generic planning tool — no personal data. Feed it a JSON spec.

Usage:
    python payoff_projection.py spec.json
    cat spec.json | python payoff_projection.py -

Input JSON schema:
{
  "strategy": "avalanche",            // "avalanche" (highest APR first) or "snowball" (smallest balance first)
  "monthly_surplus": 1500,            // extra $/month available beyond minimums
  "cash_floor": 0,                    // not used in the core projection; informational
  "start_month": "2026-06",           // YYYY-MM
  "max_months": 120,                  // safety cap
  "debts": [
    {"name": "Card A", "balance": 7632.0, "apr": 0.0999, "min_payment": 197.0},
    {"name": "Loan B", "balance": 8947.0, "apr": 0.0699, "min_payment": 191.0}
  ],
  "one_time_extra": {"2026-07": -2256, "2026-12": 1000}
      // optional: negative = a one-time expense that reduces that month's surplus;
      //           positive = a one-time inflow that adds to that month's surplus.
}

Output: prints a month-by-month table, per-debt payoff months, total interest,
and the debt-free month.
"""
import json
import sys
from datetime import date


def _month_iter(start_ym, n):
    y, m = (int(x) for x in start_ym.split("-"))
    for _ in range(n):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def project(spec):
    strategy = spec.get("strategy", "avalanche")
    surplus = float(spec.get("monthly_surplus", 0))
    start = spec.get("start_month", date.today().strftime("%Y-%m"))
    max_months = int(spec.get("max_months", 120))
    one_time = spec.get("one_time_extra", {}) or {}

    debts = []
    for d in spec["debts"]:
        debts.append({
            "name": d["name"],
            "bal": float(d["balance"]),
            "apr": float(d.get("apr", 0.0)),
            "min": float(d.get("min_payment", 0.0)),
            "retired": None,
        })

    def priority_order():
        live = [d for d in debts if d["bal"] > 0.005]
        if strategy == "snowball":
            return sorted(live, key=lambda d: d["bal"])
        return sorted(live, key=lambda d: d["apr"], reverse=True)  # avalanche

    rows = []
    total_interest = 0.0

    for i, ym in enumerate(_month_iter(start, max_months)):
        if all(d["bal"] <= 0.005 for d in debts):
            break

        # 1) accrue interest
        month_interest = 0.0
        for d in debts:
            if d["bal"] > 0:
                interest = d["bal"] * d["apr"] / 12.0
                d["bal"] += interest
                month_interest += interest
        total_interest += month_interest

        # 2) freed-up minimums (from already-retired debts) roll into the surplus
        freed = sum(d["min"] for d in debts if d["bal"] <= 0.005 and d["retired"] is not None)
        budget = surplus + freed + float(one_time.get(ym, 0.0))

        # 3) pay minimums on live debts
        for d in debts:
            if d["bal"] > 0:
                pay = min(d["min"], d["bal"])
                d["bal"] -= pay
                budget -= pay

        # 4) throw remaining budget at debts in priority order
        if budget > 0:
            for d in priority_order():
                if budget <= 0:
                    break
                pay = min(budget, d["bal"])
                d["bal"] -= pay
                budget -= pay

        # 5) mark newly retired debts
        for d in debts:
            if d["bal"] <= 0.005 and d["retired"] is None:
                d["bal"] = 0.0
                d["retired"] = ym

        rows.append((ym, {d["name"]: round(d["bal"], 2) for d in debts}))

    debt_free = rows[-1][0] if rows and all(d["bal"] <= 0.005 for d in debts) else "NOT within max_months"
    return {
        "rows": rows,
        "total_interest": round(total_interest, 2),
        "debt_free_month": debt_free,
        "payoff": {d["name"]: d["retired"] for d in debts},
    }


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "-"
    raw = sys.stdin.read() if arg == "-" else open(arg).read()
    spec = json.loads(raw)
    result = project(spec)

    names = [d["name"] for d in spec["debts"]]
    print(f"Strategy: {spec.get('strategy', 'avalanche')}")
    print("Month   | " + " | ".join(f"{n[:12]:>12}" for n in names))
    print("-" * (10 + 15 * len(names)))
    for ym, bals in result["rows"]:
        print(f"{ym} | " + " | ".join(f"{bals[n]:>12,.0f}" for n in names))
    print()
    for name, when in result["payoff"].items():
        print(f"  {name} retired: {when or 'NOT retired'}")
    print(f"\nTotal interest paid: ${result['total_interest']:,.2f}")
    print(f"Debt-free month:     {result['debt_free_month']}")


if __name__ == "__main__":
    main()
