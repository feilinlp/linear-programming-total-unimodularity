# E4: Generic LP or specialised algorithm?

Owner: P4 (Daryl). Code: [e4.py](e4.py). Full results: [results/results.md](results/results.md) and the CSV files in [results/](results/).

## 1. Question

For a TU problem, Hoffman–Kruskal says the LP relaxation already has an integral optimal vertex, so a simplex solver returns the exact integer answer. **If the LP is exact, should we just use it?** Or are the specialised algorithms from the lectures still the better tool?

E4 runs the same instances through a generic LP solver and through the specialised algorithm for each problem, checks that they agree, and times them. It also looks at one problem with no well-known specialised algorithm (shift scheduling), and at a small change that breaks TU (overnight shifts).

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
| LP dual | HiGHS 1.15.1 dual simplex (`solver="simplex"`, `simplex_strategy=1`), default presolve. This is what HiGHS chooses by default for these LPs. |
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
- **Runtime**: median of 3 runs. A run slower than 2 s is not repeated. For the LP, model building in Python (*LP build*) is timed separately from solving. For SciPy and networkx, only the algorithm call is timed.
- **C1, C2**: ILP optimum, number of branch-and-bound nodes, and (C2) the gap between ILP and LP optimum.

**König cover.** By König's theorem, starting from a maximum matching M, let Z be all vertices reachable from unmatched left vertices by alternating paths (left → right along any edge, right → left along a matching edge). Then (left vertices not in Z) ∪ (right vertices in Z) is a minimum vertex cover. `e4.py` builds it with one breadth-first search. (networkx's `to_vertex_cover` searches from every vertex separately, which took minutes on the 10,000-per-side graph, so we don't use it.)

**Checks built into the script** (it stops if any fails): all methods agree on every instance; both LP variants are integral on every flow and matching instance; the vertex cover LP is integral and equals the matching size; every day-shift LP is integral and equals the ILP optimum; the C₃ example gives LP 1.5 and ILP 2; every overnight LP is ≤ its ILP optimum.

**Reproduce:**

```
pip install -r requirements.txt
python3 e4.py      # about 2 minutes on a 2-core Linux x86_64 machine
```

Values, integrality and node counts are deterministic. Runtimes vary between machines and runs.

## 5. Results

From [results/results.md](results/results.md). Runtimes are solve times; *LP build* (not shown) was under 10 ms everywhere.

**A. Max-flow**

| Instance | Arcs | Max flow | LP integral? | LP dual | LP primal | SciPy EK | SciPy Dinic | nx EK | nx Dinic |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| random n=100 | 510 | 145 | yes | 3.9 ms | 2.5 ms | 0.2 ms | 0.3 ms | 1.4 ms | 2.6 ms |
| random n=1,000 | 5,100 | 2,283 | yes | 134 ms | 84 ms | 5.3 ms | 1.8 ms | 44 ms | 196 ms |
| random n=3,000 | 15,300 | 7,045 | yes | 864 ms | 796 ms | 72 ms | 5.8 ms | 463 ms | 2.10 s |
| random n=10,000 | 51,000 | 24,757 | yes | 13.86 s | 7.56 s | 888 ms | 24 ms | 4.48 s | 32.35 s |
| grid 10×10 | 380 | 211 | yes | 2.3 ms | 2.2 ms | 0.3 ms | 0.2 ms | 4.2 ms | 5.0 ms |
| grid 30×30 | 3,540 | 916 | yes | 46 ms | 36 ms | 3.8 ms | 2.1 ms | 359 ms | 278 ms |
| grid 70×70 | 19,460 | 2,232 | yes | 1.00 s | 864 ms | 110 ms | 32 ms | 8.92 s | 6.17 s |

**B. Bipartite matching** ("matching" = max matching = min vertex cover)

| Instance | Edges | Matching | LP integral? | LP dual | LP primal | SciPy HK | nx HK |
|---|---:|---:|---|---:|---:|---:|---:|
| random n=100 per side | 300 | 91 | yes | 2.4 ms | 2.3 ms | < 0.1 ms | 0.7 ms |
| random n=1,000 per side | 3,000 | 923 | yes | 46 ms | 55 ms | 0.7 ms | 29 ms |
| random n=10,000 per side | 30,000 | 9,274 | yes | 1.97 s | 2.12 s | 13 ms | 449 ms |
| Unicode languages | 1,255 | 188 | yes | 5.5 ms | 5.5 ms | 0.1 ms | 1.5 ms |
| Crime | 1,476 | 451 | yes | 8.6 ms | 6.3 ms | 0.1 ms | 8.5 ms |
| arXiv cond-mat | 58,595 | 12,652 | yes | 544 ms | 576 ms | 4.2 ms | 182 ms |

**C1. Day shifts (TU)**: on all 15 instances, LP = ILP, the LP solution was integral, and the ILP solver used 1 node (the root).

| Horizon | Shifts | LP time | ILP time |
|---|---:|---:|---:|
| 24 h | 57 | 0.5 ms | 4.8 ms |
| 168 h | 489 | 1.9 ms | 8.0 ms |
| 672 h | 2,001 | 7.3 ms | 25.5 ms |

**C2. Overnight shifts (not TU)**

- C₃ example: LP = 1.5 with x = (½, ½, ½); ILP = 2.
- 200 random instances: the LP was fractional and strictly below the ILP optimum on **24 (12%)**. The gap was 0.33 to 0.75 staff (median 0.5), and in all 24 cases the ILP optimum was the LP value rounded up.
- The ILP solver still finished at the root node (1 node) on every instance.

## 6. Highlights

