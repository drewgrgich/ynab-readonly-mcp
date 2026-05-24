---
name: paycheck-surplus-check
description: >-
  Work out how much cash is genuinely free after a paycheck by netting upcoming
  bills across the whole pay cycle, not just the next few days. Use this whenever
  the user just got paid and wonders what's left, asks how much they can safely
  spend, save, or put toward debt this week or this pay period, asks "what can I
  afford right now," or wants to avoid over-committing money that's already
  spoken for. Trigger on phrases like "how much extra do I have," "what's my
  surplus this paycheck," "can I afford to send $X to my loan," or "just got
  paid, what's safe to use." Requires a connected read-only YNAB MCP server.
---

# Paycheck Surplus Check

Answer the question "how much of this paycheck is *actually* free?" honestly — by looking across the entire pay cycle, not just the bills due in the next day or two. This skill reads and advises only; the user makes any transfers or payments themselves.

## The trap this avoids

People get paid weekly or biweekly but their biggest bills (rent/mortgage) hit monthly. So the week a paycheck lands often *looks* flush, while the week the big bill lands is tight. Judging "free surplus" off the current week in isolation leads to over-spending and then scrambling. The fix is to net the paycheck against the **whole cycle's** obligations before calling anything surplus.

## Steps

1. **Snapshot the money.** Call `ynab_list_accounts` for current balances and `ynab_get_scheduled_transactions` for what's coming.

2. **Set the cycle horizon.** Figure out when the next paycheck lands (ask the cadence — weekly, biweekly, semi-monthly — if it isn't obvious from inflows). The relevant window is from now until the paycheck *after* next, so you can see the lumpy bill and the income meant to cover it together.

3. **Total committed outflows in the window.** Add up scheduled bills, expected variable spending (groceries, gas, dining — ask for a rough number if unknown), and any **sinking-fund / goal contributions** the user makes each cycle.

4. **Exclude money that's already spoken for.** In YNAB, dollars sitting in savings, holding, or sinking-fund categories are already assigned to a future purpose — they are *not* free surplus, even though they're sitting in an account. Subtract them. This is the most common source of a falsely high "surplus" number.

5. **Apply the lumpy-week rule.** Only count this paycheck's leftover as truly free if the cycle's biggest bill (usually housing) is already covered by the paycheck that lands right before it. If it isn't, this paycheck's "extra" is really pre-funding that bill — not surplus.

6. **Report and recommend.** Give the free-surplus number, then suggest where it could go (toward a debt — pair with `debt-payoff-planner` — or a savings goal), with a conservative buffer recommendation for the first cycle or two while the user calibrates.

## Output format

```
## True free surplus this paycheck: ~$X

What landed: $A
Committed this cycle: $B  (bills $..., variable $..., sinking funds $...)
Already earmarked (excluded): $C
Lumpy bill check: [covered by the prior paycheck / not yet — hold $D]

Suggestion: send ~$E toward [goal/debt], keep ~$F as buffer.
```

## Honesty notes

If income for the cycle isn't certain (variable hours, a pending payment), say so and size the recommendation conservatively. And never instruct the user that you've moved money — you can only recommend; they act.
