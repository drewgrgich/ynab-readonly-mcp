# YNAB Read-Only MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) server that lets an AI assistant (Claude, Cursor, etc.) **read** your [YNAB](https://www.ynab.com/) budget — and *only* read it.

Every tool in this server issues `GET` requests against the YNAB API. There is no code path that can create, update, approve, or delete anything in your budget. If you want an AI that can help you understand your money without any chance of it changing your data, this is built for exactly that.

> **Unofficial.** This project is not affiliated with, endorsed by, or sponsored by You Need A Budget LLC. "YNAB" is a trademark of its respective owner.

## Why this one?

There are other excellent YNAB MCP servers, and several of them are more *capable* than this one — they can add transactions, approve them, update categories, or expose the entire API surface. That power is great if you want an AI to actively manage your budget.

This server makes the opposite bet: **safety and legibility over capability.**

- **Read-only by design.** The server only ever performs `GET` requests, and every tool is annotated `readOnlyHint: true`. There is no `create`, `update`, or `delete` tool to misfire — not because the model is asked nicely to behave, but because the capability isn't in the code. It's the version you'd be comfortable pointing at your real, live budget.
- **Clean, human-readable output.** Tools return formatted Markdown — grouped accounts, dollar-formatted balances, tidy tables — rather than raw API JSON. That's easier for the model to reason over and easier for you to skim in the chat.
- **One auditable file, no build step.** The whole server is a single ~600-line Python file you can read top to bottom in a few minutes. No transpile, no bundle, no `dist/`. Verify for yourself that it never writes.
- **Your token never touches the model.** The YNAB Personal Access Token is read from an environment variable and used only to authenticate HTTP calls. It is never passed to the LLM.

## Choosing between YNAB MCP servers

The YNAB + MCP ecosystem is in good shape, and the other servers out there are genuinely good — some are more powerful than this one. The right choice just depends on the job you're hiring it for:

| If you want… | Reach for… |
|--------------|------------|
| AI that can **add, approve, or edit** transactions and manage your budget | a full read-write server — there are several solid ones |
| **Complete coverage** of every YNAB API endpoint | an auto-generated, full-API server |
| A **safe, read-only, auditable** window into your budget with clean output | **this one** |

This project isn't trying to be the most capable YNAB server — it's trying to be the one you don't have to think twice about. If "the AI literally cannot change my financial data" is a requirement rather than a nice-to-have, that's the lane this fills. It also deliberately hand-picks its nine tools rather than auto-generating one per API endpoint: that keeps the surface small, the output clean, and write endpoints out of the picture entirely.

## Tools

| Tool | What it returns |
|------|-----------------|
| `ynab_list_budgets` | All budgets on your account, with IDs |
| `ynab_get_budget_summary` | High-level overview: accounts + category-group totals |
| `ynab_list_accounts` | Account balances (working / cleared / uncleared) by type |
| `ynab_list_categories` | Category groups with budgeted / spent / available |
| `ynab_list_transactions` | Transactions, filterable by date, account, category, or payee |
| `ynab_get_month` | Full category breakdown for one budget month |
| `ynab_list_months` | Month-by-month income / budgeted / activity overview |
| `ynab_list_payees` | All payees with IDs |
| `ynab_get_scheduled_transactions` | Upcoming recurring transactions (great for forecasting) |

## Bundled skills

Because the server is read-only, the value is in *what you do with the data* — so it ships with a small set of optional [skills](./skills/) that turn reads into useful analysis. They're "safe by construction" in the same spirit: they read and advise, never act.

| Skill | What it does |
|-------|--------------|
| [`debt-payoff-planner`](./skills/debt-payoff-planner/) | Month-by-month avalanche/snowball payoff plan and debt-free date |
| [`paycheck-surplus-check`](./skills/paycheck-surplus-check/) | True free surplus after netting the whole cycle's bills |
| [`sinking-fund-checkup`](./skills/sinking-fund-checkup/) | Whether savings goals are on track + monthly catch-up |
| [`monthly-budget-review`](./skills/monthly-budget-review/) | Income vs. spend, overspending, and upcoming bills for a month |

