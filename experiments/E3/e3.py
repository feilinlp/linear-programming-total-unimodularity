"""E3: Does the LP algorithm matter?

Solves the vertex cover LP (VC LP)

    min sum_v x_v  s.t.  x_u + x_v >= 1 for every edge {u, v},  0 <= x <= 1

on bipartite graphs (constraint matrix TU) with HiGHS in three configurations,
all with presolve off so that we compare the algorithms themselves:

    simplex   dual simplex
    ipm+x     interior point method (IPM), then crossover
    ipm       IPM alone (run_crossover = "off")

Prediction: simplex and IPM + crossover always return an integral optimal
vertex (Hoffman-Kruskal). IPM alone ends in the relative interior of the optimal
face, so it is fractional on exactly the "free" vertices: those that lie in some
but not all minimum vertex covers.

Run from this folder:  python3 e3.py
Writes results/results.csv (every measurement) and results/results.md (tables).
"""

import csv
import platform
import statistics
import sys
import time
from pathlib import Path

import highspy
import networkx as nx
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"

FRAC_TOL = 1e-6        # x_v counts as fractional if |x_v - round(x_v)| > FRAC_TOL
OBJ_RTOL = 1e-6        # relative tolerance when comparing optimal values
LP_CHECK_MAX_N = 2000  # cross-check the free set with 2n LPs up to this many vertices
REPEATS = 3            # runtimes are the median over this many solves

CONFIGS = {
    "simplex": {"solver": "simplex", "simplex_strategy": 1},  # 1 = dual simplex
    "ipm+x": {"solver": "ipm", "run_crossover": "on"},
    "ipm": {"solver": "ipm", "run_crossover": "off"},
}

KONECT = [  # (instance name, edge list)
    ("Unicode languages", DATA / "unicodelang" / "out.unicodelang"),
    ("Crime", DATA / "moreno_crime" / "out.moreno_crime_crime"),
    ("arXiv cond-mat", DATA / "opsahl-collaboration" / "out.opsahl-collaboration"),
]


# ---------------------------------------------------------------- instances

def load_konect(path):
    """Bipartite KONECT edge list: column 1 = left id, column 2 = right id.

    Edge weights (column 3, if any) are ignored: E3 uses unit costs.
    """
    G = nx.Graph()
    with open(path) as f:
        header = f.readline()
        assert header.startswith("% bip"), f"{path} is not a bipartite KONECT file"
        for line in f:
            if line.startswith("%") or not line.strip():
                continue
            a, b = line.split()[:2]
            G.add_edge(("L", int(a)), ("R", int(b)))
    return G


def instances():
    """Yield (family, name, graph). Every graph must be bipartite."""
    for k in (2, 10, 50, 500):
        yield "even cycle", f"C{2 * k}", nx.cycle_graph(2 * k)
    for k in (3, 10, 30, 100):
        yield "K_{n,n}", f"K{k},{k}", nx.complete_bipartite_graph(k, k)
    for k in (4, 10, 30, 100):
        yield "grid", f"grid {k}x{k}", nx.grid_2d_graph(k, k)
    # Controls: bipartite graphs with a unique minimum cover (no ties expected).
    for k in (3, 30):
        yield "control", f"K{k},{k + 1}", nx.complete_bipartite_graph(k, k + 1)
    yield "control", "Davis (real)", nx.davis_southern_women_graph()
    for name, path in KONECT:
        yield "real", name, load_konect(path)


# ---------------------------------------------------------------- the VC LP

def build_vc_lp(n, edges, options):
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("presolve", "off")
    for key, value in options.items():
        h.setOptionValue(key, value)
    m = len(edges)
    h.addVars(n, np.zeros(n), np.ones(n))
    h.changeColsCost(n, np.arange(n, dtype=np.int32), np.ones(n))
    # one row x_u + x_v >= 1 per edge, added in a single call (CSR format)
    h.addRows(m, np.ones(m), np.full(m, highspy.kHighsInf), 2 * m,
              np.arange(0, 2 * m, 2, dtype=np.int32), edges.ravel(), np.ones(2 * m))
    return h


def solve(n, edges, options):
    """Solve the VC LP REPEATS times; return (objective, x, info, median seconds)."""
    times = []
    for _ in range(REPEATS):
        h = build_vc_lp(n, edges, options)
        start = time.perf_counter()
        h.run()
        times.append(time.perf_counter() - start)
        assert h.getModelStatus() == highspy.HighsModelStatus.kOptimal, h.getModelStatus()
    info = h.getInfo()
    x = np.array(h.getSolution().col_value)
    return info.objective_function_value, x, info, statistics.median(times)


