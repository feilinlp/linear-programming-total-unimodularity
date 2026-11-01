# E1: Is TU necessary?

Code: [e1.py](e1.py). Inputs: [data/graphs.jsonl](data/graphs.jsonl).
Results: [results/results.md](results/results.md) and [results/results.csv](results/results.csv).

This follows E3's structure: one script, one README, pinned requirements,
a data folder and a results folder. Equations use ordinary text and code
blocks, so no LaTeX renderer is required.

## 1. Question

Total unimodularity (TU) guarantees integral vertices when the right-hand
side is integral. Does a particular LP need a TU matrix to have the same
optimum as its integer version?

We use the project's unit-cost vertex cover model. A cover selects at least
one endpoint of every edge. Here n is the number of vertices and m the number
of edges. The variable x_v indicates whether vertex v is selected.

```text
Minimise:     sum of x_v over all vertices v
Subject to:  x_u + x_v >= 1, for every edge {u,v}

ILP:         x_v is either 0 or 1
LP:          0 <= x_v <= 1
```

The LP permits every integer cover and additional fractional solutions, so
`OPT_LP <= OPT_ILP`. The relaxation is **exact** when these values agree.

Let A be the unsigned edge–vertex incidence matrix: one row per edge and
one column per vertex, with 1 at each endpoint. The constraints are
`Ax >= 1`. This A is TU if and only if the graph is bipartite.
Every non-bipartite random graph therefore supplies a non-TU instance.

## 2. Prediction and important distinctions

TU is sufficient, but is not necessary for **one objective and right-hand
side** to be exact. We measure these statements separately:

| Measurement | Meaning |
|---|---|
| Exact value | OPT_LP = OPT_ILP; an integral LP optimum exists |
| Integral returned answer | The particular simplex vector contains only 0 and 1 |

An integral LP answer must be exact: it is an integer-feasible solution that
already attains the LP lower bound. The converse can fail because different
optimal vertices can tie, including both integral and fractional ones.

**Example: a square with a diagonal.** Use cycle edges 01, 12, 23, 30 and
diagonal 02. Triangle 012 makes A non-TU. However, disjoint edges 01 and 23
give a lower bound of 2, and cover {0,2} attains 2.

```text
Integral optimum:    (1, 0, 1, 0)           cost = 2
Fractional optimum:  (1/2, 1/2, 1/2, 1/2)   cost = 2
LP optimum = ILP optimum = 2
```

The all-half vector is itself a vertex here: the three tight triangle
equations force its first three coordinates to 1/2, and a tight edge to
vertex 3 fixes the fourth. Even simplex can select a fractional answer
on an exact non-TU instance.

An integer-valued LP objective also does not establish exactness. Two
disjoint triangles have LP optimum 3 and ILP optimum 4.

## 3. Instances

| Setting | Supplied run |
|---|---|
| Distribution | Independent Erdos–Renyi G(n,p) draws, conditional on non-bipartiteness |
| Number of vertices n | 10, 20, 40, 60 |
| Edge probability p | 0.05, 0.10, 0.20, 0.40, 0.70 |
| Accepted graphs per (n,p) | 50 |
| Total random graphs | 1,000 |
| Master seed | 20261102 |
| Vertex costs | All 1 |
| Connectedness filter | None; disconnected graphs and isolates retained |

Include each unordered vertex pair independently with probability p.
Reject bipartite graphs and retain the first 50 accepted draws per cell.
Each cell uses seed + 1000003 * n_index + 10007 * p_index, with zero-based
positions in the parameter lists. Abort after 1,000,000 proposals per cell.

This is rejection sampling from G(n,p) conditional on non-bipartiteness,
not uniform sampling over all non-bipartite graphs. Repeated graphs are
allowed: these are independent draws with replacement. For example,
n=10, p=0.05 required 3,015 proposals to obtain 50 accepted graphs.

There are 12 analytical controls: C3/C4, C5/C6, a square with a diagonal,
a triangle with one leaf, a triangle with a leaf at every vertex, two
disjoint triangles, K4/K8, a triangle with an isolate, and an edgeless graph.
Their objective values are independently known. Controls are excluded
from the random-graph percentages.

**Saved inputs.** The first line of data/graphs.jsonl records the parameters.
Each subsequent JSON line records a graph, its full edge list, vertex count,
and, for random graphs, its cell seed and accepted proposal number.
The explicit vertex count preserves isolated vertices.

## 4. Method