See [`skills/README.md`](./skills/README.md) for details. They're optional — the server works fine without them.

## Security & trust

This server is meant to be pointed at a real budget, so it's built to earn that:

- **Read-only, and proven so.** Every tool issues only `GET` requests, and a test in [`tests/`](./tests/) fails the build if a `post`/`put`/`delete`/`patch` ever shows up in the source. The guarantee is enforced on every commit, not just promised in a README.
- **Your token stays out of the model.** `YNAB_API_TOKEN` is read from the environment and used only to authenticate calls to YNAB. It's never placed in tool output or sent to the LLM.
- **One file to audit.** The server is a single ~600-line Python file with no build step — read it top to bottom and confirm for yourself exactly what it does.
- **Least privilege.** A YNAB Personal Access Token only touches your YNAB data (it can't move real money), and this server only ever reads it.
- **Nothing personal in the repo.** Your token lives in your environment or a gitignored `.env`; local client configs are gitignored too.

## Setup

### 1. Get a YNAB Personal Access Token

1. Go to <https://app.ynab.com/settings/developer>
2. Click **New Token**, enter your password, and copy the token (you only see it once).

### 2. Install `uv` (recommended)

[`uv`](https://docs.astral.sh/uv/) handles Python and dependencies with no manual virtualenv.

```bash
# macOS
brew install uv
# or: curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Connect it to your MCP client

**Claude Desktop** — edit your config file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ynab": {
      "command": "uv",
      "args": [
        "run",
        "--with", "mcp[cli]",
        "--with", "httpx",
        "--with", "pydantic",
        "/absolute/path/to/ynab-readonly-mcp/ynab_mcp.py"
      ],
      "env": {
        "YNAB_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

Replace `/absolute/path/to/...` with where you cloned this repo, and `your-token-here` with your token. Restart the client; you should see the YNAB tools appear.

**Optional:** add `"YNAB_BUDGET_ID": "..."` to the `env` block to set a default budget so you don't pass a budget ID to every tool. Find the ID by running `ynab_list_budgets` once. Leave it out to use YNAB's "last-used" budget.

> Once published to PyPI, the `command`/`args` simplify to `"command": "uvx"`, `"args": ["ynab-readonly-mcp"]` — no clone required. See [`PUBLISHING.md`](./PUBLISHING.md).

### Other clients

The same idea works anywhere that speaks MCP — just match each client's config shape.

**Cursor** (`~/.cursor/mcp.json`, or `.cursor/mcp.json` in a project):

```json
{
  "mcpServers": {
    "ynab": {
      "command": "uv",
      "args": ["run", "--with", "mcp[cli]", "--with", "httpx", "--with", "pydantic",
               "/absolute/path/to/ynab-readonly-mcp/ynab_mcp.py"],
      "env": { "YNAB_API_TOKEN": "your-token-here" }
    }
  }
}
```

**OpenCode** (`~/.config/opencode/opencode.json`):

```json
{
  "mcp": {
    "ynab": {
      "type": "local",
      "command": ["uv", "run", "--with", "mcp[cli]", "--with", "httpx", "--with", "pydantic",
                  "/absolute/path/to/ynab-readonly-mcp/ynab_mcp.py"],
      "enabled": true,
      "environment": { "YNAB_API_TOKEN": "your-token-here" }
    }
  }
}
```

### Alternative: classic virtualenv

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
YNAB_API_TOKEN=your-token-here python ynab_mcp.py
```

## Example prompts

- "List my YNAB budgets."
- "What are my account balances right now?"
- "How much is left in my Groceries category this month?"
- "Show me transactions over $100 from the last two weeks."
- "What recurring bills are coming up?"

## Notes

- **Rate limit:** YNAB allows 200 requests/hour per token. The server surfaces a clear message if you hit it.
- **Amounts:** YNAB stores money in "milliunits"; the server converts everything to readable dollar strings.
- **Privacy:** the token lives only in your environment. Don't commit your real config file — see `.gitignore` and `.env.example`.

## License

[MIT](./LICENSE)
