# Amendment 1 to the Civil Comments Gemini Terminal Rule — Cutoff Superseded

Frozen: 2026-08-28T04:55Z.

- **Parent (amended) commit:** `9175211` ("Freeze outcome-blind Gemini
  terminal rule with hard 2026-08-31 cutoff"). That commit is preserved in
  history unmodified; nothing in it is rewritten or deleted.
- **Scope of this amendment:** it supersedes ONLY the hard wall-clock cutoff
  (2026-08-31T07:00:00Z) frozen in
  `docs/civil_comments_gemini_terminal_rule.md` /
  `config/civil_comments_gemini_terminal_rule.json`. Every other provision of
  the terminal rule remains in force verbatim.
- **Reason:** latest user clarification and submission logistics. The
  2026-08-31T07:00:00Z cutoff was an assistant-chosen date that does not
  reflect the user's latest instruction and is not usable for the current
  submission timeline. Waiting until August 31 must not function as a
  scientific stopping rule.
- **Outcome-blindness at amendment time:** no Civil Comments LLM S-versus-A
  result (GPT, Claude, or Gemini) had been computed or inspected when this
  amendment was made. The GPT and Claude stores are frozen but unanalyzed;
  the Gemini store is partial and unanalyzed; no LLM score has been joined
  to A or Z. This is therefore a prospective, infrastructure-only amendment.
- **Not modified by this amendment:** model ID, prompt, manifest, A, Z, the
  ConditionalG2 statistic, B = 999, permutation seeds, the 24-test
  multiplicity rule, frozen exclusions, negative controls, and every other
  scientific analysis rule. All are untouched.

## Corrected Gemini execution policy (supersedes only the cutoff)

1. Preserve every valid score and every already-frozen exclusion.
2. Never rescore a previously successful row.
3. Never rescore the 2,339 already-frozen quota technical exclusions.
4. Continue only unresolved rows.
5. Continue rotating among verified Gemini projects as quota permits.
6. All rotations remain infrastructure-only and completely blind to A, Z,
   and all evaluator results.
7. Do NOT wait until August 31 as a scientific stopping rule.
8. The practical objective is to finish Gemini early enough for the current
   paper submission and verification workflow.
9. If the existing Gemini projects do not provide enough capacity in time,
   STOP and report the exact remaining unresolved count so the user can
   supply additional authorized Gemini project credentials.
10. No new accounts/projects are created without explicit user action.
11. A newly supplied credential may be added only after: secure storage
    outside the repository; non-dataset smoke verification; confirmation
    that it calls exactly `gemini-3.7-flash` (provider model echo checked);
    identical frozen prompt/settings; and addition to the infrastructure
    provenance ledger
    (`results/civil_comments/gemini_credential_provenance.json`).
12. Credential/project changes never create a new scientific evaluator
    condition.

## Supervisor consequence

The automated recovery supervisor is corrected so that it cannot idle-wait
toward August 31: it probes all verified credentials (burst-verified, 15
consecutive clean non-dataset calls, exact model echo required), scores
unresolved rows whenever any verified project has quota, and whenever ALL
verified projects are simultaneously quota-exhausted with unresolved rows
remaining it emits a CAPACITY REPORT containing the exact unresolved count,
so the user can immediately decide whether to supply additional authorized
credentials (per items 9–11) or stop the branch. The incomplete-at-stop
procedure of the parent rule (preserve partial store; record valid /
invalid / technical / unresolved counts, request-order ranges, credential
segments, stop reason; provider-level incomplete-scoring deviation; no
silent redefinition of the 24-test family) remains in force unchanged.
