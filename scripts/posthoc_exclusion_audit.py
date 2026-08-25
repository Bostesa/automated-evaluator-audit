"""POST-HOC ROBUSTNESS ARTIFACT — technical-exclusion sensitivity audit.

*** NOT PART OF THE PREREGISTERED PRIMARY HYPOTHESIS TEST. ***

This audit was specified and run AFTER the primary result was observed
(Stage E, results/primary_analysis.json).  It examines whether the 467
HTTP-429 technical exclusions from the frozen primary scoring run could
plausibly have selected observations in a way that materially affects the
primary result.  It does not rescore, impute, replace, or modify anything:
the frozen exclusion rule remains binding and the primary result stands as
reported.

Compares included vs excluded essays ONLY on variables that existed before
judge scoring (ELL status, human holistic score, prompt, stratum, essay
length, request order) plus purely technical request metadata already
logged.  The judge score is never used as a predictor (excluded essays have
none).

Also computes a deliberately conservative bound: how extreme the unobserved
scores of the 467 excluded essays would have to be (separately by ELL
status, within the 1-6 score range) to eliminate or reverse the observed
-0.320 conditional mean difference.  This is a diagnostic; no imputation
enters any result.

Outputs: results/posthoc_exclusion_audit.json (+ .md summary).
"""

from __future__ import annotations

import csv
import datetime
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

STORE = ROOT / "data" / "scoring" / "primary"
RAW = STORE / "scores__gpt-5.4-mini-2026-03-17__plain.jsonl"
MANIFEST = ROOT / "data" / "scoring" / "primary_sample_manifest.csv"
ESSAY_LEVEL = ROOT / "data" / "persuade" / "persuade_essay_level.csv"
ESSAY_TEXTS = ROOT / "data" / "persuade" / "essay_texts.csv"


def verify_frozen() -> None:
    from offcriterion.pipeline.storage import RawScoreStore

    RawScoreStore(STORE).verify_frozen()


def load() -> list[dict]:
    records = {r["essay_id_comp"]: r
               for r in (json.loads(l) for l in RAW.open(encoding="utf-8"))}
    manifest = list(csv.DictReader(MANIFEST.open()))
    meta = {r["essay_id_comp"]: r for r in csv.DictReader(ESSAY_LEVEL.open())}
    wanted = set(records)
    chars: dict[str, int] = {}
    with ESSAY_TEXTS.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["essay_id_comp"] in wanted:
                chars[row["essay_id_comp"]] = len(row["full_text"])
    rows = []
    for pos, m in enumerate(manifest):
        eid = m["essay_id_comp"]
        rec, md = records[eid], meta[eid]
        rows.append({
            "essay_id_comp": eid,
            "excluded": bool(rec["error_status"]),
            "ell": 1 if md["ell_status"] == "Yes" else 0,
            "human_score": int(md["holistic_essay_score"]),
            "prompt": md["prompt_name"],
            "stratum": (md["prompt_name"], md["holistic_essay_score"]),
            "chars": chars[eid],
            "words": int(md["essay_word_count"]),
            "manifest_pos": pos,
            "retry_count": rec["retry_count"],
            "prompt_tokens": rec["prompt_tokens"],
            "parsed_score": rec.get("parsed_score"),
            "timestamp": rec["timestamp_utc"],
        })
    return rows


def rate(k: int, n: int) -> float:
    return round(k / n, 5) if n else float("nan")


def logistic_irls(X: np.ndarray, y: np.ndarray, max_iter: int = 200):
    """Plain Newton-Raphson logistic regression; returns beta, SE, converged."""
    n, p = X.shape
    beta = np.zeros(p)
    for _ in range(max_iter):
        eta = X @ beta
        mu = 1.0 / (1.0 + np.exp(-eta))
        w = mu * (1 - mu)
        grad = X.T @ (y - mu)
        H = (X * w[:, None]).T @ X
        try:
            step = np.linalg.solve(H + 1e-9 * np.eye(p), grad)
        except np.linalg.LinAlgError:
            return beta, np.full(p, np.nan), False
        beta = beta + step
        if np.max(np.abs(step)) < 1e-10:
            cov = np.linalg.inv(H + 1e-9 * np.eye(p))
            return beta, np.sqrt(np.diag(cov)), True
    return beta, np.full(p, np.nan), False


def loglik(X: np.ndarray, y: np.ndarray, beta: np.ndarray) -> float:
    eta = X @ beta
    return float(np.sum(y * eta - np.log1p(np.exp(eta))))


