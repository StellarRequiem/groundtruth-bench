"""Build the committed corpus from REAL Wikipedia (CC BY-SA) extracts — the provenance of data/dataset.jsonl.

Integrity rules (why this is a credible benchmark, not a fabricated one):
- Source texts are REAL, fetched from Wikipedia's REST summary API and SNAPSHOTTED verbatim into the
  dataset (no LLM-generated "sources"; no live fetch at eval time).
- Gold is set BY CONSTRUCTION, not subjective labeling — so there is no annotator-toward-agreement bias:
    * SUPPORTED  — claim is a sentence taken verbatim from the article's own extract.
    * UNSUPPORTED — claim is that sentence with a number deterministically swapped to a false value
                    (same terms, wrong fact), OR a sentence from a DIFFERENT article (topic mismatch).
    * UNSOURCED  — a real claim paired with an empty source list.
- Everything is NFC-normalized; ids are stable; ~20% is marked held-out (deterministic).
- A separate hand-crafted HARD set (semantic traps / paraphrases) lives in tools/hard_set.jsonl and is
  merged in — these are the cases lexical grounding is expected to get WRONG, included on purpose so the
  confusion matrix shows grounded's real profile rather than a curated-easy score.

Run:  python tools/build_corpus.py   # rewrites data/dataset.jsonl (then `groundtruth build` to commit)
This is a DEV tool; the committed artifact is data/dataset.jsonl, not this script's live output.
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "dataset.jsonl"
HARD = Path(__file__).resolve().parent / "hard_set.jsonl"
UA = {"User-Agent": "groundtruth-bench/0.1 (https://github.com/StellarRequiem/groundtruth-bench; research)"}

# A diverse, stable title list — landmarks, science, geography, history, biology, space.
TITLES = [
    "Eiffel Tower", "Mount Everest", "Great Wall of China", "Pacific Ocean", "Amazon River",
    "Sahara", "Mount Kilimanjaro", "Nile", "Mariana Trench", "Lake Baikal",
    "Photosynthesis", "Mitochondrion", "DNA", "Periodic table", "Speed of light",
    "Gravity", "Black hole", "Solar System", "Jupiter", "Saturn",
    "Roman Empire", "French Revolution", "Industrial Revolution", "Renaissance", "World War II",
    "Albert Einstein", "Isaac Newton", "Marie Curie", "Charles Darwin", "Leonardo da Vinci",
    "Python (programming language)", "Internet", "Transistor", "Vaccine", "Penicillin",
    "Mount Fuji", "Niagara Falls", "Grand Canyon", "Great Barrier Reef", "Antarctica",
    "Honey bee", "Blue whale", "Giant panda", "Octopus", "Tardigrade",
    "Volcano", "Earthquake", "Glacier", "Tsunami", "Hurricane",
]


def fetch_extract(title: str) -> dict | None:
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title)
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))
        return {"extract": nfc(d["extract"]), "url": d["content_urls"]["desktop"]["page"]}
    except Exception as e:  # noqa: BLE001 — a flaky fetch just drops that article
        print(f"  skip {title}: {e}")
        return None


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def sentences(text: str) -> list[str]:
    # simple, deterministic sentence split on '. ' boundaries; good enough for lead extracts
    parts = re.split(r"(?<=[.])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 20]


_NUM = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")


def poison_number(sentence: str) -> str | None:
    """Swap the first number for a deterministically different one (same terms, wrong fact)."""
    m = _NUM.search(sentence)
    if not m:
        return None
    orig = m.group(0)
    digits = orig.replace(",", "")
    try:
        val = int(digits) if "." not in digits else float(digits)
    except ValueError:
        return None
    new = str(int(val) + 9999) if isinstance(val, int) else f"{val + 9999.0:g}"
    if new in sentence:  # ensure the poisoned value is genuinely absent
        new = new + "1"
    return sentence[:m.start()] + new + sentence[m.end():]


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def title_tokens(title: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[A-Za-z]{4,}", title) if w.lower() not in {"the", "and", "for"}]


def pick_unrelated(fetched: list, i: int) -> dict | None:
    """An article whose extract does NOT mention this article's title tokens — so the topic-mismatch
    claim is genuinely unsupported by it (avoids the Jupiter-mentioned-in-Saturn accidental-support bug)."""
    toks = title_tokens(fetched[i][0])
    for k in range(1, len(fetched)):
        cand = fetched[(i + k) % len(fetched)][1]
        low = cand["extract"].lower()
        if not any(t in low for t in toks):
            return cand
    return None


def build() -> list[dict]:
    items: list[dict] = []
    fetched: list[tuple[str, dict]] = []
    for t in TITLES:
        d = fetch_extract(t)
        if d and len(sentences(d["extract"])) >= 1:
            fetched.append((t, d))
    print(f"fetched {len(fetched)}/{len(TITLES)} articles")

    for i, (title, d) in enumerate(fetched):
        s = slug(title)
        sents = sentences(d["extract"])
        prov = {"source": "Wikipedia", "url": d["url"], "license": "CC BY-SA 4.0", "retrieved": "2026-06-11"}

        # SUPPORTED — verbatim first sentence
        items.append({"id": f"wiki-{s}-sup1", "claim": sents[0], "source_texts": [d["extract"]],
                      "gold": "SUPPORTED", "provenance": prov})
        # SUPPORTED — verbatim second sentence (more variety) when present
        if len(sents) >= 2:
            items.append({"id": f"wiki-{s}-sup2", "claim": sents[1], "source_texts": [d["extract"]],
                          "gold": "SUPPORTED", "provenance": prov})
        # UNSUPPORTED — number swapped (same terms, wrong fact) if the lead has a number
        poisoned = next((p for p in (poison_number(x) for x in sents[:3]) if p), None)
        if poisoned:
            items.append({"id": f"wiki-{s}-num", "claim": poisoned, "source_texts": [d["extract"]],
                          "gold": "UNSUPPORTED", "provenance": {**prov, "note": "number swapped to a false value"}})
        # UNSUPPORTED — topic mismatch: this article's claim vs an UNRELATED article's source
        # (one that does not mention this article's subject, so it genuinely fails to support).
        other = pick_unrelated(fetched, i)
        if other:
            items.append({"id": f"wiki-{s}-mism", "claim": sents[0], "source_texts": [other["extract"]],
                          "gold": "UNSUPPORTED",
                          "provenance": {**prov, "note": f"topic mismatch vs {other['url']}"}})
        # UNSOURCED — real claim, no source (every 3rd article, to keep the class present but minority)
        if i % 3 == 0:
            items.append({"id": f"wiki-{s}-uns", "claim": sents[0], "source_texts": [],
                          "gold": "UNSOURCED", "provenance": {**prov, "note": "no source provided"}})

    # merge the hand-crafted hard set (semantic traps / paraphrases)
    if HARD.is_file():
        hard = [json.loads(line) for line in HARD.read_text(encoding="utf-8").splitlines() if line.strip()]
        for h in hard:
            h["claim"] = nfc(h["claim"])
            h["source_texts"] = [nfc(x) for x in h["source_texts"]]
        items += hard
        print(f"merged {len(hard)} hand-crafted hard items")

    # finalize: schema_version, NFC, deterministic held-out (~20%, every 5th by sorted id)
    for it in items:
        it["schema_version"] = 1
        it["claim"] = nfc(it["claim"])
        it["source_texts"] = [nfc(x) for x in it["source_texts"]]
    items.sort(key=lambda x: x["id"])
    for n, it in enumerate(items):
        it["held_out"] = (n % 5 == 0)
    return items


def main() -> None:
    items = build()
    with OUT.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    by_gold: dict[str, int] = {}
    for it in items:
        by_gold[it["gold"]] = by_gold.get(it["gold"], 0) + 1
    print(f"wrote {len(items)} items -> {OUT}")
    print("by gold:", by_gold, "| held-out:", sum(it["held_out"] for it in items))


if __name__ == "__main__":
    main()
