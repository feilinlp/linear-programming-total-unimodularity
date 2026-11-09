"""E4: Generic LP or specialised algorithm?

TU tells us the LP relaxation of these problems is exact. E4 asks whether
"just solve the LP" is a sensible way to get the answer, by comparing a
generic LP solver with the specialised algorithms for each problem.

Part A  Max-flow           HiGHS LP  vs  Edmonds-Karp, Dinic (networkx and SciPy)
Part B  Bipartite matching HiGHS LP  vs  Hopcroft-Karp (networkx and SciPy)
                           + vertex cover via Koenig's theorem
Part C  Shift scheduling   HiGHS LP  vs  HiGHS MIP (branch-and-bound)
                           day shifts (interval matrix, TU) and
                           overnight shifts (circular ones, not TU)

The LP is always solved with HiGHS simplex (dual and primal in Parts A and B,
dual in Part C), so it returns a vertex, which is integral when the matrix is
TU (Hoffman-Kruskal).

Prediction (README Section 2):
  A, B: same optimum; LP solution integral; specialised algorithms faster.
  C:    day shifts: LP = MIP and the MIP needs no branching;
        overnight shifts: the LP can be fractional and below the MIP optimum.

Run from this folder:  python3 e4.py
Optional:              python3 e4.py --node-check   (writes results/node_check.csv only)
Writes results/flow.csv, results/matching.csv, results/scheduling.csv,
results/overnight.csv, results/metadata.json and results/results.md.
"""

import csv
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import highspy
import networkx as nx
import numpy as np
import scipy
import scipy.sparse as sp
from scipy.sparse.csgraph import maximum_bipartite_matching, maximum_flow

HERE = Path(__file__).resolve().parent
E3_DATA = HERE.parent / "E3" / "data"   # KONECT graphs are reused from E3, not copied
RESULTS = HERE / "results"

SEED = 4234
REPEATS = 3            # runtimes are the median of this many runs ...
SLOW_S = 2.0           # ... except that a run slower than this is not repeated
FRAC_TOL = 1e-6        # a value counts as fractional if |x - round(x)| > FRAC_TOL
OBJ_TOL = 1e-6         # absolute tolerance when comparing optimal values
CAP_RANGE = (1, 100)   # integer arc capacities, uniform
NX_MAX_ARCS = 60_000   # skip the pure-Python networkx max-flow runs above this size (too slow)

KONECT = [  # (instance name, edge list), the bipartite graphs used in E3
    ("Unicode languages", E3_DATA / "unicodelang" / "out.unicodelang"),
    ("Crime", E3_DATA / "moreno_crime" / "out.moreno_crime_crime"),
    ("arXiv cond-mat", E3_DATA / "opsahl-collaboration" / "out.opsahl-collaboration"),
]


# ---------------------------------------------------------------- helpers

def timed(fn, repeats=REPEATS):
    """Run fn() up to `repeats` times; return (last result, median seconds).
    Runs slower than SLOW_S are not repeated, to keep the whole script short."""
    times, out = [], None
    for _ in range(repeats):
        start = time.perf_counter()
        out = fn()
        times.append(time.perf_counter() - start)
        if times[-1] > SLOW_S:
            break
    return out, statistics.median(times)


def max_frac(x):
    x = np.asarray(x, dtype=float)
    return float(np.max(np.abs(x - np.round(x)))) if x.size else 0.0


def new_highs(**options):
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    for key, value in options.items():
        h.setOptionValue(key, value)
    return h


# Two simplex variants. Both end at a vertex, so both are integral on TU instances.
# Dual simplex is the setting E3 used; primal simplex is added for comparison.
LP_CONFIGS = {
    "dual": {"solver": "simplex", "simplex_strategy": 1},
    "primal": {"solver": "simplex", "simplex_strategy": 4},
}
LP_OPTIONS = LP_CONFIGS["dual"]


def add_rows_csr(h, A, lower, upper):
    """Add the rows of a scipy sparse matrix A to a HiGHS model in one call."""
    A = sp.csr_matrix(A)
    h.addRows(A.shape[0], np.asarray(lower, float), np.asarray(upper, float), A.nnz,
              A.indptr[:-1].astype(np.int32), A.indices.astype(np.int32),
              A.data.astype(float))


