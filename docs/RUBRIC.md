# Gold-label rubric (FROZEN)

The `gold` label is a **human faithfulness judgment**: *does the claim follow from the provided
source text alone?* — independent of, and never set by, the `grounded` scorer. Four classes:

| Label | Definition |
|---|---|
| **SUPPORTED** | The source text states, or directly entails, the claim. A faithful paraphrase counts. |
| **WEAK** | The source is topically relevant and partially supports the claim, but a material part (a number, an entity, a qualifier) is not established by the source. |
| **UNSUPPORTED** | The source does not support the claim — it is absent, contradicted, or about a different fact. A claim the source actively negates is UNSUPPORTED, even if the words overlap heavily. |
| **UNSOURCED** | No source is provided (empty `source_texts`). The claim may be true in the world, but there is nothing to ground it against. |

## Rules that bind the judgment
1. **Source-only.** Judge against the provided text, not world knowledge. "Pluto is a planet" is
   UNSUPPORTED when the source says it was reclassified as a dwarf planet — regardless of any prior
   belief.
2. **Meaning over words.** Lexical overlap is not support. A claim that shares most words with the
   source but reverses its meaning (negation, wrong entity, wrong unit) is UNSUPPORTED.
3. **Numbers and units are material.** A different number, or the same number with a different unit, is
   not supported.
4. **No curation toward the scorer.** Items are NOT filtered to make `grounded` look good. Cases where
   lexical grounding is expected to fail are included on purpose; the confusion matrix reports the loss.

## How `gold` is actually assigned in this corpus
- **`wiki-*` items — by construction** (deterministic, see `/tools/build_corpus.py`):
  SUPPORTED = claim is a verbatim sentence from the source; UNSUPPORTED = that sentence with a number
  swapped to a false value, or a sentence from a different article; UNSOURCED = empty source.
- **`hard-*` items — single annotator** against this rubric (no inter-annotator agreement is claimed;
  this is stated honestly rather than overclaimed). These are the semantic/paraphrase/unit cases that
  construction can't generate.

## Held-out slice
~20% of items (every 5th by sorted id) are marked `held_out: true` and reported as a separate agreement
number, so a reader can see performance on a slice the corpus design did not tune against.
