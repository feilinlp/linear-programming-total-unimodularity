# E2: How costly is recognising TU?

Code: [e2.py](e2.py). Inputs: [data/manifest.json](data/manifest.json).
Results: [results/](results/).

Status: **correctness checks and full benchmark completed.**
Measured results: [results/main_run/results.md](results/main_run/results.md).
Raw measurements: [results/main_run/results.csv](results/main_run/results.csv).
Scaling figures and paired comparisons: [analysis/analysis.md](analysis/analysis.md).

Where to look:

```text
e2.py                  generate inputs, check recognisers, run benchmarks
summarise.py           completion counts and per-input timing summaries
analyse.py             scaling, paired comparisons and figures
data/                  340 inputs and manifest
results/
  checks.txt           completed correctness checks
  main_run/            measured repetitions, metadata and completion summary
analysis/
  analysis.md          interpreted results and property comparisons
  *.csv                derived scaling and paired tables
  figures/             PNG previews and PDF report figures
```

The preliminary `results/pilot/`, Python caches and local `.venv/` directories
are ignored by Git. Source code, inputs, main measurements, metadata and report
figures remain included. The two scripts have separate roles: `summarise.py`
produces measurement summaries, while `analyse.py` produces interpretation.

## 1. Question

Compare exact determinant enumeration (`brute`), direct Ghouila-Houri
row-signing enumeration (`gh`) and CMR's default structural recogniser (`cmr`).
A recognition algorithm must accept TU matrices and reject non-TU matrices.
Analyse the two outcomes separately: exhaustive positive decisions need a
complete search, whereas negative decisions can stop at an obstruction.
Observed curves illustrate behaviour on these families; they do not prove
complexity bounds. Python enumeration versus compiled CMR also compares
implementations, not just abstract algorithms.

## 2. Prediction and important distinctions

The exhaustive methods have exponential worst-case search spaces, while CMR
uses structural recognition. We expect CMR to handle larger inputs, but any
method may be fastest on small instances. This is a prediction, not a measured
finding. Both positive and negative decisions are part of the comparison.

- TU instances require the exhaustive methods to finish their searches.
- Non-TU instances can reject early; obstruction size and ordering can matter.
- Block sums test whether separable structure changes recognition time.
- Transformed pairs must preserve the answer, though their runtimes may differ.

## 3. Instances

The data is split by property into eight family files, with a small manifest:

```text
data/
  manifest.json             seeds, counts and file hashes
  even_cycle.json           sparse TU scaling
  odd_cycle.json            growing non-TU obstruction
  bipartite.json            graph size and density
  interval.json             consecutive-ones structure and interval lengths
  embedded_triangle.json    small obstruction in a growing matrix
  block_cycles.json         separability / 1-sum structure
  control.json              analytical correctness controls
  transformed.json          paired representation checks
```

Each family file contains a `matrices` array. It stores actual entries, dimensions (including isolated graph vertices),
nonzero counts, expected TU labels, parameters and available witnesses.
Mathematical justifications are documented here rather than repeated in each record.
All row/column and witness indices are zero-based. Master seed: 20261108.
Matrix rows are displayed on separate lines for readability. The runner loads
all family files through `manifest.json`, verifies their hashes, and preserves
the original IDs and parent relationships. All 340 matrices are unchanged.
`--data` accepts the dataset directory or its manifest. Use `--family` to choose
a subset for a run; do not pass an individual family file as the complete dataset.

| Family | Count | Settings | Known answer / property |
|---|---:|---|---|
| even_cycle | 10 | orders 4,6,8,10,12,16,24,40,80,160 | TU; sparse scaling |
| odd_cycle | 10 | orders 3,5,7,9,11,15,23,39,79,159 | non-TU; full determinant magnitude 2 |
| bipartite | 120 | 8,12,20,40,80,160 vertices; p=0.2,0.6; ten draws/cell | TU; size and edge density |
| interval | 120 | square orders 4,6,8,10,16,32; short/long intervals; ten draws/cell | TU; consecutive ones in each column |
| embedded_triangle | 6 | orders 7,11,19,35,67,131 | non-TU; C3 block plus even-cycle block |
| block_cycles | 22 | total orders 8,12,16,24,32,48,64,96; 1,2,4 equal even-cycle blocks when valid | TU; 1-sum structure at fixed order/nonzeros |
| control | 12 | zero, identity, signed rank-one, entry ±2 and signed determinant-2 examples | nine TU, three non-TU |
| transformed | 40 | eight originals, five variants each | same answer as parent |

