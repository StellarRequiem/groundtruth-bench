"""Verify a committed dataset reproduces its committed root — the skeptic's one command."""
from __future__ import annotations

from .canonical import dataset_root
from .commit import parse_commitment


def verify_dataset(items: list[dict], commitment_path: str) -> tuple[bool, str]:
    """Recompute the root from the items and compare it to COMMITMENT.txt.

    Returns ``(ok, message)``. ``ok`` is True iff the recomputed root equals the committed one —
    i.e. the shipped dataset is exactly what was committed (no post-hoc edits).
    """
    committed = parse_commitment(commitment_path)
    recomputed = dataset_root(items)
    ok = recomputed == committed.get("root")
    if ok:
        return True, f"OK root={recomputed}"
    return False, f"MISMATCH recomputed={recomputed} committed={committed.get('root')}"
