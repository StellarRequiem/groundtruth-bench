# groundtruth-bench — citation faithfulness you can *re-run to the same hash*

> Faithfulness evals are the trust gate for RAG / deep-research agents — but the standard ones
> (RAGAS, ARES) are LLM-as-judge, so re-running them gives a **different number**, and their test
> sets are static, so they **leak into training**. groundtruth-bench fixes both: the dataset is
> **cryptographically committed** (sources snapshotted + hashed, no live fetch) and every score
> **re-runs to a byte-identical hash**.

It is the layer *above* [`grounded`](https://github.com/StellarRequiem/grounded) (the deterministic,
zero-dependency, offline citation scorer): a committed dataset of `(claim, snapshotted-source, gold
label)` items + a harness that runs `grounded` over them and emits a hash-committed scorecard.
Commitment + tamper-evidence reuse [`verity-core`](https://github.com/StellarRequiem/verity-core).

**No LLM judge anywhere in the scoring path** — so it's free, offline, and fits a laptop.

## Why it's different
| | RAGAS / ARES (LLM-judge) | groundtruth-bench |
|---|---|---|
| Re-run → same number? | ✗ (judge variance) | ✓ **byte-identical** |
| Test set committed / leak-proof? | ✗ static, contaminable | ✓ snapshot + hash commitment |
| Cost / offline | $ per run, network | $0, offline |

The win is scoped to **reproducibility · commitment · cost** — *not* a claim that lexical grounding
is more accurate than semantic entailment. The scorecard publishes the gold-agreement either way.

## Quickstart (clean clone → verify in under a minute)
```sh
git clone https://github.com/StellarRequiem/groundtruth-bench && cd groundtruth-bench
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"

.venv/bin/groundtruth build     # freeze + commit the dataset (writes data/COMMITMENT.txt)
.venv/bin/groundtruth verify    # recompute the root; exit 0 iff it matches the commitment
.venv/bin/groundtruth score     # deterministic scorecard -> scorecard.json
```
Run `score` twice on two machines (same pinned Python) → the two `scorecard.json` are **byte-identical**.

## How the commitment works
Each dataset item is canonicalized (all-`str` keys, **NFC-normalized**, float-free) and hashed with
verity-core's canonical-JSON→sha256 `entry_hash` as a leaf; the **root** = `sha256` of the
id-sorted leaf hashes (order-independent). `build` records a `dataset_commit` event in an append-only
verity `AuditChain` **before** scoring (pre-registration), and writes `data/COMMITMENT.txt`. `verify`
recomputes the root and compares — any post-commit edit to a **committed (eval-relevant) field**
(`id` / `schema_version` / `claim` / `source_texts` / `gold` / `held_out`) changes the root. Provenance
metadata is deliberately excluded from the commitment, so edits to `provenance` or any non-committed
field do **not** change the root and are not detected by `verify`.

**Honest limits:** the commitment proves *no edit after commit*, **not** *no cherry-pick before
commit* — so the corpus + gold are pre-registered and a held-out slice is reported separately. Gold
labels are single-annotator against a frozen rubric (no inter-annotator number is claimed). `grounded`
scores **lexical overlap**, so a claim that lexically matches but semantically contradicts its source
(e.g. "the Sun is mainly helium" vs a source saying hydrogen is primary) is a known off-diagonal —
the scorecard's confusion matrix shows it rather than hiding it.

## Determinism pins (why the bytes match)
Python minor version pinned (`.python-version` = 3.12, `requires-python <3.13`); `grounding()` is called
directly (never the network/cache path); the scorecard is serialized canonically (`sort_keys`,
`ensure_ascii`, fixed separators, **no floats** — percentages are integers ×100); line endings LF.
The committed-dataset **leaf/root** hash is genuinely *cross-version* stable (golden exotic-Unicode leaf
identical on 3.12 + 3.14). The **scorecard** is not version-independent: `grounded`'s Unicode-aware `\d`
matches more codepoints under Unicode 16 (3.14) than Unicode 15 (3.12), so the Python pin is
**load-bearing for scorecard byte-identity, not merely defense-in-depth**.

## What it measures (current corpus)
A committed **200-item corpus** — real CC-BY-SA Wikipedia extracts (gold set *by construction*; see
[`docs/RUBRIC.md`](docs/RUBRIC.md) + [`data/NOTICE.md`](data/NOTICE.md)) plus a hand-curated hard set.

`grounded`'s agreement with gold is **88.50% overall — but that number is carried by construction.**
**115 of 200 items (57%) are zero-discrimination** (97 verbatim-substring SUPPORTED + 18 empty-source
UNSOURCED) that any lexical scorer gets for free. On the **85 discriminative items** (number-swap,
topic-mismatch, hard set) agreement is **72.94%** — the honest headline. The held-out **82.50%** is the
same construction mix on a smaller n, **not a generalization slice**. Read `agreement_discriminative_pct_x100`
in the scorecard, not just the overall number.

Per class: SUPPORTED 100/102, UNSOURCED 18/18 — but UNSUPPORTED recall is weaker (gold-UNSUPPORTED scored
SUPPORTED = 5, plus 16 WEAK leakage), and the hard set is **4/12**: semantic contradiction ("the Sun is
mainly helium"), unit mismatch (Everest "8849 feet"), debunked myths (Great Wall from the Moon),
paraphrase recall — exactly where lexical grounding fails, and the confusion matrix **reports** it. A
faithfulness benchmark you can trust says where the scorer is wrong.

## Status
**G4 (Prove-It)** — survived an independent adversarial pass (empirical, 3 hostile lenses): byte-identity,
commitment/tamper-detection, collision-safety, and cross-version leaf stability all held; the headline was
de-gimmed to the honest 72.94% above per the gate. 18 tests, **100% coverage**; cross-OS byte-identity CI.
The live **RAGAS** reproducibility comparison is an opt-in, isolated CI job ([`ragas-compare.yml`](.github/workflows/ragas-compare.yml));
see [`docs/GAPS.md`](docs/GAPS.md) for what's proven vs pending. Part of the
[StellarRequiem](https://github.com/StellarRequiem) verification cluster.
