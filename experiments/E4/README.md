# E4: Generic LP or specialised algorithm?

Owner: P4 (Daryl). Code: [e4.py](e4.py). Full results: [results/results.md](results/results.md) and the CSV files in [results/](results/).

## 1. Question

For a TU problem, Hoffman–Kruskal says the LP relaxation already has an integral optimal vertex, so a simplex solver returns the exact integer answer. **If the LP is exact, should we just use it?** Or are the specialised algorithms from the lectures still the better tool?

E4 runs the same instances through a generic LP solver and through the specialised algorithm for each problem, checks that they agree, and times them. It also looks at shift scheduling, where we compare against a generic ILP solver rather than a specialised algorithm, and at a small change that breaks TU (overnight shifts).

| Part | Problem | LP + TU against | Constraint matrix |
|---|---|---|---|
| A | Max-flow | Edmonds–Karp, Dinic (L6) | directed incidence matrix (TU) |
| B | Bipartite matching (+ vertex cover via König) | Hopcroft–Karp | bipartite incidence matrix (TU) |
| C1 | Shift scheduling, day shifts | generic ILP solver (HiGHS branch-and-bound) | interval matrix, consecutive 1s (TU) |
| C2 | Shift scheduling, overnight shifts | generic ILP solver | circular 1s (not TU) |

## 2. Prediction

| Part | Prediction |
|---|---|
| A, B | Every method reaches the **same optimum**; the LP solution is **integral**; the specialised algorithms are **faster**. |
| B | The vertex cover built from a maximum matching (König) has the same size as the matching, and equals the vertex cover LP optimum (LP duality + TU). |
| C1 | LP optimum = ILP optimum and the LP solution is integral, so the ILP solver needs **no branching**. |
| C2 | The LP **can** be fractional and below the ILP optimum, as in the C₃ example (LP 1.5, ILP 2). |

## 3. Instances

**Generated** with a fixed seed (4234), so a rerun gives identical instances. **Real** graphs are the KONECT bipartite graphs from E3, read directly from [../E3/data](../E3/data) (not copied).

| Part | Family | Sizes | Details |
|---|---|---|---|
| A | Random network (generated) | 100, 1,000, 3,000, 10,000 nodes | about 5 random arcs out of each node; super source joined to 5% of nodes, super sink reached from another 5% |
| A | Grid network (generated) | 10×10, 30×30, 70×70 | arcs both ways between neighbours; source joined to the left column, sink from the right column (image-segmentation shape) |
| A | Capacities | – | uniform random integers 1–100 |
| B | Random bipartite (generated) | 100, 1,000, 10,000 per side | about 3 edges per vertex |
| B | Real (KONECT, from E3) | 868 / 1,380 / 38,741 vertices | Unicode languages, Crime, arXiv cond-mat |
| C1 | Day shifts (generated) | horizons 24 h, 168 h, 672 h; 5 demand profiles each | one row per hour; every shift of 4, 6 or 8 hours that ends inside the horizon; demand uniform 1–20 staff per hour |
| C2 | Overnight shifts (generated) | 200 instances on a 24-hour cycle, plus the C₃ example | same as C1, but shifts may wrap past midnight |

Why the super source and sink in A: with an ordinary node as the source, the max flow is capped by its 5 or so outgoing arcs, and every method finishes almost instantly. Joining the source to many nodes makes the flow (and the work) grow with the network.

## 4. Method

**LP models** (all as in the lectures; m and n here are counts in each model):

```text
Max-flow     max  (flow out of s) - (flow into s)
             s.t. flow in - flow out = 0   at every node other than s, t
                  0 <= f_e <= c_e           for every arc e

Matching     max  sum of x_e
             s.t. sum of x_e over edges e at v <= 1   for every vertex v
                  x_e >= 0

Scheduling   min  sum of x_j                   (number of staff hired)
             s.t. sum of x_j over shifts j covering hour t >= demand_t
                  x_j >= 0                     (integer for the ILP)
```