Like E3, we use HiGHS. E1 accesses it through SciPy, which the project brief
also permits. Standard-library code handles random graphs and bipartiteness;
the only dependencies are NumPy and SciPy.

| Model | Configuration |
|---|---|
| LP | linprog(method="highs-ds"): dual simplex; presolve off; primal/dual feasibility tolerances 1e-8 |
| ILP | milp: integer variables bounded by 0 and 1; presolve on; relative MIP gap 0; 30-second time limit |

For the LP, SciPy expects inequalities in the opposite direction, so the
script passes -Ax <= -1. The ILP accepts 1 <= Ax <= infinity. Its integer
variable types and [0,1] bounds together make the variables binary.

LP presolve is disabled to observe the vertex chosen by simplex itself.
Presolve can change which optimum is returned. ILP presolve remains on
because it supplies an independent optimal-value baseline.

**Checks on every instance:**

- Both solvers must report optimality. An unfinished solve aborts and is
  never silently excluded from the sample.
- Both vectors must satisfy the original edges and bounds. The ILP vector
  must be integral, with its final MIP bound equal to its objective within 1e-6.
- The LP vector must be half-integral within tolerance. Its coordinates and
  dual multipliers are reconstructed as rational numbers. Primal and dual
  feasibility and equality of objectives are then checked exactly.
- Every non-bipartite graph must supply a valid odd cycle. Exact integer
  arithmetic checks that its incidence determinant has magnitude 2.
- For n <= 12, exhaustive vertex-cover enumeration checks the ILP optimum.
- Selecting all LP coordinates at least 1/2 must give a cover of size no
  greater than twice the LP optimum.

The bounded LP's dual includes multipliers for the upper bounds:

```text
Maximise:     sum of y_e - sum of z_v
Subject to:  sum of y_e over edges incident to v - z_v <= 1, for each v
             y_e >= 0; z_v >= 0
```

There is one y per edge and one z per upper bound x_v <= 1. A feasible dual
vector gives a lower bound on every feasible primal cost; equality proves
LP optimality. On positive-gap instances, integer optimality relies on
HiGHS's completed MIP solve and numerical bound checks. The saved files
are not formal MIP proof traces.

**Metrics:** exactness; returned-vector integrality; half-coordinate count;
additive gap OPT_ILP - OPT_LP; ratio OPT_ILP / OPT_LP; structural and solver
diagnostics. The ratio is undefined for the edgeless control and is blank
in CSV. Classification uses reconstructed exact LP values and integer
cover sizes, rather than a loose objective comparison.

Per-cell summaries include 95% Wilson intervals for exactness. Zero exact
cases out of 50 has an upper endpoint of about 7.1%; it does not prove that
exactness is impossible in that cell.

## 5. Results

From the supplied measured run; full tables are in
[results/results.md](results/results.md).

| Outcome among 1,000 random graphs | Count | Share |
|---|---:|---:|
| Exact value, integral simplex vector | 242 | 24.2% |
| Exact value, fractional simplex vector | 46 | 4.6% |
| Positive LP–ILP gap | 712 | 71.2% |
| All exact values | 288 | 28.8% |

Exact-value rates depend strongly on the parameter cell:

| n | p=0.05 | p=0.10 | p=0.20 | p=0.40 | p=0.70 |
|---:|---:|---:|---:|---:|---:|
| 10 | 64% | 78% | 66% | 42% | 0% |
| 20 | 68% | 84% | 22% | 0% | 0% |
| 40 | 92% | 18% | 0% | 0% | 0% |
| 60 | 42% | 0% | 0% | 0% | 0% |

At n=10, p=0.40, 21 graphs were exact but only 12 returned integral vectors.
At n=40, p=0.05, 46 were exact but only 43 returned integral vectors.
These examples demonstrate why both measurements are necessary.

All fractional simplex coordinates were 1/2. The largest observed random
ratio was 55/30, approximately 1.8333. At n=60, p=0.70, the mean ratio was
1.8220. These are measured sample values, not universal worst-case claims.

The pooled 28.8% weights the 20 chosen cells equally. It is not the
probability that an arbitrary non-bipartite graph is exact.

## 6. Why the results agree with theory

**TU versus one exact instance.** TU guarantees integral vertices for every
integral right-hand side. E1 fixes both the covering RHS and the unit-cost
objective. A non-TU matrix can succeed for this particular choice without
satisfying the universal guarantee. The diamond is an explicit example.

**Why odd cycles reject TU.** An odd cycle supplies a square incidence
submatrix with determinant magnitude 2. Additional edges do not change
the selected cycle-edge rows. This is a graph-specific test, not a general
TU recogniser.