def solve_lp(build, repeats=REPEATS):
    """build() returns a ready HiGHS model. Times build and run separately."""
    builds, runs = [], []
    for _ in range(repeats):
        t0 = time.perf_counter()
        h = build()
        t1 = time.perf_counter()
        h.run()
        t2 = time.perf_counter()
        builds.append(t1 - t0)
        runs.append(t2 - t1)
        assert h.getModelStatus() == highspy.HighsModelStatus.kOptimal, h.getModelStatus()
        if runs[-1] > SLOW_S:
            break
    info = h.getInfo()
    x = np.array(h.getSolution().col_value)
    return {"obj": info.objective_function_value, "x": x,
            "iters": info.simplex_iteration_count,
            "build_s": statistics.median(builds), "solve_s": statistics.median(runs)}


# ---------------------------------------------------------------- Part A: max-flow

def random_network(n, out_deg, rng):
    """Sparse random digraph on n nodes with about out_deg * n distinct arcs (no self-loops),
    plus a super source s joined to n/20 random nodes and a super sink t joined from
    another n/20. (With a single ordinary node as source, the flow is capped by its
    handful of arcs and the instance is trivial.)"""
    m = out_deg * n
    tails = rng.integers(0, n, size=2 * m)
    heads = rng.integers(0, n, size=2 * m)
    keep = tails != heads
    arcs = np.unique(np.stack([tails[keep], heads[keep]], axis=1), axis=0)
    arcs = arcs[rng.permutation(len(arcs))[:m]]
    k = max(2, n // 20)
    ends = rng.permutation(n)[:2 * k]
    s, t = n, n + 1
    arcs = np.vstack([arcs, np.stack([np.full(k, s), ends[:k]], 1),
                      np.stack([ends[k:], np.full(k, t)], 1)])
    caps = rng.integers(CAP_RANGE[0], CAP_RANGE[1] + 1, size=len(arcs))
    return n + 2, arcs, caps, s, t


def grid_network(k, rng):
    """k x k grid with arcs both ways between neighbours; super source s joined to
    the left column and super sink t joined to the right column (image-segmentation style)."""
    idx = lambda r, c: r * k + c
    arcs = []
    for r in range(k):
        for c in range(k):
            if c + 1 < k:
                arcs += [(idx(r, c), idx(r, c + 1)), (idx(r, c + 1), idx(r, c))]
            if r + 1 < k:
                arcs += [(idx(r, c), idx(r + 1, c)), (idx(r + 1, c), idx(r, c))]
    s, t = k * k, k * k + 1
    arcs += [(s, idx(r, 0)) for r in range(k)] + [(idx(r, k - 1), t) for r in range(k)]
    arcs = np.array(arcs)
    caps = rng.integers(CAP_RANGE[0], CAP_RANGE[1] + 1, size=len(arcs))
    return k * k + 2, arcs, caps, s, t


def flow_instances(rng):
    for n in (100, 1_000, 3_000, 10_000):
        yield "random", f"random n={n:,}", random_network(n, 5, rng)
    for k in (10, 30, 70):
        yield "grid", f"grid {k}x{k}", grid_network(k, rng)


def flow_lp(n, arcs, caps, s, t):
    """max (flow out of s - flow into s)
       s.t. flow in - flow out = 0 at every v other than s, t;  0 <= f_e <= c_e.
       Conservation rows form a directed incidence matrix (one +1, one -1 per column): TU."""
    m = len(arcs)
    tail, head = arcs[:, 0], arcs[:, 1]
    inner = np.setdiff1d(np.arange(n), [s, t])
    row_of = -np.ones(n, dtype=np.int64)
    row_of[inner] = np.arange(len(inner))
    rows, cols, vals = [], [], []
    for nodes, sign in ((head, 1.0), (tail, -1.0)):
        r = row_of[nodes]
        ok = r >= 0
        rows.append(r[ok]); cols.append(np.arange(m)[ok]); vals.append(np.full(ok.sum(), sign))
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                      shape=(len(inner), m))
    cost = (tail == s).astype(float) - (head == s).astype(float)

    def build(options=LP_OPTIONS):
        h = new_highs(**options)
        h.addVars(m, np.zeros(m), caps.astype(float))
        h.changeColsCost(m, np.arange(m, dtype=np.int32), cost)
        h.changeObjectiveSense(highspy.ObjSense.kMaximize)
        add_rows_csr(h, A, np.zeros(len(inner)), np.zeros(len(inner)))
        return h
    return build, A


