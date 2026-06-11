"""Build-time commitment: compute the dataset root and anchor it in the verity audit chain.

Pre-registration discipline: ``build`` is the ONLY mutating step. It commits the corpus +
frozen gold labels and appends a ``dataset_commit`` event to an append-only chain BEFORE any
scoring runs. The root is a pure function of the items (no timestamps/floats), so it re-derives
identically anywhere; the chain event is the tamper-evident provenance that the commit happened.
"""
from __future__ import annotations

from pathlib import Path

from verity.audit import AuditChain

from .canonical import dataset_root, SCHEMA_VERSION

ALGO = "sha256-sorted-leaves"


def write_commitment(items: list[dict], commitment_path: str, ledger_path: str) -> str:
    """Compute the root, record a ``dataset_commit`` chain event, write COMMITMENT.txt. Returns the root."""
    root = dataset_root(items)
    AuditChain(ledger_path).append(
        "dataset_commit",
        {"schema_version": SCHEMA_VERSION, "n_items": len(items), "root": root, "algo": ALGO},
        actor="groundtruth",
    )
    Path(commitment_path).write_text(
        f"algo={ALGO}\nschema_version={SCHEMA_VERSION}\nn_items={len(items)}\nroot={root}\n",
        encoding="utf-8",
    )
    return root


def parse_commitment(path: str) -> dict:
    """Parse the ``key=value`` COMMITMENT.txt into a dict."""
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out