There are **300 main inputs and 40 transformed inputs**. For bipartite graphs,
include each cross-partition edge independently with probability p; retain
isolates/disconnected graphs and repeated draws. Every edge becomes a row
with two ones. Dimensions are number of edges by number of vertices.

For an order n interval matrix, independently choose each column's interval
length uniformly from 1..max(1,floor(n/4)) (short), or ceil(n/2)..n (long),
then choose a valid starting row uniformly. Intervals are saved as half-open
[start,stop) pairs. These distributions are not uniform over all TU matrices.

Block matrices hold dimensions and nonzero count fixed while varying the
number of cycle components. They test 1-sum structure; they do not exercise
general 2-/3-sum decomposition. Default CMR may use fast recognition paths;
do not claim it used a particular decomposition without separate evidence.

The embedded triangle is initially at the leading corner, deliberately easy
for increasing-order minor enumeration. Permuted variants examine placement.
Odd cycles give contrasting large obstructions: proper square minors are TU.

Select the first and middle input from each of bipartite, interval,
embedded_triangle and block_cycles, then create transpose, two permutations,
sign flips and combined permutation/sign flips. Exact transformations and
parent IDs are saved. Analyse these as paired comparisons, not independent draws.

## 4. Method

Brute force first rejects entries outside {-1,0,1}, then enumerates minors
by increasing order, row combination, column combination. Bareiss elimination
uses arbitrary-precision Python integers and exact division.

GH first rejects out-of-range entries and transposes to minimise the number
of enumerated rows. For every nonempty subset, it tries signings until one
has all column sums in {-1,0,1}. Fixing its first sign to +1 removes globally
negated duplicates. If no signing works, reject. This is straightforward
Python enumeration, not CMR's optimised GH implementation. It recomputes sums;
do not attribute the optimised library's complexity constant to this code.

`check` verifies shapes, nonzero counts, family constructions, saved negative
witness determinants and transformed-parent relationships. It compares brute
force and GH on all 512 binary 3x3 matrices, plus signed/out-of-range controls.
With `--with-cmr`, CMR must agree too. The exhaustive binary reference uses
Leibniz determinants, independent of Bareiss. Returned Python negative
certificates are checked outside timing. For large positives, confidence comes
from construction properties and cross-method agreement, not formal proof traces.

### Timing and outputs


Each call runs in a fresh subprocess, with an external wall-clock timeout.
This bounds even a single costly determinant/signing search. All methods'
`wall_seconds` include process startup, stdin transfer, parsing, execution and
output. Python `algorithm_seconds` includes its entry scan, enumeration and
counters, but excludes startup/JSON parsing. CMR raw stats are retained without
assuming a version-specific internal timing format. **Do not compare Python
algorithm_seconds directly with CMR wall_seconds as though scopes match.**
A startup advantage at tiny sizes is part of the end-to-end comparison only.

Generation, construction validation and post-run certificate checking are
outside timing. Method order is seeded and shuffled for each input/repetition.
No warm-up calls are made; report this and retain every repetition. Medians
are meaningful for completed repetitions; mixed completion/timeout cases
need explicit censoring, not a median formed by treating time limits as successful solves.

Benchmark outputs in each run directory under `results/`:

- `results.csv`: dimensions, expected/observed decision, status, times and counters.
- `measurements.jsonl`: full records, Python witnesses and CMR logs.
- `summary.csv` and `results.md`: generated afterward by `summarise.py`.
- `metadata.json`: input/source/binary hashes, environment, invocation options,
  selected input IDs and user-supplied CMR build note.

Analysis outputs are kept separately in `analysis/`: `analysis.md`, `scaling.csv`,
`paired.csv`, `transformed_pairs.csv`, `analysis_metadata.json` and `figures/`.
`analyse.py` writes there by default; use `--output` for another analysis directory.

