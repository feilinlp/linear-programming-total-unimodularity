# When is an LP enough? Total unimodularity and exact integer optimisation

CS4234 Optimization Algorithms (NUS, AY2026/27 Semester 1, instructor Diptarka Chakraborty). Group mini-project.

> **AI assistants working in this repo:** read this whole file before doing anything. It sets the project scope, the course requirements, the notation and the slide style. Follow it unless a team member tells you otherwise in the session. Section 9 lists the rules.

---

## 1. The project in one paragraph

Integer linear programming (ILP) is NP-hard; linear programming (LP) is solvable in polynomial time. Usually the LP relaxation of an ILP returns fractional answers, but for some problems the LP returns an integer optimum "for free". **Research question:** *when does solving an LP give an integer optimum, how do we recognise such problems, and does the LP algorithm we use matter?* The answer centres on **total unimodularity (TU)**: if the constraint matrix A is TU and b is integral, every vertex of {x : Ax ≤ b} is integral (Hoffman–Kruskal 1956).

**Running example (use on every slide):** the vertex cover LP, min Σ xᵥ s.t. x_u + x_v ≥ 1 for each edge, 0 ≤ x ≤ 1.
- On the **triangle C₃** the LP optimum is (½, ½, ½), value 1.5, but the integer optimum is 2. The incidence matrix is not TU.
- On the **4-cycle C₄** the LP returns an integral cover such as (1, 0, 1, 0), value 2. The graph is bipartite, so its incidence matrix is TU.

**Project type:** a reading core plus a small experimental part (Section 5).

## 2. Course requirements (from the official instructions)

**Group:** 3–4 students; expectations are the same for every group size.

**Trailer presentation (Week 9):**
- **8 minutes, hard cap.** The instructors stop the talk at 8:00.
- Every member speaks for roughly the same time (about 2 minutes each), usually 1–2 slides each.
- Present **plans, not results**: introduce the problem, the algorithms or techniques we will study, the intended scope, and whether we do empirical evaluation.
- **Notation, terminology and visual style must be consistent across slides and presenters.**
- Peer review: each student evaluates two other groups' trailers. The questionnaire is due 16 Oct (Fri, Week 9), 23:59.

**Write-up:**
- Due **13 Nov (Fri, Week 13), 23:59**. Exactly one member submits.
- Main body **at most 10 pages, single column, 11pt font**. Do not change this format. Anything beyond goes in a clearly marked appendix.
- Structure: **Introduction** (context, problem, scope, papers covered) → **Preliminaries** (only needed definitions and notation) → **Main content** (2–3 sections, in our own words; methodology and findings for experiments) → **Conclusion** (what we did and learned, plus state of the art beyond our scope) → **Appendix**.
- End with a one-paragraph **AI Disclosure** stating where and how we used AI tools. It does not count towards the 10 pages.
- For the experimental part: describe instances, metrics, parameters and procedure so results are reproducible; connect results to the theory; explain why results agree or differ. **Do not submit only tables and plots.** Put all code and data in this repo and link it in the report.

**Academic rules that apply to everything here, including AI output:**
- We must understand and be able to defend every definition, claim, proof, experiment, citation and line of code. The instructor may interview the group; failing to explain our own work can cost a large share of the marks.
- Focus on one or two results in depth rather than many superficially. If we omit technical details, say so explicitly in the report.
- Verify every citation (Google Scholar) before it goes into slides or the report.

## 3. Related course material

Our project builds on these lectures. Use the same notation and refer to them when it helps the audience.

| Lecture | Content we rely on |
|---|---|
| **L4: LP relaxation, Vertex Cover, MAX-SAT** | ILP is hard; LP relaxation (OPT_LP ≥ OPT_ILP for max, ≤ for min); the four-step recipe (model as ILP → relax → solve LP → round); vertex cover ILP and **threshold rounding at ½ gives a 2-approximation**; randomized rounding for MAX-SAT (1 − 1/e), best-of-two gives ¾ |
| **L4–L5: Network flow 1–2** | Flow definition (capacity, conservation); Ford–Fulkerson; residual network; cuts; **max-flow min-cut theorem**; Ford–Fulkerson takes Θ(mC) time, which is **not polynomial** because C takes only log C bits |
| **L6: Network flow 3** | Capacity scaling, O(m² log c_max); shortest augmenting paths (Edmonds–Karp), O(m²n); history table (Dinitz 1972, O(n³), Orlin O(mn)); flows with lower bounds; **integrality theorem** (integer capacities ⇒ an integral max flow exists); **bipartite matching via max flow**; edge-disjoint paths |
| **L7 (Week 8): Linear programming 1** | Geometry: hyperplanes, halfspaces, feasible polytope; **a bounded nonempty LP has an optimal vertex**; convexity and vertices; standard form; possible outcomes (optimal / infeasible / unbounded); the three LP algorithms in one line each (simplex, ellipsoid, interior point); solvers (Gurobi, CPLEX, MOSEK, SciPy); **duality**: weak and strong duality, dual solution as an optimality certificate; modelling tricks (|x|, max); LP relaxation of vertex cover |

