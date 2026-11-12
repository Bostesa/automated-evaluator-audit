# SPAIS 2026 paper and supporting material

**Do Robot Safety Judges Confuse Success with Safety?**

Nathan Samson, University of Maryland, Baltimore County

Accepted at the Science of Physical AI Safety workshop at CoRL 2026.

| File | Contents |
| --- | --- |
| [Main paper](spais74_camera_ready.pdf) | Four pages of main text and one reference page, without the appendix |
| [Supporting material](spais74_supporting_material.pdf) | Exact prompts and score anchors, settings, full storyboard, distributions and threshold summaries |
| [Citation](CITATION.bib) | BibTeX entry for the workshop paper |
| [Checksums](FILES.json) | SHA-256 hashes and the source publication commit |

Direct downloads: [paper](https://raw.githubusercontent.com/Bostesa/automated-evaluator-audit/main/papers/spais2026/spais74_camera_ready.pdf) and [supporting material](https://raw.githubusercontent.com/Bostesa/automated-evaluator-audit/main/papers/spais2026/spais74_supporting_material.pdf).

Both PDFs are unchanged copies of the readability version already published
at commit `9c643d4fdc766a62f425c28c5643a373d4ddf141`. The earlier approved
version remains on `publication-spais2026-camera-ready`.

## Reproduction scope

The supporting PDF records the experiment's prompts, scale, settings and
additional results. These PDFs allow readers to inspect the reported study.
They are not a runnable reproduction package. This branch does not include
the robot trajectories, raw provider responses or robotics analysis scripts.
The repository's existing essay-audit CLI serves a different study.

Changing the stated outcome changed ratings of fixed images. The study does
not establish internal conceptual confusion or independently verified safety
errors. Human safety judgments and events omitted from the storyboard remain
unmeasured.
