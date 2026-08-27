# Civil Comments additional audit — frozen analysis plan

**Frozen 2026-08-27, before any evaluator score existed.**

This is an **additional real-world case study** for *"What Else Do
Automated Evaluators Measure?"*, designed **after** the PERSUADE
confirmatory study. It is **not** part of the original PERSUADE
preregistration, and it is not described as "preregistered": the public
timestamping mechanism is this repository's pushed freeze commit, not a
registry entry. The accurate description is: *an additional analysis
whose specification was frozen before evaluator scores were analyzed
with respect to the external attributes.*

The machine-readable version of everything below is
`config/civil_comments_additional_audit.json`; the frozen selection,
canonicalization, binning, and discretization rules are implemented and
unit-tested in `scripts/civil_comments_freeze.py` and
`tests/test_civil_comments_freeze.py`. No S-versus-A quantity appears in
this document because none exists yet.

## 1. Scientific question

For each prespecified identity-mention attribute `A`, test

```
H0 :  S  ⫫  A  |  Z
```

where `S` is the Detoxify-original toxicity score discretized by the
A-blind rule of §7, `A` indicates whether the individual comment
contains the corresponding prespecified identity mention (§4), and `Z`
is the exact seven-dimensional vector of human toxicity annotations
(§5).

A rejection means the automated toxicity score retains conditional
statistical dependence on the identity-mention attribute among comments
with identical observed human toxicity annotation vectors. It does
**not** by itself establish discrimination, unfairness, causal use of
identity language, that the human annotations completely capture the
intended construct, or a mechanism explaining the dependence.

## 2. Dataset (frozen)

Civil Comments / Jigsaw Unintended Bias **identity-annotated subset**,
as distributed in the WILDS CivilComments source table
`all_data_with_identities.csv`:

- File: `data/civil_comments/all_data_with_identities.csv` (untracked;
  see `data/civil_comments/README.md` for reconstruction).
- SHA-256:
  `403e638c83a225d738a937ff98b61fd0631e30f710d57928c7766d413526b77f`,
  272,542,670 bytes, **448,000 rows**, comment ids unique.
- Source: `https://huggingface.co/datasets/shlomihod/civil-comments-wilds`
  (file `all_data_with_identities.csv`, revision
  `3fbfeca80bad0f3aec37e72fa07eff222b6e752f`) — the WILDS (Koh et al.
  2021) CivilComments source table; the official WILDS CodaLab bundle
  was unreachable (HTTP 500) at feasibility time.
- License: CC0 1.0. Attribution: Jigsaw / Conversation AI, *Unintended
  Bias in Toxicity Classification*; WILDS benchmark (Koh et al. 2021)
  for the derived table.

No other mirror or version may be silently substituted after this
freeze; every load verifies the SHA-256 before proceeding.

## 3. Primary sample: one comment per article

Article clustering is measurable and nontrivial in this corpus
(`results/civil_comments/feasibility.json`): 94.3% of comments share an
`article_id` with another included comment (median 2, mean 6.44, max
472 comments per article), and identity composition is substantially
overdispersed across articles. The primary analysis therefore gives up
redundant comments rather than relying on comment-level independence
when the clustering variable is actually observed: **exactly one
comment per `article_id`**, with the full census as a prespecified
sensitivity (§9).

Frozen selection rule (deterministic; independent of `A`, `Z`, `S`,
comment text, row order, and article size):

```
selection_key = SHA256("civil-comments-additional-audit-v1:" + comment_id_as_string)
```

Within each `article_id`, retain the comment with the lexicographically
smallest lowercase-hex key. A row with a missing `article_id` would form
its own singleton pseudo-article and be retained (zero such rows exist).

The frozen manifest is `results/civil_comments/primary_manifest.csv`
(69,573 comments; SHA-256
`892245a7899401c1041f3cf7bc17528d80d9812efacefe994dbfd16fec97469e`),
recorded before scoring. Per-identity support counts for the
constructed sample are frozen in
`results/civil_comments/feasibility.json`; e.g. muslim: 1,872 of 69,573
comments have A=1, and informative exact-Z strata retain 59,164
comments (1,480 with A=1). Every identity has ample support.

## 4. Attribute family A (frozen; one confirmatory family)

The externally defined WILDS CivilComments eight-identity family, in
frozen order: `male, female, LGBTQ, christian, muslim, other_religions,
black, white`.

`A = 1` iff the stored column value is `>= 1/2` under **exact rational
comparison** of the stored decimal string; `A = 0` otherwise. Column
mapping: the six single identities use the corresponding identity
annotation fraction columns. The two aggregates use the source table's
own binary columns, whose construction was verified on all 448,000 rows
(and is the unique such construction among subsets of the candidate
columns):