Timeout decisions are unknown; counters from killed processes are unavailable.
Errors and incorrect decisions are saved and stop the run. Report completion
rates separately from completed runtimes. For random cells, show instance-level
spread; repetitions of one instance are timing repeats, not new data points.

## 5. Results

All 512 binary 3x3 inputs and twelve analytical controls passed with all three
methods; see [results/checks.txt](results/checks.txt). The twelve-control pilot
completed all 108 invocations.

The full run tested all 340 saved inputs, with three repetitions per method
and a **one-second wall-clock limit per invocation**, for 3,060 attempts.
The run took approximately 19 minutes. This explicitly overrides the runner's
five-second default to keep the complete benchmark manageable.

| Method | Completed / attempts | Timeouts | Inputs completed on all three repetitions |
|---|---:|---:|---:|
| Brute force | 480 / 1,020 | 540 | 160 / 340 |
| Ghouila-Houri | 549 / 1,020 | 471 | 183 / 340 |
| CMR | 1,020 / 1,020 | 0 | 340 / 340 |

**No completed decision disagreed with its known answer.** Timeouts are unknown
decisions, not incorrect answers. The pooled completion shares describe this
chosen dataset, not a probability over arbitrary matrices.

### Findings and connection to theory

- On even cycles, brute force completed through order 10, but timed out from
  the tested order 12 onward. GH completed through order 12 and timed out from
  order 16 onward. CMR completed all tested orders, through 160.
- On odd cycles, brute force completed through order 9, GH through order 11,
  and CMR through order 159. These non-TU inputs have no smaller violating
  minor, so exhaustive determinant search cannot reject on a small obstruction.
- In contrast, GH rejected every embedded-triangle input, including order 131.
  Brute force completed through order 35 but timed out at 67 and 131: even a
  small obstruction can be costly when all smaller minor orders are searched
  first. Non-TU recognition time depends on obstruction structure and ordering.
- All transformed cases that finished retained their parent's expected answer.
  CMR completed every transformed case; exhaustive timeouts remain inconclusive.
- CMR had the lowest end-to-end median on every input. The predicted possible
  small-input advantage for brute force did not occur with this invocation
  setup. Python worker startup is substantial, so this is not evidence that
  CMR's recognition kernel always performs less work on tiny matrices.

### Paired comparisons and input properties

The complete tables and figures are in [analysis.md](analysis/analysis.md).
They aggregate each input's three-repetition median, then give every input in
its parameter cell equal weight. A cell median is omitted when any input did
not finish all repetitions; ranges show input variation, not confidence intervals.

- Across the 160 inputs where both exhaustive methods finished, GH had the
  lower algorithm-time median on 151, brute force on 8, with one tie. The median
  brute/GH algorithm-time ratio was 13.937. Excluding transformed copies gives
  124 GH wins, 8 brute-force wins and one tie on 133 common main inputs, with
  median ratio 10.449. These comparisons exclude Python worker startup and
  input/output; the former wall-time ratio of 1.060 largely hid this difference.
  Comparisons against CMR retain wall time. No speed ratio is imputed for timeouts.
- At 12 graph vertices, GH's median across ten input medians was 43.9 ms at
  p=0.2 and 559.6 ms at p=0.6. Brute force completed 7/10 versus 0/10 inputs.
  Increasing p changes both density and the number of matrix rows, so this
  does not isolate density at fixed dimensions.
- At interval order 10, brute-force cell medians were 592.4 ms for short and
  831.0 ms for long intervals. All inputs finished. GH gave 54.8 versus 52.0 ms,
  so longer intervals did not uniformly slow every method. Dimensions are
  fixed here; nonzero count and determinant/signing work can change.
- CMR was faster with two blocks than one at 5/8 matched orders, and with four
  blocks than one at 2/6 matched orders. This is not a consistent block benefit.
  CMR block timings are only a few milliseconds, and each block configuration
  has one matrix with three timing repetitions. The data does not establish a
  decomposition speedup or identify CMR's internal recognition path.

The cycle/obstruction figure addresses scaling, the random-family figure
compares density and interval settings, and the block figure holds dimensions
and nonzeros fixed. Each figure includes wall-time panels for all methods and
algorithm-time panels for brute force and GH, revealing scaling below the
Python startup floor. Algorithm panels omit CMR because no comparable internal
time was saved. Timeout markers indicate the external wall-clock limit, not
measured algorithm times or algorithm-time lower bounds. Controls and transformed-pair details are supporting
validation and can go in an appendix rather than the main report.

