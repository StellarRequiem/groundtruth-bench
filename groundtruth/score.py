"""Score the committed dataset with ``grounded`` (deterministic) → a byte-stable scorecard.

The scorecard is the artifact two CI runners must produce byte-for-byte identically. It is
therefore float-free (counts are ints; the agreement percentage is an int ×100 computed by
integer division — never ``round()`` of a float) and serialized canonically.
"""
from __future__ import annotations

import json

from grounded import grounding

from .canonical import SCHEMA_VERSION, VERDICTS


def _is_gimme(item: dict) -> bool:
    """A zero-discrimination item — one any lexical scorer gets for free, so it tests nothing:
    a SUPPORTED claim copied verbatim (substring) from its source, or an empty-source UNSOURCED."""
    if item["gold"] == "UNSOURCED" and not item["source_texts"]:
        return True
    if item["gold"] == "SUPPORTED" and any(item["claim"] in s for s in item["source_texts"]):
        return True
    return False


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
        "gimme": int(_is_gimme(item)),
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
    """Score every item → the committed scorecard dict.

    Rows are sorted by id so byte-identity is a consequence of the (order-independent) commitment,
    not of incidental dataset-file line order. The headline ``agreement`` is reported ALONGSIDE the
    de-gimmed ``agreement_discriminative`` — the honest number on items a lexical scorer can't get for
    free (no verbatim-substring SUPPORTED, no empty-source UNSOURCED)."""
    rows = sorted((score_item(it) for it in items), key=lambda r: r["id"])
    disc = [r for r in rows if not r["gimme"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "commitment_root": commitment_root,
        "python": python,
        "n_items": len(rows),
        "n_gimme": sum(r["gimme"] for r in rows),
        "n_discriminative": len(disc),
        "agreement_pct_x100": agreement_pct_x100(rows),
        "agreement_discriminative_pct_x100": agreement_pct_x100(disc),
        "agreement_heldout_pct_x100": agreement_pct_x100([r for r in rows if r["held_out"]]),
        "confusion": confusion(rows),
        "rows": rows,
    }


def canonical_json(obj) -> str:
    """The byte-identity serializer: sorted keys, ASCII-escaped, fixed separators, no floats."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
