# Honest gaps & security review

The benchmark's value is that you can re-run it and check it. That only means something if the limits
are stated plainly. This is the list of what is **proven**, what is **not**, and what is **out of scope**.

## What is proven (re-runnable evidence)
- **Byte-identical re-run.** Two runs of `groundtruth score` produce a byte-for-byte identical
  `scorecard.json`. Proven in CI **across two different machines (ubuntu + macos)** from a clean clone.
- **Commitment / tamper-evidence.** The dataset commits to a sorted-leaf sha256 root (verity-core
  `entry_hash`). `verify` recomputes it; any post-commit edit to a **committed (eval-relevant) field**
  changes the root → exit 1. Tested. (Provenance metadata is excluded from the commitment by design —
  edits to it are not detected; this is stated, not marketed as full tamper-evidence.)
- **Cross-version determinism — leaf/root only.** A golden exotic-Unicode leaf hash (`3278329c…`, with
  CJK + emoji + Greek + a combining accent) is **identical under CPython 3.12.13 and 3.14.5**, so the
  committed-dataset leaf/root is genuinely cross-version stable. **But the SCORECARD is not**:
  `grounded`'s Unicode-aware `\d` matches more codepoints under Unicode 16 (3.14) than Unicode 15 (3.12),
  so a claim with a U16-only digit can flip its verdict across minors. **The Python pin is therefore
  load-bearing for scorecard byte-identity, not defense-in-depth.** (The 3.14 leaf result is proven by a
  committed golden test verified locally + a dedicated CI golden-leaf job; the package itself pins 3.12.)
- **Honest scoring (de-gimmed).** `grounded` agreement with gold is **88.50% overall, but that is carried
  by 115/200 zero-discrimination gimmes** (97 verbatim-substring SUPPORTED + 18 empty-source UNSOURCED).
  On the **85 discriminative items it is 72.94%** — the honest number, reported as
  `agreement_discriminative_pct_x100` in the scorecard. The hard set is **4/12**; the confusion matrix
  reports `grounded`'s false-SUPPORTs (gold-UNSUPPORTED scored SUPPORTED = 5, + 16 WEAK). Nothing is
  curated to flatter the scorer; the held-out 82.50% is the same construction mix, not a generalization axis.

## What is NOT proven / claimed
- **`grounded` is not claimed to be accurate.** It scores *lexical* overlap, not semantic entailment.
  The "beats RAGAS" claim is scoped strictly to **reproducibility · cost · offline**, never accuracy.
  On semantic contradiction, unit mismatch, negation, and paraphrase recall, `grounded` is wrong — by
  design the benchmark shows this rather than hiding it.
- **The live RAGAS head-to-head number is pending.** RAGAS is third-party code; per our isolation rule
  it is **not installed or run on the host**. The comparison harness (`tools/ragas_compare.py` +
  `.github/workflows/ragas-compare.yml`, `workflow_dispatch`) runs RAGAS **only in the disposable CI
  runner** and needs an API key the repo owner adds as a secret. Until that operator-triggered run, the
  RAGAS-side non-determinism is argued **by inspection**: RAGAS faithfulness is an LLM-as-judge metric,
  so re-running it on identical inputs yields different scores (a published, well-documented property);
  GroundTruth's byte-identity is the contrast. No RAGAS number is fabricated.
- **Gold for `hard-*` items is single-annotator.** No inter-annotator agreement (Cohen's κ) is claimed;
  the `wiki-*` majority is gold-by-construction (deterministic), which carries no annotator bias.
- **Verbatim-SUPPORTED items are "gimmes."** Many `wiki-*` SUPPORTED items are sentences copied verbatim
  from the source — `grounded` should get these. The held-out slice and the hard set exist so the
  headline isn't carried by gimmes — read `agreement_discriminative_pct_x100` (72.94%), the confusion
  matrix, and the hard-set breakdown, not just the 88.50% overall.
- **No calibration claim.** GroundTruth measures agreement, not a probabilistic forecast — there is no
  Brier/calibration number to report (N/A for this artifact).

## Security review
- **No untrusted code execution.** Scoring calls `grounded.grounding(claim, source_texts)` on dataset
  **text** — the text is parsed and compared, never `eval`'d, imported, or executed. Source texts are
  snapshotted at build time; **no network fetch runs in the eval path** (`grounded`'s `fetch.py` is never
  called).
- **Third-party isolation.** The only third-party code that touches this project is RAGAS, and it is
  confined to the `workflow_dispatch` CI job — never the developer host (matches the project rule and the
  mcp-bench precedent).
- **Single-writer commitment.** `build` is the only mutating subcommand; the verity `AuditChain`'s lock
  is in-process, so `build` is documented as a single-writer one-shot.
- **Determinism hazards pinned.** NFC enforced at build (`assert_nfc`); float-free hashed artifacts
  (percentages are integer ×100); LF line endings (`.gitattributes`); `PYTHONHASHSEED=0` in CI.
