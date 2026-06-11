"""LLM-as-judge reproducibility comparison — the G4 head-to-head baseline.

CLAIM under test: an LLM-as-judge faithfulness scorer (the design RAGAS implements) is NOT reproducible
— re-running it on identical inputs yields different scores — whereas GroundTruth re-runs to a
byte-identical scorecard.

We score faithfulness with a minimal judge called DIRECTLY via the Anthropic SDK rather than through
RAGAS, because RAGAS's transitive langchain dependencies do not pin onto a coherent modern stack (its
`ragas.llms.base` hard-imports `langchain_community.chat_models.vertexai`, removed in the langchain 0.3
split — itself a point about reproducibility). The mechanism under test is identical: an LLM judges
whether a claim is supported by its source and returns a 0–1 score. We run it twice at temperature 0
(the most-reproducible setting) AND twice at 0.7 (a realistic setting), and report how many item scores
change on a re-run, beside GroundTruth's byte-identical re-run.

⚠️ THIRD-PARTY ISOLATION / METERED: calls a metered LLM API. Runs ONLY in the disposable CI runner
(.github/workflows/judge-compare.yml, workflow_dispatch), never a developer host; needs ANTHROPIC_API_KEY
as a CI secret. Carries NO weight in the byte-identity/commitment claims — those stand on their own.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "dataset.jsonl"
SAMPLE = int(os.environ.get("JUDGE_SAMPLE", os.environ.get("RAGAS_SAMPLE", "12")))
MODEL = os.environ.get("JUDGE_MODEL", "claude-haiku-4-5")
_NUM = re.compile(r"[01](?:\.\d+)?")


def load_sample() -> list[dict]:
    items = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    items = [it for it in items if it.get("source_texts")]  # need a context to judge faithfulness
    return items[:SAMPLE]


def judge_once(items: list[dict], temperature: float) -> list[float]:
    """Score each item's faithfulness once via a direct Anthropic-SDK judge → per-item 0–1."""
    from anthropic import Anthropic  # noqa: PLC0415 (CI-only import)

    client = Anthropic()
    scores: list[float] = []
    for it in items:
        src = "\n".join(it["source_texts"])
        prompt = (f"Source:\n{src}\n\nClaim: {it['claim']}\n\n"
                  "Is the claim fully supported by the source above? Reply with ONLY a faithfulness "
                  "score from 0.00 to 1.00 (1.00 = fully supported, 0.00 = unsupported). Number only.")
        msg = client.messages.create(model=MODEL, max_tokens=10, temperature=temperature,
                                     messages=[{"role": "user", "content": prompt}])
        txt = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        m = _NUM.search(txt)
        scores.append(float(m.group(0)) if m else -1.0)
    return scores


def groundtruth_repro_check(items: list[dict]) -> bool:
    from groundtruth import build_scorecard, dataset_root, canonical_json
    root = dataset_root(items)
    return canonical_json(build_scorecard(items, root, "3.12")) == canonical_json(build_scorecard(items, root, "3.12"))


def _delta(a: list[float], b: list[float]) -> dict:
    deltas = [abs(x - y) for x, y in zip(a, b)]
    changed = sum(1 for d in deltas if d > 1e-9)
    return {"run1_mean": round(statistics.fmean(a), 4), "run2_mean": round(statistics.fmean(b), 4),
            "items_changed": changed, "max_item_delta": round(max(deltas), 4) if deltas else 0.0}


def main() -> int:
    items = load_sample()
    if "--groundtruth-only" in sys.argv:  # host-safe sanity path (no API)
        ok = groundtruth_repro_check(items)
        print(f"GroundTruth re-run byte-identical on {len(items)} items: {ok}")
        return 0 if ok else 1

    report = {"n": len(items), "judge_model": MODEL,
              "temp_0": _delta(judge_once(items, 0.0), judge_once(items, 0.0)),
              "temp_0_7": _delta(judge_once(items, 0.7), judge_once(items, 0.7)),
              "groundtruth_rerun_byte_identical": groundtruth_repro_check(items)}
    (ROOT / "judge_compare.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    t0, t7 = report["temp_0"], report["temp_0_7"]
    print(f"\nVERDICT: the LLM judge ({MODEL}) changed {t0['items_changed']}/{len(items)} item scores on a "
          f"re-run at temp=0 and {t7['items_changed']}/{len(items)} at temp=0.7; GroundTruth re-run "
          f"byte-identical: {report['groundtruth_rerun_byte_identical']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
