# E2 results

The correctness suite and benchmark have completed.
Measurements and completion summaries are here; interpretation and figures are in
[../analysis/](../analysis/).

- [checks.txt](checks.txt): all three methods passed 512 binary 3x3 inputs and 12 analytical controls.
- [main_run/results.md](main_run/results.md): full dataset completion tables.
- [Analysis report](../analysis/analysis.md): scaling figures, property comparisons and paired analysis.
- [../analysis/scaling.csv](../analysis/scaling.csv): parameter-cell completion and timings.
- [../analysis/paired.csv](../analysis/paired.csv): method comparisons on identical completed inputs.
- [../analysis/figures/](../analysis/figures/): PNG/PDF figures for the report.
- [main_run/results.csv](main_run/results.csv): all 3,060 attempts, including 1,011 timeouts.
- [main_run/summary.csv](main_run/summary.csv): per-input medians only when all repetitions completed.
- [main_run/measurements.jsonl](main_run/measurements.jsonl): witnesses and raw CMR logs.
- [main_run/metadata.json](main_run/metadata.json): versions, build details, hashes and parameters.

Full run: 340 matrices, three methods, three repetitions, one-second wall limit
per invocation. All 2,049 completed decisions were correct. CMR completed every
input on every repetition. Read ../README.md for interpretation and timing limits.

The preliminary pilot passed all 108 control invocations. Its local outputs are
ignored by Git because the same controls are included in the full benchmark.

The main run folder was renamed from `full/` to `main_run/`. Historical
invocation paths in metadata are retained exactly as recorded.