- `LGBTQ` = 1{ max(homosexual_gay_or_lesbian, bisexual,
  other_sexual_orientation, transgender, other_gender) >= 0.5 }
- `other_religions` = 1{ max(jewish, hindu, buddhist, atheist,
  other_religion) >= 0.5 }

No aggregate may be invented or modified after results. There is **no
privileged primary identity**: all eight tests form one confirmatory
family with **Holm correction** across the eight permutation p-values.
This choice is made before evaluator results and is justified because
the family is externally defined and symmetric rather than selected
according to anticipated effect size.

## 5. Human conditioning vector Z (frozen)

Primary `Z` is the exact observed seven-label fraction vector
`(toxicity, severe_toxicity, identity_attack, insult, threat, obscene,
sexual_explicit)`. Two comments share a stratum **iff** all seven
values are exactly equal under the frozen canonical representation:
each stored decimal string is parsed exactly with Python
`fractions.Fraction` (finite decimal → reduced rational; no float
round-trip anywhere), and the stratum key is the tuple of reduced
`numerator/denominator` strings in the frozen column order
(`z_key_exact` in `scripts/civil_comments_freeze.py`). The primary `Z`
is **not** binned.

Pure-A and singleton strata contribute no information and are omitted,
exactly as in the existing conditional-audit implementation
(`Strata.n_usable`).

## 6. Z sensitivity (frozen)

One prespecified sensitivity replaces exact fractions with semantic
bins, addressing the varying-annotator-count lattice implicit in exact
fractions. Overall toxicity: `{0}`, `(0, 1/4]`, `(1/4, 1/2)`,
`[1/2, 3/4)`, `[3/4, 1]`. Each of the six subtypes: `{0}`, `(0, 1/2)`,
`[1/2, 1]`. Boundary membership is exactly as written, under exact
rational comparison (`bin_overall_toxicity`, `bin_subtype`; boundary
behavior unit-tested). No alternative bin definitions may be tested.

## 7. Evaluator and scoring (frozen pins)

**Detoxify-original** — checkpoint `toxic_original-c1212f89.ckpt`,
SHA-256
`c1212f89ac23307ab33932ce29dc446a6e030fb3f384a500890bbe662b7b544a`,
438,021,897 bytes, from
`https://github.com/unitaryai/detoxify/releases/download/v0.1-alpha/toxic_original-c1212f89.ckpt`
(hash-verified local copy under `data/civil_comments/checkpoints/`).
Architecture: `bert-base-uncased` / `BertForSequenceClassification`
with six sigmoid heads. Training corpus: the **Jigsaw 2018 Toxic
Comment Classification Challenge Wikipedia talk-page corpus** — this is
distinct from the Civil Comments / Jigsaw 2019 unintended-bias corpus
used for evaluation. Detoxify-**unbiased** is excluded as primary
evaluator because it was trained on the Civil Comments lineage.

Pinned environment (`.venv-cc`; instantiation from the pinned
checkpoint verified under these versions on 2026-08-27 without scoring
any comment): Python 3.12.11 (CPython, macOS arm64), detoxify 0.5.2
(PyPI), torch 2.13.0, transformers 5.16.1, tokenizers 0.23.1,
sentencepiece 0.2.2, safetensors 0.8.0, huggingface-hub 1.28.0, numpy
2.5.2. Tokenizer: `BertTokenizer` from `bert-base-uncased` at HF
revision `86b5e0934494bd15c9632b12f734a8a67f723594`, cached locally
with per-file SHA-256s recorded in the config.

Frozen deterministic scoring procedure (target head: `toxicity`):

- the package's intended sigmoid scoring path, `Detoxify.predict`
  (tokenizer with `truncation=True`, `padding=True`,
  `model_max_length=512`; `torch.sigmoid` over logits) — never a
  generic Hugging Face pipeline;
- `comment_text` passed verbatim (A-free; no preprocessing; the 2
  empty-text rows are scored as the empty string);
- CPU, float32, `model.eval()`, no grad;
- fixed batch partition: comments ordered by ascending integer comment
  id, consecutive batches of 32 — batch composition is frozen and
  independent of A, Z, text length, and article;
- raw continuous toxicity probabilities stored keyed **only** by
  comment id and hash-frozen **before** any identity attribute is
  joined to evaluator outputs;
- 512-token truncation is normal evaluator behavior (disclosed
  limitation), not an exclusion.

## 8. Score discretization (frozen, A-blind)

The G² statistic requires discrete `S`. Frozen rule, implemented and
unit-tested before any score exists (`discretize_scores`):

1. score the full 448,000-comment census;
2. before joining identity attributes, compute pooled empirical deciles
   of `S`: nine boundaries at `k/10`, `k = 1..9`, via
   `numpy.quantile(method="linear")` (Hyndman–Fan type 7);
