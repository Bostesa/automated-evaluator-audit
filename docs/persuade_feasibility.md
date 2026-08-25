# PERSUADE 2.0 feasibility analysis

Date: 2026-08-25. Stage: pre-registration planning. **No LLM scoring has been
performed.** All power numbers below are planning calculations under stated
synthetic assumptions, not claims about the unknown real effect.

## Proposed primary null

```
H0 :  S  _||_  A  |  Y, P
```

- `S` — LLM judge holistic score (not yet collected)
- `A` — writer English-language-learner (ELL) status
- `Y` — human holistic score (1–6)
- `P` — writing prompt

This is an **observational conditional-dependence null**. `Y` is an observed
human rating and a proxy for the intended writing construct, not ground truth.
A rejection must not be described as proof that the judge causally used
demographic information: under imperfect construct measurement it cannot be
distinguished from residual construct signal that the human score does not
capture (assumption A2 in `docs/assumptions.md`).

## Data provenance

| item | value |
|---|---|
| Corpus | PERSUADE 2.0 (Crossley, Baffour, Tian, Franklin, Benner & Boser, 2024, *Assessing Writing* 61) |
| Canonical source | https://github.com/scrosseye/persuade_corpus_2.0 → Google Drive links in its README |
| Files | `persuade_train.csv` (617 MB), `persuade_corpus_2.0_test.csv` (382 MB, from password-protected `persuade_test.zip`; password published in the canonical README) |
| SHA-256 | train `f61319ed…c467e23`, test zip `51c907f9…7facb2` (full digests in `data/persuade/README.md`) |
| Downloaded | 2026-08-25 |
| License | CC BY-NC-SA 4.0 (non-commercial research use) |

Both CSVs are **discourse-element-level** (285,383 rows). They were
deduplicated to one row per `essay_id_comp` (metadata verified constant within
essay; 0 conflicts) → `data/persuade/persuade_essay_level.csv`. The numeric
`essay_id` column is Excel-mangled scientific notation (`5.40889E+12`) and is
**not** unique (25,994 distinct values for 25,996 essays); `essay_id_comp` is
the reliable key.

## Dataset audit

- **Total essays: 25,996**; unique `essay_id_comp`: 25,996; duplicated IDs: 0.
- **Duplicate essays:** 0 groups of identical `full_text` (SHA-1).
- **Repeated writers:** the corpus contains **no writer identifier** of any
  kind, so repeated writers cannot be detected or ruled out from the data.
  This bears on assumption A1 (independence between units); it must be argued
  from corpus documentation, not tested here.
- **Prompts: 15**, across 5 providers (Indiana, Virginia, NCES, Florida,
  Georgia Virtual) and 2 tasks (independent / source-based).
- **Human holistic score** (`holistic_essay_score`, 1–6): 0% missing.
  Distribution: 1: 1,028 · 2: 5,699 · 3: 8,368 · 4: 6,731 · 5: 3,297 · 6: 873.
- **ELL status** (`ell_status`), exact raw encodings, nothing collapsed:

  | raw value | n | share |
  |---|---|---|
  | `'No'` | 22,451 | 86.36% |
  | `'Yes'` | 2,244 | 8.63% |
  | `''` (empty) | 1,209 | 4.65% |
  | `' '` (single space) | 92 | 0.35% |

  The two empty-ish encodings are distinct in the file: `''` is almost
  entirely provider *Georgia Virtual*; `' '` is provider *Indiana*. Both are
  treated as missing; they are **reported separately and not recoded into a
  third category**.
- **Structural missingness:** the entire prompt **"Phones and driving"**
  (1,168 essays — the whole Georgia Virtual provider) has no ELL coding at
  all. The complete-case analysis therefore covers **14 of 15 prompts**. This
  is provider-level, not random, missingness; it limits generalisation to
  that provider, not validity within the analysed strata.
- **Missingness totals:** ELL 1,301/25,996 (5.0%); prompt 0; human score 0.
- **Complete cases** (prompt, human score, and ELL all present): **24,695**.

## Stratum structure for `(P, Y)` conditioning

Full table: `results/persuade_feasibility/strata.csv` (83 rows), cell-level
table `cells.csv`, compact view `strata_compact.txt`.

| quantity | value |
|---|---|
| `(prompt, human_score)` strata observed | 83 (of 90 possible; 7 absent) |
| usable strata (≥2 units, both ELL categories present) | **61** |
| degenerate strata | 22 = 21 all-`No` + 1 all-`Yes` ("Distance learning", Y=1, 9/9 ELL); 0 singletons |
| essays in usable strata (**effective permutation N**) | **23,334** (94.5% of complete cases) |
| essays lost to degenerate strata | 1,361 |
| ELL-Yes essays inside usable strata | 2,235 (9.6% of usable pool) |
| usable stratum sizes | min 3 · median 386 · mean 382.5 · max 783 |
| within-stratum minority share | min 0.0058 · median 0.0634 · max 0.50 |
| usable strata with minority count < 5 | 10 (holding 1,250 essays) |
| usable strata with minority count = 1 | 2 |

