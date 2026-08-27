"""Unit tests for the frozen Civil Comments pre-scoring design rules.

These test the *rules* (hash selection, canonical Z representation,
semantic bins, attribute threshold, decile discretisation, negative
control generation) on synthetic inputs; they never touch the 448,000-row
source CSV, so they run in the ordinary suite.
"""

from __future__ import annotations

import hashlib
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from civil_comments_freeze import (  # noqa: E402
    IDENTITIES,
    SELECTION_SEED_STRING,
    attribute_value,
    bin_overall_toxicity,
    bin_subtype,
    canonical_fraction,
    discretize_scores,
    negative_control,
    select_primary,
    selection_key,
    support_counts,
    z_key_binned,
    z_key_exact,
)

Z_DEFAULTS = {
    "toxicity": "0.0",
    "severe_toxicity": "0.0",
    "identity_attack": "0.0",
    "insult": "0.0",
    "threat": "0.0",
    "obscene": "0.0",
    "sexual_explicit": "0.0",
}


def _row(comment_id: str, article_id: str, **overrides: str) -> dict[str, str]:
    row = {"id": comment_id, "article_id": article_id, "comment_text": "x"}
    row.update(Z_DEFAULTS)
    for identity in IDENTITIES:
        row[identity] = "0.0"
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Hash selection
# ---------------------------------------------------------------------------


def test_selection_key_matches_frozen_construction() -> None:
    expected = hashlib.sha256(
        f"{SELECTION_SEED_STRING}:12345".encode("utf-8")
    ).hexdigest()
    assert selection_key("12345") == expected


def test_select_primary_picks_min_key_and_ignores_row_order() -> None:
    rows = [_row(str(i), article_id="7") for i in range(20)]
    rows += [_row("100", article_id="8")]
    winner = min((selection_key(str(i)), str(i)) for i in range(20))[1]

    chosen = select_primary(rows)
    assert [r["article_id"] for r in chosen] == sorted(
        {"7", "8"}, key=lambda art: int(next(r["id"] for r in chosen if r["article_id"] == art))
    )
    assert {r["article_id"]: r["id"] for r in chosen}["7"] == winner
    assert {r["article_id"]: r["id"] for r in chosen}["8"] == "100"

    reversed_choice = select_primary(list(reversed(rows)))
    assert [(r["id"], r["article_id"]) for r in reversed_choice] == [
        (r["id"], r["article_id"]) for r in chosen
    ]


def test_select_primary_missing_article_id_becomes_singleton() -> None:
    rows = [_row("1", article_id=""), _row("2", article_id=""), _row("3", article_id="9")]
    chosen = select_primary(rows)
    assert {r["id"] for r in chosen} == {"1", "2", "3"}


def test_selection_is_blind_to_labels_and_text() -> None:
    plain = _row("42", article_id="1")
    loaded = _row(
        "42", article_id="1", comment_text="entirely different", toxicity="1.0", muslim="1.0"
    )
    assert selection_key(plain["id"]) == selection_key(loaded["id"])


# ---------------------------------------------------------------------------
# Canonical Z representation and binning
# ---------------------------------------------------------------------------


def test_canonical_fraction_is_exact_decimal_parsing() -> None:
    assert canonical_fraction("0.5") == Fraction(1, 2)
    assert canonical_fraction("0.50") == Fraction(1, 2)
    assert canonical_fraction("0") == 0
    assert canonical_fraction("0.757142857") == Fraction(757142857, 10**9)
    # and is NOT the float round-trip
    assert canonical_fraction("0.1") == Fraction(1, 10) != Fraction(0.1)


def test_z_key_exact_equates_equal_decimals_only() -> None:
    a = _row("1", "1", toxicity="0.60", insult="0.5")
    b = _row("2", "1", toxicity="0.6", insult="0.50")
    c = _row("3", "1", toxicity="0.6", insult="0.500000001")
    assert z_key_exact(a) == z_key_exact(b)
    assert z_key_exact(a) != z_key_exact(c)


@pytest.mark.parametrize(
    "value, expected",
    [("0", 0), ("0.1", 1), ("0.25", 1), ("0.3", 2), ("0.499", 2), ("0.5", 3), ("0.749", 3), ("0.75", 4), ("1", 4)],
)
def test_bin_overall_toxicity_boundaries(value: str, expected: int) -> None:
    assert bin_overall_toxicity(Fraction(value)) == expected


