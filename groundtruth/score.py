"""Score the committed dataset with ``grounded`` (deterministic) → a byte-stable scorecard.

The scorecard is the artifact two CI runners must produce byte-for-byte identically. It is
therefore float-free (counts are ints; the agreement percentage is an int ×100 computed by
integer division — never ``round()`` of a float) and serialized canonically.
"""
from __future__ import annotations

import json

from grounded import grounding

from .canonical import SCHEMA_VERSION

VERDICTS = ("SUPPORTED", "WEAK", "UNSUPPORTED", "UNSOURCED")


def score_item(item: dict) -> dict:
    """Run ``grounded`` on one item. Calls ``grounding()`` directly — never the network path."""
    g = grounding(item["claim"], item["source_texts"])
    return {
        "id": item["id"],
        "verdict": g["verdict"],
        "nums": g["nums"], "terms": g["terms"],
        "num_hit": g["num_hit"], "term_hit": g["term_hit"],
        "gold": item["gold"],
        "match": int(g["verdict"] == item["gold"]),
        "held_out": bool(item["held_out"]),
    }


def agreement_pct_x100(rows: list[dict]) -> int:
    """Integer percentage ×100: ``(10000*matches)//total``. NEVER ``round()`` a float."""
    total = len(rows)
    if total == 0:
        return 0
    matches = sum(r["match"] for r in rows)
    return (10000 * matches) // total


def confusion(rows: list[dict]) -> dict:
    """4×4 gold×verdict confusion matrix as nested ints."""
    m = {g: {v: 0 for v in VERDICTS} for g in VERDICTS}
    for r in rows:
        if r["gold"] in m and r["verdict"] in m[r["gold"]]:
            m[r["gold"]][r["verdict"]] += 1
    return m


def build_scorecard(items: list[dict], commitment_root: str, python: str) -> dict:
    """Score every item (dataset order preserved as a list) → the committed scorecard dict."""
    rows = [score_item(it) for it in items]
    return {
        "schema_version": SCHEMA_VERSION,
        "commitment_root": commitment_root,
        "python": python,
        "n_items": len(rows),
        "agreement_pct_x100": agreement_pct_x100(rows),
        "agreement_heldout_pct_x100": agreement_pct_x100([r for r in rows if r["held_out"]]),
        "confusion": confusion(rows),
        "rows": rows,
    }


def canonical_json(obj) -> str:
    """The byte-identity serializer: sorted keys, ASCII-escaped, fixed separators, no floats."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
