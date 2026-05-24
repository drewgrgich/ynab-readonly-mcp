---
name: monthly-budget-review
description: >-
  Produce a clear monthly budget review from YNAB: income vs. spending, where the
  money went, overspent categories, and bills coming up. Use this whenever the
  user wants a recap of how a month went, asks where their money went, wants to
  catch overspending, asks for a spending summary or month-end review, or wants
  to know if they came out ahead. Trigger on phrases like "how did I do this
  month," "where did all my money go," "did I overspend anywhere," "give me a
  monthly review," or "recap my spending for [month]." Requires a connected
  read-only YNAB MCP server.
---

# Monthly Budget Review

Give the user a fast, honest read on a month: did they come out ahead, where did the money actually go, what got overspent, and what's coming next. Read-only — this informs; it changes nothing.

## Steps

1. **Get the month.** Determine which month (default to the current one; accept "last month" or a specific month). Call `ynab_get_month` for that month's income, budgeted, activity, and per-category breakdown.

2. **Find overspending.** From the month detail (or `ynab_list_categories`), flag any category whose **available balance is negative** — that's real overspending and the first thing the user wants to see.

3. **Rank the spending.** Sort categories by activity to surface the top spending areas. Most people are surprised by one or two — name them.

4. **Surface notable transactions.** Call `ynab_list_transactions` (filter to the month) to pull the largest individual transactions, which often explain a category that ran hot.

5. **Look ahead.** Call `ynab_get_scheduled_transactions` for upcoming recurring bills so the review ends with what's next, not just what's past.

6. **Add one or two observations.** Don't just dump numbers — note the one or two things that actually matter (a category trending up, a great month for dining discipline, an unusual one-off). Keep it kind and useful, not preachy.

## Output format

```
## [Month] review

Income: $A   Spent: $B   Net: [+/-]$C

Overspent: [category (−$x), ...]  (or "Nothing overspent — nice.")

Top spending:
1. [category] — $x
2. ...

Notable: [largest / unusual transactions]

Coming up: [next big scheduled bills]

Takeaway: [1–2 plain-language observations]
```

## Tone

Be a helpful co-pilot, not a scold. If a month went over, state it plainly and move on to what's actionable. If it went well, say so — positive reinforcement keeps people engaged with their budget.