**Where our project connects to the lectures:**
- **L7 says an optimum is at a vertex.** We ask when that vertex is integral (TU).
- **L6's integrality theorem for flows** is a special case of TU: the incidence matrix of a directed graph is TU.
- **L6's bipartite matching via flow** and **König's theorem** come from TU and LP duality (L7).
- **L4's vertex cover rounding** loses a factor of 2 on general graphs; on bipartite graphs the LP is already exact.
- **L4–L6's point that Θ(mC) is not polynomial** is the same "polynomial in the number of bits" idea we use for LP algorithms.

## 4. Notation (use everywhere)

Follow L7's conventions.

| Symbol | Meaning |
|---|---|
| A ∈ ℝ^{m×n} | constraint matrix: **m constraints (rows), n variables (columns)** |
| b, c | right-hand side, objective vector |
| x | primal variables; y for dual variables |
| Standard form | max cᵀx s.t. Ax ≤ b, x ≥ 0. Dual: min bᵀy s.t. Aᵀy ≥ c, y ≥ 0 |
| B, A_B | a basis (set of m linearly independent columns) and the corresponding square submatrix; a basic solution is x_B = A_B⁻¹b |
| L | input size in bits (for complexity statements) |
| C₃, C₄ | triangle and 4-cycle (running example) |
| G = (V, E) | graph; n = \|V\|, m = \|E\| **only in graph contexts** (say so explicitly when it clashes with the LP meaning) |
| TU | totally unimodular: every square submatrix has determinant in {−1, 0, 1} |
| VC LP | vertex cover LP: min Σᵥ xᵥ s.t. x_u + x_v ≥ 1 ∀{u,v} ∈ E, 0 ≤ x ≤ 1 |

Terminology: say "interior point method (IPM)", "dual simplex", "crossover", "branch-and-bound (B&B)". Use British or American spelling consistently within one document (the title uses "optimisation"; pick one per file).

## 5. Plan and roles

**Trailer outline (8:00 cap; target ≈ 7:15, leaving 45 s spare):**

| # | Slide | Presenter | Time |
|---|---|---|---|
| 0 | Title | – | – |
| 1 | The problem: C₃ vs C₄, "ILP NP-hard, LP polynomial: when is LP = ILP?" | P1 · Yee Hern | 1:00 |
| 2 | Key technique: TU, Cramer's rule, Hoffman–Kruskal, bipartite ⇔ incidence matrix TU | P1 · Yee Hern | 1:00 |
| 3 | Recognising TU: brute force, Ghouila-Houri, Seymour decomposition (CMR) | P2 · Yock Cheng | 1:30 |
| 4 | Solving the LP: simplex, ellipsoid, interior point; complexity; Klee–Minty | P3 · Feilin | 1:00 |
| 5 | Applications: max-flow, bipartite matching and König, shift scheduling | P4 · Daryl | 0:45 |
| 6 | Empirical evaluation: E1–E4 | P3 · Feilin | 1:00 |
| 7 | Scope and roadmap; frontier | P4 · Daryl | 1:00 |

If we go over time, merge slides 5 and 7.

**Planned experiments** (tools: Python, HiGHS via `highspy`/SciPy, networkx, CMR):

| | Why | Setup | Prediction |
|---|---|---|---|
| **E1** | What happens as we leave the TU world? | Random bipartite graphs; add odd-cycle edges one at a time; solve VC and matching LPs and the ILP (HiGHS B&B) | 0% fractional while bipartite; afterwards values stay in {0, ½, 1} (Nemhauser–Trotter 1975); LP/IP gap grows |
| **E2** | How do we recognise TU in practice? | Brute-force determinants vs Ghouila-Houri vs CMR on growing TU and non-TU matrices | First two exponential, CMR polynomial |
| **E3** | Does the LP algorithm matter? | TU instances with tied optima (even cycles, K_{n,n}, grids); HiGHS dual simplex vs IPM with crossover vs IPM without crossover | Simplex and IPM+crossover always integral; IPM without crossover can return the fractional centre of the optimal face |
| **E4** | If the LP is exact, should we just use it? | Max-flow and bipartite matching; HiGHS LP vs Dinic / Hopcroft–Karp | Same optimum; specialised algorithms faster |

