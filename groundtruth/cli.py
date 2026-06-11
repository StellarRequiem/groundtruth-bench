"""groundtruth CLI — build (commit) · score · verify.

    groundtruth build   --dataset data/dataset.jsonl   # freeze + commit (single-writer)
    groundtruth score   --out scorecard.json           # deterministic scorecard
    groundtruth verify                                  # recompute root; exit 0 iff it matches
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .commit import write_commitment, parse_commitment
from .score import build_scorecard, canonical_json
from .verify import verify_dataset


def _py() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def _pct(x100: int) -> str:
    """Render an int×100 percentage without ever constructing a float."""
    return f"{x100 // 100}.{x100 % 100:02d}%"


def load_dataset(path: str) -> list[dict]:
    items = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def _cmd_build(args) -> int:
    items = load_dataset(args.dataset)
    root = write_commitment(items, args.commitment, args.ledger)
    print(f"committed {len(items)} item(s) -> root={root}")
    return 0


def _cmd_score(args) -> int:
    items = load_dataset(args.dataset)
    root = parse_commitment(args.commitment).get("root", "")
    card = build_scorecard(items, root, _py())
    Path(args.out).write_text(canonical_json(card) + "\n", encoding="utf-8")
    print(f"scored {card['n_items']} item(s) -> agreement {_pct(card['agreement_pct_x100'])} "
          f"(held-out {_pct(card['agreement_heldout_pct_x100'])}) [py {card['python']}] -> {args.out}")
    return 0


def _cmd_verify(args) -> int:
    items = load_dataset(args.dataset)
    ok, msg = verify_dataset(items, args.commitment)
    print(msg)
    return 0 if ok else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="groundtruth",
        description="Contamination-committed, byte-reproducible citation-faithfulness harness.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="freeze + commit the dataset (the only mutating step)")
    b.add_argument("--dataset", default="data/dataset.jsonl")
    b.add_argument("--commitment", default="data/COMMITMENT.txt")
    b.add_argument("--ledger", default="data/ledger.jsonl")
    b.set_defaults(func=_cmd_build)

    s = sub.add_parser("score", help="score the committed dataset → a byte-stable scorecard")
    s.add_argument("--dataset", default="data/dataset.jsonl")
    s.add_argument("--commitment", default="data/COMMITMENT.txt")
    s.add_argument("--out", default="scorecard.json")
    s.set_defaults(func=_cmd_score)

    v = sub.add_parser("verify", help="recompute the root; exit 0 iff it matches COMMITMENT.txt")
    v.add_argument("--dataset", default="data/dataset.jsonl")
    v.add_argument("--commitment", default="data/COMMITMENT.txt")
    v.set_defaults(func=_cmd_verify)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