Sparsity pattern: the degenerate all-`No` strata are concentrated at high
scores (Y = 5, 6) on the independent-writing prompts — ELL writers are rare
in the top score bands. **No pooling was applied.** Any pooling (e.g. merging
Y = 5–6, or dropping thin strata by a prespecified rule) changes the null
being tested and must be an explicit, prespecified design decision. Note the
permutation test itself needs no rescue: degenerate strata contribute exactly
nothing to any statistic and do not threaten validity — the cost is only the
1,361 essays (5.5%) that carry no information about `A` given `(P, Y)`.

## Power planning

Design matched to the real structure: observed 61 usable strata with observed
sizes; each simulated essay keeps its **actual ELL label** (so within-stratum
ELL proportions are exactly the observed ones); six-category ordinal judge
score used natively (no discretisation); the planned stratified permutation
test (conditional G², B = 999, α = 0.05); essays sampled without replacement
from the usable pool.

Planning assumptions (stated, not estimated):

- judge dispersion `S = clamp(Y + e, 1, 6)`, `P(e = −1, 0, +1) = (0.2, 0.6, 0.2)`;
- alternative: an ELL essay's judge score is shifted down one rubric category
  with probability π — **weak π = 0.05, moderate π = 0.10, strong π = 0.20**
  (group mean shifts of 0.05 / 0.10 / 0.20 rubric points);
- π = 0 is the calibration check.

| n scored | mean ELL in sample | usable strata in sample | Type I (pi=0) | weak (pi=0.05) | moderate (pi=0.10) | strong (pi=0.20) |
|---|---|---|---|---|---|---|
| 500 | 48 | 21 | 0.046 | 0.068 | 0.104 | 0.150 |
| 1,000 | 96 | 30 | 0.044 | 0.070 | 0.146 | 0.282 |
| 2,000 | 191 | 41 | 0.038 | 0.098 | 0.228 | 0.548 |
| 4,000 | 384 | 49 | 0.036 | 0.172 | 0.374 | 0.884 |
| 8,000 | 766 | 56 | 0.042 | 0.300 | 0.752 | 0.990 |
| 10,000 | 957 | 57 | 0.064 | 0.348 | 0.840 | 1.000 |
| 12,000 | 1149 | 58 | 0.032 | 0.444 | 0.914 | 1.000 |
| 16,000 | 1532 | 60 | 0.052 | 0.538 | 0.984 | 1.000 |
| 23,334 | 2235 | 61 | 0.052 | 0.830 | 1.000 | 1.000 |

500 replicates per cell, B = 999 permutations, alpha = 0.05; Monte Carlo SE on a rate near 0.8 is about 0.018, near 0.05 about 0.010.

## LLM inference volume

One "judge condition" = one (judge model × rubric/prompt variant). Each essay
scored once per condition:

| n scored | calls per judge-condition | x2 conditions | x4 conditions |
|---|---|---|---|
| 500 | 500 | 1,000 | 2,000 |
| 1,000 | 1,000 | 2,000 | 4,000 |
| 2,000 | 2,000 | 4,000 | 8,000 |
| 4,000 | 4,000 | 8,000 | 16,000 |
| 8,000 | 8,000 | 16,000 | 32,000 |
| 16,000 | 16,000 | 32,000 | 64,000 |
| 23,334 | 23,334 | 46,668 | 93,336 |

## Recommendation

**GO**, with two scale caveats and one assumption to argue in writing.

The prespecified `(prompt x human_score)` conditioning scheme is statistically
viable as designed:

1. **Within-stratum variation is sufficient.** 61 of 83 strata contain both
   ELL categories, holding 23,334 essays (94.5% of complete cases) and 2,235
   ELL-Yes essays. Degenerate strata cost only 5.5% of essays and zero
   validity. No pooling is needed and none is proposed.
2. **The test is calibrated on the real structure.** Simulated Type I error
   at alpha = 0.05 is 0.036-0.052 across every candidate sample size using
   the observed strata, observed ELL imbalance, and native 1-6 categories.
3. **Power is plausible at achievable scale** under the stated planning
   assumptions. Approximate smallest n for ~80% power: **strong (pi = 0.20):
   ~3,500-4,000 essays; moderate (pi = 0.10): ~9,000-10,000 essays
   (interpolated; 0.752 at 8,000, 0.984 at 16,000); weak (pi = 0.05):
   essentially the full usable corpus (0.830 at n = 23,334).** These are
   planning numbers under an assumed judge-dispersion model, not claims about
   the real effect.

Caveats attached to the GO:

- **Scale choice determines detectable effect size.** A budget-limited run of
  ~4,000 essays only powers strong dependence; a run below ~8,000 essays
  should prespecify that weak dependence is outside its detectable range
  rather than interpret a null result as absence of dependence. Scoring the
  full 23,334-essay usable pool is the only configuration powered for weak
  effects.
- **A1 (independence between units) must be argued from corpus
  documentation**, since the data contain no writer identifier. There are no
  duplicate essays; repeated writers can be neither confirmed nor excluded
  from the data alone.
- **One prompt is structurally excluded**: "Phones and driving" (all of
  provider Georgia Virtual) has no ELL coding, so conclusions cover 14
  prompts / 4 providers.
- Rejection is evidence that the judge score carries information about ELL
  status beyond the human score and prompt. Under imperfect construct
  measurement by `Y`, it is **not** proof of causal use of demographic
  information, and must not be reported as such.