def run_flow(family, name, inst):
    n, arcs, caps, s, t = inst
    m = len(arcs)
    build, A = flow_lp(n, arcs, caps, s, t)
    row = {"family": family, "instance": name, "nodes": n, "arcs": m}
    values = {}
    for cfg, options in LP_CONFIGS.items():
        lp = solve_lp(lambda: build(options))
        f = lp["x"]
        # The LP flow must be a valid flow: conservation and capacities.
        assert np.max(np.abs(A @ f)) < 1e-6 and np.all(f >= -1e-9) and np.all(f <= caps + 1e-9)
        values[f"lp_{cfg}"] = lp["obj"]
        row.update({f"lp_{cfg}_max_frac": max_frac(f), f"lp_{cfg}_iters": lp["iters"],
                    f"lp_{cfg}_build_s": lp["build_s"], f"lp_{cfg}_solve_s": lp["solve_s"]})

    csr = sp.csr_matrix((caps.astype(np.int32), (arcs[:, 0], arcs[:, 1])), shape=(n, n))
    for method in ("edmonds_karp", "dinic"):
        res, sec = timed(lambda: maximum_flow(csr, s, t, method=method))
        values[f"scipy_{method}"] = res.flow_value
        row[f"scipy_{method}_s"] = sec
    if m <= NX_MAX_ARCS:
        G = nx.DiGraph()
        G.add_weighted_edges_from(((int(a), int(b), int(c)) for (a, b), c in zip(arcs, caps)),
                                  weight="capacity")
        for label, func in (("edmonds_karp", nx.algorithms.flow.edmonds_karp),
                            ("dinic", nx.algorithms.flow.dinitz)):
            val, sec = timed(lambda: nx.maximum_flow_value(G, s, t, flow_func=func))
            values[f"nx_{label}"] = val
            row[f"nx_{label}_s"] = sec
    else:
        row["nx_edmonds_karp_s"] = row["nx_dinic_s"] = ""
    ref = values["scipy_dinic"]
    assert all(abs(v - ref) <= OBJ_TOL for v in values.values()), values
    row["value"] = int(round(ref))
    row["all_equal"] = True
    return row


# ---------------------------------------------------------------- Part B: matching

def load_konect(path):
    """Bipartite KONECT edge list -> array of (left, right) pairs, 0-based per side."""
    pairs = []
    with open(path) as f:
        assert f.readline().startswith("% bip"), path
        for line in f:
            if line.startswith("%") or not line.strip():
                continue
            a, b = line.split()[:2]
            pairs.append((int(a), int(b)))
    pairs = np.unique(np.array(pairs), axis=0)
    _, left = np.unique(pairs[:, 0], return_inverse=True)
    _, right = np.unique(pairs[:, 1], return_inverse=True)
    return int(left.max()) + 1, int(right.max()) + 1, np.stack([left, right], axis=1)


def random_bipartite(n, avg_deg, rng):
    m = avg_deg * n
    pairs = np.unique(np.stack([rng.integers(0, n, 2 * m), rng.integers(0, n, 2 * m)], 1), axis=0)
    pairs = pairs[rng.permutation(len(pairs))[:m]]
    return n, n, pairs


def matching_instances(rng):
    for n in (100, 1_000, 10_000):
        yield "random", f"random n={n:,} per side", random_bipartite(n, 3, rng)
    for name, path in KONECT:
        yield "real", name, load_konect(path)


