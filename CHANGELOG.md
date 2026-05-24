# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project follows
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-05-24

### Added
- Initial release. A read-only YNAB MCP server with nine tools: list budgets,
  budget summary, list accounts, list categories, list transactions, get month,
  list months, list payees, and scheduled transactions.
- Optional `YNAB_BUDGET_ID` environment variable to set a default budget.
- Bundled analysis skills (`skills/`): `debt-payoff-planner`,
  `paycheck-surplus-check`, `sinking-fund-checkup`, and `monthly-budget-review`.
- A test that fails the build if any write HTTP verb appears in the source,
  turning the read-only design into an enforced guarantee.
- Packaging via `pyproject.toml` with a `ynab-readonly-mcp` console entry point.
- CI workflow that compiles the server and runs the test suite on every push.
- `ynab_list_accounts` now surfaces the stored interest rate and minimum payment
  for loan/debt-type accounts (mortgage, student loan, personal loan, auto loan,
  etc.). Credit cards and lines of credit have no rate in YNAB, so none is shown.
  The `debt-payoff-planner` skill reads these automatically and only asks the user
  for card/line-of-credit rates.
