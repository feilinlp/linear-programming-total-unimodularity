# Feedback on `main.pdf`

**A newer build has been reviewed:** see [the fresh reread and current findings](feedback-reread.md). The notes below refer to the earlier build and are retained as review history; items marked resolved in the fresh review are no longer current requests for changes.

Reviewed on 12 November 2026. Target: `report/build/main.pdf` (18 pages; SHA-256 `1394df9daeba80715c407d54d1adc564bba0c1ba0cc13aed150c0ca5b2aec96b`). Page numbers below refer to this PDF.

The report has a coherent argument: TU guarantees integral vertices; exactness for one objective is weaker; and the solver determines which optimal point is returned. The triangle, square with a diagonal, and free-vertex examples make these distinctions concrete. The proofs of TU sufficiency, bipartiteness, and half-integrality supply useful depth, and the experiments explain their findings instead of merely listing measurements. I would retain this structure and focus revisions on the points below.

I read the PDF, visually inspected all 18 pages, consulted the LaTeX and official course instructions, and checked selected results against saved CSVs and metadata. I did not rerun the experiments or audit every reference in full. The main body occupies pages 1–10, the source uses single-column 11pt, and the AI Disclosure is one paragraph at the end, as required. I did not find obvious clipping or unresolved cross-references in the rendered document.

## Assessment against the mini-project instructions

This additional assessment uses the actual [mini-project instructions](../../mini-project-instructions.pdf), especially “What to Do” on pages 1–2, “Types of Projects” on page 2, and “On Preparing your Write-up” on page 3. It distinguishes requirements already met from changes needed to support compliance. It is not a predicted grade or a guarantee of acceptance.

| Requirement in the instructions | Assessment of this report | Feedback to fulfil or strengthen it |
| --- | --- | --- |
| Focused question, accurate literature, and evidence of understanding — “Types of Projects”, opening paragraph | The three questions share a clear theme, and worked examples and proofs demonstrate engagement. Coverage is broad for ten pages. | Identify the two central ideas as TU implying integral vertices and the distinction between an integral vertex and another optimal point. Present recognition methods and applications as supporting these ideas. Correct the technical claims identified below. |
| Main body up to ten pages, single column, 11pt — Write-up item 2 | Met for the reviewed build: main text ends on page 10; `main.tex` sets 11pt and a single column. | Recheck the compiled PDF after revisions. Make room by shortening secondary material; preserve the required body format. |
| Introduction gives context, problem, scope and papers covered — Write-up item 3 | Met: pages 1–2 provide the LP/ILP motivation, running example, questions and cited roadmap. | Make the reading focus explicit in one sentence. For example: “Our reading core is the TU-to-integrality proof and the geometry of tied optima; the recognition and application experiments examine their practical implications.” |
| Preliminaries contain relevant definitions and notation — Write-up item 4 | Met: Section 2 defines the concepts used later, including exactness versus integrality. | Retain this distinction and the graph/matrix dimension conventions. Avoid adding textbook background that is not subsequently used. |
| Two to three sections of main technical content — Write-up item 5 | Met: Sections 3, 4 and 5 are exactly three main technical sections. | Retain this structure. Experiments can remain integrated with the relevant theory; a separate experimental section is not required. |
| Explain one or two results carefully, with assumptions, analysis and examples; disclose omissions — “What to Do” item 7 and “Reading project” | Substantially met by the Hoffman–Kruskal sufficiency proof, graph examples and half-integrality proof. The omitted converses and Seymour proof are explicitly acknowledged. | Preserve these proofs. Complete the short free-vertex justification and fix the simplex/IPM guarantees below. Clearly distinguish a conceptual algorithm sketch from a complete implementation. The instructions allow omitted technical details when they are identified; a full Seymour proof is unnecessary. |
| Meaningful baselines, instances, metrics, parameters and procedure — “Implementation or experimental project” and Write-up item 5 | Relevant baselines and experimental setups are present. Some settings essential to interpretation appear only in Appendix A, and environment descriptions need reconciliation. | Put the key presolve, numerical and timing conventions into the main setup paragraphs. Keep full commands, version records and detailed tables in the appendix. Apply corrections 4–6 below. |
| Explain results and connect them to theory, rather than submit only tables or plots — “Implementation or experimental project” | Met: each experiment interprets results using the preceding theory. | Retain explanations of exact non-TU instances, fractional optimal IPM points and early obstructions in recognition. Qualify timing/size summaries and distinguish measured findings from proposed explanations. |
| Accessible code and data, with a repository link in the report — “Implementation or experimental project” | Verified: the report includes the repository URL, and direct unauthenticated GitHub checks found the public repository, all four experiment scripts, READMEs, requirements, saved results and the stored E1–E3 inputs. E4 generates instances and reuses E3 data. | Preserve the link and ensure the final submitted report corresponds to the intended repository revision. A commit identifier would make the results easier to trace. Public availability was checked; a clean reproduction of all experiments was not performed in this review. |
| Conclusion states accomplishments, lessons and relevant state of the art beyond scope — Write-up item 6 | Present on page 10: the three answers, limitations, bounded-subdeterminant results and an open question. | Fix the missing TDI hypothesis and overly broad recognition/timing summaries. Verify that each frontier citation supports the precise claim made. Keep the frontier concise and distinguish known special cases from the general open question. |
| Supporting material in marked appendices; first ten pages are the primary grading basis — Write-up item 7 | Appendices A–C are clearly marked, and main results are in the first ten pages. Some essential experimental controls are deferred. | Make the first ten pages sufficient to understand why each comparison is valid. Move only the short, essential methodological qualifications into the main text; full logs and raw timing tables can stay outside it. |
| Understand and defend every claim, proof, experiment, citation and line of code — “What to Do” item 4 and Write-up item 8 | Cannot be certified by reading a PDF. The explanations provide evidence, but the remaining technical gaps should be resolved. | Each member should be able to explain the central proof, the solver-output distinction, the experimental controls and the scope of the evidence. Check cited results against their actual statements; bibliographic metadata checks alone do not validate the claims. |
| Short, honest, one-paragraph AI Disclosure at the end — Write-up item 9 | The required paragraph is present at the end on page 18 and describes substantial assistance. The source still contains a TODO to confirm its claims. | Confirm the description of AI use, reruns and human review before submission; revise any assertion the group cannot substantiate. Include this feedback/review assistance if used. The paragraph can be shortened while retaining the tools, tasks and extent of assistance; no specific word count is imposed by the instructions. |

