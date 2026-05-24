---
name: sinking-fund-checkup
description: >-
  Check whether savings goals and sinking funds are on track and compute the
  monthly amount needed to catch up. Use this whenever the user asks if they're
  saving enough for an upcoming non-monthly bill (insurance premiums, property
  taxes, holidays, annual subscriptions, tuition), whether their YNAB goals or
  targets are funded, how much to set aside each month, or wants a checkup on
  their envelopes. Trigger on phrases like "am I on track for my insurance bill,"
  "how much should I save each month for X," "are my goals funded," "will I have
  enough saved by [date]," or "check my sinking funds." Requires a connected
  read-only YNAB MCP server.
---

# Sinking Fund Checkup

Tell the user, for each savings goal, whether it's funded, behind, or ahead — and exactly how much to contribute monthly to hit it on time. Read-only: this reports the gaps; the user funds the categories in YNAB.

## Why sinking funds matter

A sinking fund spreads a big, infrequent bill (a $1,800 semi-annual insurance premium, say) into small monthly contributions so it never blows up a single month's budget. The whole approach only works if the contributions are actually keeping pace with the target — and that's easy to lose track of across a dozen envelopes. This checkup surfaces the ones quietly falling behind before the bill arrives.

## Steps

1. **Read the categories.** Call `ynab_list_categories`. Categories with a goal have a goal marker (YNAB exposes `goal_type` — e.g. a target balance, a target balance by date, or a monthly funding goal). Focus on these, plus any the user names.

2. **For each goal, compute the gap.** Compare the **available balance** against the **target amount**. Gap = target − available (a positive gap means underfunded).

3. **Compute the monthly catch-up.**
   - If the goal has a **target date**, months remaining = months between now and that date; monthly catch-up = gap ÷ months remaining.
   - If there's no date, report the gap and, if the user can tell you when the bill is due, compute from there.

4. **Classify and prioritize.** Mark each goal funded / on track / behind. Push the **time-sensitive** ones (due soon and underfunded) to the top — those are where a missed contribution actually hurts.

5. **Watch for the lumpy ones.** Biannual or annual bills (insurance, registration, taxes) are the classic sinking-fund failures because the due date feels far away. Call these out specifically.

## Output format

```
## Sinking fund checkup

| Goal | Saved | Target | Due | Status | Monthly catch-up |
|------|-------|--------|-----|--------|------------------|
| ...  | $..   | $..    | ... | behind | $.. /mo          |

Behind and time-sensitive: [list]
On track: [list]
Total monthly contribution to keep everything on schedule: $X
```

## Note

The numbers come straight from the budget, so this is a factual checkup, not a guess. If a goal has no target or date set in YNAB, say so and ask the user for the bill amount and due date rather than inventing them.