These results agree with the expected practical advantage of structural
recognition over exhaustive search on growing inputs. They do not prove
asymptotic bounds, establish general superiority of one language-independent
algorithm, or show that CMR needed a nontrivial Seymour decomposition.

Per-family completion tables are in [results/main_run/results.md](results/main_run/results.md).
Per-input medians are in [results/main_run/summary.csv](results/main_run/summary.csv);
raw repetitions and search counters remain in the CSV/JSONL files.

## 6. Reproduce and validate

From this directory, using Python 3.10 or later:

```bash
# First: dataset checks, 512 binary 3x3 matrices and twelve controls.
python3 e2.py check

# Include CMR in the correctness suite after building it.
python3 e2.py check --with-cmr --cmr /absolute/path/to/cmr-tu

# Reproduce the twelve-control pilot in a fresh directory.
python3 e2.py run --family control --cmr /absolute/path/to/cmr-tu --time-limit 1 --output results/new-pilot

# Pilot on small inputs across families.
python3 e2.py run --max-dimension 8 --cmr /absolute/path/to/cmr-tu --output results/small

# Full benchmark. Set the CMR build note to the actual commit/compiler/build.
python3 e2.py run --cmr /absolute/path/to/cmr-tu --cmr-build-note 'COMMIT; COMPILER; Release' --time-limit 1 --output results/new-full
```

To run Python methods before installing CMR:

```bash
python3 e2.py run --family control --methods brute gh --output results/python-pilot
```

For example, run just the two cycle families with:

```bash
python3 e2.py run --family even_cycle odd_cycle --cmr /absolute/path/to/cmr-tu --output results/cycles
```

Use `--ids even_cycle_000 odd_cycle_000` for specific inputs; `--family` accepts
multiple names. `--max-dimension` limits max(rows,columns), not graph vertices.
`--repeats` defaults to 3 and `--time-limit` to 5 seconds per invocation.
Every selected input/method/repetition is attempted; there is no automatic
skipping of later sizes. At 340 inputs and three methods/repeats, there are
3,060 attempts. The full run can take hours if many calls time out. Start with
the pilots, choose a feasible final budget, and document any changed selection.
Do not repeatedly reuse a full run's directory: the runner refuses to overwrite
measurements. Partial outputs remain available after interruption or failure.

To regenerate inputs intentionally (not needed to run existing inputs):

```bash
python3 e2.py generate --force
```

This command only constructs inputs; it never calls a TU recogniser.

### CMR prerequisite


CMR is a separate C/C++ library, not a pip dependency. Obtain the official
source, record its commit, and follow its build instructions with Release
optimisation. Supply the resulting cmr-tu executable with `--cmr`.
For this run, CMR 1.4.0 was built in `/private/tmp/e2-cmr-build` from commit
`0c42a44deb8262a1f2a400add5d6be80e90eda3c`, using Apple clang 21.0.0, Release
optimisation, static CMR and Homebrew GMP. Build paths are temporary.
On this machine the build also needed `-I/opt/homebrew/include`.

To rebuild the exact measured CMR version in a fresh source directory on this
Apple Silicon setup (GMP is installed under `/opt/homebrew`):

```bash
git clone https://github.com/discopt/cmr.git /tmp/e2-cmr-source
git -C /tmp/e2-cmr-source checkout 0c42a44deb8262a1f2a400add5d6be80e90eda3c
cmake -S /tmp/e2-cmr-source -B /tmp/e2-cmr-build -DCMAKE_BUILD_TYPE=Release -DTESTS=OFF -DGMP=ON -DSHARED=OFF -DCMAKE_PREFIX_PATH=/opt/homebrew -DCMAKE_C_FLAGS=-I/opt/homebrew/include -DCMAKE_CXX_FLAGS=-I/opt/homebrew/include -DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON
cmake --build /tmp/e2-cmr-build --target cmr_tu -j 4
```

