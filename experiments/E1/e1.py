"""E1: Is TU necessary for one vertex-cover LP to be exact?

Run: python e1.py
Check independently: python e1.py --check
Inputs: data/graphs.jsonl; outputs: results/results.csv and results/results.md.

SciPy's public linprog and milp interfaces both call HiGHS. Graph generation
and bipartiteness use the standard library, so networkx/highspy are not needed.
See README.md for the sampling distribution, tolerances and interpretation.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import random
import statistics
import time

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"
TOL = 1e-6
LP_OPTIONS = {"presolve": False, "primal_feasibility_tolerance": 1e-8,
              "dual_feasibility_tolerance": 1e-8}
MIP_OPTIONS = {"presolve": True, "mip_rel_gap": 0.0, "time_limit": 30.0}


def require(condition, message):
    """Unlike assert, these experimental checks also run under python -O."""
    if not condition:
        raise RuntimeError(message)


@dataclass(frozen=True)
class Graph:
    n: int
    edges: tuple[tuple[int, int], ...]

    def __post_init__(self):
        require(self.n >= 1, "The graph must contain at least one vertex")
        require(self.edges == tuple(sorted(set(self.edges))), "Edges must be sorted and unique")
        require(all(0 <= u < v < self.n for u, v in self.edges), "Not a simple graph on 0,...,n-1")

    @classmethod
    def make(cls, n, edges):
        return cls(n, tuple(sorted({tuple(sorted(e)) for e in edges})))

    def adjacency(self):
        adj = [[] for _ in range(self.n)]
        for u, v in self.edges:
            adj[u].append(v)
            adj[v].append(u)
        return adj


def odd_cycle(graph):
    """Return a simple odd cycle (vertices, without repeated start), or None.

    BFS tries to two-colour every connected component. A same-colour edge,
    together with the two tree paths to their lowest common ancestor, gives
    an odd cycle. This is also the certificate that the VC matrix is not TU.
    """
    adj = graph.adjacency()
    colour, parent = [-1] * graph.n, [-1] * graph.n
    for root in range(graph.n):
        if colour[root] != -1:
            continue
        colour[root] = 0
        queue = deque([root])
        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if colour[v] == -1:
                    colour[v], parent[v] = 1 - colour[u], u
                    queue.append(v)
                elif colour[v] == colour[u]:
                    path_u, path_v = [u], [v]
                    while parent[path_u[-1]] != -1:
                        path_u.append(parent[path_u[-1]])
                    while parent[path_v[-1]] != -1:
                        path_v.append(parent[path_v[-1]])
                    while (len(path_u) > 1 and len(path_v) > 1
                           and path_u[-2] == path_v[-2]):
                        path_u.pop()
                        path_v.pop()
                    cycle = path_u + list(reversed(path_v[:-1]))
                    validate_cycle(graph, cycle)
                    return cycle
    return None


def validate_cycle(graph, cycle):
    require(len(cycle) >= 3 and len(cycle) % 2 == 1, "Witness is not an odd cycle")
    require(len(set(cycle)) == len(cycle), "Witness repeats a vertex")
    edges = set(graph.edges)
    require(all(tuple(sorted((cycle[i], cycle[(i + 1) % len(cycle)]))) in edges
                for i in range(len(cycle))), "Witness uses a missing edge")


def determinant_bareiss(matrix):
    """Exact integer determinant; used only on the odd-cycle witness matrix."""
    a = [list(map(int, row)) for row in matrix]
    n, sign, previous = len(a), 1, 1
    for k in range(n - 1):
        if a[k][k] == 0:
            pivot = next((i for i in range(k + 1, n) if a[i][k]), None)
            if pivot is None:
                return 0
            a[k], a[pivot], sign = a[pivot], a[k], -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                value = a[i][j] * a[k][k] - a[i][k] * a[k][j]
                require(value % previous == 0, "Non-exact Bareiss division")
                a[i][j] = value // previous
        previous = a[k][k]
        for i in range(k + 1, n):
            a[i][k] = 0
    return sign * a[-1][-1]


def witness_determinant(cycle):
    k = len(cycle)
    # Rows are the cycle's edges in cyclic order, columns its vertices.
    matrix = [[int(j == i or j == (i + 1) % k) for j in range(k)] for i in range(k)]
    det = determinant_bareiss(matrix)
    require(abs(det) == 2, "Odd-cycle incidence determinant must have magnitude 2")
    return det


def component_count(graph):
    adj, seen, count = graph.adjacency(), set(), 0
    for root in range(graph.n):
        if root in seen:
            continue
        count += 1
        seen.add(root)
        stack = [root]
        while stack:
            for v in adj[stack.pop()]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
    return count


def incidence(graph):
    """Sparse A, one edge per row and one vertex per column; Ax >= 1."""
    m = len(graph.edges)
    columns = np.asarray(graph.edges, dtype=np.int32).reshape(-1)
    return coo_matrix((np.ones(2 * m), (np.repeat(np.arange(m), 2), columns)),
                      shape=(m, graph.n)).tocsc()


def validate_solution(graph, x, integral=False):
    require(len(x) == graph.n and np.all(np.isfinite(x)), "Invalid solution vector")
    require(np.min(x) >= -TOL and np.max(x) <= 1 + TOL, "A bound is violated")
    require(all(x[u] + x[v] >= 1 - TOL for u, v in graph.edges), "An edge is uncovered")
    if integral:
        require(np.max(np.abs(x - np.rint(x))) <= TOL, "ILP answer is fractional")


def rationalise(values):
    result = [Fraction(float(v)).limit_denominator(1_000_000) for v in values]
    require(all(abs(float(a) - float(b)) <= TOL for a, b in zip(result, values)),
            "Dual multipliers cannot be reconstructed accurately")
    return result


def exact_lp_certificate(graph, x, y, z):
    """Check a primal/dual certificate using rational arithmetic.

    Primal: min 1^T x, Ax >= 1, 0 <= x <= 1.
    Dual:   max 1^T y - 1^T z, A^T y - z <= 1, y,z >= 0.
    z accounts for the upper bounds; do not silently omit bound multipliers.
    """
    require(np.max(np.abs(2 * x - np.rint(2 * x))) <= TOL, "Simplex answer is not half-integral")
    px = [Fraction(int(round(2 * value)), 2) for value in x]
    dy, dz = rationalise(y), rationalise(z)
    require(all(0 <= a <= 1 for a in px), "Exact primal bound failed")
    require(all(px[u] + px[v] >= 1 for u, v in graph.edges), "Exact primal edge failed")
    require(all(a >= 0 for a in dy + dz), "Exact dual multiplier is negative")
    loads = [Fraction(0) for _ in range(graph.n)]
    for (u, v), value in zip(graph.edges, dy):
        loads[u] += value
        loads[v] += value
    require(all(a - b <= 1 for a, b in zip(loads, dz)), "Exact dual constraint failed")
    require(sum(px) == sum(dy) - sum(dz), "Exact primal/dual objectives differ")
    return px, dy, dz


def brute_force_cover(graph):
    """Independent ground truth for small graphs, with no optimisation library."""
    for k in range(graph.n + 1):
        for subset in itertools.combinations(range(graph.n), k):
            selected = set(subset)
            if all(u in selected or v in selected for u, v in graph.edges):
                return k
    raise RuntimeError("All vertices should be a cover")


def solve_graph(graph, repeats=1, time_limit=30.0):
    b_matrix, cost = incidence(graph), np.ones(graph.n)
    lp_times, mip_times = [], []
    lp = mip = None
    for _ in range(repeats):
        start = time.perf_counter()
        lp = linprog(cost, A_ub=-b_matrix, b_ub=-np.ones(len(graph.edges)),
                     bounds=(0, 1), method="highs-ds", options=LP_OPTIONS)
        lp_times.append(time.perf_counter() - start)
        require(lp.success and lp.status == 0, f"LP did not prove optimality: {lp.message}")
        start = time.perf_counter()
        mip = milp(cost, integrality=np.ones(graph.n), bounds=Bounds(0, 1),
                   constraints=LinearConstraint(b_matrix, 1, np.inf),
                   options={**MIP_OPTIONS, "time_limit": time_limit})
        mip_times.append(time.perf_counter() - start)
        require(mip.success and mip.status == 0, f"ILP did not prove optimality: {mip.message}")
    validate_solution(graph, lp.x)
    validate_solution(graph, mip.x, integral=True)
    require(abs(sum(lp.x) - lp.fun) <= TOL and abs(sum(mip.x) - mip.fun) <= TOL,
            "Solution and reported objective disagree")
    # A_ub=-A, so y is the negative of the inequality marginal. Upper-bound
    # marginals are also nonpositive; their negatives are z in the dual.
    px, dy, dz = exact_lp_certificate(graph, lp.x, -lp.ineqlin.marginals, -lp.upper.marginals)
    lp_value, ilp_value = float(sum(px)), int(round(mip.fun))
    require(abs(mip.fun - ilp_value) <= TOL, "Noninteger ILP objective")
    require(lp_value <= ilp_value, "LP lower bound exceeds integer optimum")
    require(mip.mip_gap <= TOL and abs(mip.mip_dual_bound - ilp_value) <= TOL,
            "ILP proof bound does not match its incumbent")
    lp_integral = all(a.denominator == 1 for a in px)
    exact = int(2 * lp_value) == 2 * ilp_value
    require(not lp_integral or exact, "An integral LP optimum must be exact")
    # In a minimisation problem this is the conventional ratio, >= 1.
    ratio = ilp_value / lp_value if lp_value else None
    half_count = sum(a == Fraction(1, 2) for a in px)
    rounded = [int(a >= Fraction(1, 2)) for a in px]
    validate_solution(graph, rounded, integral=True)
    require(sum(rounded) <= 2 * lp_value, "Threshold rounding exceeds 2*LP")
    enumerated = brute_force_cover(graph) if graph.n <= 12 else None
    require(enumerated is None or enumerated == ilp_value, "Enumeration disagrees with ILP")
    cycle = odd_cycle(graph)
    determinant = witness_determinant(cycle) if cycle is not None else None
    category = ("exact_integral" if lp_integral else
                "exact_fractional" if exact else "positive_gap")
    metrics = {
        "n": graph.n, "m": len(graph.edges), "components": component_count(graph),
        "isolates": sum(not neighbours for neighbours in graph.adjacency()),
        "nonbipartite": cycle is not None, "odd_cycle_length": len(cycle) if cycle else 0,
        "witness_determinant": determinant, "lp_value": lp_value, "ilp_value": ilp_value,
        "exact": exact, "lp_integral": lp_integral, "category": category,
        "half_count": half_count, "gap_additive": ilp_value - lp_value,
        "gap_ratio": ratio, "rounded_size": sum(rounded),
        "lp_ms": 1000 * statistics.median(lp_times),
        "ilp_ms": 1000 * statistics.median(mip_times), "lp_iterations": int(lp.nit),
        "mip_nodes": int(mip.mip_node_count), "mip_dual_bound": float(mip.mip_dual_bound),
        "mip_gap": float(mip.mip_gap), "brute_force_optimum": enumerated,
        "exact_lp_certificate": True,
    }
    certificate = {
        "odd_cycle": cycle, "lp_x": [str(a) for a in px],
        "dual_y": [str(a) for a in dy], "dual_z": [str(a) for a in dz],
        "ilp_x": [int(round(a)) for a in mip.x],
    }
    return metrics, certificate


def cycle_graph(n):
    return Graph.make(n, [(i, (i + 1) % n) for i in range(n)])


def controls():
    """(name, graph, analytical LP optimum, analytical ILP optimum)."""
    yield "C3", cycle_graph(3), 1.5, 2
    yield "C4", cycle_graph(4), 2, 2
    yield "C5", cycle_graph(5), 2.5, 3
    yield "C6", cycle_graph(6), 3, 3
    yield "square_diagonal", Graph.make(4, cycle_graph(4).edges + ((0, 2),)), 2, 2
    yield "triangle_leaf", Graph.make(4, ((0, 1), (0, 2), (1, 2), (0, 3))), 2, 2
    yield "triangle_three_leaves", Graph.make(6, ((0, 1), (0, 2), (1, 2), (0, 3), (1, 4), (2, 5))), 3, 3
    yield "two_triangles", Graph.make(6, ((0, 1), (0, 2), (1, 2), (3, 4), (3, 5), (4, 5))), 3, 4
    for n in (4, 8):
        yield f"K{n}", Graph.make(n, itertools.combinations(range(n), 2)), n / 2, n - 1
    yield "triangle_isolate", Graph.make(4, cycle_graph(3).edges), 1.5, 2
    yield "empty4", Graph.make(4, ()), 0, 0


def erdos_renyi(n, p, rng):
    """G(n,p): include each possible edge independently with probability p."""
    return Graph.make(n, ((u, v) for u in range(n) for v in range(u + 1, n)
                          if rng.random() < p))


def wilson_interval(successes, total):
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z * z / total
    centre = (rate + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total**2)) / denominator
    return max(0, centre - radius), min(1, centre + radius)


def summarise(rows, proposals):
    groups = defaultdict(list)
    for row in rows:
        if row["kind"] == "random":
            groups[(row["n"], row["p"])].append(row)
    summaries = []
    for (n, p), group in sorted(groups.items()):
        total = len(group)
        exact_count = sum(r["exact"] for r in group)
        low, high = wilson_interval(exact_count, total)
        summaries.append({
            "n": n, "p": p, "accepted": total, "proposals": proposals[(n, p)],
            "acceptance_rate": total / proposals[(n, p)], "exact_count": exact_count,
            "exact_rate": exact_count / total, "exact_wilson_low": low, "exact_wilson_high": high,
            "integral_count": sum(r["lp_integral"] for r in group),
            "exact_fractional_count": sum(r["category"] == "exact_fractional" for r in group),
            "positive_gap_count": sum(r["category"] == "positive_gap" for r in group),
            "mean_gap_additive": statistics.mean(r["gap_additive"] for r in group),
            "mean_gap_ratio": statistics.mean(r["gap_ratio"] for r in group),
            "max_gap_ratio": max(r["gap_ratio"] for r in group),
            "mean_half_fraction": statistics.mean(r["half_count"] / n for r in group),
            "median_lp_ms": statistics.median(r["lp_ms"] for r in group),
            "median_ilp_ms": statistics.median(r["ilp_ms"] for r in group),
        })
    return summaries


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_results(path, rows, summaries, args):
    random_rows = [r for r in rows if r["kind"] == "random"]
    exact = sum(r["exact"] for r in random_rows)
    integral = sum(r["lp_integral"] for r in random_rows)
    exact_fractional = exact - integral
    lines = ["# E1 measured results", "", "Generated by `e1.py`; see `metadata.json` for the full environment.", "",
             f"Random non-bipartite graphs: **{len(random_rows)}**; LP = ILP: **{exact}**; "
             f"simplex answer integral: **{integral}**; equal values but fractional answer: **{exact_fractional}**.", "",
             "The pooled count gives equal weight to the chosen parameter cells. It is not an estimate "
             "for all non-bipartite graphs. The rates below are conditional on non-bipartiteness.", "",
             "## Analytical controls", "", "| Instance | n | m | Non-bipartite | LP | ILP | Half coordinates | Category |",
             "|---|---:|---:|---|---:|---:|---:|---|"]
    for r in rows:
        if r["kind"] == "control":
            lines.append(f"| {r['instance']} | {r['n']} | {r['m']} | {r['nonbipartite']} | "
                         f"{r['lp_value']:g} | {r['ilp_value']} | {r['half_count']} | {r['category']} |")
    lines += ["", "## Random graphs", "", "95% Wilson intervals describe per-cell binomial sampling uncertainty.", "",
              "| n | p | Kept/drawn | LP=ILP | Exact rate [95% CI] | Integral answer | Exact but fractional | Mean ILP/LP | Max ILP/LP |",
              "|---:|---:|---:|---:|---|---:|---:|---:|---:|"]
    for s in summaries:
        lines.append(f"| {s['n']} | {s['p']:g} | {s['accepted']}/{s['proposals']} | {s['exact_count']} | "
                     f"{100*s['exact_rate']:.1f}% [{100*s['exact_wilson_low']:.1f}, {100*s['exact_wilson_high']:.1f}] | "
                     f"{s['integral_count']} | {s['exact_fractional_count']} | "
                     f"{s['mean_gap_ratio']:.4f} | {s['max_gap_ratio']:.4f} |")
    lines += ["", "## Validation", "", "- Both solvers proved optimality for every recorded instance.",
              "- Every LP has an independently checked, exact rational primal/dual certificate.",
              "- Every non-bipartite instance has a verified odd cycle with determinant magnitude 2.",
              "- All simplex coordinates are in {0, 1/2, 1}; every ILP vector is a valid 0/1 cover.",
              "- All analytical control optima agree; all instances with n <= 12 agree with exhaustive cover enumeration.",
              "- Every threshold-rounded LP vector is a cover of size at most 2 * LP.", "",
              "## Timing scope", "",
              f"Per-instance times are the median of {args.repeats} call(s). Sparse matrix construction is excluded; "
              "SciPy/HiGHS conversion, presolve (ILP only), solving and postsolve are included. "
              "These are diagnostic timings, not a controlled LP-versus-ILP speed benchmark.", "",
              "## Interpretation", "",
              "An exact non-TU example refutes the claim that TU is necessary for one objective and right-hand side. "
              "It does not refute the all-integer-right-hand-sides characterisation of TU. "
              "A fractional returned answer can occur even when an integral optimum exists. "
              "An integer-valued LP objective also need not imply exactness (two disjoint triangles).", ""]
    path.write_text("\n".join(lines))


def metadata(args):
    highs_version = "not exposed by this SciPy build"
    try:  # Metadata only; all solves use public SciPy APIs.
        from scipy.optimize._highspy import _core
        highs_version = ".".join(str(getattr(_core, f"HIGHS_VERSION_{part}"))
                                 for part in ("MAJOR", "MINOR", "PATCH"))
    except (ImportError, AttributeError):
        pass
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
        "highs": highs_version, "platform": platform.platform(), "processor": platform.processor(),
        "seed": args.seed, "n_values": args.n, "p_values": args.p, "samples_per_cell": args.samples,
        "repeats": args.repeats, "tolerance": TOL, "lp_options": LP_OPTIONS,
        "mip_options": {**MIP_OPTIONS, "time_limit": args.time_limit},
        "sampling": "Independent G(n,p) draws, reject bipartite graphs, keep first samples per cell",
        "cell_seed_rule": "seed + 1000003*n_index + 10007*p_index (zero-based CLI list indices)",
        "solver_threads_and_seed": "HiGHS defaults; graph RNG seeded separately",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "command": f"python e1.py --seed {args.seed} --samples {args.samples} --n "
                   + " ".join(map(str, args.n)) + " --p " + " ".join(map(str, args.p))
                   + f" --repeats {args.repeats} --time-limit {args.time_limit}",
    }


def input_parameters(args):
    return {"seed": args.seed, "n": args.n, "p": args.p, "samples": args.samples}


def generate_inputs(args):
    """Known controls, then independent G(n,p) draws conditioned on non-bipartiteness."""
    inputs = []
    for name, graph, expected_lp, expected_ilp in controls():
        inputs.append({"kind": "control", "instance": name, "p": "", "cell_seed": "", "draw": "",
                       "n": graph.n, "edges": graph.edges,
                       "expected_lp": expected_lp, "expected_ilp": expected_ilp})
    for ni, n in enumerate(args.n):
        for pi, p in enumerate(args.p):
            cell_seed = args.seed + 1_000_003 * ni + 10_007 * pi
            rng, kept, drawn = random.Random(cell_seed), 0, 0
            while kept < args.samples:
                require(drawn < args.max_proposals, f"Rejection budget reached at n={n}, p={p}")
                drawn += 1
                graph = erdos_renyi(n, p, rng)
                if odd_cycle(graph) is None:
                    continue
                inputs.append({"kind": "random", "instance": f"n{n}_p{p:g}_{kept:03d}",
                               "p": p, "cell_seed": cell_seed, "draw": drawn,
                               "n": graph.n, "edges": graph.edges})
                kept += 1
    return inputs


def load_inputs(args):
    """Replay saved edge lists; generate only if missing or explicitly requested."""
    DATA.mkdir(exist_ok=True)
    path = DATA / "graphs.jsonl"
    if not path.exists() or args.regenerate:
        inputs = generate_inputs(args)
        with path.open("w") as f:
            f.write(json.dumps({"parameters": input_parameters(args)}) + "\n")
            for record in inputs:
                f.write(json.dumps(record, separators=(",", ":")) + "\n")
        return inputs
    with path.open() as f:
        header = json.loads(next(f))
        require(header["parameters"] == input_parameters(args),
                "Saved parameters differ; use --regenerate to generate the requested dataset")
        return [json.loads(line) for line in f if line.strip()]


def self_check():
    """Exhaustive independent checks, kept here so E1 needs no test folder."""
    count = 0
    for n in range(1, 6):
        possible = list(itertools.combinations(range(n), 2))
        for mask in range(1 << len(possible)):
            graph = Graph.make(n, [edge for i, edge in enumerate(possible) if mask & (1 << i)])
            # Independent colouring enumeration checks the BFS implementation.
            bipartite = any(all(((bits >> u) & 1) != ((bits >> v) & 1)
                                for u, v in graph.edges) for bits in range(1 << n))
            require((odd_cycle(graph) is None) == bipartite, "Colouring cross-check failed")
            row, _ = solve_graph(graph)
            require(row["ilp_value"] == brute_force_cover(graph), "Cover cross-check failed")
            require(not bipartite or (row["exact"] and row["lp_integral"]),
                    "Bipartite LP was not integral and exact")
            count += 1
    for name, graph, expected_lp, expected_ilp in controls():
        row, _ = solve_graph(graph)
        require(row["lp_value"] == expected_lp and row["ilp_value"] == expected_ilp,
                f"Analytical control failed: {name}")
    diamond = Graph.make(4, ((0, 1), (1, 2), (2, 3), (0, 3), (0, 2)))
    # Its all-half optimum is a vertex: four tight rows have nonzero determinant.
    require(abs(determinant_bareiss(incidence(diamond).toarray()[:4])) == 2,
            "Diamond fractional-vertex check failed")
    require(count == 1099, "Wrong number of exhaustive checks")
    print(f"PASS: all {count} simple graphs on 1..5 vertices, 12 controls and diamond vertex check.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", nargs="+", type=int, default=[10, 20, 40, 60])
    parser.add_argument("--p", nargs="+", type=float, default=[0.05, 0.1, 0.2, 0.4, 0.7])
    parser.add_argument("--samples", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--max-proposals", type=int, default=1_000_000)
    parser.add_argument("--output", type=Path, default=RESULTS)
    parser.add_argument("--regenerate", action="store_true", help="Replace the saved graph dataset")
    parser.add_argument("--check", action="store_true", help="Run exhaustive small checks and exit")
    args = parser.parse_args()
    if (args.samples < 1 or args.repeats < 1 or args.time_limit <= 0 or args.max_proposals < 1
            or any(n < 3 for n in args.n) or any(not 0 < p <= 1 for p in args.p)
            or len(set(args.n)) != len(args.n) or len(set(args.p)) != len(args.p)):
        parser.error("Use positive limits, distinct n >= 3 and distinct 0 < p <= 1")
    if args.check:
        self_check()
        return
    inputs = load_inputs(args)
    args.output.mkdir(parents=True, exist_ok=True)
    rows, proposals, solutions = [], {}, []
    cells = defaultdict(list)
    for record in inputs:
        graph = Graph.make(record["n"], record["edges"])
        metrics, certificate = solve_graph(graph, args.repeats, args.time_limit)
        if record["kind"] == "control":
            require(metrics["lp_value"] == record["expected_lp"]
                    and metrics["ilp_value"] == record["expected_ilp"],
                    f"Analytical control failed: {record['instance']}")
        else:
            require(metrics["nonbipartite"], f"Bipartite random input: {record['instance']}")
            key = (graph.n, record["p"])
            proposals[key] = max(proposals.get(key, 0), record["draw"])
        row = {key: record[key] for key in ("kind", "instance", "p", "cell_seed", "draw")}
        row.update(metrics)
        rows.append(row)
        solutions.append({"instance": row["instance"], **certificate})
        if row["kind"] == "random":
            key = (row["n"], row["p"])
            cells[key].append(row)
            if len(cells[key]) == args.samples:
                group = cells[key]
                print(f"n={key[0]:2} p={key[1]:.2f}: accepted {len(group)}/{proposals[key]}, "
                      f"exact={sum(r['exact'] for r in group)}, "
                      f"integral={sum(r['lp_integral'] for r in group)}", flush=True)
    require(len(rows) == 12 + len(args.n) * len(args.p) * args.samples, "Wrong dataset size")
    require(all(len(group) == args.samples for group in cells.values()), "Incomplete cell")
    summaries = summarise(rows, proposals)
    write_csv(args.output / "results.csv", rows)
    write_csv(args.output / "summary.csv", summaries)
    with (args.output / "solutions.jsonl").open("w") as f:
        for record in solutions:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
    info = metadata(args)
    info["input_file"] = "data/graphs.jsonl"
    info["input_sha256"] = hashlib.sha256((DATA / "graphs.jsonl").read_bytes()).hexdigest()
    info["data_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (args.output / "results.csv", args.output / "summary.csv",
                                     args.output / "solutions.jsonl")}
    (args.output / "metadata.json").write_text(json.dumps(info, indent=2) + "\n")
    write_results(args.output / "results.md", rows, summaries, args)
    print(f"Wrote {len(rows)} checked results to {args.output}", flush=True)


if __name__ == "__main__":
    main()
