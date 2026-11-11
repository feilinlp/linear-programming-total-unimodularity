# E1 rerun with the shared pinned versions

This folder holds a verification rerun of E1, made on 12 November 2026 to check that the saved results in [`../`](../) do not depend on the solver version. It does not replace them: the report's numbers come from the original run.

| | Original run (`../metadata.json`) | This rerun (`metadata.json`) |
|---|---|---|
| Date (UTC) | 2026-11-01 | 2026-11-11 (12 November, Singapore time) |
| Platform | Linux x86_64 | macOS arm64 |
| Python | 3.12.14 | 3.13.9 |
| NumPy | 2.3.5 | 2.5.4 |
| SciPy | 1.17.0 | 1.18.1 |
| HiGHS (bundled with SciPy) | 1.8.0 | 1.12.0 |

Command, from `experiments/E1` in an environment built from `requirements.txt`:

```
python3 e1.py --output results/rerun-pinned-2026-11-12
```

The graph dataset (`data/graphs.jsonl`, SHA-256 in `metadata.json`) and every solver option were the same.

## Comparison of `results.csv`, row by row (1,012 instances: 1,000 random graphs and 12 controls)

| Columns | Rows that differ |
|---|---|
| `lp_value`, `ilp_value`, `exact`, `lp_integral`, `category`, `half_count`, `gap_additive`, `gap_ratio`, `rounded_size`, `lp_iterations`, `brute_force_optimum`, and all graph columns | 0 |
| `mip_nodes` (B&B node count) | 114 |
| `mip_dual_bound` | 229, all by at most 2.5e-11 (floating-point rounding) |
| `mip_gap` | 9, all by at most 2.1e-15 (floating-point rounding) |
| `lp_ms`, `ilp_ms` (timings) | all, as expected |

So every value the report uses (exactness, integrality, half-integral coordinates, ratios and the selected simplex vertex's classification) is identical under the pinned versions. Only B&B node counts, which the report does not use, changed with the HiGHS version.