The group plan says to commit to 1–2 of these; agree the final set before Week 9.

**Scope:** Hoffman–Kruskal, bipartite ⇔ TU, Ghouila-Houri (statement and idea), conceptual comparison of LP algorithms, experiments. **Out of scope** (mention only): proof of Seymour's theorem, implementing Seymour or ellipsoid, TDI (Edmonds–Giles), the non-bipartite matching polytope (Edmonds). **Frontier for the conclusion:** bimodular ILP is strongly polynomial (Artmann–Weismantel–Zenklusen, STOC 2017); Δ-modular ILP with two nonzeros per row (Fiorini–Joret–Weltge–Yuditsky); recent progress on nearly-TU and Δ-modular problems.

**Timeline:** trailer in Week 9 → experiments done ≈ Week 11 → full draft Week 12 → submit 13 Nov, 23:59.

## 6. Repository layout

```
README.md          this file (project brief for humans and AI)
CLAUDE.md          pointer to this file for Claude Code
AGENTS.md          pointer to this file for other coding agents
slides/
  deck.html        the single shared trailer deck (all presenters)
  theme.css        shared style; do not override per slide
  deck.js          navigation (←/→, N = notes, F = fullscreen, T = theme)
script/
  P1.md … P4.md    word-for-word talk scripts, one per presenter
notes/
  P1.md … P4.md    each presenter's research summary and references
experiments/       code and data (added later)
report/            the write-up (added later)
```

## 7. Slide style rules (all presenters)

1. **One deck.** Every presenter edits `slides/deck.html`. Each slide is one `<section class="slide">` with `data-owner="P1"` etc. Do not create separate decks.
2. **Use `theme.css` only.** No inline colours or fonts. Colours mean the same thing everywhere:
   - `--good` (green): integral / TU / works
   - `--warn` (orange): fractional / not TU / fails
   - `--accent` (blue): headings, highlights
   - `--muted` (grey): secondary text, "out of scope"
3. **Every slide has:** a kicker (`N · Section`), a title written as a claim or question, **one figure or one table**, and the footer (project name · presenter).
4. **Keep body text short:** short phrases rather than sentences, and no more than about 60 words per slide outside the figure. Details go into the speaker notes (`<aside class="notes">`), not on the slide.
5. Use the C₃ / C₄ running example wherever a picture is needed.
6. Notation from Section 4 only. Math in the `.math` class (serif italic).
7. **Timing.** Each script in `script/` is written at ≈ 140 words per minute and must fit the slot in Section 5. Do one timed full run-through before Week 9.

## 8. Tools

- Python 3, `highspy` (HiGHS: dual simplex, IPM with optional crossover, MIP branch-and-bound). `scipy.optimize.linprog(method="highs-ds" | "highs-ipm")` also uses HiGHS, but use `highspy` when you need to switch crossover off (`run_crossover = "off"`).
- `networkx` for graph generation and the combinatorial baselines (max-flow, Hopcroft–Karp).
- CMR (Combinatorial Matrix Recognition library) for the Seymour-based TU test.

## 9. Rules for AI assistants

1. Read Sections 2, 4 and 7 before writing slides, scripts or report text. Respect the 8-minute cap, the per-presenter time slots, the 10-page limit and the "plans, not results" rule for the trailer.
2. Use the notation in Section 4 and the running example in Section 1. Do not introduce new symbols for existing concepts.
3. Do not edit another presenter's slide, script or notes unless that person asks.
4. **Never invent citations.** Mark any reference you have not checked against the source as unverified. Never present a number, runtime or result as measured unless it came from code in this repo.
5. Keep explanations at the level of the lectures in Section 3. When something goes beyond them, say so, and add a one-line intuition.
6. Prefer short, clear text. Slides: short phrases, about 60 words at most. Scripts: spoken sentences, ≈ 140 words per minute.
7. Record any significant AI help so the team can write the AI Disclosure paragraph.
