# Data licensing & attribution

The **code** in this repository is MIT-licensed (see `/LICENSE`). The **dataset** in this directory is
**not** MIT — the source texts are derived from third-party content under its own license:

## Wikipedia source texts — CC BY-SA 4.0
The `source_texts` of every `wiki-*` item in `dataset.jsonl` are extracts fetched from the English
Wikipedia REST summary API (`https://en.wikipedia.org/api/rest_v1/page/summary/...`) and snapshotted
verbatim at build time. Each item records its article URL in `provenance.url`. Wikipedia text is
licensed under **Creative Commons Attribution-ShareAlike 4.0** (CC BY-SA 4.0):
<https://creativecommons.org/licenses/by-sa/4.0/>. Attribution is the article URL in each item;
this dataset (the `wiki-*` items' source texts) is therefore made available under **CC BY-SA 4.0** to
satisfy ShareAlike. © Wikipedia contributors.

## `hard-*` items
The `hard-*` items are **hand-curated**: each `source_text` is a short, verifiable factual statement
written for this benchmark (with a Wikipedia reference in `provenance.ref` for checking), paired with a
crafted `claim` that probes lexical-grounding failure modes (semantic contradiction, unit mismatch,
negation, paraphrase, number formatting). Their gold labels are single-annotator judgments against the
rubric in `/docs/RUBRIC.md`. They are marked `provenance.source = "hand-curated (verifiable fact)"`.

## How `gold` is set (no annotator-toward-agreement bias)
For `wiki-*` items, gold is set **by construction**, not subjective labeling:
`SUPPORTED` = claim is a sentence taken verbatim from the source; `UNSUPPORTED` = that sentence with a
number swapped to a false value, or a sentence from a different article (topic mismatch); `UNSOURCED` =
a real claim with an empty source list. See `/tools/build_corpus.py` for the exact construction.