**Solvers and implementations:**

| Name | What it is |
|---|---|
| LP dual | HiGHS 1.15.1 dual simplex (`solver="simplex"`, `simplex_strategy=1`), default presolve. E3 used the same setting. |
| LP primal | HiGHS primal simplex (`simplex_strategy=4`). Also ends at a vertex. |
| SciPy EK / Dinic | `scipy.sparse.csgraph.maximum_flow(method="edmonds_karp" / "dinic")`, compiled code |
| SciPy HK | `scipy.sparse.csgraph.maximum_bipartite_matching`, Hopcroft–Karp, compiled code |
| nx EK / Dinic / HK | networkx 3.6.1 `edmonds_karp`, `dinitz`, `hopcroft_karp_matching`, pure Python |
| ILP | HiGHS MIP solver (branch-and-bound) with default settings |

We use **both** SciPy and networkx because HiGHS is compiled C++. Comparing it only with pure-Python code would mix up two effects: the algorithm, and the implementation language. SciPy gives a like-for-like (compiled vs compiled) comparison; networkx shows what happens when the specialised algorithm is written in a slow language.

**What we measure:**
- **Optimal value** of every method; the script stops if any two disagree (tolerance 10⁻⁶).
- **Integrality** of the LP solution: largest |x − round(x)|; integral if ≤ 10⁻⁶.
- **Validity**: the LP flow satisfies conservation and capacities; the LP matching uses each vertex at most once; the König cover covers every edge.
- **Runtime**: median of up to 3 runs; a run slower than 2 s is not repeated. In Parts A and B, model building in Python (*LP build*) is timed separately from solving, and for SciPy and networkx only the algorithm call is timed. In Part C, LP and ILP times both include building the model.
- **C1, C2**: ILP optimum, number of branch-and-bound nodes, and (C2) the gap between ILP and LP optimum.

**König cover.** By König's theorem, starting from a maximum matching M, let Z be all vertices reachable from unmatched left vertices by alternating paths (left → right along any edge, right → left along a matching edge). Then (left vertices not in Z) ∪ (right vertices in Z) is a minimum vertex cover. `e4.py` builds it with one breadth-first search. (networkx's `to_vertex_cover` runs a separate search from every vertex, so its time grows roughly with the square of the graph size; it was far too slow on our larger graphs, so we don't use it.)

**Checks built into the script** (it stops if any fails): all methods agree on every instance; both LP variants are integral on every flow and matching instance; the vertex cover LP is integral and equals the matching size; every day-shift LP is integral and equals the ILP optimum; the C₃ example gives LP 1.5 and ILP 2; every overnight LP is ≤ its ILP optimum.

**Reproduce:**

```
pip install -r requirements.txt
python3 e4.py                 # about 75 seconds on an Apple arm64 MacBook Air
python3 e4.py --node-check    # optional, a few seconds: writes results/node_check.csv only
```

Values, integrality, simplex iteration counts and node counts are deterministic. Runtimes, and the ratios between them, vary between machines and runs (see Section 8).

## 5. Results

