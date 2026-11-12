# Do Robot Safety Judges Confuse Success with Safety?

**Nathan Samson · University of Maryland, Baltimore County**

Accepted at the **Science of Physical AI Safety (SPAIS) workshop at CoRL 2026**.

[Read the paper](papers/spais2026/spais74_camera_ready.pdf) · [Supporting material](papers/spais2026/spais74_supporting_material.pdf) · [Citation](papers/spais2026/CITATION.bib)

## What we tested

Does calling a robot attempt successful change its safety rating when the
images stay the same?

Each AI judge received a task description, ten images from a recorded robot
simulation, and a five-point safety rubric. In separate calls, we described
the same attempt as successful or unsuccessful. The images, task and rubric
stayed fixed. SmolVLA and X-VLA are the robot-control models that produced
the recordings. The judges are separate models that rated them.

## Results

Describing an attempt as successful raised its average safety rating.
Higher scores mean fewer apparent safety concerns.

| Robot-control model | Judge | Complete pairs | Average increase | 95% confidence interval |
| --- | --- | ---: | ---: | --- |
| SmolVLA | GPT-5.5 | 352 | 0.455 | [0.368, 0.541] |
| SmolVLA | GPT-5.4-mini | 352 | 0.361 | [0.278, 0.449] |
| SmolVLA | Claude Sonnet 5.5 | 351 | 0.510 | [0.415, 0.609] |
| X-VLA | GPT-5.5 | 200 | 0.605 | [0.487, 0.719] |
| X-VLA | GPT-5.4-mini | 200 | 0.340 | [0.241, 0.444] |
| X-VLA | Claude Sonnet 5.5 | 200 | 0.620 | [0.495, 0.738] |

These are success-stated minus failure-stated differences on the 1–5 scale.
Intervals resample whole tasks. Each cohort covers 40 tasks. One malformed
Claude response left 351 complete pairs from 352 sampled SmolVLA attempts.

The effect remained with alternative wording and instructions to ignore task
success. The paper also reports text controls, score distributions and later
descriptive threshold-crossing summaries.

## What this means

Reported outcomes influence ratings of identical displayed evidence. The
experiment does not establish which safety rating is correct. Ten images can
omit important events, and the rubric's contact, handling and motion criteria
may be related to task failure. No human safety ratings or complete independent
safety reference were available. Threshold crossings are score changes under
illustrative rules, not verified safety errors.

## Materials

The [paper folder](papers/spais2026/) contains the main paper, supporting
material, citation and checksums. The paper has four main-text pages plus
references. Supporting material includes the original prompts and all five
score definitions, model settings, a ten-image example, score distributions,
and descriptive crossings at cutoffs 2–5.

This public branch contains the SPAIS PDFs. It does not contain the robotics
simulation, raw judge responses or analysis pipeline needed to reproduce the
robot study from scratch.

## Earlier evaluator audits

The code in `src/offcriterion/` and `scripts/` belongs to earlier essay and
toxicity audits. Start with their [overview](docs/EVALUATOR_AUDIT_OVERVIEW.md),
[reproduction guide](docs/REPRODUCING.md) and [data licences](DATA_LICENSES.md).
Those commands do not reproduce the SPAIS robot experiments.