def matching_lp(nl, nr, pairs):
    """max sum_e x_e  s.t.  sum_{e at v} x_e <= 1 for every vertex v,  x >= 0.
       Rows = vertex-edge incidence matrix of a bipartite graph: TU."""
    m = len(pairs)
    rows = np.concatenate([pairs[:, 0], nl + pairs[:, 1]])
    cols = np.concatenate([np.arange(m), np.arange(m)])
    A = sp.csr_matrix((np.ones(2 * m), (rows, cols)), shape=(nl + nr, m))

    def build(options=LP_OPTIONS):
        h = new_highs(**options)
        h.addVars(m, np.zeros(m), np.full(m, highspy.kHighsInf))
        h.changeColsCost(m, np.arange(m, dtype=np.int32), np.ones(m))
        h.changeObjectiveSense(highspy.ObjSense.kMaximize)
        add_rows_csr(h, A, np.full(nl + nr, -highspy.kHighsInf), np.ones(nl + nr))
        return h
    return build, A


def vc_lp_value(nl, nr, pairs):
    """Vertex cover LP (the dual of the matching LP): min sum x_v s.t. x_u + x_v >= 1."""
    m = len(pairs)
    n = nl + nr
    rows = np.concatenate([np.arange(m), np.arange(m)])
    cols = np.concatenate([pairs[:, 0], nl + pairs[:, 1]])
    A = sp.csr_matrix((np.ones(2 * m), (rows, cols)), shape=(m, n))
    h = new_highs(**LP_OPTIONS)
    h.addVars(n, np.zeros(n), np.ones(n))
    h.changeColsCost(n, np.arange(n, dtype=np.int32), np.ones(n))
    add_rows_csr(h, A, np.ones(m), np.full(m, highspy.kHighsInf))
    h.run()
    assert h.getModelStatus() == highspy.HighsModelStatus.kOptimal
    return h.getInfo().objective_function_value, max_frac(h.getSolution().col_value)


def koenig_cover(nl, nr, pairs, match_left):
    """Koenig's construction, in one breadth-first search (linear time).
    match_left[i] = right partner of left vertex i, or -1 if unmatched.
    Z = vertices reachable from unmatched left vertices by alternating paths
    (left -> right along any edge, right -> left along the matching edge).
    Minimum vertex cover = (left vertices not in Z) + (right vertices in Z).
    (networkx's to_vertex_cover searches from every vertex separately, which
    is far too slow on our larger graphs.)"""
    adj = sp.csr_matrix((np.ones(len(pairs), dtype=np.int8), (pairs[:, 0], pairs[:, 1])),
                        shape=(nl, nr))
    match_right = -np.ones(nr, dtype=np.int64)
    matched = match_left >= 0
    match_right[match_left[matched]] = np.nonzero(matched)[0]
    zl = ~matched                       # unmatched left vertices start the search
    zr = np.zeros(nr, dtype=bool)
    frontier = np.nonzero(zl)[0]
    while frontier.size:
        nbrs = np.unique(adj[frontier].indices)
        new_r = nbrs[~zr[nbrs]]
        zr[new_r] = True
        nxt = match_right[new_r]
        nxt = nxt[(nxt >= 0) & ~zl[nxt]]
        zl[nxt] = True
        frontier = nxt
    return ~zl, zr


