# Frozen judge prompts

Frozen at preregistration (2026-08-25), before any judge scoring. Rubric text
is verbatim from the canonical PERSUADE holistic rating forms
(`sat_rubric_only_indy.pdf`, `sat_rubric_only_source_based.pdf` in
https://github.com/scrosseye/persuade_corpus_2.0; SHA-256 recorded in
`data/persuade/README.md`), including the original documents' typographical
quirks, which are reproduced rather than edited.

- `judge_prompt_independent.txt` — primary condition, Independent task.
- `judge_prompt_source_based.txt` — primary condition, Text dependent task.
  The canonical corpus provides source-text *titles only* (the passages are
  third-party copyrighted articles not distributed with the corpus); the
  prompt says so explicitly rather than pretending the passages are present.
- `condition_ignore_demographics.txt` — the SECONDARY condition inserts this
  paragraph immediately before the RUBRIC heading. Everything else is
  byte-identical to the primary condition.

Placeholders `{assignment}`, `{source_titles}`, `{essay}` are filled by
`offcriterion.pipeline.prompts.build_judge_prompt` from corpus fields
(`assignment`, `source_text`, `full_text`). No demographic field and no human
score is ever an input to prompt construction; this is enforced structurally
and by tests.
