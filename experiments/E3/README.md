# E3: Does the LP algorithm matter?

Owner: P3 (Feilin). Code: [e3.py](e3.py). Full results: [results/results.md](results/results.md) and [results/results.csv](results/results.csv).

## 1. Question

Hoffman–Kruskal says that if A is TU (and b is integral), every **vertex** of the feasible region is integral. It does not say every **optimal point** is integral. When several vertices tie for the optimum, the whole face between them is optimal, and most points on that face are fractional. So the answer we get depends on where the LP algorithm stops:

- **Simplex** walks from vertex to vertex, so it stops at a vertex, which is integral.
- **Interior point (IPM)** stays strictly inside the polytope. It converges to the centre of the optimal face (Güler–Ye), so it can return a fractional point.
- **Crossover** starts from the IPM point and moves to an optimal vertex (Megiddo).

**E3 tests this on TU instances: is the solver's answer integral, and if not, exactly which coordinates are fractional?**

## 2. Prediction

We use the vertex cover LP (VC LP) from the running example, with unit costs:

> min Σᵥ xᵥ s.t. x_u + x_v ≥ 1 for every edge {u, v}, 0 ≤ x ≤ 1.

Call a vertex v **free** if it is in some minimum vertex covers but not in others, and **fixed** otherwise. On a TU instance the optimal face is the convex hull of the minimum covers. So xᵥ takes both values 0 and 1 on the face if v is free, and one value if v is fixed.

| Configuration | Prediction |
|---|---|
| Dual simplex | integral, always |
| IPM + crossover | integral, always |
| IPM alone | fractional on **exactly the free vertices**. A point in the interior of the optimal face sits strictly between 0 and 1 on every coordinate that varies across the face, and at the bound on every coordinate that doesn't. |

This turns "IPM may be fractional" into a prediction we can check vertex by vertex.

## 3. Instances

Every instance is a **bipartite** graph, so its incidence matrix is TU (P1's bipartite ⇔ TU theorem). The bound rows 0 ≤ x ≤ 1 add an identity block, which keeps it TU. The script checks bipartiteness (`nx.is_bipartite`) before solving.

| Family | Instances | Why |
|---|---|---|
| Even cycles | C₄, C₂₀, C₁₀₀, C₁₀₀₀ | the running example; both colour classes are minimum covers |
| Complete bipartite | K₃,₃, K₁₀,₁₀, K₃₀,₃₀, K₁₀₀,₁₀₀ | same, with many more edges |
| Grids | 4×4, 10×10, 30×30, 100×100 | sparse and large (up to 10,000 vertices) |
| Controls | K₃,₄, K₃₀,₃₁, Davis Southern Women | unique minimum cover, so no ties: every solver should be integral |
| Real (KONECT) | Unicode languages (small), Crime (small), arXiv cond-mat (large) | do real TU instances have ties, and how many? |

Real datasets (edge lists copied into [data/](data/); edge weights ignored because E3 uses unit costs):

| Instance | Vertices / edges | What it is | Source |
|---|---|---|---|
| Unicode languages | 868 / 1,255 | countries – languages spoken there (149 edges have weight 0; we keep them, since the edge is listed) | KONECT `unicodelang`, from Unicode CLDR |
| Crime | 1,380 / 1,476 | people – crime cases they were involved in | KONECT `moreno_crime` |
| arXiv cond-mat | 38,741 / 58,595 | authors – papers, arXiv condensed matter 1995–1999 | KONECT `opsahl-collaboration`, from Newman (2001) |
| Davis Southern Women | 32 / 89 | women – social events | built into networkx (`nx.davis_southern_women_graph()`) |

## 4. Method

**Solver.** HiGHS 1.15.1 via `highspy`, three configurations:

| Name | HiGHS options |
|---|---|
| `simplex` | `solver="simplex"`, `simplex_strategy=1` (dual simplex) |
| `ipm+x` | `solver="ipm"`, `run_crossover="on"` |
| `ipm` | `solver="ipm"`, `run_crossover="off"` |

**Presolve is off in every run** (`presolve="off"`). Presolve is a clean-up step HiGHS runs before the algorithm. On graphs with leaf vertices it settles many ties by itself (a leaf u with neighbour v can always be set to x_u = 0, x_v = 1), so IPM never sees them. Turning it off means we compare simplex and IPM themselves. In an exploratory run, the default presolve hid most of the effect on the real graphs. That run is not part of this experiment.

**What we measure, per instance and configuration:**
- **Fractional count:** number of coordinates with |xᵥ − round(xᵥ)| > 10⁻⁶.
- **Free set (the prediction),** computed in two independent ways:
  1. **From a maximum matching (all instances).** By König's theorem, every minimum cover takes exactly one endpoint of each edge of a maximum matching M, and no unmatched vertex. An unmatched vertex is in no minimum cover, so its neighbours are in every minimum cover, so their partners in M are in none, and so on along alternating paths (König's construction). Matching edges reached this way have a forced choice. On every other matching edge both choices occur, so both endpoints are free. Runtime: Hopcroft–Karp plus one graph search.
  2. **By LP (instances with ≤ 2,000 vertices).** For each v, minimise and maximise xᵥ subject to the VC constraints and Σ x ≤ OPT. v is free if max − min > ½; on a TU instance the range is exactly 0 or 1.
