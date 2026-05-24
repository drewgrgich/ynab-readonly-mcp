"""
Tests that enforce the core promise of this project: it can read your YNAB
budget, but it is structurally incapable of changing it.

The first test is the important one — it turns the marketing claim ("read-only
by design") into an invariant checked on every commit. If anyone ever adds a
write call, the build fails.
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "ynab_mcp.py"
SOURCE = SRC.read_text()


def test_no_write_http_verbs():
    """No non-GET HTTP may appear anywhere in the source."""
    forbidden = [
        "client.post", "client.put", "client.delete", "client.patch",
        ".request(", '"POST"', '"PUT"', '"DELETE"', '"PATCH"',
    ]
    hits = [f for f in forbidden if f in SOURCE]
    assert not hits, f"Found non-read HTTP usage (this server must stay read-only): {hits}"


def test_at_least_one_get():
    assert "client.get(" in SOURCE, "expected the server to make GET requests"


def test_all_tools_declared_read_only():
    """Every registered tool must advertise readOnlyHint=True, and none False."""
    tool_count = SOURCE.count("@mcp.tool(")
    readonly_true = len(re.findall(r'"readOnlyHint":\s*True', SOURCE))
    readonly_false = len(re.findall(r'"readOnlyHint":\s*False', SOURCE))
    assert tool_count > 0, "expected at least one tool"
    assert readonly_false == 0, "a tool is marked readOnlyHint=False"
    assert readonly_true == tool_count, (
        f"{tool_count} tools defined but {readonly_true} marked read-only"
    )


def _load_module():
    spec = importlib.util.spec_from_file_location("ynab_mcp", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_format_milliunits():
    """YNAB stores money in milliunits; the server must render dollars correctly."""
    mod = _load_module()
    assert mod._format_milliunits(1_234_560) == "$1,234.56"
    assert mod._format_milliunits(0) == "$0.00"
    assert mod._format_milliunits(-5_000) == "$-5.00"


def test_debt_fields_for_loans():
    """Loan accounts expose a rate (1000x-scaled) and a milliunit minimum payment;
    accounts without debt fields (cards, cash) produce nothing."""
    mod = _load_module()
    loan = {
        "debt_interest_rates": {"2025-01-01": 5000, "2026-01-01": 4960},
        "debt_minimum_payments": {"2026-01-01": 256_700},
    }
    out = mod._format_debt_fields(loan)
    assert "4.96%" in out          # uses the most recent date, 1000x scale
    assert "$256.70" in out
    # no debt fields -> empty string (the credit-card / cash case)
    assert mod._format_debt_fields({"debt_interest_rates": {}, "debt_minimum_payments": None}) == ""
    assert mod._format_debt_fields({}) == ""
