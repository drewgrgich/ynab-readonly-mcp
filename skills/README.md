# Bundled Skills

These are optional [Agent Skills](https://modelcontextprotocol.io/) that pair with the read-only YNAB MCP server. Each is a focused playbook that tells an AI assistant how to turn the data this server reads into something useful — a payoff plan, a surplus check, a savings checkup, a monthly review.

They fit the server's philosophy: every skill **reads and advises only**. None of them moves money, changes a budget, or takes an action — they help you *understand* your finances and recommend what you might do. You stay in control of every actual change.

| Skill | Use it when you want to… |
|-------|--------------------------|
| [`debt-payoff-planner`](./debt-payoff-planner/) | See a month-by-month payoff plan and your debt-free date (avalanche or snowball) |
| [`paycheck-surplus-check`](./paycheck-surplus-check/) | Know how much of a paycheck is genuinely free after the whole cycle's bills |
| [`sinking-fund-checkup`](./sinking-fund-checkup/) | Check whether your savings goals are on track and what to set aside monthly |
| [`monthly-budget-review`](./monthly-budget-review/) | Recap a month: income vs. spend, overspending, and what's coming up |

## Using them

How you load a skill depends on your client. In general, point your assistant at the skill folder (or install it via your client's skills mechanism) and ask the relevant question — the description in each `SKILL.md` is written so the assistant knows when to reach for it. All four assume this YNAB MCP server is connected so they can read your budget.

Each skill is a single `SKILL.md` (plus, for the payoff planner, a small projection script). They're short and readable — open one up to see exactly what it will do before you use it.