The public-access assessment above is based on the [linked project repository](https://github.com/feilinlp/linear-programming-total-unimodularity) and its unauthenticated GitHub API file listing, checked on 12 November 2026. Direct HTTP and API requests returned 200 and confirmed that the repository is public.

### Changes with the most value for the assignment

1. **Make the main experimental descriptions sufficient for assessment.** Add to E3’s setup that presolve is off in all configurations so reductions do not select among tied optima before the compared algorithms run. State E1’s LP presolve setting and zero-gap ILP solve criterion. For E4, identify the timing scope and state that runs exceeding two seconds are not repeated. These facts are currently in Appendix A; the instructor primarily grades the first ten pages. State numerical rounding conventions alongside the relevant E3 result, and identify the 16-instance limit of its second verification method.

2. **Use depth rather than additional breadth to demonstrate understanding.** Prioritise the mathematical corrections and the missing free-vertex justification already listed below. Shorten the historical LP-complexity survey if space is needed. Four experiments are not prohibited, and the instructions do not require another experiment, a new theorem or a state-of-the-art implementation. Retain the experiments that directly answer the stated questions.

3. **Make the contribution and literature boundaries explicit.** Distinguish established theorems and library implementations from the group’s experiments and explanations. Existing text already says CMR was reused and some proofs were omitted. Preserve that honesty, and describe the free-vertex comparison and counterexamples as evidence of engagement without claiming mathematical novelty. When an algorithm is only described conceptually, say which details are omitted.

4. **Keep conclusions within the evidence.** Explain what each experiment establishes and its practical limits: E1 concerns the sampled non-bipartite unit-cost graphs; E2’s measurements do not prove CMR’s asymptotic complexity; E3 tests one solver on bipartite VC instances; and E4 compares particular implementations on particular instances. The current limitation paragraph provides a good starting point. These qualifications help fulfil the requirement for an accurate interpretation of experimental results.

5. **Use the final review to substantiate the AI Disclosure.** The instructions permit AI use without a mark deduction for using it, but require understanding and responsibility. Before retaining “the group has reviewed all AI-assisted material”, complete that review. Useful discussion prompts are why an optimal face can contain fractional points despite integral vertices, why the square with a diagonal is exact but non-TU, why presolve is disabled in E3, and why a timeout is not a measured algorithm completion time. This is preparation for the stated possibility of an interview, not an additional deliverable.

6. **Check the final build and submission.** After edits, inspect the rendered PDF, confirm the main body still ends within ten pages, check links/citations/figures, and ensure the final disclosure is still last. The instructions specify that exactly one member submits by **13 November 2026, 23:59 (Singapore time)**. This review does not verify submission, topic registration, the earlier trailer presentation or individual peer-review completion; those requirements cannot be inferred from `main.pdf`.

These recommendations do not require adding an abstract, a separate related-work section, author-contribution statements, extra experiments or full proofs of every cited result: none is prescribed by the supplied instructions. Formatting suggestions below are readability improvements; table-caption position and landscape appendix figures are not stated course requirements.

## Corrections to prioritise

1. **Algorithm 4 promises more than its pseudocode establishes — page 8, Section 5.1.**

   The output says “an optimal point”, but stopping at positive `epsilon` produces an approximate solution. One Newton step followed by a reduction of `mu` also needs a step-size/centrality condition to justify path following. More significantly, the next stage says to move within the optimal face, although the finite IPM iterate generally has not reached that face.

   Label this explicitly as a schematic explanation, change its output to an approximately optimal point without crossover, and describe crossover as basis recovery followed by feasibility/optimality checks. If retaining executable-looking pseudocode, include a feasibility-preserving Newton step, an appropriate convergence test, and a defined crossover procedure. Include nonnegativity/bound slacks in the barrier or explain that they have already been folded into the inequalities.

   Keep the distinction between an ideal limiting point and the finite solver output explicit. The relative-interior argument is useful; it does not require claiming that every practical IPM returns the same centre. The cited [Güler–Ye paper](https://link.springer.com/article/10.1007/BF01580610) establishes strict-complementarity properties for specified classes of IPMs.

2. **Add the missing hypothesis to the TDI sentence — page 10, “Beyond our scope”.**

   TDI alone does not imply that the primal polyhedron is integral: the right-hand side must also be integral. TDI is a property of the inequality system, rather than just its matrix. Suggested replacement: “A totally dual integral system with an integral right-hand side defines an integral polyhedron, even when its constraint matrix is not TU.” This condition is stated explicitly in [Schrijver’s paper, introduction](https://ir.cwi.nl/pub/2538/2538D.pdf).

3. **Qualify simplex improvement and termination — pages 7–8, Algorithm 3.**

   Degenerate pivots can leave the objective unchanged, and arbitrary choices in the entering-variable and ratio-test steps can cycle. Consequently, the current pseudocode does not guarantee its promised output on every feasible input. Say that pivots *do not worsen* the objective, and either specify an anti-cycling rule or state that termination assumes one. This also makes the later discussion of degeneracy consistent with the algorithm description. Phase I may remain omitted because a feasible basis is explicitly an input.

4. **Separate the environment of the archived measurements from the verification environment — page 14, Appendix A.**

   “All four use one Python environment” obscures the provenance of the saved results. E1’s `results/metadata.json` records Python 3.12.14, SciPy 1.17.0 and HiGHS 1.8.0; its README documents that run. E4’s saved metadata records NumPy 2.4.1, while Appendix A specifies 2.5.4. E4’s README already distinguishes its committed run from a later rerun with the shared pins.

   State that the pinned requirements describe the recommended reproduction environment, identify the original environments separately, and save or link the verification outputs supporting the claimed agreement under the new versions. This does not establish that the reruns failed; it makes their evidence traceable. The distinction matters particularly for E1’s selected optimal vector, since changing the solver can change which tied vertex simplex selects.

5. **State the limits and numerical conventions of the E3 checks — pages 7–9 and Appendix A.**

   The setup says the free vertices were confirmed by a second method. In fact, the independent LP check covered 16 of 18 instances, excluding the `100×100` grid and arXiv. Appendix A explains the size limit, but the main text should say “independently checked on the 16 instances with at most 2,000 vertices”.

   Also document the implementation’s rounding convention: `e3.py` selects coordinates at least `0.5 - 1e-6`, rather than using a literal `0.5` cutoff. The percentage “at one-half” uses a separate `1e-4` tolerance. These are reasonable conventions, but they should accompany claims about rounding and numerical equality. On page 7, write “For the VC LP **on bipartite graphs**” before saying its optimal vertices are 0/1 covers; general VC LP vertices can be fractional, as Section 3.3 proves.

6. **Narrow the E4 timing claim and distinguish explanation from measurement — pages 9–10 and 15.**

   “The LP was always about two orders of magnitude behind the compiled code” overstates the saved table. Relative to compiled Dinic, the dual LP is about 13 times slower on the smallest grid and 31 times slower on the largest grid; the largest random network gives about 654 times. Across the saved flow and matching cases, the ratios depend substantially on instance and simplex variant.

   Suggested wording: “Compiled specialised algorithms were consistently faster; the gap reached roughly two to three orders of magnitude on the largest random instances.” Retain the concrete 300–650 ratio for the largest random flow network.

   The degeneracy explanation is plausible, but the saved pivot counts do not establish how many pivots were degenerate or how much time they caused. Present it as a possible explanation unless degenerate-pivot or profiling measurements are added. Also avoid saying every pivot updates a factorisation: practical solvers can refactorise or use other update strategies.

7. **Qualify the recognition summary — page 10, second conclusion bullet.**

   “Exhaustive tests failed beyond order 10–12” is too broad. Table 2 shows brute force succeeding on embedded triangles through order 35 and GH through all tested embedded-triangle sizes, including 131. Suggested replacement: “On cycles and several TU families, exhaustive recognition became impractical around order 10–12; small, early obstructions allowed substantially larger negative instances.” This preserves one of E2’s most informative findings.

## Explanations worth strengthening

- **Complete the free-vertex argument, page 8.** Algorithm 5 explains why propagation identifies vertices in no/every minimum cover, but the assertion that all remaining matched vertices are free needs one more step. After propagation, construct one minimum cover choosing the left endpoint of every remaining matching edge and another choosing the right endpoint, retaining the forced choices. Explain why both cover all edges and have size `|M|`. This connects the algorithm’s final line to its claim without a long proof.

- **Simplify the pivot-rule sentence, page 7.** Steepest-edge uses edge norms; Devex approximates those weights. Saying that both divide the displayed reduced cost by “the edge length” blurs this distinction and the difference between primal and dual pivoting. A short sentence saying that HiGHS uses weighted pivot strategies is enough. If defaults are retained, mention the possible dual switch to Devex already documented in Appendix A.

- **Keep empirical percentages tied to their sample.** The 28.8% result is valid for the specified equal allocation of 50 accepted non-bipartite graphs to each `(n,p)` cell. It is not a prevalence estimate for arbitrary non-TU LPs. The current phrase “our non-TU graphs” is appropriate; preserve that qualification. An optional limitation sentence could explain the conditioning on non-bipartiteness.

## Formatting and presentation

- **Figure 8, page 17: highest-priority visual improvement.** The six-panel plot is rotated within a portrait page, and the smaller matrix-order tick labels crowd together. Use a true landscape PDF page so viewers open it in the intended orientation, or split it into portrait figures. Reduce the number of tick labels and enlarge panel labels. Keep Appendix C’s heading/introduction with the figure where possible; it currently begins on page 16 and leaves substantial unused space there.

- **Table 7, page 15: improve readability.** Nine columns make the max-flow timings noticeably small. Split compiled and Python baselines into two tables, or use a landscape appendix table. Retain legible labels and consistent units rather than shrinking the font further.

- **Improve a few page breaks.** The introduction’s final paragraph and repository footnote continue onto page 2; Section 3.1 begins on page 2 while its first lemma is on page 3; Section 4.1’s opening brute-force paragraph breaks across pages 5–6; and E3’s results begin with two lines at the bottom of page 8. Reserve space for headings and short opening paragraphs, and shorten nearby prose to stay within ten main-body pages. Do not reduce the required body font or margins to solve this.

- **Make table headings more self-contained.** In Table 3, group the three solver columns under “Fractional coordinates”. In Table 2, use “Largest completed size” over the method columns so readers do not have to infer the meaning of `10`, `12` and `all` from the caption. Table 1’s caption should say “parentheses”, since the entries use parentheses rather than square brackets.

- **Consider moving table captions above the tables.** They currently appear below, like figure captions. This is a stylistic option, but putting table captions above would distinguish the adjacent Figure 5 and Table 1 and help readers identify dense tables before reading their numbers.

- **Optional appendix/reference cleanup.** Page 13 contains only the last four references. Slightly tighter bibliography spacing might avoid this mostly empty page, provided it remains readable. This is lower priority than the plot and table improvements and has no effect on the ten-page main-body limit.

## Checks supporting this feedback

- E1’s saved random-instance rows reproduce **288/1,000 exact LPs**, **46 exact instances with fractional simplex output**, and the maximum ratio **55/30**.
- E2’s saved data contain **3,060 calls**; all **1,020 CMR calls** completed, and every completed decision agrees with the expected answer. The saved paired analysis supports **151 GH wins among 160 completed pairs**, with a median brute/GH algorithm-time ratio of approximately **13.94**.
- E3’s **18 saved rows** all report equality of the predicted free set and IPM fractional set. The largest recorded fixed-coordinate error is approximately **3.44×10⁻⁸**. The two largest graphs lack the additional per-coordinate LP check, as noted above.
- E4’s saved overnight results contain **24 positive-gap cases among 200 random instances**, with gaps from approximately **1/3 to 3/4**. The additional triangle control was excluded from that count.

This feedback was prepared with OpenAI Codex by inspecting the PDF, source, saved experimental evidence and selected primary references. No report source, PDF or experimental output was changed during the review. Include this review assistance when updating the project’s AI Disclosure if the feedback is used.
