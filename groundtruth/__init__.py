"""groundtruth-bench — a contamination-committed, byte-reproducible citation-faithfulness harness.

Scoring is done by ``grounded`` (deterministic, zero-dep, offline); the dataset is committed to a
verifiable root via ``verity-core``'s canonical-JSON→sha256 primitive. Every score re-runs to a
byte-identical scorecard — the property no LLM-judge faithfulness benchmark can offer.
"""
from .canonical import dataset_root, leaf_hash, canonical_item, nfc, assert_nfc, SCHEMA_VERSION
from .commit import write_commitment, parse_commitment
from .score import build_scorecard, canonical_json, score_item, agreement_pct_x100, confusion, VERDICTS
from .verify import verify_dataset

__version__ = "0.1.0"
__all__ = ["dataset_root", "leaf_hash", "canonical_item", "nfc", "assert_nfc", "SCHEMA_VERSION",
           "write_commitment", "parse_commitment", "build_scorecard", "canonical_json",
           "score_item", "agreement_pct_x100", "confusion", "VERDICTS", "verify_dataset"]