def run_matching(family, name, inst):
    nl, nr, pairs = inst
    m = len(pairs)
    build, A = matching_lp(nl, nr, pairs)
    lps = {}
    for cfg, options in LP_CONFIGS.items():
        lps[cfg] = solve_lp(lambda: build(options))
        x = lps[cfg]["x"]
        assert np.max(A @ x) <= 1 + 1e-6 and np.all(x >= -1e-9)

    bi = sp.csr_matrix((np.ones(m, dtype=np.int8), (pairs[:, 0], pairs[:, 1])), shape=(nl, nr))
    res, sec_sp = timed(lambda: maximum_bipartite_matching(bi, perm_type="column"))
    size_sp = int(np.sum(res >= 0))

    G = nx.Graph()
    top = [("L", i) for i in range(nl)]
    G.add_nodes_from(top)
    G.add_nodes_from(("R", j) for j in range(nr))
    G.add_edges_from((("L", int(a)), ("R", int(b))) for a, b in pairs)
    M, sec_nx = timed(lambda: nx.bipartite.hopcroft_karp_matching(G, top_nodes=top))
    size_nx = len(M) // 2

    # Koenig: a minimum vertex cover built from the maximum matching has the same size,
    # and equals the optimum of the vertex cover LP (LP duality + TU).
    (in_l, in_r), sec_cover = timed(lambda: koenig_cover(nl, nr, pairs, res), 1)
    assert np.all(in_l[pairs[:, 0]] | in_r[pairs[:, 1]]), "Koenig cover misses an edge"
    cover_size = int(in_l.sum() + in_r.sum())
    vc_val, vc_frac = vc_lp_value(nl, nr, pairs)

    sizes = {"scipy_hk": size_sp, "nx_hk": size_nx, "koenig_cover": cover_size, "vc_lp": vc_val}
    sizes.update({f"lp_{c}": lp["obj"] for c, lp in lps.items()})
    assert all(abs(v - size_sp) <= OBJ_TOL for v in sizes.values()), sizes
    row = {"family": family, "instance": name, "left": nl, "right": nr, "edges": m,
           "value": size_sp, "all_equal": True, "vc_lp_max_frac": vc_frac}
    for c, lp in lps.items():
        row.update({f"lp_{c}_max_frac": max_frac(lp["x"]), f"lp_{c}_iters": lp["iters"],
                    f"lp_{c}_build_s": lp["build_s"], f"lp_{c}_solve_s": lp["solve_s"]})
    row.update({"scipy_hk_s": sec_sp, "nx_hk_s": sec_nx, "koenig_cover_s": sec_cover})
    return row


# ---------------------------------------------------------------- Part C: scheduling

SHIFT_LENGTHS = (4, 6, 8)   # hours
DEMAND_RANGE = (1, 20)      # staff needed per hour, uniform integer


def shifts(T, cyclic):
    """Every shift = (start, length). Day shifts must end by hour T;
    overnight (cyclic) shifts may wrap past the end of the horizon to the start."""
    return [(s, L) for L in SHIFT_LENGTHS for s in range(T) if cyclic or s + L <= T]


def coverage_matrix(T, shift_list):
    """Rows = hours, columns = shifts; entry 1 if the shift covers that hour.
       Day shifts: consecutive 1s in every column (interval matrix, TU).
       Overnight shifts: the 1s may wrap round (circular ones, not TU in general)."""
    rows, cols = [], []
    for j, (s, L) in enumerate(shift_list):
        for h in range(s, s + L):
            rows.append(h % T); cols.append(j)
    return sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(T, len(shift_list)))


def scheduling_model(A, demand, integer, mip_options=None):
    """min number of staff  s.t.  staff on duty at hour t >= demand_t,  x >= 0 (integer for the MIP)."""
    T, k = A.shape
    h = new_highs(**((mip_options or {}) if integer else LP_OPTIONS))
    h.addVars(k, np.zeros(k), np.full(k, highspy.kHighsInf))
    h.changeColsCost(k, np.arange(k, dtype=np.int32), np.ones(k))
    add_rows_csr(h, A, demand.astype(float), np.full(T, highspy.kHighsInf))
    if integer:
        h.changeColsIntegrality(k, np.arange(k, dtype=np.int32),
                                np.full(k, highspy.HighsVarType.kInteger, dtype=np.uint8))
    return h


def solve_scheduling(A, demand, repeats=REPEATS):
    out = {}
    for kind, integer in (("lp", False), ("mip", True)):
        def run():
            h = scheduling_model(A, demand, integer)
            h.run()
            assert h.getModelStatus() == highspy.HighsModelStatus.kOptimal
            return h
        h, sec = timed(run, repeats)
        info = h.getInfo()
        out[kind] = {"obj": info.objective_function_value, "s": sec,
                     "x": np.array(h.getSolution().col_value),
                     "nodes": info.mip_node_count if integer else None}
    return out


def demand_profile(T, rng):
    return rng.integers(DEMAND_RANGE[0], DEMAND_RANGE[1] + 1, size=T)