**Why halves appear.** This proof goes beyond the lectures. At a vertex,
look at tight edge constraints joining fractional coordinates. If a
component of this tight-edge graph were bipartite, increase one colour
class slightly and decrease the other. This preserves all tight sums;
the opposite perturbation is also feasible for a sufficiently small
change. The original point would be a midpoint, contradicting that it is
a vertex. Every such component therefore contains an odd cycle. Along
tight edges, values alternate between a and 1-a; an odd cycle forces
a=1/2. Thus every vertex coordinate is 0, 1/2 or 1. This does not restrict
arbitrary nonvertex optima, such as some of E3's IPM outputs.

**Why large gaps occur.** In a complete graph on n>=3 vertices, adding
the edge inequalities gives LP optimum n/2, attained by all-half. An
integer cover needs n-1 vertices, so its ratio is 2-2/n, approaching 2.
This illustrates a possible large-gap pattern without claiming that the
gap or exactness changes monotonically with edge density.

**Connection to E3.** E1 can return a fractional optimal vertex because
its matrix is non-TU. E3 uses TU matrices: its fractional no-crossover IPM
outputs can lie between integral optimal vertices. The experiments test
different limitations of the integrality guarantee.

## 7. Reproduce and validate

From this directory:

```bash
python -m pip install -r requirements.txt
python e1.py
```

The script loads the saved graphs when data/graphs.jsonl exists. If it is
missing, it generates and saves the default dataset first. To regenerate:

```bash
python e1.py --regenerate
```

For independent small-instance checks, without the full random experiment:

```bash
python e1.py --check
```

This checks all 1,099 simple labelled graphs with one to five vertices
against exhaustive cover and two-colouring searches, then the 12 controls
and the diamond's fractional vertex. Everything is in e1.py; no separate
test directory is needed.

The supplied run used Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0 and bundled
HiGHS 1.8.0. E3's direct highspy build is different. Do not combine their
runtime tables as one benchmark. Exact graph optimum values should agree,
while selected optimal vectors and runtimes can vary with solver version,
ordering and presolve.

Times surround the solver calls: sparse construction and verification are
excluded; SciPy/HiGHS conversion and enabled presolve are included. The
default is one call per model; --repeats 3 instead reports median times.
These timings are diagnostic, not a controlled speed comparison.

## 8. Files and limitations

| Entry | Contents |
|---|---|
| data/ | graphs.jsonl: parameters and all input graphs |
| results/ | results.csv: measurements; results.md: tables; summary.csv: per-cell metrics; solutions.jsonl: rational LP certificates and integer vectors; metadata.json: versions, options and hashes |
| e1.py | Generation, loading, solving, verification, tables and optional self-check |
| README.md | Question, method, findings, theory and reproduction |
| requirements.txt | The two pinned dependencies |

Limitations: unit costs only, one solver family, a finite n/p grid, one seed
and no real-world non-bipartite datasets. LP presolve is off while ILP
presolve is on; these timings do not establish a general speed comparison.
Simplex and MIP have exponential worst-case behaviour. This is not a
polynomial-time algorithm for general vertex cover.

## 9. References and AI assistance

- Nemhauser and Trotter (1975), *Vertex packings: Structural properties and
  algorithms*, Mathematical Programming 8, 232–248.
  [Publisher](https://doi.org/10.1007/BF01580444). Metadata and abstract
  checked; full subscription paper not accessed. Its abstract states the
  half-integrality of basic packing solutions; complementing variables
  connects packing to vertex cover.
- [MIT 15.083J, Lecture 16: Geometry](https://ocw.mit.edu/courses/15-083j-integer-programming-and-combinatorial-optimization-fall-2009/21984f599b1e793a2ce1bfec0fec6bfc_MIT15_083JF09_lec16.pdf),
  page 1: checked for the all-integral-RHS characterisation of TU.
- [SciPy dual simplex](https://docs.scipy.org/doc/scipy-1.17.0/reference/optimize.linprog-highs-ds.html)
  and [MILP documentation](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.milp.html):
  checked for configurations, statuses and bound fields.

Sources were checked on 2 November 2026 to the extent stated above.
Project-required Google Scholar verification remains outstanding because
Scholar could not be retrieved. Complete it before citing historical
papers in the report.

OpenAI Codex assisted with E1 design, code, runs, validation, source checking
and documentation. The group should understand and be able to defend all
code and claims, and include this help in its AI Disclosure. The original
slides, scripts, notes and E3 were not edited.
