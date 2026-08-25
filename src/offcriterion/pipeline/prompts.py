"""Judge prompt construction from frozen templates.

The templates live in ``prompts/`` and were frozen at preregistration.  This
module can only inject four things: the essay text, the task type, the
assignment text, and the source-text titles.  There is no code path by which a
demographic attribute or a human score can enter a judge prompt: the function
signature does not accept them, and the test suite asserts both the signature
and the absence of metadata markers in rendered prompts.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

_PROMPT_DIR = Path(__file__).resolve().parents[3] / "prompts"

PRIMARY_CONDITION = "plain"
SECONDARY_CONDITION = "ignore_demographics"
CONDITIONS = (PRIMARY_CONDITION, SECONDARY_CONDITION)

_TEMPLATES = {
    "Independent": "judge_prompt_independent.txt",
    "Text dependent": "judge_prompt_source_based.txt",
}
_MODIFIER_FILE = "condition_ignore_demographics.txt"


def _read(name: str, prompt_dir: Path | None = None) -> str:
    return ((prompt_dir or _PROMPT_DIR) / name).read_text(encoding="utf-8")


def build_judge_prompt(
    essay_text: str,
    task: str,
    assignment: str,
    source_titles: str,
    condition: str = PRIMARY_CONDITION,
    prompt_dir: Path | None = None,
) -> str:
    """Render the frozen template for one essay.

    ``condition="ignore_demographics"`` inserts the frozen modifier paragraph
    immediately before the RUBRIC heading; everything else is byte-identical
    to the primary condition.
    """
    if task not in _TEMPLATES:
        raise ValueError(f"unknown task {task!r}")
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")
    template = _read(_TEMPLATES[task], prompt_dir)
    if condition == SECONDARY_CONDITION:
        modifier = _read(_MODIFIER_FILE, prompt_dir).strip()
        template = template.replace("RUBRIC\n", modifier + "\n\nRUBRIC\n", 1)
    rendered = template.replace("{assignment}", assignment)
    rendered = rendered.replace("{source_titles}", source_titles)
    rendered = rendered.replace("{essay}", essay_text)
    return rendered


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def load_prompt_materials(path: Path) -> dict[str, dict[str, str]]:
    """``prompt_name -> {task, assignment, source_text}`` from the extract."""
    with path.open(newline="", encoding="utf-8") as f:
        return {
            row["prompt_name"]: {
                "task": row["task"],
                "assignment": row["assignment"],
                "source_text": row["source_text"],
            }
            for row in csv.DictReader(f)
        }