1. **Same answer, every time.** On all 13 flow and matching instances, the LP (both simplex variants), SciPy and networkx agreed on the optimal value, and both LP solutions were integral. On matching, the König cover and the vertex cover LP gave the same number as the matching. This is the "same optimum" prediction, and Hoffman–Kruskal's guarantee in action.

2. **Like for like, the specialised algorithms win by two orders of magnitude.** Against compiled SciPy code, the LP was much slower on every non-trivial instance: on the 10,000-node random network, 13.86 s (dual) or 7.56 s (primal) against 24 ms for Dinic, about **300–575×**; on arXiv cond-mat, 544 ms against 4.2 ms for Hopcroft–Karp, about **130×**.

3. **The gap widens with size.** Going from 1,000 to 10,000 nodes in the random networks (10× bigger), the dual simplex took about **100×** longer (134 ms → 13.86 s), while SciPy Dinic took about **13×** longer (1.8 → 24 ms). Dual simplex pivots grew from 3,364 to 51,576, and each pivot also gets more expensive as the LP grows.

4. **Implementation matters as much as the algorithm.** Pure-Python networkx can lose to the compiled LP: on the 10,000-node network, networkx Dinic took 32.35 s against 13.86 s for the LP, and on the 70×70 grid, networkx Edmonds–Karp took 8.92 s against 1.00 s. For matching, networkx Hopcroft–Karp still beat the LP (449 ms vs 1.97 s on 10,000 per side). So "specialised is faster" is a statement about algorithms of equal implementation quality.

5. **Dinic vs Edmonds–Karp.** In SciPy, Dinic was 37× faster than Edmonds–Karp on the 10,000-node network (24 ms vs 888 ms), in line with L6: Dinic augments along a whole blocking flow per phase instead of one shortest path at a time.

6. **Shift scheduling: the LP alone gives the schedule.** With day shifts (TU), the LP was always integral and equal to the ILP optimum, and solving the LP was 3–10× faster than calling the ILP solver. Since there is no well-known specialised algorithm here, this is where TU pays off most directly.

7. **Overnight shifts break exactness, but only sometimes.** Letting shifts wrap past midnight made 12% of instances non-exact (and the C₃ example). That matches the wording on our slide: losing TU *allows* fractional optima; it does not force them (compare E1).

8. **Branch-and-bound node counts didn't separate the two cases.** HiGHS closed every overnight gap at the root node, even with presolve and heuristics turned off in a side check (not part of the script). Modern ILP solvers add cutting planes at the root, and on these small 24-row instances that was enough. So the evidence for C1 vs C2 is LP integrality and LP = ILP, not the node count.

## 7. Why the results agree with the theory

- **Same optimum and integral LP.** All three constraint matrices in A, B and C1 are TU (directed incidence, bipartite incidence, interval). Simplex returns a basic solution x_B = A_B⁻¹b, a vertex, which Hoffman–Kruskal makes integral. Primal and dual simplex both end at a vertex, so both are integral.
- **König.** The matching LP and the vertex cover LP are each other's duals (L7). Both matrices are TU, so both have integral optima, and strong duality makes the values equal: max matching = min vertex cover.
- **Why the specialised algorithms are faster.** Edmonds–Karp, Dinic and Hopcroft–Karp work directly on the graph: each phase is a breadth- or depth-first search costing O(m). Simplex works on the matrix: every pivot updates a factorised basis, and the number of pivots grew roughly in proportion to the size of the LP. Flow and matching LPs are also highly **degenerate**: many bases describe the same vertex, so many pivots make no progress. *(Beyond the lectures. Intuition: simplex can spend many steps "turning on the spot" at one corner before it can move to a better one.)*
- **Overnight shifts.** Wrapping a shift past midnight puts the 1s at the top and bottom of its column, so the column is no longer consecutive. Three such shifts on a 3-hour cycle give exactly the triangle's incidence matrix, whose determinant is 2 (P1's slides), so A is not TU and a fractional vertex such as (½, ½, ½) can be optimal.

## 8. Limitations and notes

- **One machine.** Runtimes are from one 2-core Linux x86_64 cloud machine. Absolute times will differ on a laptop; the ratios and the integrality results should not.
- **Generated instances for A and C.** Only B uses real data. Real max-flow benchmarks (for example DIMACS) and real rostering data were not used.
- **Default HiGHS settings** apart from the simplex variant. We did not tune the LP. Primal simplex was faster than dual on max-flow (7.56 s vs 13.86 s on the largest network) and similar on matching. Interior point is covered by E3.
- **The networkx size cap** (`NX_MAX_ARCS = 60,000`) was not reached: networkx ran on every instance.
- **Unit costs in scheduling** (minimise the number of staff). Shift-dependent costs would change the numbers but not the TU argument.
- **Node counts** in C1 and C2 are all 1, so they don't distinguish TU from non-TU here (highlight 8).
- **Timing scope.** LP times exclude building the model in Python (under 10 ms everywhere). SciPy times exclude building the sparse matrix; networkx times exclude building the graph.

## 9. Files

```
e4.py              the experiment (instances, models, solves, checks, tables)
requirements.txt   pinned versions
results/           written by e4.py:
  flow.csv           Part A, one row per instance
  matching.csv       Part B
  scheduling.csv     Part C1, one row per demand profile
  overnight.csv      Part C2, one row per instance (C3 example first)
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
- Bartholdi, Orlin & Ratliff (1980), "Cyclic scheduling via integer programs with circular ones", *Operations Research* (overnight shifts). *(unverified)*
- KONECT datasets: see [../E3/README.md](../E3/README.md), Section 10.

## AI assistance

`e4.py` and this README were drafted with Claude (Anthropic) in a session with Daryl on 9 Nov 2026, following the group plan in the root README and the structure of E3. The group should read and be able to explain every line before using it in the report (see the root [README](../../README.md), Section 2).