def run_scheduling(rng):
    """Day shifts on horizons from one day to four weeks (one hour per row)."""
    rows = []
    for days in (1, 7, 28):
        T = 24 * days
        sl = shifts(T, cyclic=False)
        A = coverage_matrix(T, sl)
        for rep in range(5):
            d = demand_profile(T, rng)
            r = solve_scheduling(A, d)
            lp, mip = r["lp"], r["mip"]
            assert abs(lp["obj"] - mip["obj"]) <= OBJ_TOL, (lp["obj"], mip["obj"])
            rows.append({"horizon_h": T, "seed_rep": rep, "shifts": len(sl),
                         "lp_value": round(lp["obj"], 6), "mip_value": round(mip["obj"], 6),
                         "lp_max_frac": max_frac(lp["x"]), "mip_nodes": mip["nodes"],
                         "lp_s": lp["s"], "mip_s": mip["s"]})
    return rows


def run_overnight(rng, n_instances=200):
    """Overnight shifts on a repeating 24-hour day: the 1s in a column may wrap
    past midnight. Includes the 3-hour C3 example from the slides."""
    rows = []
    # The C3 example: 3 hours in a cycle, demand 1, shifts {1,2}, {2,3}, {3,1}.
    A3 = coverage_matrix(3, [(0, 2), (1, 2), (2, 2)])
    r = solve_scheduling(A3, np.ones(3, dtype=int), 1)
    rows.append({"instance": "C3 example", "lp_value": r["lp"]["obj"], "mip_value": r["mip"]["obj"],
                 "lp_max_frac": max_frac(r["lp"]["x"]), "mip_nodes": r["mip"]["nodes"],
                 "lp_x": " ".join(f"{v:g}" for v in r["lp"]["x"])})
    T = 24
    sl = shifts(T, cyclic=True)
    A = coverage_matrix(T, sl)
    for i in range(n_instances):
        d = demand_profile(T, rng)
        r = solve_scheduling(A, d, 1)
        rows.append({"instance": f"random {i}", "lp_value": round(r["lp"]["obj"], 6),
                     "mip_value": round(r["mip"]["obj"], 6),
                     "lp_max_frac": max_frac(r["lp"]["x"]), "mip_nodes": r["mip"]["nodes"],
                     "lp_x": ""})
    for row in rows:
        assert row["lp_value"] <= row["mip_value"] + OBJ_TOL   # the LP is a relaxation
    return rows


# ---------------------------------------------------------------- output

def fmt_s(x):
    if x == "" or x is None:
        return "–"
    return f"{x * 1000:.1f} ms" if x < 1 else f"{x:.2f} s"


def integral(r):
    """'yes' if both simplex variants returned an integral solution."""
    return "yes" if all(r[f"lp_{c}_max_frac"] <= FRAC_TOL for c in LP_CONFIGS) else "NO"


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def environment():
    return {"python": platform.python_version(), "highspy": highspy.Highs().version(),
            "networkx": nx.__version__, "scipy": scipy.__version__, "numpy": np.__version__,
            "platform": f"{platform.system()} {platform.machine()}", "seed": SEED,
            "repeats": REPEATS}


