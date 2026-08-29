# Civil Comments LLM extension — overnight result report

Generated 2026-08-29T02:12:05Z (UTC). Status: **COMPLETE**.
Final commit: `3ce29c06aa8b86508254895f2bd8b82b10ed6d95`.

## Final N and exclusions per evaluator

| Evaluator | N records | valid | technical | invalid |
|---|---|---|---|---|
| gpt-5.4-mini-2026-03-17 | 69573 | 69573 | 0 | 0 |
| claude-haiku-4-5-20251001 | 69573 | 69573 | 0 | 0 |
| gemini-3.7-flash | 69573 | 67183 | 2384 | 6 |

Detoxify-original results are in `results/civil_comments/audit_results.json` (8-test family).

## 24-test secondary replication family (Holm across all 24)

Holm rejections at alpha=0.05: **21 / 24**.

| Evaluator | Identity | gap(1–5) | G² | raw p | Holm p | reject |
|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | LGBTQ | +0.1761 | 677.246 | 0.0010 | 0.0240 | YES |
| claude-haiku-4-5-20251001 | black | +0.2902 | 1056.770 | 0.0010 | 0.0240 | YES |
| claude-haiku-4-5-20251001 | christian | +0.0382 | 791.761 | 0.1070 | 0.3210 | no |
| claude-haiku-4-5-20251001 | female | +0.1317 | 1546.250 | 0.0010 | 0.0240 | YES |
| claude-haiku-4-5-20251001 | male | +0.0775 | 1263.125 | 0.0100 | 0.0400 | YES |
| claude-haiku-4-5-20251001 | muslim | +0.3724 | 1203.149 | 0.0010 | 0.0240 | YES |
| claude-haiku-4-5-20251001 | other_religions | +0.3384 | 665.622 | 0.0010 | 0.0240 | YES |
| claude-haiku-4-5-20251001 | white | +0.3606 | 1503.986 | 0.0010 | 0.0240 | YES |
| gemini-3.7-flash | LGBTQ | +0.1155 | 543.725 | 0.2450 | 0.4900 | no |
| gemini-3.7-flash | black | +0.1635 | 885.673 | 0.0010 | 0.0240 | YES |
| gemini-3.7-flash | christian | +0.0033 | 718.248 | 0.2720 | 0.4900 | no |
| gemini-3.7-flash | female | +0.0780 | 1298.992 | 0.0010 | 0.0240 | YES |
| gemini-3.7-flash | male | +0.0606 | 1222.339 | 0.0050 | 0.0250 | YES |
| gemini-3.7-flash | muslim | +0.2543 | 933.707 | 0.0010 | 0.0240 | YES |
| gemini-3.7-flash | other_religions | +0.1383 | 472.925 | 0.0010 | 0.0240 | YES |
| gemini-3.7-flash | white | +0.2763 | 1216.508 | 0.0010 | 0.0240 | YES |
| gpt-5.4-mini-2026-03-17 | LGBTQ | +0.2548 | 720.313 | 0.0040 | 0.0240 | YES |
| gpt-5.4-mini-2026-03-17 | black | +0.4578 | 1207.012 | 0.0010 | 0.0240 | YES |
| gpt-5.4-mini-2026-03-17 | christian | +0.0434 | 1050.725 | 0.0020 | 0.0240 | YES |
| gpt-5.4-mini-2026-03-17 | female | +0.1703 | 1765.622 | 0.0010 | 0.0240 | YES |
| gpt-5.4-mini-2026-03-17 | male | +0.1137 | 1572.959 | 0.0030 | 0.0240 | YES |
| gpt-5.4-mini-2026-03-17 | muslim | +0.5677 | 1303.886 | 0.0010 | 0.0240 | YES |
| gpt-5.4-mini-2026-03-17 | other_religions | +0.3801 | 651.484 | 0.0010 | 0.0240 | YES |
| gpt-5.4-mini-2026-03-17 | white | +0.5885 | 1798.985 | 0.0010 | 0.0240 | YES |

## Negative controls (calibration)

| Evaluator | identities with raw p<0.05 |
|---|---|
| gpt | 0: none |
| claude | 0: none |
| gemini | 1: christian |

## Binned-Z sensitivity

| Evaluator | identities with raw p<0.05 |
|---|---|
| gpt | 8: male, female, LGBTQ, christian, muslim, other_religions, black, white |
| claude | 8: male, female, LGBTQ, christian, muslim, other_religions, black, white |
| gemini | 7: male, female, LGBTQ, muslim, other_religions, black, white |

## Technical-exclusion / missingness audit

| Evaluator | excluded | technical | invalid | rate |
|---|---|---|---|---|
| gpt | 0 | 0 | 0 | 0.00000 |
| claude | 0 | 0 | 0 | 0.00000 |
| gemini | 2390 | 2384 | 6 | 0.03435 |

Cross-evaluator summary: `results/civil_comments/cross_evaluator_summary.json`.

## Artifact SHA-256

- `results/civil_comments/llm_scores_gemini_FROZEN.json` — `9abcb3a9ec19df79a9c075684ce259e7288442ea04dbfcb87a61defe7b515d26`
- `results/civil_comments/llm_audit_results.json` — `1ade58806be4de8f9bcbac27e99942a1ad4b3af3e3b01284d4fe21b697465d01`
- `results/civil_comments/llm_exclusion_audit.json` — `89fb376a93add41771a201eed9edccb6bd48e04bd6242cc876b5fc4a6c5a8c51`
- `results/civil_comments/cross_evaluator_summary.json` — `518148db318256c99f842c7e8d9021f42d395f06bd86ba8a03f13c00b6fc2566`
