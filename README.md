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
recomputes the root and compares — any post-commit edit to the dataset changes the root.

**Honest limits:** the commitment proves *no edit after commit*, **not** *no cherry-pick before
commit* — so the corpus + gold are pre-registered and a held-out slice is reported separately. Gold
labels are single-annotator against a frozen rubric (no inter-annotator number is claimed). `grounded`
scores **lexical overlap**, so a claim that lexically matches but semantically contradicts its source
(e.g. "the Sun is mainly helium" vs a source saying hydrogen is primary) is a known off-diagonal —
the scorecard's confusion matrix shows it rather than hiding it.

## Determinism pins (why the bytes match)
Python minor version pinned (`.python-version` = 3.12); `grounding()` is called directly (never the
network/cache path); the scorecard is serialized canonically (`sort_keys`, `ensure_ascii`, fixed
separators, **no floats** — percentages are integers ×100); line endings pinned to LF.

## Status
**G2 walking skeleton** — `build`/`score`/`verify` work end-to-end on a 6-item real slice (5/6
agreement; the held-out item agrees). The full ~200–300-item committed corpus + the two-runner
byte-identity CI + the live RAGAS comparison land in G3/G4. Part of the
[StellarRequiem](https://github.com/StellarRequiem) verification cluster.