def write_markdown(flow, matching, sched, overnight, path):
    env = environment()
    L = ["# E4 results", "",
         f"Generated by `e4.py`. Environment: Python {env['python']}, highspy {env['highspy']}, "
         f"networkx {env['networkx']}, SciPy {env['scipy']}, NumPy {env['numpy']}, {env['platform']}. "
         f"Seed {SEED}. Runtimes are medians of up to {REPEATS} runs (a run slower than {SLOW_S:g} s is not repeated) "
         f"and vary between machines and runs.", "",
         "## A. Max-flow: HiGHS LP vs Edmonds–Karp and Dinic", "",
         "LP dual / LP primal = HiGHS dual / primal simplex, solve time only. *LP build* is the Python time to set the model up. "
         "networkx is pure Python; SciPy is compiled. \"–\" = skipped (networkx too slow at this size).", "",
         "| Instance | Nodes | Arcs | Max flow | LP integral? | LP dual | LP primal | LP build | SciPy EK | SciPy Dinic | nx EK | nx Dinic |",
         "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in flow:
        L.append(f"| {r['instance']} | {r['nodes']:,} | {r['arcs']:,} | {r['value']:,} | "
                 f"{integral(r)} | {fmt_s(r['lp_dual_solve_s'])} | {fmt_s(r['lp_primal_solve_s'])} | "
                 f"{fmt_s(r['lp_dual_build_s'])} | {fmt_s(r['scipy_edmonds_karp_s'])} | {fmt_s(r['scipy_dinic_s'])} | "
                 f"{fmt_s(r['nx_edmonds_karp_s'])} | {fmt_s(r['nx_dinic_s'])} |")
    L += ["", "All methods returned the same max-flow value on every instance (checked by the script).", "",
          "## B. Bipartite matching: HiGHS LP vs Hopcroft–Karp; vertex cover via König", "",
          "| Instance | Left | Right | Edges | Max matching = min cover | LP integral? | LP dual | LP primal | LP build | SciPy HK | nx HK |",
          "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|"]
    for r in matching:
        L.append(f"| {r['instance']} | {r['left']:,} | {r['right']:,} | {r['edges']:,} | {r['value']:,} | "
                 f"{integral(r)} | {fmt_s(r['lp_dual_solve_s'])} | {fmt_s(r['lp_primal_solve_s'])} | "
                 f"{fmt_s(r['lp_dual_build_s'])} | {fmt_s(r['scipy_hk_s'])} | {fmt_s(r['nx_hk_s'])} |")
    L += ["", "On every instance the matching LP, SciPy and networkx Hopcroft–Karp, the König cover built "
          "from the matching, and the vertex cover LP all gave the same value (checked by the script).", "",
          "## C1. Day shifts (interval matrix, TU): LP vs MIP", "",
          "5 random demand profiles per horizon, demand 1–20 staff per hour, shifts of 4, 6 or 8 hours. "
          "LP and MIP times both include building the model.", "",
          "| Horizon | Shifts | LP = MIP (all 5)? | LP integral (all 5)? | MIP nodes (max) | LP time (median) | MIP time (median) |",
          "|---|---:|---|---|---:|---:|---:|"]
    for T in sorted({r["horizon_h"] for r in sched}):
        g = [r for r in sched if r["horizon_h"] == T]
        L.append(f"| {T} h | {g[0]['shifts']:,} | yes | "
                 f"{'yes' if all(r['lp_max_frac'] <= FRAC_TOL for r in g) else 'NO'} | "
                 f"{max(r['mip_nodes'] for r in g)} | {fmt_s(statistics.median(r['lp_s'] for r in g))} | "
                 f"{fmt_s(statistics.median(r['mip_s'] for r in g))} |")
    c3 = overnight[0]
    rnd = overnight[1:]
    frac = [r for r in rnd if r["lp_max_frac"] > FRAC_TOL]
    gap = [r for r in rnd if r["mip_value"] - r["lp_value"] > OBJ_TOL]
    branched = [r for r in rnd if r["mip_nodes"] > 1]
    L += ["", "## C2. Overnight shifts (circular ones, not TU): LP vs MIP", "",
          f"C3 example (3 hours in a cycle, demand 1, shifts of 2 hours): LP = {c3['lp_value']:g} "
          f"with x = ({c3['lp_x']}), MIP = {c3['mip_value']:g}.", "",
          f"{len(rnd)} random 24-hour cyclic instances (same demand and shift lengths as C1, shifts may wrap past midnight):", "",
          "| Measure | Count | Share |", "|---|---:|---:|",
          f"| LP solution fractional | {len(frac)} | {100 * len(frac) / len(rnd):.0f}% |",
          f"| LP value < MIP value (relaxation not exact) | {len(gap)} | {100 * len(gap) / len(rnd):.0f}% |",
          f"| MIP needed branching (> 1 node) | {len(branched)} | {100 * len(branched) / len(rnd):.0f}% |",
          f"| MIP optimum = LP value rounded up (when not exact) | {sum(r['mip_value'] == np.ceil(r['lp_value'] - OBJ_TOL) for r in gap)} | of {len(gap)} |"]
    if gap:
        gaps = [r["mip_value"] - r["lp_value"] for r in gap]
        L += ["", f"When the LP was not exact, MIP − LP ranged from {min(gaps):.3g} to {max(gaps):.3g} staff "
              f"(median {statistics.median(gaps):.3g})."]
    path.write_text("\n".join(L) + "\n")


# ---------------------------------------------------------------- optional node check

NODE_CHECK_MIP = {"presolve": "off", "mip_heuristic_effort": 0.0}


def run_node_check(n_instances=200):
    """Optional (python3 e4.py --node-check). Does the MIP need branching once
    presolve and primal heuristics are switched off? Same model and demand
    distribution as Part C, but its own random instances (seed SEED + 1), so the
    main results are unaffected. Node counts are deterministic (no timings)."""
    rng = np.random.default_rng(SEED + 1)
    T = 24
    mats = {"day": coverage_matrix(T, shifts(T, cyclic=False)),
            "overnight": coverage_matrix(T, shifts(T, cyclic=True))}
    rows = []
    A3 = coverage_matrix(3, [(0, 2), (1, 2), (2, 2)])
    cases = [("overnight", "C3 example", A3, np.ones(3, dtype=int))]
    for i in range(n_instances):
        d = demand_profile(T, rng)
        cases += [(kind, f"random {i}", A, d) for kind, A in mats.items()]
    for kind, name, A, d in cases:
        lp = scheduling_model(A, d, integer=False)
        lp.run()
        mip = scheduling_model(A, d, integer=True, mip_options=NODE_CHECK_MIP)
        mip.run()
        assert mip.getModelStatus() == highspy.HighsModelStatus.kOptimal
        lp_val = lp.getInfo().objective_function_value
        mip_val = mip.getInfo().objective_function_value
        rows.append({"shifts": kind, "instance": name, "lp_value": round(lp_val, 6),
                     "mip_value": round(mip_val, 6), "lp_exact": abs(lp_val - mip_val) <= OBJ_TOL,
                     "mip_nodes": mip.getInfo().mip_node_count})
    RESULTS.mkdir(exist_ok=True)
    write_csv(rows, RESULTS / "node_check.csv")
    for kind in ("day", "overnight"):
        g = [r for r in rows if r["shifts"] == kind]
        print(f"{kind}: {len(g)} instances, LP not exact on {sum(not r['lp_exact'] for r in g)}, "
              f"MIP nodes > 1 on {sum(r['mip_nodes'] > 1 for r in g)} "
              f"(max {max(r['mip_nodes'] for r in g)})", file=sys.stderr)
    print(f"wrote {RESULTS / 'node_check.csv'}", file=sys.stderr)


def main():
    rng = np.random.default_rng(SEED)
    RESULTS.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    log = lambda msg: print(f"[{time.perf_counter() - t0:6.0f} s] {msg}", file=sys.stderr, flush=True)

    # Each part's CSV is written as soon as that part finishes.
    flow = []
    for family, name, inst in flow_instances(rng):
        log(f"flow: {name}")
        flow.append(run_flow(family, name, inst))
    assert all(integral(r) == "yes" for r in flow), "flow LP not integral"
    write_csv(flow, RESULTS / "flow.csv")

    matching = []
    for family, name, inst in matching_instances(rng):
        log(f"matching: {name}")
        matching.append(run_matching(family, name, inst))
    assert all(integral(r) == "yes" and r["vc_lp_max_frac"] <= FRAC_TOL for r in matching)
    write_csv(matching, RESULTS / "matching.csv")

    log("scheduling: day shifts")
    sched = run_scheduling(rng)
    assert all(r["lp_max_frac"] <= FRAC_TOL for r in sched), "day-shift LP not integral"
    write_csv(sched, RESULTS / "scheduling.csv")

    log("scheduling: overnight shifts")
    overnight = run_overnight(rng)
    assert overnight[0]["lp_value"] == 1.5 and overnight[0]["mip_value"] == 2
    write_csv(overnight, RESULTS / "overnight.csv")

    (RESULTS / "metadata.json").write_text(json.dumps(environment(), indent=2) + "\n")
    write_markdown(flow, matching, sched, overnight, RESULTS / "results.md")
    log(f"done, wrote {RESULTS}")


if __name__ == "__main__":
    if "--node-check" in sys.argv[1:]:
        run_node_check()
    else:
        main()
