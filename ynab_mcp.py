#!/usr/bin/env python3
"""
MCP Server for YNAB (You Need A Budget).

Provides read-only tools to interact with the YNAB API, including
viewing budgets, accounts, categories, transactions, and monthly summaries.
"""

import os
import json
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

import httpx
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("ynab_mcp")

# Constants
API_BASE_URL = "https://api.ynab.com/v1"
YNAB_TOKEN = os.environ.get("YNAB_API_TOKEN", "")
# Optional: set a default budget so callers don't have to pass budget_id every time.
# When unset, tools fall back to YNAB's "last-used" budget.
DEFAULT_BUDGET_ID = os.environ.get("YNAB_BUDGET_ID", "").strip()


# --- Shared Utilities ---

def _get_headers() -> dict:
    """Return authorization headers for the YNAB API."""
    if not YNAB_TOKEN:
        raise ValueError(
            "YNAB_API_TOKEN environment variable is not set. "
            "Get your token at https://app.ynab.com/settings/developer"
        )
    return {"Authorization": f"Bearer {YNAB_TOKEN}"}


def _resolve_budget(budget_id: str) -> str:
    """Resolve which budget to target.

    If the caller left budget_id at its "last-used" default (or empty) and the
    user has set a YNAB_BUDGET_ID, prefer that explicit default. Otherwise honor
    whatever the caller passed.
    """
    if (not budget_id or budget_id == "last-used") and DEFAULT_BUDGET_ID:
        return DEFAULT_BUDGET_ID
    return budget_id