- **Exact match:** whether the set of fractional coordinates of `ipm` equals the free set (the same vertices, not just the same count).
- **Margins:** how far the free coordinates are from an integer, and how close the fixed coordinates are to one.
- **Values of the free coordinates** in the `ipm` answer, and what L4's threshold rounding at ½ gives if applied to them.
- **Iterations and runtime** (median of 3 solves, model building excluded).

**Checks built into the script** (it stops if any fails): every graph is bipartite; every solve reports "optimal"; all three configurations reach the same optimal value (relative tolerance 10⁻⁶, because IPM alone stops slightly short, e.g. 12652.00001 vs 12652); the LP optimum equals the maximum matching size (König); and both free-set methods agree.

**Reproduce:**

```
pip install -r requirements.txt
python3 e3.py      # about 1 minute on an Apple arm64 laptop
```

Integrality results were identical across our runs; runtimes vary between runs.

## 5. Results

From [results/results.md](results/results.md). "Free" is the prediction; the last three columns count fractional coordinates.

| Instance | n | OPT | Free | Simplex | IPM + crossover | IPM alone | IPM alone = free set? |
|---|---:|---:|---:|---:|---:|---:|---|
| C₄ / C₂₀ / C₁₀₀ / C₁₀₀₀ | 4 – 1,000 | n/2 | n | 0 | 0 | n | yes |
| K₃,₃ … K₁₀₀,₁₀₀ | 6 – 200 | n/2 | n | 0 | 0 | n | yes |
| grid 4×4 … 100×100 | 16 – 10,000 | n/2 | n | 0 | 0 | n | yes |
| K₃,₄, K₃₀,₃₁, Davis | 7 – 61 | 3, 30, 14 | 0 | 0 | 0 | 0 | yes |
| Unicode languages | 868 | 188 | 90 | 0 | 0 | 90 | yes |
| Crime | 1,380 | 451 | 348 | 0 | 0 | 348 | yes |
| arXiv cond-mat | 38,741 | 12,652 | 7,934 | 0 | 0 | 7,934 | yes |

## 6. Highlights

1. **The prediction held on all 18 instances.** Simplex and IPM + crossover returned an integral vertex every time. IPM alone was fractional on exactly the free vertices: the same set of vertices, not just the same number. On the largest instance, arXiv cond-mat, the 7,934 vertices that the matching argument predicts are free are exactly the 7,934 that IPM left fractional.

2. **The result does not depend on the 10⁻⁶ tolerance.** In the IPM-alone answers, every free coordinate is at least 0.018 away from an integer, and every fixed coordinate is within 3.4 × 10⁻⁸ of one. Any threshold between about 10⁻⁷ and 10⁻² gives the same classification.

3. **On the synthetic families IPM returns all ½; on real graphs it doesn't.** On even cycles, K_{n,n} and even grids, every vertex is free and IPM puts every coordinate at exactly ½: the optimal face is symmetric, so its centre is the midpoint. On the real graphs the free coordinates range from 0.019 to 0.981, and only 5–11% of them are at ½. Half-integrality (Nemhauser–Trotter) is a property of **vertices**; IPM's answer is not a vertex, so it doesn't apply.

4. **Whether ties occur depends on the graph.** The symmetric families tie on every vertex. The controls (K_{n,n+1} and Davis) have a unique optimum, so all three configurations return the same integral answer. The real graphs are in between: 10% (Unicode languages), 25% (Crime) and 20% (arXiv cond-mat) of vertices are free. So "the algorithm matters" is a statement about tied optima, and real data has plenty of them.

5. **Skipping crossover and rounding instead can cost a factor of 2, even when the LP is exact.** Applying L4's threshold rounding (round xᵥ ≥ ½ up) to the IPM-alone answer always gives a valid cover. On every symmetric instance it gives exactly **2 · OPT**, the worst case of L4's 2-approximation, on instances where the LP optimum is already an integer cover. On the real graphs the loss is small: 1.6% (Unicode), 1.8% (Crime), 3.3% (arXiv). Crossover is what turns "the LP is exact" into "the solver's answer is exact".

