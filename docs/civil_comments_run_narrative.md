# Civil Comments LLM-evaluator extension — run narrative and interpretation

_Written after the unattended run completed (2026-08-29). This is my
considered read of the frozen results; it supersedes the auto-generated draft.
Scope: the **secondary cross-evaluator replication family** (3 LLM evaluators ×
8 identities), NOT the PERSUADE preregistration and NOT the Civil Comments
primary confirmatory family. It was frozen before any evaluator score was
joined to the identity attributes A._

## Bottom line

All 69,573 manifest rows were scored by Gemini and the store was frozen and
hashed. The prespecified analysis ran to completion.

- **21 of 24 tests reject at Holm-corrected α = 0.05.** Across GPT-5.4-mini,
  Claude Haiku 4.5, and Gemini 3.7 Flash, the 1–5 toxicity rating retains
  residual statistical dependence on an identity-mention attribute among
  comments that share the *same* seven-label human annotation vector Z — for
  almost every identity and every model.
- The conventional evaluator agrees and is even stronger: **Detoxify rejects
  8 of 8** in its own frozen family. So the effect is not architecture-specific
  and not specific to LLMs versus a conventional classifier.
- **Every conditional gap is positive**: mentioning one of these identities is
  associated with a *higher* model toxicity rating than the human labels alone
  would predict, at matched human annotations.
- **The result is robust.** Negative controls reject 1 of 24 (chance level for
  α = 0.05), so the permutation machinery is calibrated; the binned-Z
  sensitivity rejects 23 of 24, tracking the exact-Z primary closely.

## The one real nuance: `christian`

The three cells that do **not** reject are `claude:christian`,
`gemini:christian`, and `gemini:LGBTQ`. The `christian` story is the
interesting one and is consistent across all three models: its conditional gap
is essentially **zero** everywhere — GPT +0.043, Claude +0.038, Gemini +0.003
on the 1–5 scale — whereas the other identities show gaps up to +0.59. GPT's
`christian` cell technically rejects, but only because with full 69,573-row
coverage even a near-zero gap is detectable; the *effect size* is negligible.

My read: among these eight attributes, mentioning `christian` is the one that
does **not** move the evaluators' toxicity rating once you hold the human
labels fixed. That asymmetry — large positive gaps for `muslim`, `black`,
`white`, `LGBTQ`, etc., and ~0 for `christian` — is the most substantively
interesting pattern in the table and deserves a sentence in the write-up.

## Effect sizes (weighted conditional mean gap, A=1 − A=0, on the 1–5 scale)

GPT shows the largest gaps, Gemini the smallest, same direction throughout:

- **GPT**: white +0.59, muslim +0.57, black +0.46, other_religions +0.38,
  LGBTQ +0.25, female +0.17, male +0.11, christian +0.04.
- **Claude**: muslim +0.37, white +0.36, other_religions +0.34, black +0.29,
  LGBTQ +0.18, female +0.13, male +0.08, christian +0.04.
- **Gemini**: white +0.28, muslim +0.25, black +0.16, other_religions +0.14,
  LGBTQ +0.12 (n.s.), female +0.08, male +0.06, christian +0.003 (n.s.).

The G² statistics are large (hundreds to ~1,800), but that is partly the
N = 69,573 sample; the gaps are the interpretable quantity.

## Final N and exclusions

| Evaluator | model | valid | technical | invalid | excl. rate |
|---|---|---|---|---|---|
| GPT | gpt-5.4-mini-2026-03-17 | 69,573 | 0 | 0 | 0.00% |
| Claude | claude-haiku-4-5-20251001 | 69,573 | 0 | 0 | 0.00% |
| Gemini | gemini-3.7-flash | 67,183 | 2,384 | 6 | 3.44% |

## Missingness — the caveat that matters

Gemini's 3.44% exclusions are almost entirely **infrastructure**, not model
behavior: HTTP 429 quota floods at project exhaustion boundaries, a few HTTP
503s, and 11 client-side network failures from a Wi-Fi outage. They cluster
late in comment-id order (last-decile exclusion count 22 vs first-decile 1),
which is exactly where the quota floods and outage landed — an artifact of *when*
scoring happened, and A-blind by construction.

One flag from the audit: **Gemini's exclusion rate for `christian` is
associated with A** (two-sided Fisher p = 0.00034); the other seven identities
show no association (all p > 0.09). So `gemini:christian`'s non-rejection could
in principle be entangled with differential missingness. However, `christian`'s
gap is ~0 in the **fully-covered** GPT and Claude stores too, so I read the
`christian` null as real rather than a Gemini missingness artifact — but the
paper should state the caveat explicitly and lean on GPT/Claude for the
`christian` conclusion.

## What this does and does not mean

A rejection means only that the evaluator's rating retains residual conditional
statistical dependence on an identity-mention attribute given the observed human
annotations. It is **not** evidence of discrimination, unfairness, causal use of
identity, or demographic inference; it does not treat the human toxicity labels
as ground truth; and it does not say identity language is irrelevant to
toxicity. It is a measurement about the joint distribution of scores, identity
mentions, and human labels — nothing stronger.

## What happened operationally (all outcome-blind)

The scientific spec never changed: pinned `gemini-3.7-flash`, the frozen rubric
prompt, the strict 1–5 JSON schema, temperature 0 / seed 427183 / thinkingLevel
low, the 3-retry policy, ascending-comment-id order, and the append-only store.
Only credential/quota infrastructure varied, and every probe/rotation decision
used solely HTTP status, record counts, and non-dataset smoke calls — never a
score, A, or Z. The run was heavily quota-bound: the three original projects and
five early repair keys degraded to HTTP 401 (invalid auth, not quota) and were
excluded; fresh Tier-1 projects (extra6/7/8) carried the bulk of the rows; a
Wi-Fi outage produced the 11 network exclusions. Full ledger and every
credential-health event are in
`results/civil_comments/gemini_credential_provenance.json` and
`docs/deviations.md`.

## Suggested next steps (manuscript intentionally NOT modified)

1. Report the 21/24 headline with the Detoxify 8/8 as the cross-method anchor.
2. Foreground the `christian` ~0-gap asymmetry — it is the most interesting
   substantive finding and a natural discussion point.
3. State the Gemini missingness caveat (3.44%, infrastructure-caused,
   `christian` A-association) and lean on GPT/Claude where it matters.
4. Keep the framing at "residual conditional dependence," not discrimination.
5. Only then integrate the frozen numbers into the two-page write-up.

## Artifacts

- `results/civil_comments/llm_audit_results.json` — the 24 tests, Holm,
  negative controls, binned-Z sensitivity.
- `results/civil_comments/llm_exclusion_audit.json` — missingness audit.
- `results/civil_comments/cross_evaluator_summary.json` — Detoxify/GPT/Claude/
  Gemini comparison.
- `results/civil_comments/llm_scores_gemini_FROZEN.json` — frozen store hash and
  pooled A-blind stats.
- `results/civil_comments/overnight_report.json` — the orchestrator's
  machine-readable report.

Full test suite passed (`pytest`), and all artifacts are committed and pushed.
