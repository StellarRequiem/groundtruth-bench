"""Exercise the CLI end-to-end via main() so the build/score/verify handlers are covered,
and confirm the gate's exit codes (0 PASS · 1 on a tampered dataset)."""
import json
from pathlib import Path

from groundtruth.cli import main

DATA = Path(__file__).resolve().parent.parent / "data" / "dataset.jsonl"


def test_cli_build_verify_score(tmp_path):
    commitment = tmp_path / "COMMITMENT.txt"
    ledger = tmp_path / "ledger.jsonl"
    out = tmp_path / "scorecard.json"
    assert main(["build", "--dataset", str(DATA), "--commitment", str(commitment), "--ledger", str(ledger)]) == 0
    assert commitment.exists() and ledger.exists()
    assert main(["verify", "--dataset", str(DATA), "--commitment", str(commitment)]) == 0
    assert main(["score", "--dataset", str(DATA), "--commitment", str(commitment), "--out", str(out)]) == 0
    card = json.loads(out.read_text())
    assert card["n_items"] == 200
    assert card["agreement_pct_x100"] == 8700
    # the scorecard file ends with a single trailing newline and is canonical (no spaces after separators)
    text = out.read_text()
    assert text.endswith("}\n") and ", " not in text and ": " not in text


def test_cli_verify_exit_1_on_tamper(tmp_path):
    commitment = tmp_path / "COMMITMENT.txt"
    ledger = tmp_path / "ledger.jsonl"
    main(["build", "--dataset", str(DATA), "--commitment", str(commitment), "--ledger", str(ledger)])
    bad = tmp_path / "bad.jsonl"
    lines = DATA.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace('"gold": "SUPPORTED"', '"gold": "UNSUPPORTED"', 1)  # flip a committed label
    bad.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert main(["verify", "--dataset", str(bad), "--commitment", str(commitment)]) == 1


def test_cli_score_twice_is_byte_identical(tmp_path):
    commitment = tmp_path / "COMMITMENT.txt"
    ledger = tmp_path / "ledger.jsonl"
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    main(["build", "--dataset", str(DATA), "--commitment", str(commitment), "--ledger", str(ledger)])
    main(["score", "--dataset", str(DATA), "--commitment", str(commitment), "--out", str(a)])
    main(["score", "--dataset", str(DATA), "--commitment", str(commitment), "--out", str(b)])
    assert a.read_bytes() == b.read_bytes()