Then use `--cmr /tmp/e2-cmr-build/cmr-tu`. On other systems, adjust GMP paths
and compiler flags; record the actual configuration. The CMR binary itself is
not committed. The saved inputs and measurements do not depend on retaining
the original temporary build directory.

- Official build instructions: https://discopt.github.io/cmr/build.html
- Recognition options: https://discopt.github.io/cmr/tu.html
- Dense input format: https://discopt.github.io/cmr/file-formats.html

The runner sends dense input on stdin and explicitly selects decomposition:
`cmr-tu - --algo decomposition --stats --time-limit 5`.
It recognises the exact decision messages from the official CLI source:
https://github.com/discopt/cmr/blob/master/src/main/tu_main.c
CMR 1.4's stderr rejection for entries outside {-1,0,1} is also parsed and its
reported entry checked against the input. An unfamiliar message is an error,
not a guessed decision. Raw stdout/stderr
and return codes are saved for completed CMR invocations. No decomposition
or minimal-witness output is requested in timed runs, since producing these
can change the work done. CMR's reported decision is checked against the
known construction label; no independent CMR certificate is claimed.


To summarise a completed run without rerunning recognition:

```bash
python3 summarise.py results/main_run
python3 analyse.py results/main_run
```

To regenerate the report figures as well, install the optional pinned analysis
packages in a separate environment (tested with Python 3.14):

```bash
python3 -m venv /tmp/e2-analysis
/tmp/e2-analysis/bin/python -m pip install -r requirements-analysis.txt
/tmp/e2-analysis/bin/python analyse.py results/main_run --plots
```

Neither analysis command calls a recogniser. `analyse.py` checks the raw result
hash, dataset hashes and all planned repetitions before producing tables.
The summary rejects missing or duplicate repetitions too. A table-only refresh
retains existing figure links only when the recorded raw-data and analysis-code
hashes match.
It records the analysis code hashes and plotting version separately from the
original benchmark metadata. Figures include PNG previews and vector PDFs.

## 7. Files and limitations

- `e2.py`: deterministic generation, exact recognisers, correctness checks and runner.
- `summarise.py`: completion tables and uncensored per-input medians.
- `analyse.py`: verified-data scaling tables, paired comparisons and optional figures.
- `requirements-analysis.txt`: optional pinned plotting environment.
- `data/*.json`: family inputs and manifest; no solver outputs.
- `results/`: correctness log, measurements, run metadata and completion summaries.
- `analysis/`: interpretation, property/paired tables and report figures.
- `requirements.txt`: no third-party Python packages required.

Only structured synthetic families are included; results are not a general
worst-case assessment of CMR. Defaults may recognise graph families without
nontrivial Seymour decomposition. Matrix ordering is deliberately fixed within
a family, except the explicit transformed inputs. Random duplicates are retained.

## 8. References and AI assistance

TU family labels rely on bipartite incidence TU, consecutive-ones TU, TU closure
under block sums/transposition/sign changes/permutations, and odd-cycle minors.
Source checks on 8 November 2026:

- Walter and Truemper, *Implementation of a unimodularity test*, Mathematical
  Programming Computation 5 (2013), 57–73, DOI 10.1007/s12532-012-0048-x.
  Bibliographic details checked against the [official CMR documentation](https://discopt.github.io/cmr/tu.html).
  The authors' [2012 arXiv preprint](https://arxiv.org/abs/1202.4061) confirms
  title, authors and the polynomial recognition subject in its abstract.
  This was a metadata/abstract check, not a full-paper proof review.
- The [CMR CLI source at the measured commit](https://github.com/discopt/cmr/blob/0c42a44deb8262a1f2a400add5d6be80e90eda3c/src/main/tu_main.c)
  was inspected for the actual command and output handling. Online CMR docs
  display version 1.3.0; the measured build is 1.4.0 as recorded in metadata.

Google Scholar was attempted but was inaccessible through the research tool.
Project-required Scholar verification and review of historical theorem sources
remain outstanding; no unchecked historical reference is marked verified.

E2 was developed with assistance from OpenAI Codex, guided by the user's
instructions and feedback. This included preparing synthetic inputs,
implementing and running the benchmarks, and analysing and documenting the
saved results. The group remains responsible for checking and understanding
the code, results and claims.