@pytest.mark.parametrize(
    "value, expected", [("0", 0), ("0.001", 1), ("0.499", 1), ("0.5", 2), ("1", 2)]
)
def test_bin_subtype_boundaries(value: str, expected: int) -> None:
    assert bin_subtype(Fraction(value)) == expected


def test_z_key_binned_uses_all_seven_labels() -> None:
    base = _row("1", "1", toxicity="0.8", threat="0.4")
    assert z_key_binned(base) == "4|0|0|0|1|0|0"


# ---------------------------------------------------------------------------
# Attribute definition
# ---------------------------------------------------------------------------


def test_attribute_threshold_is_exact_at_one_half() -> None:
    assert attribute_value(_row("1", "1", muslim="0.5"), "muslim") == 1
    assert attribute_value(_row("1", "1", muslim="0.499999999"), "muslim") == 0
    assert attribute_value(_row("1", "1", muslim="0.0"), "muslim") == 0
    assert attribute_value(_row("1", "1", LGBTQ="1"), "LGBTQ") == 1


# ---------------------------------------------------------------------------
# Decile discretisation rule (frozen ahead of any score existing)
# ---------------------------------------------------------------------------


def test_discretize_matches_numpy_type7_deciles() -> None:
    rng = np.random.default_rng(0)
    s = rng.uniform(size=10_000)
    boundaries, bins = discretize_scores(s)
    expected = np.quantile(s, [k / 10 for k in range(1, 10)], method="linear")
    np.testing.assert_array_equal(boundaries, np.unique(expected))
    counts = np.bincount(bins, minlength=10)
    assert counts.size == 10 and abs(counts.max() - counts.min()) <= 2


def test_discretize_identical_values_share_a_category() -> None:
    s = np.array([0.0] * 500 + [0.9] * 500)
    boundaries, bins = discretize_scores(s)
    assert np.unique(bins[s == 0.0]).size == 1
    assert np.unique(bins[s == 0.9]).size == 1
    # coincident decile boundaries collapse deterministically
    assert boundaries.size == np.unique(boundaries).size


def test_discretize_boundary_value_goes_up() -> None:
    s = np.arange(101, dtype=np.float64)  # type-7 deciles land exactly on data
    boundaries, bins = discretize_scores(s)
    b0 = boundaries[0]
    assert b0 in s
    assert bins[s == b0][0] == np.searchsorted(boundaries, b0, side="right") == 1


# ---------------------------------------------------------------------------
# Support counts and negative control
# ---------------------------------------------------------------------------


def test_support_counts_drop_singleton_and_pure_strata() -> None:
    rows = [
        _row("1", "1", muslim="1.0", toxicity="0.5"),
        _row("2", "1", muslim="0.0", toxicity="0.5"),
        _row("3", "1", muslim="0.0", toxicity="0.5"),
        _row("4", "1", muslim="1.0", toxicity="0.9"),  # pure-A stratum
        _row("5", "1", muslim="1.0", toxicity="0.9"),
        _row("6", "1", muslim="0.0", toxicity="0.1"),  # singleton stratum
    ]
    keys = [z_key_exact(r) for r in rows]
    support = support_counts(rows, keys)["muslim"]
    assert support == {
        "n": 6,
        "n_a1": 3,
        "n_informative_strata": 1,
        "n_retained": 3,
        "n_retained_a1": 1,
    }


def test_negative_control_preserves_stratum_counts_and_is_frozen() -> None:
    rng = np.random.default_rng(11)
    rows = []
    for i in range(300):
        rows.append(
            _row(
                str(i),
                str(i),
                toxicity=str(Fraction(int(rng.integers(0, 3)), 4)),
                muslim="1.0" if rng.uniform() < 0.3 else "0.0",
            )
        )
    keys = [z_key_exact(r) for r in rows]
    first = negative_control(rows, keys)
    second = negative_control(rows, keys)
    assert first == second  # frozen seeds, no hidden state

    a = np.array([attribute_value(r, "muslim") for r in rows])
    nc = np.array(first["muslim"])
    for key in set(keys):
        members = np.array([i for i, k in enumerate(keys) if k == key])
        assert nc[members].sum() == a[members].sum()