Copied from the committed [results/results.md](results/results.md) (Daryl's MacBook Air, Apple arm64, Python 3.13.12). **Rerunning `e4.py` overwrites results.md, so if you rerun, update the runtimes in this section to match.** Runtimes are solve times; *LP build* (not shown) was under 5 ms everywhere.

**A. Max-flow**

| Instance | Arcs | Max flow | LP integral? | LP dual | LP primal | SciPy EK | SciPy Dinic | nx EK | nx Dinic |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| random n=100 | 510 | 145 | yes | 2.7 ms | 1.6 ms | 0.1 ms | 0.1 ms | 1.1 ms | 1.9 ms |
| random n=1,000 | 5,100 | 2,283 | yes | 83 ms | 51 ms | 2.8 ms | 1.2 ms | 31 ms | 124 ms |
| random n=3,000 | 15,300 | 7,045 | yes | 498 ms | 497 ms | 57 ms | 3.7 ms | 320 ms | 2.78 s |
| random n=10,000 | 51,000 | 24,757 | yes | 10.13 s | 4.70 s | 576 ms | 15.5 ms | 2.46 s | 19.41 s |
| grid 10×10 | 380 | 211 | yes | 1.6 ms | 1.7 ms | 0.1 ms | 0.1 ms | 4.7 ms | 6.2 ms |
| grid 30×30 | 3,540 | 916 | yes | 29 ms | 21 ms | 2.5 ms | 1.3 ms | 252 ms | 199 ms |
| grid 70×70 | 19,460 | 2,232 | yes | 599 ms | 524 ms | 78 ms | 19 ms | 5.73 s | 3.99 s |

**B. Bipartite matching** ("matching" = max matching = min vertex cover)

| Instance | Edges | Matching | LP integral? | LP dual | LP primal | SciPy HK | nx HK |
|---|---:|---:|---|---:|---:|---:|---:|
| random n=100 per side | 300 | 91 | yes | 1.1 ms | 1.2 ms | < 0.1 ms | 0.5 ms |
| random n=1,000 per side | 3,000 | 923 | yes | 34 ms | 36 ms | 0.4 ms | 12 ms |
| random n=10,000 per side | 30,000 | 9,274 | yes | 1.14 s | 1.13 s | 8.0 ms | 229 ms |
| Unicode languages | 1,255 | 188 | yes | 2.3 ms | 2.3 ms | < 0.1 ms | 0.7 ms |
| Crime | 1,476 | 451 | yes | 3.7 ms | 3.6 ms | 0.1 ms | 2.8 ms |
| arXiv cond-mat | 58,595 | 12,652 | yes | 307 ms | 308 ms | 2.4 ms | 87 ms |

**C1. Day shifts (TU)**: on all 15 instances, LP = ILP, the LP solution was integral, and the ILP solver used 1 node (the root).

| Horizon | Shifts | LP time (incl. build) | ILP time (incl. build) |
|---|---:|---:|---:|
| 24 h | 57 | 0.2 ms | 3.2 ms |
| 168 h | 489 | 1.0 ms | 4.6 ms |
| 672 h | 2,001 | 4.3 ms | 14.3 ms |

**C2. Overnight shifts (not TU)**

- C₃ example: LP = 1.5 with x = (½, ½, ½); ILP = 2.
- 200 random instances: the LP was fractional and strictly below the ILP optimum on **24 (12%)**. The gap was 0.33 to 0.75 staff (median 0.5), and in all 24 cases the ILP optimum was the LP value rounded up.
- The ILP solver still finished at the root node (1 node) on every instance.
- Node check (`--node-check`, presolve and primal heuristics off, its own 200 + 200 random instances plus the C₃ example): the LP was not exact on 16 of 201 overnight instances (including C₃) and on 0 of 200 day-shift instances, and **every** MIP still finished at the root node.

## 6. Highlights

1. **Same answer, every time.** On all 13 flow and matching instances, the LP (both simplex variants), SciPy and networkx agreed on the optimal value, and both LP solutions were integral. On matching, the König cover and the vertex cover LP gave the same number as the matching. This is the "same optimum" prediction, and Hoffman–Kruskal's guarantee in action.

2. **Like for like, the specialised algorithms always win, by up to two to three orders of magnitude.** Against compiled SciPy code, the LP was slower on every instance, but the gap depends on the instance and the simplex variant. In the committed run: on the 10,000-node random network, about 10 s (dual) or 5 s (primal) against about 15 ms for Dinic (about 300–650×); on arXiv cond-mat, about 0.3 s against about 2 ms for Hopcroft–Karp (about 130×); on the grids, only about 13–31× (dual simplex against Dinic). The exact ratios also change between runs and machines.

3. **The gap widens with size.** Going from 1,000 to 10,000 nodes in the random networks (10× bigger), the dual simplex time grew by about two orders of magnitude, while SciPy Dinic grew by about one. Dual simplex pivots grew from 3,364 to 51,576 (deterministic), and each pivot also gets more expensive as the LP grows.

4. **Implementation matters as much as the algorithm.** Pure-Python networkx can lose to the compiled LP: on the 10,000-node network, networkx Dinic was slower than the LP (about 19 s vs 10 s in the committed run), and on the 70×70 grid networkx Edmonds–Karp was roughly 10× slower than the LP. For matching, networkx Hopcroft–Karp still beat the LP (about 0.2 s vs 1.1 s on 10,000 per side). So "specialised is faster" is a statement about algorithms of equal implementation quality.

5. **Dinic vs Edmonds–Karp.** In SciPy, Dinic was more than an order of magnitude faster than Edmonds–Karp on the 10,000-node network (37× in the committed run; 16× in a groupmate's rerun), in line with L6: Dinic augments along a whole blocking flow per phase instead of one shortest path at a time.

6. **Shift scheduling: the LP alone gives the schedule.** With day shifts (TU), the LP was always integral and equal to the ILP optimum, and solving the LP was several times faster than calling the ILP solver (3–16× in the committed run). Interval matrices can also be turned into a min-cost flow problem by subtracting consecutive rows (Veinott & Wagner 1962, unverified), so a flow algorithm would be the natural specialised baseline here. **We did not implement that flow reformulation**; we compare against a generic ILP solver, the tool someone would reach for without knowing about TU.

7. **Overnight shifts break exactness, but only sometimes.** Letting shifts wrap past midnight made 12% of instances non-exact (and the C₃ example). That matches the wording on our slide: losing TU *allows* fractional optima; it does not force them (compare E1).

8. **Branch-and-bound node counts didn't separate the two cases.** HiGHS closed every overnight gap at the root node, also with presolve and primal heuristics switched off (`python3 e4.py --node-check`, results in `results/node_check.csv`). We did not isolate the cause; the most likely one is the cutting planes HiGHS adds at the root, which on these small 24-row instances are enough. So the evidence for C1 vs C2 is LP integrality and LP = ILP, not the node count.

## 7. Why the results agree with the theory

- **Same optimum and integral LP.** All three constraint matrices in A, B and C1 are TU (directed incidence, bipartite incidence, interval). Simplex returns a basic solution x_B = A_B⁻¹b, a vertex, which Hoffman–Kruskal makes integral. Primal and dual simplex both end at a vertex, so both are integral.
- **König.** The matching LP and the vertex cover LP are each other's duals (L7). Both matrices are TU, so both have integral optima, and strong duality makes the values equal: max matching = min vertex cover.
- **Why the specialised algorithms are faster.** Edmonds–Karp, Dinic and Hopcroft–Karp work directly on the graph, using breadth- and depth-first searches that touch each arc a few times per phase, and they need few phases. Simplex works on the matrix, and the number of pivots grew faster than the size of the LP (15× more pivots for a 10× larger random network). A possible further reason, which we did not measure: flow and matching LPs are highly **degenerate** (many bases describe the same vertex), so many pivots may make no progress. Measuring it would need counts of degenerate pivots or a profile of the solver. *(Beyond the lectures. Intuition: simplex can spend many steps "turning on the spot" at one corner before it can move to a better one.)*
- **Overnight shifts.** Wrapping a shift past midnight puts the 1s at the top and bottom of its column, so the column is no longer consecutive. Three such shifts on a 3-hour cycle give exactly the triangle's incidence matrix, whose determinant is 2 (P1's slides), so A is not TU and a fractional vertex such as (½, ½, ½) can be optimal.

## 8. Limitations and notes

- **Runtimes depend on the machine and the run.** The runtimes above are from one MacBook Air (Apple arm64). An earlier run on a 2-core Linux x86_64 machine, and a groupmate's rerun, gave identical values, integrality results and simplex iteration counts. Runtimes **and the ratios between methods** differed (for example SciPy Edmonds–Karp vs Dinic: 37× vs 16×), but every run showed the same pattern: the LP slower than the compiled specialised algorithms, and pure-Python networkx Dinic slower than the LP on the largest network. In the committed run the gap was two to three orders of magnitude on the largest random instances and much less on the grids (about 13–31×). Treat exact ratios as indicative only.
- **Generated instances for A and C.** Only B uses real data. Real max-flow benchmarks (for example DIMACS) and real rostering data were not used.
- **Default HiGHS settings** apart from the simplex variant. We did not tune the LP. Primal simplex was faster than dual on max-flow (about 2× on the largest network) and similar on matching. Interior point is covered by E3.
- **The networkx size cap** (`NX_MAX_ARCS = 60,000`) was not reached: networkx ran on every instance.
- **Unit costs in scheduling** (minimise the number of staff). Shift-dependent costs would change the numbers but not the TU argument.
- **Node counts** in C1, C2 and the node check are all 1, so they don't distinguish TU from non-TU here (highlight 8).
- **No specialised algorithm for scheduling.** The min-cost flow reformulation of day-shift scheduling (highlight 6) was not implemented.
- **Shared environment.** `requirements.txt` pins the versions shared by all four experiments (highspy 1.15.1, networkx 3.6.1, NumPy 2.5.4, SciPy 1.18.1). The committed run used NumPy 2.4.1; a rerun with the shared pins gave identical values, integrality results, iteration counts and node counts, including `--node-check`.
- **Timing scope.** LP times exclude building the model in Python (under 5 ms everywhere). SciPy times exclude building the sparse matrix; networkx times exclude building the graph.

## 9. Files

```
e4.py              the experiment (instances, models, solves, checks, tables)
requirements.txt   pinned versions
results/           written by e4.py:
  flow.csv           Part A, one row per instance
  matching.csv       Part B
  scheduling.csv     Part C1, one row per demand profile
  overnight.csv      Part C2, one row per instance (C3 example first)
  node_check.csv     written by `e4.py --node-check` only
  metadata.json      versions, platform, seed
  results.md         all tables
```

## 10. References

**None has been checked on Google Scholar yet; check before citing in the report.**

- Hoffman & Kruskal (1956), integral boundary points of convex polyhedra. *(unverified)*
- Edmonds & Karp (1972), "Theoretical improvements in algorithmic efficiency for network flow problems", *J. ACM*. *(unverified)*
- Dinic (1970), "Algorithm for solution of a problem of maximum flow in networks with power estimation", *Soviet Math. Doklady*. *(unverified)*
- Hopcroft & Karp (1973), "An n^{5/2} algorithm for maximum matchings in bipartite graphs", *SIAM J. Computing*. *(unverified)*
- König (1931), on graphs and matrices (König's theorem). *(unverified)*
- Huangfu & Hall (2018), "Parallelizing the dual revised simplex method", *Math. Prog. Computation* (HiGHS). *(unverified)*
- Veinott & Wagner (1962), "Optimal capacity scheduling", *Operations Research* (interval matrices as min-cost flow). *(unverified)*
- Bartholdi, Orlin & Ratliff (1980), "Cyclic scheduling via integer programs with circular ones", *Operations Research* (overnight shifts). *(unverified)*
- KONECT datasets: see [../E3/README.md](../E3/README.md), Section 10.

## AI assistance

`e4.py` and this README were drafted with Claude (Anthropic) in a session with Daryl on 9 Nov 2026, following the group plan in the root README and the structure of E3. The group should read and be able to explain every line before using it in the report (see the root [README](../../README.md), Section 2).
