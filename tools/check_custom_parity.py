"""Validate the custom coverage ledger; --require-complete is the release gate."""

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    inventory = json.loads((ROOT / "docs/api_inventory.json").read_text())
    ledger = json.loads((ROOT / "docs/CUSTOM_PARITY.json").read_text())
    expected = set().union(*(set(v["UILayout"]["members"]) for v in inventory.values()))
    assert set(ledger["members"]) == expected, "Inventory and parity ledger differ"
    tree = ast.parse((ROOT / "beyond_ui/layout.py").read_text())
    cls = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Layout"
    )
    implemented = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    allowed = {
        "unimplemented",
        "partial",
        "implemented",
        "execution-tested",
        "reference-matched",
    }
    for name, row in ledger["members"].items():
        assert row["status"] in allowed, (name, row["status"])
        if row["status"] != "unimplemented" and row["kind"] == "method":
            assert name in implemented, name
        if row["status"] == "reference-matched":
            assert row.get("reference") and row.get("comparison_evidence"), name
            assert (ROOT / row["reference"]).is_file(), name
            assert (ROOT / row["comparison_evidence"]).is_file(), name
    remaining = [
        name
        for name, row in ledger["members"].items()
        if row["status"] != "reference-matched"
    ]
    summary = {
        "documented_members": len(expected),
        "partial_members": sum(
            r["status"] == "partial" for r in ledger["members"].values()
        ),
        "reference_matched": len(expected) - len(remaining),
        "remaining": len(remaining),
        "full_custom_parity": not remaining,
    }
    print(json.dumps(summary, indent=2))
    if args.require_complete and remaining:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
