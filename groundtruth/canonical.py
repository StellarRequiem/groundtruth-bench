"""Canonicalization + leaf/root hashing for the committed dataset.

The whole project rests on these byte-identity rules:
- Every committed string is NFC-normalized at build time. ``verity-core``'s
  ``entry_hash`` serializes with ``ensure_ascii=False`` (raw UTF-8), so NFC is the
  *sole* guarantor that the same logical text hashes to the same bytes everywhere.
- No floats in any hashed artifact — counts are ``int``, percentages are ``int`` ×100.
- The dataset root folds id-SORTED leaf hashes, so ingest order never affects the root.
"""
from __future__ import annotations

import hashlib
import unicodedata

from verity.audit import entry_hash, GENESIS

SCHEMA_VERSION = 1


def nfc(s: str) -> str:
    """NFC-normalize a string (idempotent)."""
    return unicodedata.normalize("NFC", s)


def assert_nfc(s: str) -> str:
    """Build-time guard: a committed string must already be NFC. Raises if not."""
    if unicodedata.normalize("NFC", s) != s:
        raise ValueError(f"string is not NFC-normalized: {s!r}")
    return s


def canonical_item(item: dict) -> dict:
    """The float-free, NFC, all-str-keyed view of a dataset item that gets hashed.

    Only eval-relevant fields are committed — ``provenance`` metadata (url/date) is
    deliberately excluded so a URL going stale never changes the commitment.
    """
    return {
        "id": assert_nfc(item["id"]),
        "schema_version": SCHEMA_VERSION,
        "claim": assert_nfc(item["claim"]),
        "source_texts": [assert_nfc(s) for s in item["source_texts"]],
        "gold": item["gold"],
        "held_out": bool(item["held_out"]),
    }


def leaf_hash(item: dict) -> str:
    """One dataset item → its leaf hash, reusing verity-core's canonical-JSON→sha256 primitive."""
    return entry_hash(seq=0, prev_hash=GENESIS, actor="groundtruth",
                      event_type="dataset_item", event_data=canonical_item(item))


def dataset_root(items: list[dict]) -> str:
    """Fold id-sorted leaf hashes to one verifiable root. Order-independent; duplicate ids raise."""
    pairs = [(assert_nfc(it["id"]), leaf_hash(it)) for it in items]
    ids = [i for i, _ in pairs]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate item ids in dataset — ids must be unique")
    pairs.sort(key=lambda p: p[0])  # sort by stable id, not ingest order
    return hashlib.sha256("\n".join(h for _, h in pairs).encode("utf-8")).hexdigest()
