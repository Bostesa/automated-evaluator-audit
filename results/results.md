# OffCriterion: synthetic validation results

Null hypothesis under test: `H0: S _||_ A | Z`. Significance level alpha = 0.05.

## Table 1. Rejection rates at n = 2000

| Scenario            | Null              | Proposed (cond. G^2) | Mean disparity       | Regression LRT       | Marginal t-test*     | Regression F (asymp.) |
|---------------------|-------------------|----------------------|----------------------|----------------------|----------------------|-----------------------|
| conditional_null    | H0 true           | 0.046 [0.035, 0.061] | 0.056 [0.043, 0.072] | 0.055 [0.042, 0.071] | 1.000 [0.996, 1.000] | 0.055 [0.042, 0.071]  |
| mean_dependence     | H0 false          | 0.907 [0.887, 0.923] | 0.998 [0.993, 0.999] | 0.999 [0.994, 1.000] | 1.000 [0.996, 1.000] | 0.999 [0.994, 1.000]  |
| variance_only       | H0 false          | 1.000 [0.996, 1.000] | 0.048 [0.036, 0.063] | 0.044 [0.033, 0.059] | 1.000 [0.996, 1.000] | 0.045 [0.034, 0.060]  |
| shape_only          | H0 false          | 0.705 [0.676, 0.732] | 0.044 [0.033, 0.059] | 0.051 [0.039, 0.066] | 1.000 [0.996, 1.000] | 0.052 [0.040, 0.068]  |
| confounded_observed | H0 true           | 0.048 [0.036, 0.063] | 0.051 [0.039, 0.066] | 0.046 [0.035, 0.061] | 1.000 [0.996, 1.000] | 0.044 [0.033, 0.059]  |
| confounded_proxy    | H0 not guaranteed | 0.991 [0.983, 0.995] | 1.000 [0.996, 1.000] | 1.000 [0.996, 1.000] | 1.000 [0.996, 1.000] | 1.000 [0.996, 1.000]  |

Empirical rejection rates at alpha = 0.05 over 1000 replicates, n = 2000. Brackets give Wilson 95% intervals.

* The marginal t-test conditions on nothing and therefore tests S _||_ A, not the audit
  null S _||_ A | Z. Its rejections in the conditional-null scenarios are correct answers
  to a different question, not Type I errors of the audit. It is shown to make the cost of
  skipping the conditioning step visible.

## Table 2. Rejection rates by sample size

| Scenario            | n    | Proposed (cond. G^2) | Mean disparity | Regression LRT | Marginal t-test* | Regression F (asymp.) |
|---------------------|------|----------------------|----------------|----------------|------------------|-----------------------|
| conditional_null    | 200  | 0.056                | 0.053          | 0.048          | 0.995            | 0.054                 |
| conditional_null    | 500  | 0.049                | 0.042          | 0.041          | 1.000            | 0.039                 |
| conditional_null    | 2000 | 0.046                | 0.056          | 0.055          | 1.000            | 0.055                 |
| mean_dependence     | 200  | 0.142                | 0.224          | 0.230          | 1.000            | 0.234                 |
| mean_dependence     | 500  | 0.254                | 0.566          | 0.601          | 1.000            | 0.593                 |
| mean_dependence     | 2000 | 0.907                | 0.998          | 0.999          | 1.000            | 0.999                 |
| variance_only       | 200  | 0.285                | 0.050          | 0.047          | 0.972            | 0.050                 |
| variance_only       | 500  | 0.788                | 0.048          | 0.045          | 1.000            | 0.046                 |
| variance_only       | 2000 | 1.000                | 0.048          | 0.044          | 1.000            | 0.045                 |
| shape_only          | 200  | 0.095                | 0.047          | 0.054          | 0.997            | 0.056                 |
| shape_only          | 500  | 0.162                | 0.046          | 0.047          | 1.000            | 0.049                 |
| shape_only          | 2000 | 0.705                | 0.044          | 0.051          | 1.000            | 0.052                 |
| confounded_observed | 200  | 0.037                | 0.047          | 0.042          | 0.993            | 0.046                 |
| confounded_observed | 500  | 0.035                | 0.037          | 0.043          | 1.000            | 0.043                 |
| confounded_observed | 2000 | 0.048                | 0.051          | 0.046          | 1.000            | 0.044                 |
| confounded_proxy    | 200  | 0.189                | 0.393          | 0.394          | 0.996            | 0.386                 |
| confounded_proxy    | 500  | 0.425                | 0.837          | 0.842          | 1.000            | 0.844                 |
| confounded_proxy    | 2000 | 0.991                | 1.000          | 1.000          | 1.000            | 1.000                 |

Empirical rejection rates at alpha = 0.05 by sample size.
