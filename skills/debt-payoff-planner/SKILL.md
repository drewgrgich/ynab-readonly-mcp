---
name: debt-payoff-planner
description: >-
  Build a month-by-month debt payoff plan from YNAB data using the avalanche
  (highest interest first) or snowball (smallest balance first) method. Use this
  whenever the user wants to pay off debt faster, asks when they'll be debt-free,
  wants a payoff timeline or projection, asks whether to attack one debt before
  another, wonders how much extra to put toward debt, or compares avalanche vs.
  snowball. Trigger even when the user doesn't use those words — phrases like
  "when will I finish paying off my car," "should I pay the credit card or the
  loan first," "what's my debt-free date," or "I have some extra money, where
  should it go" all apply. Requires a connected read-only YNAB MCP server.
---

# Debt Payoff Planner

Turn the balances in a YNAB budget into a concrete, month-by-month payoff plan and a debt-free date. This skill only *reads* and *advises* — it never moves money or changes the budget. The user executes payments themselves.

## Why this is useful

People rarely know their real debt-free date because the math is tedious: interest accrues monthly, minimums differ, and as each debt clears its payment should roll onto the next one. Doing that by hand is error-prone. This skill makes the projection explicit and honest, so the user can see the payoff date and the cost of different choices.

## What YNAB does and doesn't give you

The server can read balances, account types, and recurring payments — but **YNAB does not store interest rates.** APR is the single most important input for an avalanche plan, so you must get it from the user. Don't guess or skip it.

## Steps

1. **Pull the debts.** Call `ynab_list_accounts`. Treat accounts with negative balances and a liability type as debts: `creditCard`, `lineOfCredit`, `personalLoan`, `studentLoan`, `autoLoan`, `mortgage`, `otherLiability`/`otherDebt`. List them back to the user with balances.

2. **Confirm scope and rates.** Ask the user:
   - Which debts to include. Mortgages are usually *excluded* from an aggressive payoff plan (low rate, very long term) — confirm rather than assume.
   - The **APR** for each included debt.
   - Their **monthly amount available for debt** (the surplus beyond normal expenses). If they don't know it, suggest running the `paycheck-surplus-check` skill first.
   - A **cash floor** — the minimum cash they want to keep on hand and never spend down (an emergency buffer). Acceleration only uses cash above this floor.

3. **Find the minimums.** Call `ynab_get_scheduled_transactions` to find the recurring payment for each debt, or ask. Minimums always get paid; the surplus is what accelerates payoff.

4. **Pick a strategy and explain the trade-off.**
   - **Avalanche** (default): attack the highest-APR debt first. Mathematically optimal — it minimizes total interest.
   - **Snowball**: attack the smallest balance first. Costs a little more interest but delivers quick wins, which helps people who need momentum to stick with it.
   - If the user is unsure, offer to show both so they can see the interest difference against the motivational difference.

5. **Project it.** Use `scripts/payoff_projection.py` rather than doing the arithmetic by hand — it's deterministic and handles the rollover correctly. Each month it accrues interest, pays minimums, then throws all available surplus (above the cash floor) at the priority debt; when a debt clears, its freed-up minimum rolls into the surplus for the next one. Pass the debts, surplus, strategy, and any one-time events as JSON. See the script's header for the input format.

6. **Account for one-time events.** Ask about large known one-offs in the window (a trip, a tax bill, an annual insurance premium, a bonus). These move the date and belong in the projection, not as a surprise later.

## Output format

Lead with the answer, then show the work:

```
## Debt-free date: [Month Year]

| Debt | Balance | APR | Retired |
|------|---------|-----|---------|
| ...  | ...     | ... | [Month] |

- Strategy: [avalanche/snowball] — [one line on why]
- Total interest paid: $X
- [If comparing] Snowball would cost $Y more but clears [smallest debt] in [month].
```

Then a short month-by-month table (or the highlights if it's long), and a clear list of the assumptions you used (APRs, surplus, cash floor, one-time events) so the user can challenge any of them.

## Honesty notes

State the assumptions the date depends on — especially the monthly surplus and any income that isn't guaranteed (bonuses, variable hours, expected payments). If the surplus is optimistic, the date is optimistic. A trustworthy later date beats a cheerful wrong one.