def weighted_mean_difference(s, a, strata_keys) -> float:
    """Same estimator as pipeline.analysis._weighted_diagnostics."""
    s, a = np.asarray(s, float), np.asarray(a)
    keys = np.asarray(strata_keys)
    total_w, acc = 0, 0.0
    for k in np.unique(keys):
        m = keys == k
        a_g, s_g = a[m], s[m]
        if a_g.min() == a_g.max() or m.sum() < 2:
            continue
        w = int(m.sum())
        acc += w * (s_g[a_g == 1].mean() - s_g[a_g == 0].mean())
        total_w += w
    return acc / total_w


def main() -> None:
    verify_frozen()  # audit reads the frozen store; it never writes to it
    rows = load()
    n = len(rows)
    exc = [r for r in rows if r["excluded"]]
    inc = [r for r in rows if not r["excluded"]]
    assert len(exc) == 467 and n == 11360

    report: dict = {
        "label": ("POST-HOC ROBUSTNESS ARTIFACT: technical-exclusion "
                  "sensitivity audit of the frozen primary run"),
        "status": ("post-result diagnostic; NOT part of the preregistered "
                   "primary hypothesis test; the frozen exclusion rule and "
                   "the frozen primary result are unmodified"),
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "inputs": {
            "raw_store": str(RAW.relative_to(ROOT)),
            "frozen_sha256_verified": True,
            "n_manifest": n,
            "n_included": len(inc),
            "n_excluded": len(exc),
            "exclusion_cause": "all 467: HTTP 429 after exhausting the frozen 3-retry policy",
        },
    }

    # 1. overall exclusion rate -------------------------------------------
    report["exclusion_rate_overall"] = rate(len(exc), n)

    # 2. by ELL status ----------------------------------------------------
    by_ell = {}
    for v, name in ((1, "ELL"), (0, "non-ELL")):
        grp = [r for r in rows if r["ell"] == v]
        k = sum(r["excluded"] for r in grp)
        p_hat = k / len(grp)
        se = (p_hat * (1 - p_hat) / len(grp)) ** 0.5
        by_ell[name] = {"n": len(grp), "excluded": k, "rate": rate(k, len(grp)),
                        "rate_se": round(se, 5)}
    # 2x2 test of exclusion x ELL (descriptive)
    tab = np.array([[by_ell["ELL"]["excluded"],
                     by_ell["ELL"]["n"] - by_ell["ELL"]["excluded"]],
                    [by_ell["non-ELL"]["excluded"],
                     by_ell["non-ELL"]["n"] - by_ell["non-ELL"]["excluded"]]])
    fisher = stats.fisher_exact(tab)
    by_ell["risk_difference_ELL_minus_nonELL"] = round(
        by_ell["ELL"]["rate"] - by_ell["non-ELL"]["rate"], 5)
    by_ell["fisher_exact_p_descriptive"] = round(float(fisher.pvalue), 4)
    report["exclusion_by_ell"] = by_ell

    # by human score and by prompt (marginals feeding the strata view) ----
    report["exclusion_by_human_score"] = {
        str(y): {"n": len(g), "excluded": sum(r["excluded"] for r in g),
                 "rate": rate(sum(r["excluded"] for r in g), len(g))}
        for y in sorted({r["human_score"] for r in rows})
        for g in [[r for r in rows if r["human_score"] == y]]
    }
    report["exclusion_by_prompt"] = {
        p: {"n": len(g), "excluded": sum(r["excluded"] for r in g),
            "rate": rate(sum(r["excluded"] for r in g), len(g))}
        for p in sorted({r["prompt"] for r in rows})
        for g in [[r for r in rows if r["prompt"] == p]]
    }

    # 3. by (prompt, human score) stratum ---------------------------------
    strata = sorted({r["stratum"] for r in rows})
    strat_tab = {}
    for st in strata:
        g = [r for r in rows if r["stratum"] == st]
        k = sum(r["excluded"] for r in g)
        strat_tab["|".join(st)] = {
            "n": len(g), "excluded": k, "rate": rate(k, len(g)),
            "note": "" if len(g) >= 30 else "small stratum; rate unstable",
        }
    report["exclusion_by_stratum"] = strat_tab
    chi2_ok = [st for st in strata
               if sum(1 for r in rows if r["stratum"] == st) >= 30]
    obs = np.array([[sum(r["excluded"] for r in rows if r["stratum"] == st),
                     sum(1 for r in rows if r["stratum"] == st)]
                    for st in chi2_ok])
    chi2 = stats.chi2_contingency(
        np.column_stack([obs[:, 0], obs[:, 1] - obs[:, 0]]))
    report["stratum_homogeneity_chi2_descriptive"] = {
        "strata_used_n_ge_30": len(chi2_ok),
        "chi2": round(float(chi2.statistic), 2),
        "df": int(chi2.dof),
        "p": round(float(chi2.pvalue), 4),
    }

    # 4. essay length -----------------------------------------------------
    def length_block(field: str) -> dict:
        xi = np.array([r[field] for r in inc], float)
        xe = np.array([r[field] for r in exc], float)
        pooled_sd = float(np.sqrt(((len(xi) - 1) * xi.var(ddof=1)
                                   + (len(xe) - 1) * xe.var(ddof=1))
                                  / (len(xi) + len(xe) - 2)))
        mw = stats.mannwhitneyu(xi, xe, alternative="two-sided")
        return {
            "included_mean": round(float(xi.mean()), 1),
            "excluded_mean": round(float(xe.mean()), 1),
            "included_median": float(np.median(xi)),
            "excluded_median": float(np.median(xe)),
            "difference_excluded_minus_included": round(float(xe.mean() - xi.mean()), 1),
            "standardized_mean_difference": round(float((xe.mean() - xi.mean()) / pooled_sd), 4),
            "mann_whitney_p_descriptive": round(float(mw.pvalue), 4),
        }

    report["essay_length"] = {
        "characters": length_block("chars"),
        "words_corpus_field": length_block("words"),
        "api_tokenizer_note": (
            "prompt_tokens from the API accounting exist only for successful "
            "calls; the 467 excluded records carry prompt_tokens=0 because the "
            "call never completed, so a same-tokenizer comparison is "
            "impossible.  Characters and the corpus essay_word_count field "
            "are used instead; among included essays prompt_tokens correlates "
            "with characters at r={:.3f}, so character length is an adequate "
            "proxy.".format(float(np.corrcoef(
                [r["chars"] for r in inc],
                [r["prompt_tokens"] for r in inc])[0, 1])),
        ),
    }

    # 5. request order / time course --------------------------------------
    pos = np.array([r["manifest_pos"] for r in rows])
    y = np.array([r["excluded"] for r in rows], int)
    deciles = {}
    for d in range(10):
        lo, hi = n * d // 10, n * (d + 1) // 10
        m = (pos >= lo) & (pos < hi)
        deciles[f"decile_{d + 1}"] = {
            "n": int(m.sum()), "excluded": int(y[m].sum()),
            "rate": rate(int(y[m].sum()), int(m.sum())),
        }
    # completion-time view: fraction of failures among records finishing
    # in each tenth of the wall-clock run
    ts = np.array([datetime.datetime.fromisoformat(r["timestamp"]).timestamp()
                   for r in rows])
    t_edges = np.quantile(ts, np.linspace(0, 1, 11))
    time_bins = {}
    for d in range(10):
        m = (ts >= t_edges[d]) & (ts <= t_edges[d + 1] if d == 9 else ts < t_edges[d + 1])
        time_bins[f"time_tenth_{d + 1}"] = {
            "n": int(m.sum()), "excluded": int(y[m].sum()),
            "rate": rate(int(y[m].sum()), int(m.sum())),
        }
    trend = stats.spearmanr(pos, y)
    report["request_order"] = {
        "manifest_position_deciles": deciles,
        "wallclock_completion_tenths": time_bins,
        "spearman_position_vs_exclusion": {
            "rho": round(float(trend.statistic), 4),
            "p_descriptive": round(float(trend.pvalue), 4),
        },
        "note": ("manifest position is the request submission order (10 "
                 "concurrent workers consumed the manifest in order); the "
                 "wall-clock view uses record append timestamps, which for "
                 "excluded records mark retry exhaustion"),
    }

    # retries: descriptive congestion context ------------------------------
    report["retries"] = {
        "excluded": "all 467 exhausted exactly 3 retries (by construction of the frozen policy)",
        "included_retry_distribution": {
            str(k): int(sum(1 for r in inc if r["retry_count"] == k))
            for k in sorted({r["retry_count"] for r in inc})
        },
        "included_mean_retries_by_ell": {
            "ELL": round(float(np.mean([r["retry_count"] for r in inc if r["ell"]])), 3),
            "non-ELL": round(float(np.mean([r["retry_count"] for r in inc if not r["ell"]])), 3),
        },
    }

    # 6. pre-outcome logistic model ---------------------------------------
    prompts = sorted({r["prompt"] for r in rows})
    chars_all = np.array([r["chars"] for r in rows], float)
    Xcols = [np.ones(n)]
    names = ["intercept"]
    Xcols.append(np.array([r["ell"] for r in rows], float)); names.append("ell")
    hs = np.array([r["human_score"] for r in rows], float)
    Xcols.append((hs - hs.mean()) / hs.std()); names.append("human_score_z")
    Xcols.append((chars_all - chars_all.mean()) / chars_all.std()); names.append("essay_chars_z")
    Xcols.append((pos - pos.mean()) / pos.std()); names.append("manifest_pos_z")
    for p in prompts[1:]:
        Xcols.append(np.array([r["prompt"] == p for r in rows], float))
        names.append(f"prompt[{p}]")
    X = np.column_stack(Xcols)
    beta, se, ok = logistic_irls(X, y.astype(float))
    z = beta / se
    pvals = 2 * stats.norm.sf(np.abs(z))
    ll_full = loglik(X, y.astype(float), beta)
    b0, _, _ = logistic_irls(np.ones((n, 1)), y.astype(float))
    ll_null = loglik(np.ones((n, 1)), y.astype(float), b0)
    lrt = 2 * (ll_full - ll_null)
    report["pre_outcome_logistic_model"] = {
        "outcome": "excluded (1) vs included (0); judge score never used",
        "converged": bool(ok),
        "coefficients": {
            nm: {"beta": round(float(b), 4), "se": round(float(s), 4),
                 "odds_ratio": round(float(np.exp(b)), 4),
                 "wald_p": round(float(pv), 4)}
            for nm, b, s, pv in zip(names, beta, se, pvals)
        },
        "lrt_vs_intercept_only": {
            "chi2": round(float(lrt), 2), "df": int(X.shape[1] - 1),
            "p": round(float(stats.chi2.sf(lrt, X.shape[1] - 1)), 4),
        },
        "note": ("descriptive model of missingness; a null result does NOT "
                 "establish missing-completely-at-random"),
    }

    # 7. conservative sensitivity bound -----------------------------------
    s_inc = [r["parsed_score"] for r in inc]
    a_inc = [r["ell"] for r in inc]
    k_inc = ["|".join(r["stratum"]) for r in inc]
    base = weighted_mean_difference(s_inc, a_inc, k_inc)
    exc_ell = [r for r in exc if r["ell"]]
    exc_non = [r for r in exc if not r["ell"]]
    grid = {}
    eliminating = []
    for s_e in range(1, 7):
        for s_n in range(1, 7):
            s_aug = s_inc + [s_e] * len(exc_ell) + [s_n] * len(exc_non)
            a_aug = a_inc + [1] * len(exc_ell) + [0] * len(exc_non)
            k_aug = k_inc + ["|".join(r["stratum"]) for r in exc_ell] \
                          + ["|".join(r["stratum"]) for r in exc_non]
            d = weighted_mean_difference(s_aug, a_aug, k_aug)
            grid[f"excluded_ELL={s_e},excluded_nonELL={s_n}"] = round(d, 4)
            if d >= 0:
                eliminating.append((s_e, s_n, round(d, 4)))
    most_favourable = grid["excluded_ELL=6,excluded_nonELL=1"]
    most_adverse = grid["excluded_ELL=1,excluded_nonELL=6"]
    report["conservative_sensitivity_bound"] = {
        "what_this_is": (
            "a diagnostic bound, not an imputation and not a replacement "
            "of the primary estimate: every excluded ELL essay (n="
            f"{len(exc_ell)}) is assigned one hypothetical score and every "
            f"excluded non-ELL essay (n={len(exc_non)}) another, the essays "
            "are placed back into their true (prompt, human score) strata, "
            "and the preregistered stratum-size-weighted conditional mean "
            "difference is recomputed"),
        "observed_weighted_mean_difference_included_only": round(base, 4),
        "excluded_by_ell": {"ELL": len(exc_ell), "non-ELL": len(exc_non)},
        "grid_all_36_uniform_assignments": grid,
        "most_favourable_to_null_ELL6_non1": most_favourable,
        "most_adverse_ELL1_non6": most_adverse,
        "assignments_eliminating_or_reversing": eliminating,
        "conclusion_mechanical": (
            "even the most extreme admissible configuration (all 39 excluded "
            "ELL essays scored 6, all 428 excluded non-ELL essays scored 1) "
            f"moves the weighted conditional mean difference from {base:.4f} "
            f"to {most_favourable}, "
            + ("which does NOT eliminate the deficit; no configuration of "
               "unobserved scores within 1-6 can produce a non-negative "
               "difference" if not eliminating else
               "and some extreme configurations can eliminate it (see list)")),
    }

    out = ROOT / "results" / "posthoc_exclusion_audit.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=False))
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("exclusion_by_stratum",)}, indent=2)[:6000])
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