async def _api_get(endpoint: str, params: Optional[dict] = None) -> dict:
    """Make a GET request to the YNAB API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/{endpoint}",
            headers=_get_headers(),
            params=params or {},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json().get("data", response.json())


def _handle_error(e: Exception) -> str:
    """Consistent error formatting."""
    if isinstance(e, ValueError):
        return f"Error: {e}"
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 401:
            return "Error: Invalid API token. Check your YNAB_API_TOKEN."
        elif status == 404:
            return "Error: Resource not found. Check the budget or account ID."
        elif status == 429:
            return "Error: Rate limit exceeded. YNAB allows 200 requests/hour. Wait and try again."
        return f"Error: YNAB API returned status {status}."
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again."
    return f"Error: {type(e).__name__}: {e}"


def _format_milliunits(milliunits: int) -> str:
    """Convert YNAB milliunit amounts to readable dollar strings."""
    amount = milliunits / 1000.0
    return f"${amount:,.2f}"


def _format_date(date_str: Optional[str]) -> str:
    """Format a YNAB date string for readability."""
    if not date_str:
        return "N/A"
    return date_str


# YNAB exposes interest rates and minimum payments only for loan/debt-type
# accounts (mortgage, studentLoan, personalLoan, autoLoan, medicalDebt,
# otherDebt). Credit cards and lines of credit have nowhere to store a rate, so
# these fields are absent there. The values are date-keyed maps; the current
# figure is the entry for the most recent date.
#
# Interest rates are integers scaled by 1000 (a "milli-percent"): 4960 == 4.96%.
# Minimum payments are in milliunits like any other money amount.
# NOTE: confirm the rate scale on first use against a loan whose rate you know.
INTEREST_RATE_SCALE = 1000


def _latest_dated_value(date_map):
    """Return the value for the most recent date key in a YNAB date-keyed map
    (e.g. debt_interest_rates), or None if the map is empty/absent."""
    if not date_map or not isinstance(date_map, dict):
        return None
    return date_map[max(date_map.keys())]


def _format_debt_fields(account: dict) -> str:
    """Summarize the stored interest rate and minimum payment for a loan/debt
    account. Returns '' when neither is present (the normal case for cash,
    checking, credit cards, and lines of credit)."""
    parts = []
    rate_raw = _latest_dated_value(account.get("debt_interest_rates"))
    if rate_raw:
        parts.append(f"Interest rate: {rate_raw / INTEREST_RATE_SCALE:.2f}%")
    min_raw = _latest_dated_value(account.get("debt_minimum_payments"))
    if min_raw:
        parts.append(f"Min payment: {_format_milliunits(min_raw)}")
    return " | ".join(parts)


# --- Input Models ---

class BudgetIdInput(BaseModel):
    """Input requiring only a budget ID."""
    model_config = ConfigDict(str_strip_whitespace=True)
    budget_id: str = Field(
        default="last-used",
        description="Budget ID, or 'last-used' for the most recently accessed budget"
    )


class AccountsInput(BaseModel):
    """Input for listing accounts."""
    model_config = ConfigDict(str_strip_whitespace=True)
    budget_id: str = Field(
        default="last-used",
        description="Budget ID, or 'last-used' for the most recently accessed budget"
    )
    include_closed: bool = Field(
        default=False,
        description="Whether to include closed accounts in results"
    )


class TransactionsInput(BaseModel):
    """Input for listing transactions."""
    model_config = ConfigDict(str_strip_whitespace=True)
    budget_id: str = Field(
        default="last-used",
        description="Budget ID, or 'last-used' for the most recently accessed budget"
    )
    since_date: Optional[str] = Field(
        default=None,
        description="Only return transactions on or after this date (YYYY-MM-DD)"
    )
    category_id: Optional[str] = Field(
        default=None,
        description="Filter to a specific category ID"
    )
    account_id: Optional[str] = Field(
        default=None,
        description="Filter to a specific account ID"
    )
    payee_id: Optional[str] = Field(
        default=None,
        description="Filter to a specific payee ID"
    )
    limit: int = Field(
        default=50,
        description="Max transactions to return",
        ge=1, le=500
    )


class MonthInput(BaseModel):
    """Input for getting a specific budget month."""
    model_config = ConfigDict(str_strip_whitespace=True)
    budget_id: str = Field(
        default="last-used",
        description="Budget ID, or 'last-used' for the most recently accessed budget"
    )
    month: str = Field(
        ...,
        description="Budget month in YYYY-MM-DD format (use first of month, e.g. '2026-03-01')"
    )


class CategoryTransactionsInput(BaseModel):
    """Input for getting transactions for a specific category."""
    model_config = ConfigDict(str_strip_whitespace=True)
    budget_id: str = Field(
        default="last-used",
        description="Budget ID, or 'last-used' for the most recently accessed budget"
    )
    category_id: str = Field(
        ..., description="The category ID to get transactions for"
    )
    since_date: Optional[str] = Field(
        default=None,
        description="Only return transactions on or after this date (YYYY-MM-DD)"
    )


# --- Tool Definitions ---

@mcp.tool(
    name="ynab_list_budgets",
    annotations={
        "title": "List YNAB Budgets",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ynab_list_budgets() -> str:
    """List all budgets available in the YNAB account.

    Returns budget names, IDs, last modified dates, and currency formats.
    Use this first to find your budget ID for other tools.
    """
    try:
        data = await _api_get("budgets")
        budgets = data.get("budgets", [])
        if not budgets:
            return "No budgets found in your YNAB account."

        lines = ["# Your YNAB Budgets\n"]
        for b in budgets:
            lines.append(f"## {b['name']}")
            lines.append(f"- **ID**: `{b['id']}`")
            lines.append(f"- **Last Modified**: {b.get('last_modified_on', 'N/A')}")
            cf = b.get("currency_format", {})
            if cf:
                lines.append(f"- **Currency**: {cf.get('iso_code', 'USD')}")
            lines.append("")

        default = data.get("default_budget")
        if default:
            lines.append(f"**Default budget**: {default['name']} (`{default['id']}`)")

        lines.append("\n> Tip: Use `last-used` as the budget_id to target your most recently accessed budget.")
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ynab_get_budget_summary",
    annotations={
        "title": "Get Budget Summary",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ynab_get_budget_summary(params: BudgetIdInput) -> str:
    """Get a high-level summary of a budget including accounts, categories overview, and recent activity.

    This is a good starting point to understand the overall state of a budget.
    """
    try:
        data = await _api_get(f"budgets/{_resolve_budget(params.budget_id)}")
        budget = data.get("budget", {})

        lines = [f"# Budget: {budget.get('name', 'Unknown')}\n"]

        # Accounts summary
        accounts = budget.get("accounts", [])
        open_accounts = [a for a in accounts if not a.get("closed", False) and not a.get("deleted", False)]
        lines.append(f"## Accounts ({len(open_accounts)} open)\n")
        total_balance = 0
        for a in sorted(open_accounts, key=lambda x: x.get("type", "")):
            bal = a.get("balance", 0)
            total_balance += bal
            cleared = a.get("cleared_balance", 0)
            lines.append(f"- **{a['name']}** ({a['type']}): {_format_milliunits(bal)} (cleared: {_format_milliunits(cleared)})")
        lines.append(f"\n**Total balance across all accounts**: {_format_milliunits(total_balance)}\n")

        # Category groups summary
        cat_groups = budget.get("category_groups", [])
        lines.append("## Category Groups\n")
        for cg in cat_groups:
            if cg.get("deleted") or cg.get("hidden"):
                continue
            name = cg.get("name", "Unknown")
            if name in ("Internal Master Category", "Hidden Categories"):
                continue
            cats = [c for c in budget.get("categories", [])
                    if c.get("category_group_id") == cg["id"]
                    and not c.get("deleted") and not c.get("hidden")]
            if cats:
                group_budgeted = sum(c.get("budgeted", 0) for c in cats)
                group_activity = sum(c.get("activity", 0) for c in cats)
                group_balance = sum(c.get("balance", 0) for c in cats)
                lines.append(f"### {name}")
                lines.append(f"  Budgeted: {_format_milliunits(group_budgeted)} | "
                             f"Spent: {_format_milliunits(group_activity)} | "
                             f"Available: {_format_milliunits(group_balance)}")
                lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ynab_list_accounts",
    annotations={
        "title": "List YNAB Accounts",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ynab_list_accounts(params: AccountsInput) -> str:
    """List all accounts in a budget with balances and types.

    Shows checking, savings, credit card, and other account types with
    their current balances and cleared balances.
    """
    try:
        data = await _api_get(f"budgets/{_resolve_budget(params.budget_id)}/accounts")
        accounts = data.get("accounts", [])

        if not params.include_closed:
            accounts = [a for a in accounts if not a.get("closed") and not a.get("deleted")]

        if not accounts:
            return "No accounts found."

        lines = ["# Accounts\n"]
        by_type: Dict[str, list] = {}
        for a in accounts:
            t = a.get("type", "other")
            by_type.setdefault(t, []).append(a)

        for acct_type, accts in sorted(by_type.items()):
            lines.append(f"## {acct_type.replace('_', ' ').title()}\n")
            for a in accts:
                bal = _format_milliunits(a.get("balance", 0))
                cleared = _format_milliunits(a.get("cleared_balance", 0))
                uncleared = _format_milliunits(a.get("uncleared_balance", 0))
                lines.append(f"- **{a['name']}** (ID: `{a['id']}`)")
                lines.append(f"  Balance: {bal} | Cleared: {cleared} | Uncleared: {uncleared}")
                debt = _format_debt_fields(a)
                if debt:
                    lines.append(f"  {debt}")
                if a.get("note"):
                    lines.append(f"  Note: {a['note']}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ynab_list_categories",
    annotations={
        "title": "List YNAB Categories",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ynab_list_categories(params: BudgetIdInput) -> str:
    """List all category groups and categories with budgeted amounts, activity, and available balances.

    Shows the current month's category data organized by group.
    """
    try:
        data = await _api_get(f"budgets/{_resolve_budget(params.budget_id)}/categories")
        groups = data.get("category_groups", [])

        lines = ["# Budget Categories\n"]
        for group in groups:
            if group.get("deleted") or group.get("hidden"):
                continue
            name = group.get("name", "Unknown")
            if name in ("Internal Master Category", "Hidden Categories"):
                continue

            cats = [c for c in group.get("categories", [])
                    if not c.get("deleted") and not c.get("hidden")]
            if not cats:
                continue

            lines.append(f"## {name}\n")
            lines.append("| Category | Budgeted | Spent | Available |")
            lines.append("|----------|----------|-------|-----------|")
            for c in cats:
                budgeted = _format_milliunits(c.get("budgeted", 0))
                activity = _format_milliunits(c.get("activity", 0))
                balance = _format_milliunits(c.get("balance", 0))
                goal_type = c.get("goal_type", "")
                goal_marker = f" [{goal_type}]" if goal_type else ""
                lines.append(f"| {c['name']}{goal_marker} | {budgeted} | {activity} | {balance} |")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ynab_list_transactions",
    annotations={
        "title": "List YNAB Transactions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ynab_list_transactions(params: TransactionsInput) -> str:
    """List transactions from a budget, optionally filtered by date, account, category, or payee.

    Returns transactions sorted by date (most recent first) with payee, category,
    amount, and memo details.
    """
    try:
        # Determine endpoint based on filters
        if params.account_id:
            endpoint = f"budgets/{_resolve_budget(params.budget_id)}/accounts/{params.account_id}/transactions"
        elif params.category_id:
            endpoint = f"budgets/{_resolve_budget(params.budget_id)}/categories/{params.category_id}/transactions"
        elif params.payee_id:
            endpoint = f"budgets/{_resolve_budget(params.budget_id)}/payees/{params.payee_id}/transactions"
        else:
            endpoint = f"budgets/{_resolve_budget(params.budget_id)}/transactions"

        api_params = {}
        if params.since_date:
            api_params["since_date"] = params.since_date

        data = await _api_get(endpoint, params=api_params)
        transactions = data.get("transactions", [])

        # Sort by date descending and limit
        transactions.sort(key=lambda t: t.get("date", ""), reverse=True)
        transactions = transactions[: params.limit]

        if not transactions:
            return "No transactions found matching your filters."

        lines = [f"# Transactions ({len(transactions)} shown)\n"]
        lines.append("| Date | Payee | Category | Amount | Memo |")
        lines.append("|------|-------|----------|--------|------|")

        for t in transactions:
            date = _format_date(t.get("date"))
            payee = t.get("payee_name", "Unknown")
            category = t.get("category_name", "Uncategorized")
            amount = _format_milliunits(t.get("amount", 0))
            memo = (t.get("memo") or "")[:40]
            cleared = t.get("cleared", "")
            flag = " *" if cleared == "uncleared" else ""
            lines.append(f"| {date} | {payee} | {category} | {amount}{flag} | {memo} |")

        lines.append("\n> \\* = uncleared transaction")
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ynab_get_month",
    annotations={
        "title": "Get Budget Month Detail",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ynab_get_month(params: MonthInput) -> str:
    """Get detailed category breakdown for a specific budget month.

    Shows income, budgeted amounts, spending, and available balances for
    every category in the specified month. Great for monthly reviews.
    """
    try:
        data = await _api_get(f"budgets/{_resolve_budget(params.budget_id)}/months/{params.month}")
        month = data.get("month", {})

        lines = [f"# Budget Month: {month.get('month', params.month)}\n"]
        lines.append(f"- **Income**: {_format_milliunits(month.get('income', 0))}")
        lines.append(f"- **Budgeted**: {_format_milliunits(month.get('budgeted', 0))}")
        lines.append(f"- **Activity (spending)**: {_format_milliunits(month.get('activity', 0))}")
        lines.append(f"- **To Be Budgeted**: {_format_milliunits(month.get('to_be_budgeted', 0))}")
        lines.append(f"- **Age of Money**: {month.get('age_of_money', 'N/A')} days\n")

        categories = month.get("categories", [])
        if categories:
            # Group by category_group_name
            groups: Dict[str, list] = {}
            for c in categories:
                if c.get("deleted") or c.get("hidden"):
                    continue
                gname = c.get("category_group_name", "Other")
                if gname in ("Internal Master Category", "Hidden Categories"):
                    continue
                groups.setdefault(gname, []).append(c)

            for gname, cats in sorted(groups.items()):
                lines.append(f"## {gname}\n")
                lines.append("| Category | Budgeted | Spent | Available |")
                lines.append("|----------|----------|-------|-----------|")
                for c in cats:
                    lines.append(
                        f"| {c['name']} "
                        f"| {_format_milliunits(c.get('budgeted', 0))} "
                        f"| {_format_milliunits(c.get('activity', 0))} "
                        f"| {_format_milliunits(c.get('balance', 0))} |"
                    )
                lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ynab_list_payees",
    annotations={
        "title": "List YNAB Payees",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ynab_list_payees(params: BudgetIdInput) -> str:
    """List all payees in a budget.

    Returns payee names and IDs. Useful for finding a payee ID
    to filter transactions.
    """
    try:
        data = await _api_get(f"budgets/{_resolve_budget(params.budget_id)}/payees")
        payees = data.get("payees", [])
        payees = [p for p in payees if not p.get("deleted")]

        if not payees:
            return "No payees found."

        lines = [f"# Payees ({len(payees)} total)\n"]
        for p in sorted(payees, key=lambda x: x.get("name", "").lower()):
            name = p.get("name", "Unknown")
            pid = p.get("id", "")
            lines.append(f"- **{name}** (ID: `{pid}`)")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ynab_list_months",
    annotations={
        "title": "List Budget Months",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ynab_list_months(params: BudgetIdInput) -> str:
    """List all budget months with income, activity, and to-be-budgeted totals.

    Shows a high-level month-by-month overview of budgeting activity.
    """
    try:
        data = await _api_get(f"budgets/{_resolve_budget(params.budget_id)}/months")
        months = data.get("months", [])

        if not months:
            return "No budget months found."

        lines = ["# Budget Months\n"]
        lines.append("| Month | Income | Budgeted | Activity | To Be Budgeted |")
        lines.append("|-------|--------|----------|----------|----------------|")

        for m in months[:24]:  # Show last 24 months
            lines.append(
                f"| {m.get('month', '?')} "
                f"| {_format_milliunits(m.get('income', 0))} "
                f"| {_format_milliunits(m.get('budgeted', 0))} "
                f"| {_format_milliunits(m.get('activity', 0))} "
                f"| {_format_milliunits(m.get('to_be_budgeted', 0))} |"
            )

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ynab_get_scheduled_transactions",
    annotations={
        "title": "List Scheduled Transactions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ynab_get_scheduled_transactions(params: BudgetIdInput) -> str:
    """List all scheduled (recurring) transactions in a budget.

    Shows upcoming recurring transactions with frequency, next date,
    and amounts. Useful for forecasting.
    """
    try:
        data = await _api_get(f"budgets/{_resolve_budget(params.budget_id)}/scheduled_transactions")
        txns = data.get("scheduled_transactions", [])

        if not txns:
            return "No scheduled transactions found."

        txns = [t for t in txns if not t.get("deleted")]
        txns.sort(key=lambda t: t.get("date_next", ""))

        lines = [f"# Scheduled Transactions ({len(txns)} total)\n"]
        lines.append("| Next Date | Payee | Category | Amount | Frequency |")
        lines.append("|-----------|-------|----------|--------|-----------|")

        for t in txns:
            lines.append(
                f"| {t.get('date_next', '?')} "
                f"| {t.get('payee_name', 'Unknown')} "
                f"| {t.get('category_name', 'Uncategorized')} "
                f"| {_format_milliunits(t.get('amount', 0))} "
                f"| {t.get('frequency', '?')} |"
            )

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


def main():
    """Console entry point (used by the `ynab-readonly-mcp` script)."""
    mcp.run()


if __name__ == "__main__":
    main()
