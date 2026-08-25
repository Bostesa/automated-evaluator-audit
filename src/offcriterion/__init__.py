"""OffCriterion: conditional-independence auditing for LLM evaluator scores.

Research question
-----------------
Does an evaluator score ``S`` retain information about a prespecified
off-criterion attribute ``A`` once we condition on the observed intended
construct ``Z``?

Null hypothesis
---------------
``H0 : S _||_ A | Z``

Everything in this package operates on synthetic data only.
"""

from offcriterion.data import RawSample, Sample
from offcriterion.permutation import PermutationTestResult, permutation_test
from offcriterion.statistics import STATISTICS, get_statistic

__all__ = [
    "RawSample",
    "Sample",
    "PermutationTestResult",
    "permutation_test",
    "STATISTICS",
    "get_statistic",
]

__version__ = "0.1.0"
