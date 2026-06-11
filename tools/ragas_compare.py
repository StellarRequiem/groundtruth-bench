"""RAGAS reproducibility comparison — the G4 head-to-head baseline.

CLAIM under test: an LLM-as-judge faithfulness metric (RAGAS) is NON-DETERMINISTIC — re-running it on
identical inputs yields different scores — whereas GroundTruth re-runs to a byte-identical scorecard.

This script runs RAGAS faithfulness TWICE on the same sample and reports the per-item + mean delta,
alongside GroundTruth's byte-identical re-run.

⚠️ THIRD-PARTY / ISOLATION: this installs and runs RAGAS (third-party code) and calls a metered LLM API.
Per this project's rule it must run ONLY in the disposable CI runner (.github/workflows/ragas-compare.yml,
workflow_dispatch), NEVER on a developer host. It needs an API key provided as a CI secret. It is
deliberately NOT part of the deterministic eval path or the default CI, and carries NO weight in the
byte-identity/commitment claims — those stand on their own.

Tested-on-host: NO (by design — isolation). Validate via the operator-dispatched CI run. The RAGAS API
is version-sensitive; pin `ragas` in the workflow and adjust here if the import surface has moved.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "dataset.jsonl"
SAMPLE = int(os.environ.get("RAGAS_SAMPLE", "12"))


def load_sample() -> list[dict]:
    items = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    # faithfulness needs a non-empty context; drop UNSOURCED (empty source) items
    items = [it for it in items if it.get("source_texts")]
    return items[:SAMPLE]


def run_ragas_once(items: list[dict]) -> list[float]:
    """Score faithfulness for each item once. Returns per-item faithfulness in [0,1]."""
    from ragas import EvaluationDataset, evaluate          # noqa: PLC0415 (CI-only import)
    from ragas.metrics import Faithfulness
    from ragas.llms import LangchainLLMWrapper
    from langchain_anthropic import ChatAnthropic

    llm = LangchainLLMWrapper(ChatAnthropic(model=os.environ.get("RAGAS_MODEL", "claude-haiku-4-5"),
                                            temperature=0))
    rows = [{"user_input": f"State a fact: {it['claim'][:60]}",
             "response": it["claim"],
             "retrieved_contexts": it["source_texts"]} for it in items]
    ds = EvaluationDataset.from_list(rows)
    res = evaluate(ds, metrics=[Faithfulness(llm=llm)])
    df = res.to_pandas()
    # the faithfulness column name has varied across ragas versions — find it defensively
    cols = [c for c in df.columns if "faith" in c.lower()]
    col = cols[0] if cols else "faithfulness"
    return [float(x) for x in df[col].tolist()]


def groundtruth_repro_check(items: list[dict]) -> bool:
    """GroundTruth's own re-run: identical by construction (the contrast)."""
    from groundtruth import build_scorecard, dataset_root, canonical_json
    root = dataset_root(items)
    a = canonical_json(build_scorecard(items, root, "3.12"))
    b = canonical_json(build_scorecard(items, root, "3.12"))
    return a == b


def main() -> int:
    items = load_sample()
    if "--groundtruth-only" in sys.argv:  # a host-safe sanity path (no RAGAS, no API)
        ok = groundtruth_repro_check(items)
        print(f"GroundTruth re-run byte-identical on {len(items)} items: {ok}")
        return 0 if ok else 1

    run1 = run_ragas_once(items)
    run2 = run_ragas_once(items)
    deltas = [abs(a - b) for a, b in zip(run1, run2)]
    nondet = sum(1 for d in deltas if d > 1e-9)
    report = {
        "n": len(items),
        "ragas_run1_mean": statistics.fmean(run1),
        "ragas_run2_mean": statistics.fmean(run2),
        "ragas_mean_delta": abs(statistics.fmean(run1) - statistics.fmean(run2)),
        "ragas_items_that_changed": nondet,
        "ragas_max_item_delta": max(deltas) if deltas else 0.0,
        "groundtruth_rerun_byte_identical": groundtruth_repro_check(items),
    }
    (ROOT / "ragas_compare.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nVERDICT: RAGAS changed {nondet}/{len(items)} item scores on a re-run "
          f"(mean delta {report['ragas_mean_delta']:.4f}); GroundTruth re-run byte-identical: "
          f"{report['groundtruth_rerun_byte_identical']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