6. **What each configuration costs.** IPM needed 5–17 iterations from n = 4 to n = 38,741, while dual simplex pivots grew with the size of the graph (2 to 20,439). Crossover added work that grows with size: up to 6,896 iterations on the 100×100 grid. It made IPM 2.3× slower on K₁₀₀,₁₀₀, but only about 4% slower on arXiv cond-mat. On these sparse, easy LPs dual simplex was the fastest configuration on every instance except C₁₀₀₀, though a few small gaps (K₃,₄, K₁₀₀,₁₀₀) are within run-to-run noise. Runtimes are from one laptop and vary between runs; E4 is the experiment about speed.

## 7. Why the results agree with the theory

- **Simplex** only visits basic solutions x_B = A_B⁻¹b, which are vertices. By Hoffman–Kruskal every vertex of a TU polytope with integral b is integral, so simplex can't return anything else.
- **IPM** keeps every iterate strictly inside the polytope (that is what the barrier term does), and its central path ends at the centre of the optimal face (Güler–Ye 1993). A point in the interior of a face sits strictly between its bounds on every coordinate that varies across the face. Here those are exactly the free vertices. *(This goes beyond the lectures. Intuition: the midpoint of a segment is never one of its endpoints, and the same holds for the centre of a higher-dimensional face.)*
- **Crossover** moves from the IPM point to an optimal vertex (Megiddo 1991), and every vertex is integral.
- **Why ½ on symmetric graphs but not on real ones.** For every edge {u, w} of a maximum matching, every optimal solution has x_u + x_w = 1 (the matching edges alone already need OPT = |M|). Substituting x_w = 1 − x_u turns each other edge between free vertices into a constraint x_a ≥ x_b between two free vertices on the same side. On C₂ₖ these constraints go round the cycle, so all free coordinates on one side are equal, and the centre is the midpoint ½. On real graphs the constraints are lopsided, which pulls the centre away from ½. *(Beyond the lectures; this explanation is ours, not from a source.)*

## 8. Limitations and notes

- **One solver** (HiGHS 1.15.1). Another IPM implementation may stop at a different interior point of the optimal face, but any such point is fractional on the same set of vertices, so highlight 1 shouldn't change. The exact values in highlight 3 may.
- **Unit costs only.** With random weights, ties should be rare, so we'd expect all three configurations to be integral. Not tested.
- **The VC LP only.** Bipartite matching and max-flow LPs are also TU and have tied optima (for example, K_{n,n} has n! perfect matchings), but we didn't run them.
- **The LP check of the free set** ran only up to 2,000 vertices (16 of the 18 instances). For the 100×100 grid and arXiv cond-mat, the prediction comes from the matching method alone, and IPM's answer matches it exactly.
- **HiGHS's crossover iteration counter** reports 0 on the even cycles, although the HiGHS log shows one primal and one dual push. That fits the geometry: the optimal face of C₂ₖ is a segment, so one push reaches an endpoint. Treat the counter as approximate.

## 9. Files

```
e3.py              the experiment (instances, solves, free-set computation, checks, tables)
requirements.txt   pinned versions
data/              KONECT edge lists, with their meta and README files (licence and citation)
results/           results.csv (every measurement) and results.md (tables), written by e3.py
```

## 10. References

Theory references are from [notes/P3.md](../../notes/P3.md). **None has been checked on Google Scholar yet; check before citing in the report.**

- Hoffman & Kruskal (1956), integral boundary points of convex polyhedra. *(unverified)*
- Güler & Ye (1993), "Convergence behavior of interior-point algorithms", *Math. Programming*. *(unverified)*
- Megiddo (1991), "On finding primal- and dual-optimal bases", *ORSA J. Computing*. *(unverified)*
- Nemhauser & Trotter (1975), "Vertex packings: structural properties and algorithms", *Math. Programming*. *(unverified)*
- Kunegis (2013), "KONECT – The Koblenz Network Collection", *Proc. WWW Companion*, pp. 1343–1350. *(citation as given in the KONECT README files; unverified)*
- Newman (2001), "The structure of scientific collaboration networks", *PNAS* 98(2), 404–409. Source of arXiv cond-mat. *(citation as given by KONECT; unverified)*
- Davis, Gardner & Gardner (1941), *Deep South*. Source of the Southern Women data, as credited in the networkx documentation. *(unverified)*

## AI assistance

The exploratory runs, `e3.py` and this README were drafted with Claude Code (Claude Opus 5.5) in a session with Feilin on 21 Oct 2026. The group should read and be able to explain every line before using it in the report (see the root [README](../../README.md), Section 2).
