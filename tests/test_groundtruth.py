"""GroundTruth bench — the properties the whole benchmark rests on:
byte-identical scoring, a commitment that detects tampering, float-free percentages,
NFC-enforced leaves, order-independent root. If any of these breaks, the moat is gone."""
import json
import unicodedata
from pathlib import Path

import pytest

from groundtruth import (
    dataset_root, leaf_hash, assert_nfc, build_scorecard, canonical_json,
    agreement_pct_x100, score_item, write_commitment, verify_dataset,
)
from groundtruth.cli import load_dataset

DATA = Path(__file__).resolve().parent.parent / "data" / "dataset.jsonl"
ITEMS = load_dataset(str(DATA))


# ---- byte-identity (the headline property) ----
def test_scorecard_is_byte_identical_across_runs():
    root = dataset_root(ITEMS)
    a = canonical_json(build_scorecard(ITEMS, root, "3.12"))
    b = canonical_json(build_scorecard(ITEMS, root, "3.12"))
    assert a == b
    assert a.encode("utf-8") == b.encode("utf-8")


def test_scorecard_has_no_floats():
    card = build_scorecard(ITEMS, dataset_root(ITEMS), "3.12")

    def no_float(o):
        if isinstance(o, float):
            raise AssertionError(f"float leaked into the scorecard: {o!r}")
        if isinstance(o, dict):
            [no_float(v) for v in o.values()]
        if isinstance(o, list):
            [no_float(v) for v in o]

    no_float(card)
    assert canonical_json(card) == canonical_json(json.loads(canonical_json(card)))


# ---- commitment / verify (tamper-evidence) ----
def test_verify_roundtrip_and_tamper(tmp_path):
    commitment = tmp_path / "COMMITMENT.txt"
    ledger = tmp_path / "ledger.jsonl"
    root = write_commitment(ITEMS, str(commitment), str(ledger))
    ok, msg = verify_dataset(ITEMS, str(commitment))
    assert ok and root in msg
    # tamper: edit one claim after commit → root must no longer verify
    tampered = [dict(it) for it in ITEMS]
    tampered[0] = {**tampered[0], "claim": tampered[0]["claim"] + " (edited after commit)"}
    ok2, msg2 = verify_dataset(tampered, str(commitment))
    assert not ok2 and "MISMATCH" in msg2


def test_commit_event_recorded(tmp_path):
    commitment = tmp_path / "COMMITMENT.txt"
    ledger = tmp_path / "ledger.jsonl"
    write_commitment(ITEMS, str(commitment), str(ledger))
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert rows[0]["event_type"] == "dataset_commit"
    assert rows[0]["event_data"]["algo"] == "sha256-sorted-leaves"


# ---- integer percentage (no banker's-rounding float) ----
def test_agreement_is_integer_division():
    rows = [{"match": 1}, {"match": 0}, {"match": 0}]  # 1/3
    assert agreement_pct_x100(rows) == 3333  # (10000*1)//3, NOT round(33.333)
    assert isinstance(agreement_pct_x100(rows), int)


def test_agreement_empty_is_zero():
    assert agreement_pct_x100([]) == 0


# ---- NFC enforcement (the sole leaf byte-identity guarantor) ----
def test_assert_nfc_rejects_decomposed():
    base = "\u00e9"  # precomposed e-acute (pure escape, no literal accented byte)
    nfc = unicodedata.normalize("NFC", base)
    nfd = unicodedata.normalize("NFD", base)
    assert nfd != nfc  # the character genuinely decomposes
    with pytest.raises(ValueError):
        assert_nfc(nfd)
    assert assert_nfc(nfc) == nfc


# ---- root: order-independent, duplicate-id-rejecting ----
def test_root_is_order_independent():
    assert dataset_root(ITEMS) == dataset_root(list(reversed(ITEMS)))


def test_root_rejects_duplicate_ids():
    with pytest.raises(ValueError):
        dataset_root([ITEMS[0], dict(ITEMS[0])])


def test_leaf_excludes_provenance():
    # provenance metadata must NOT affect the leaf (stale URLs can't change the commitment)
    a = leaf_hash(ITEMS[0])
    b = leaf_hash({**ITEMS[0], "provenance": {"url": "totally-different"}})
    assert a == b


# ---- the dataset itself: real grounded scoring, honest agreement ----
def test_dataset_agreement_is_real():
    card = build_scorecard(ITEMS, dataset_root(ITEMS), "3.12")
    assert card["n_items"] == 6
    assert card["agreement_pct_x100"] == 8333           # 5/6 — the 'sun' lexical trap disagrees
    assert card["agreement_heldout_pct_x100"] == 10000   # everest, held-out, agrees
    assert card["confusion"]["UNSUPPORTED"]["SUPPORTED"] == 1


def test_score_item_shape():
    r = score_item(ITEMS[0])
    assert set(r) == {"id", "verdict", "nums", "terms", "num_hit", "term_hit", "gold", "match", "held_out"}
    assert r["match"] == 1