# ---------------------------------------------------------------- free vertices

def free_vertices_matching(G):
    """Vertices in some but not all minimum vertex covers, via a maximum matching.

    By Konig's theorem a minimum cover has |M| vertices for a maximum matching M,
    so it takes exactly one endpoint of every matching edge and no unmatched
    vertex. An unmatched vertex is out of every minimum cover, so all its
    neighbours are in, so their partners in M are out, and so on along
    alternating paths (Konig's construction). Matching edges reached this way
    have a forced choice. On every other matching edge both choices occur in
    some minimum cover, so both endpoints are free.
    Returns (set of free vertices, |M|).
    """
    color = nx.bipartite.color(G)
    left = [v for v in G if color[v] == 0]
    mate = nx.bipartite.hopcroft_karp_matching(G, top_nodes=left)

    out = {v for v in G if v not in mate}  # vertices in no minimum cover
    stack = list(out)
    while stack:
        v = stack.pop()
        for w in G[v]:          # v is out, so neighbour w is in every minimum cover
            u = mate.get(w)     # ... and w's partner u is out
            assert u is not None, "unmatched w adjacent to an out vertex: M not maximum"
            if u not in out:
                out.add(u)
                stack.append(u)

    assert all(mate[v] not in out for v in mate if v in out), "a matching edge left uncovered"
    free = {v for v in mate if v not in out and mate[v] not in out}
    return free, len(mate) // 2


def free_vertices_lp(n, edges, opt):
    """Independent check: x_v is free iff max x_v - min x_v > 1/2 over the optimal face.

    On a TU instance the optimal face has 0/1 vertices, so the range of x_v is
    either 0 (fixed) or 1 (free); 1/2 is a safe threshold.
    """
    h = build_vc_lp(n, edges, {"solver": "simplex"})
    h.addRow(-highspy.kHighsInf, opt + 1e-9, n, np.arange(n, dtype=np.int32), np.ones(n))
    cols = np.arange(n, dtype=np.int32)
    free = set()
    for j in range(n):
        values = []
        for sign in (1.0, -1.0):
            cost = np.zeros(n)
            cost[j] = sign
            h.changeColsCost(n, cols, cost)
            h.run()
            values.append(sign * h.getInfo().objective_function_value)
        if values[1] - values[0] > 0.5:
            free.add(j)
    return free


# ---------------------------------------------------------------- main

def dist_to_int(x):
    return np.abs(x - np.round(x))


def run_instance(family, name, G):
    assert nx.is_bipartite(G), f"{name} is not bipartite, so its matrix is not TU"
    nodes = list(G.nodes())
    index = {v: i for i, v in enumerate(nodes)}
    n = len(nodes)
    edges = np.array([(index[u], index[v]) for u, v in G.edges()], dtype=np.int32)

    free_nodes, matching_size = free_vertices_matching(G)
    free = {index[v] for v in free_nodes}

    row = {"family": family, "instance": name, "n": n, "m": len(edges)}
    sols = {}
    for cname, options in CONFIGS.items():
        obj, x, info, secs = solve(n, edges, options)
        sols[cname] = x
        row[f"{cname}_obj"] = obj
        row[f"{cname}_frac"] = int(np.sum(dist_to_int(x) > FRAC_TOL))
        row[f"{cname}_ms"] = round(1000 * secs, 2)
        row[f"{cname}_simplex_iters"] = info.simplex_iteration_count
        row[f"{cname}_ipm_iters"] = info.ipm_iteration_count
        row[f"{cname}_crossover_iters"] = info.crossover_iteration_count

    opt = row["simplex_obj"]
    for cname in CONFIGS:
        assert abs(row[f"{cname}_obj"] - opt) <= OBJ_RTOL * max(1.0, abs(opt)), (name, cname)
    assert abs(opt - matching_size) <= OBJ_RTOL * max(1.0, opt), "LP optimum != max matching (Konig)"
    row["opt"] = round(opt)
    row["max_matching"] = matching_size
    row["free"] = len(free)

    if n <= LP_CHECK_MAX_N:
        assert free_vertices_lp(n, edges, opt) == free, f"{name}: free sets disagree"
        row["free_checked_by_lp"] = "yes"
    else:
        row["free_checked_by_lp"] = "no (too large)"

    # IPM alone: is it fractional on exactly the free vertices, and by what margin?
    d = dist_to_int(sols["ipm"])
    frac = {j for j in range(n) if d[j] > FRAC_TOL}
    fixed = [j for j in range(n) if j not in free]
    row["ipm_frac_equals_free"] = frac == free
    row["ipm_min_dist_free"] = round(float(min(d[j] for j in free)), 4) if free else ""
    row["ipm_max_dist_fixed"] = float(max((d[j] for j in fixed), default=0.0))
    vals = sols["ipm"][sorted(free)]
    row["ipm_free_at_half"] = round(float(np.mean(np.abs(vals - 0.5) <= 1e-4)), 3) if len(free) else ""
    row["ipm_free_min"] = round(float(vals.min()), 4) if len(free) else ""
    row["ipm_free_max"] = round(float(vals.max()), 4) if len(free) else ""
    # L4's threshold rounding applied to the IPM answer: always a cover, but how big?
    rounded = int(np.sum(sols["ipm"] >= 0.5 - FRAC_TOL))
    row["ipm_rounded_size"] = rounded
    row["ipm_rounded_ratio"] = round(rounded / opt, 3)
    return row