3. exact-duplicate boundaries collapse deterministically via
   `np.unique` (the empty category is removed; no replacement
   boundaries are selected);
4. `category(s) = #{boundaries <= s}`
   (`np.searchsorted(boundaries, s, side="right")`), so assignment
   depends only on the numerical value of `S` and identical values are
   never split across categories;
5. no other number of bins may be tested.

Raw scores, frozen boundaries, discrete scores, and hashes of all three
are stored. Category counts by `A` are not inspected until all score
preprocessing is frozen.

## 9. Statistic, randomization, and sensitivities

**Primary statistic:** the same conditional likelihood-ratio G²
statistic as the PERSUADE audit (`offcriterion.statistics.ConditionalG2`
over the full discrete distribution of `S` conditional on `Z`). It is
not changed after seeing results.

**Descriptive companion (frozen, not a test):** the stratum-size-
weighted conditional mean gap of the **raw** Detoxify toxicity
probability (S has a meaningful probability scale, so the decile index
is not used), sign defined as mean(S | A=1) − mean(S | A=0), aggregated
over informative strata with weights `n_z / Σ n_z` — the same
prespecified conditional weighting rule as the existing paper's
`weighted_mean_difference`.

**Randomization:** within each exact-Z stratum, hold `S` and `Z` fixed
and randomly permute `A`, preserving the observed number of `A = 1`
comments per stratum (`offcriterion.permutation`). `B = 999` random
permutations per identity test; Monte Carlo p-value
`p = (1 + #{T_b >= T_obs}) / (B + 1)`; Holm correction across the eight
p-values.

**Frozen seeds** (independently reproducible):
`numpy.random.SeedSequence(entropy=20260827, spawn_key=(slot,
identity_index))` with the frozen identity order of §4 and slots: 1 =
primary (one-per-article, exact Z); 2 = census sensitivity (exact Z);
3 = Z-binned sensitivity (one-per-article); 4 = optional
high-confidence robustness check; 5 = negative-control test; 9 =
negative-control label generation (already consumed).

**Dependence sensitivity:** the full 448,000-comment census with
identical A, Z, evaluator, discretization, statistic, multiplicity
correction, and permutation procedure. It answers whether the
conclusion changes when all comments are used despite within-article
dependence. A stronger census p-value never replaces a weaker primary
result; the article-deduplicated analysis remains primary.

## 10. Negative control (frozen)

Before observing any evaluator dependence, one frozen random
relabeling of each `A` within its exact-Z stratum of the primary sample
was generated with the committed seeds (slot 9), preserving
stratum-level A counts:
`results/civil_comments/negative_control_labels.csv`, SHA-256
`c2215e561b71b41f4018d0a8ad500b30971b61a8d7a5b98ccbbed2341220f73c`.
After scoring, the same conditional test runs on these frozen synthetic
labels. This is a calibration sanity check, **not** part of the
confirmatory family, and the relabeling is never regenerated,
convenient or not.

## 11. Optional high-confidence attribute check

Recorded, not headline analysis: `A = 1` if identity fraction `>= 4/5`,
`A = 0` if identity fraction `= 0`, intermediate fractions excluded
(exact rational comparisons). If run, it is labeled
robustness/sensitivity, never confirmatory evidence, and it enters the
two-page paper only if it materially changes interpretation.

## 12. Missingness and exclusions (frozen)

- Empty `comment_text`: retained, scored as the empty string (2 rows).
- Missing `article_id`: singleton pseudo-article rule of §3 (0 rows).
- Missing identity fractions or human toxicity labels: excluded and
  logged (0 rows in the frozen source).
- Tokenizer/scoring failure: true technical failure is excluded and
  logged per comment id; there is no other post-scoring exclusion.
- Texts exceeding 512 tokens: truncated by the evaluator; normal
  evaluator behavior, disclosed, not an exclusion.
- Evaluator scores are never excluded for being extreme.

## 13. Interpretation limitations (frozen)

1. Human annotation fractions are observed proxies for the intended
   toxicity construct, not ground truth.
2. Exact conditioning cannot guarantee that all construct-relevant
   variation has been measured.
3. Identity mention may correlate with linguistic properties not
   captured by the seven human toxicity labels.
4. A rejection establishes residual conditional dependence, not
   causation, discrimination, or unfairness.
5. The full-census sensitivity contains article-level dependence, which
   is why the one-comment-per-article analysis is primary.
6. Detoxify's 512-token input limit may truncate long comments and is
   disclosed.

## 14. Freeze procedure

Before any scoring: run the test suite; verify the PERSUADE frozen
manifests and outputs are unchanged; review the diff; confirm no
evaluator score has been generated; commit only the Civil Comments
plan/config/feasibility artifacts; record the commit SHA; verify a
clean working tree. Evaluator inference begins only after that freeze
commit exists and is pushed.
