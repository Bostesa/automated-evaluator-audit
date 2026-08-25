"""Real-data scoring pipeline: sampling -> prompts -> judge -> storage -> analysis.

Stage discipline (enforced structurally and by tests):

* SCORING stage code (`sampling`, `prompts`, `judge`, `storage`) never sees
  demographic attributes or human holistic scores beyond what the design
  needs: sampling reads the human score only to form conditioning strata and
  never reads the attribute; prompt construction can only receive the essay
  text and prompt materials.
* ANALYSIS stage code (`analysis`) refuses to run until the raw score store
  is frozen, and only then joins demographics.
"""

from offcriterion.pipeline.sampling import draw_primary_sample
from offcriterion.pipeline.prompts import build_judge_prompt
from offcriterion.pipeline.judge import FakeDeterministicJudge
from offcriterion.pipeline.storage import RawScoreStore
from offcriterion.pipeline.parse import parse_score, ParseError

__all__ = [
    "draw_primary_sample",
    "build_judge_prompt",
    "FakeDeterministicJudge",
    "RawScoreStore",
    "parse_score",
    "ParseError",
]