def write_markdown(rows, path):
    env = (f"Python {platform.python_version()}, highspy {highspy.Highs().version()}, "
           f"networkx {nx.__version__}, numpy {np.__version__}, "
           f"{platform.system()} {platform.machine()}")
    lines = ["# E3 results", "", f"Generated by `e3.py`. Environment: {env}.", "",
             f"Presolve off in every run. Fractional means |x_v - round(x_v)| > {FRAC_TOL}. "
             f"Runtimes are the median of {REPEATS} solves.", "",
             "## Integrality", "",
             "| Family | Instance | n | m | OPT | Free (predicted) | Simplex frac | IPM+X frac "
             "| IPM frac | IPM frac = free set? | Free checked by LP |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for r in rows:
        lines.append(f"| {r['family']} | {r['instance']} | {r['n']} | {r['m']} | {r['opt']} | {r['free']} "
                     f"| {r['simplex_frac']} | {r['ipm+x_frac']} | {r['ipm_frac']} "
                     f"| {'yes' if r['ipm_frac_equals_free'] else 'NO'} | {r['free_checked_by_lp']} |")
    lines += ["", "## Where IPM alone ends up", "",
              "Min distance to an integer over free vertices (how clearly fractional) vs max over "
              "fixed vertices (how close to integral). Values of the free coordinates.", "",
              "| Instance | Min dist (free) | Max dist (fixed) | Free coords at 1/2 | Min free value "
              "| Max free value | Rounded at 1/2: size | Size / OPT |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['instance']} | {r['ipm_min_dist_free']} | {r['ipm_max_dist_fixed']:.1e} "
                     f"| {r['ipm_free_at_half']} | {r['ipm_free_min']} | {r['ipm_free_max']} "
                     f"| {r['ipm_rounded_size']} | {r['ipm_rounded_ratio']} |")
    lines += ["", "## Iterations and runtime", "",
              "| Instance | n | Simplex iters | Simplex ms | IPM iters | Crossover iters | IPM+X ms | IPM ms |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['instance']} | {r['n']} | {r['simplex_simplex_iters']} | {r['simplex_ms']} "
                     f"| {r['ipm_ipm_iters']} | {r['ipm+x_crossover_iters']} | {r['ipm+x_ms']} | {r['ipm_ms']} |")
    path.write_text("\n".join(lines) + "\n")


def main():
    RESULTS.mkdir(exist_ok=True)
    rows = []
    for family, name, G in instances():
        row = run_instance(family, name, G)
        rows.append(row)
        print(f"{name:20} n={row['n']:6} free={row['free']:6} frac: simplex={row['simplex_frac']} "
              f"ipm+x={row['ipm+x_frac']} ipm={row['ipm_frac']}  match={row['ipm_frac_equals_free']}",
              flush=True)
    with open(RESULTS / "results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_markdown(rows, RESULTS / "results.md")
    print(f"wrote {RESULTS / 'results.csv'} and {RESULTS / 'results.md'}", file=sys.stderr)


if __name__ == "__main__":
    main()
