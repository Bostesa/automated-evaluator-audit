# Civil Comments (WILDS identity-annotated subset) data provenance

The dataset, the pinned Detoxify checkpoint, and the Hugging Face
tokenizer cache live in this directory but are not committed to git
(large; the canonical sources are recorded here and every load verifies
the hashes). This is the frozen data record for the Civil Comments
additional audit (`docs/civil_comments_additional_audit_plan.md`,
`config/civil_comments_additional_audit.json`).

## Source table

- File: `all_data_with_identities.csv` — the WILDS CivilComments source
  table (Koh et al., 2021): the 448,000-comment identity-annotated
  subset of Civil Comments / Jigsaw *Unintended Bias in Toxicity
  Classification*, with the seven human toxicity annotation fractions,
  all identity annotation fractions, the WILDS derived binary identity
  groups, `article_id`, and the official WILDS split.
- Obtained from
  `https://huggingface.co/datasets/shlomihod/civil-comments-wilds`
  (file `all_data_with_identities.csv`, revision
  `3fbfeca80bad0f3aec37e72fa07eff222b6e752f`), downloaded 2026-08-26.
  The official WILDS CodaLab bundle
  (`https://worksheets.codalab.org/rest/bundles/0x8cd3de0634154aeaad2ee6eb96723c6e/contents/blob/`)
  distributes the same table but returned HTTP 500 at download time.
- Reconstruction:

  ```python
  from huggingface_hub import hf_hub_download
  hf_hub_download(
      repo_id="shlomihod/civil-comments-wilds", repo_type="dataset",
      filename="all_data_with_identities.csv",
      revision="3fbfeca80bad0f3aec37e72fa07eff222b6e752f",
  )
  ```

- SHA-256:
  `403e638c83a225d738a937ff98b61fd0631e30f710d57928c7766d413526b77f`
  (272,542,670 bytes, 448,000 data rows). No other mirror or version
  may be substituted after the freeze.
- License: **CC0 1.0** (Civil Comments release; Jigsaw/Conversation AI).
  Attribution: Borkan, Dixon, Sorensen, Thain, Vasserman (2019),
  *Nuanced Metrics for Measuring Unintended Bias with Real Data for
  Text Classification*; WILDS benchmark: Koh et al. (2021).

## Evaluator checkpoint

- `checkpoints/toxic_original-c1212f89.ckpt` — Detoxify **original**
  (bert-base-uncased), release tag `v0.1-alpha`:
  `https://github.com/unitaryai/detoxify/releases/download/v0.1-alpha/toxic_original-c1212f89.ckpt`
- SHA-256:
  `c1212f89ac23307ab33932ce29dc446a6e030fb3f384a500890bbe662b7b544a`
  (438,021,897 bytes). The filename fragment `c1212f89` is the first 8
  hex characters of that hash (torch.hub convention).
- Trained on the Jigsaw 2018 Toxic Comment Classification Challenge
  (Wikipedia talk pages) — a corpus distinct from Civil Comments.

## Tokenizer cache

- `hf_cache/` — local `HF_HOME` holding `bert-base-uncased`
  (config + tokenizer files) at revision
  `86b5e0934494bd15c9632b12f734a8a67f723594`; per-file SHA-256s are
  recorded in `config/civil_comments_additional_audit.json`.
