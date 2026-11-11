# Fresh review of `main.pdf`

## Latest verification: 12 November, 02:08 build

This section supersedes the earlier reread below. Reviewed PDF SHA-256: `956cd28371b39d629783266b1e6ab15c7fd73d9a79a7258a3760896e56a9c5e1`.

**Assessment:** I found no major error in the central mathematical argument and no remaining formal mismatch with the written-report structure or page limit. The report still has ten main-body pages, single-column 11pt source, three main technical sections, marked appendices and a final one-paragraph AI Disclosure. This is a review finding, not certification of every cited paper or of the group's understanding.

The previous timing-scope inconsistency and Appendix B overstatement are fixed. Algorithm 3 now mentions anti-cycling in its box, and the IPM discussion explicitly identifies the omitted schematic details. The flow table has been split into readable compiled/Python comparisons, and Figure 8's crowded tick labels have been reduced.

The E1 rerun is now saved at `experiments/E1/results/rerun-pinned-2026-11-12`. I independently compared its 1,012 CSV rows with the original: LP/ILP values, exactness, integrality, half counts and LP iteration counts match, and B&B node counts differ on exactly 114 rows, as reported. The version metadata and comparison document are present. I did not rerun the solvers.

**One remaining repository action:** the rerun directory is untracked locally and was absent from the public repository's `main` tree when checked. Publish that folder before submission so the new path cited on page 14 is accessible to the grader. The existing E1–E4 scripts and saved baseline results are publicly available; this finding concerns the newly cited verification artifact. No commit or push was performed during this review.

**Minor precision improvements, not major failures:**

- Page 8: distinguish the exact central-path limit from a finite numerical IPM answer. Suggested phrasing: “The limiting point is fractional exactly on the free vertices; E3 checks this prediction for finite solver outputs using a numerical tolerance.” A finite strictly interior iterate can differ slightly from a fixed 0/1 value. The measured tolerance and error margins already support the experimental findings.
- Figure 3, page 3: explicitly say that both pictured systems also impose `x1,x2 >= 0`. Those bounds are implicit from the standard LP convention, but adding them to the caption would completely specify the bounded polygons drawn.

**Optional formatting polish:**

- Shorten the end of the introduction so that its last sentence and repository footnote do not spill onto page 2.
- Keep Section 4.1's opening brute-force paragraph together; it currently starts at the bottom of page 5 and continues on page 6.
- Keep the page 7–8 IPM paragraph together if space permits; page 8 currently begins “is unique”. Preserve the ten-page main-body limit and required font.
- The mostly empty final bibliography page is harmless. It is lower priority than smooth paragraph breaks. The revised timing tables and landscape plot no longer need the earlier readability fixes.

The formal requirements assessment was checked against `mini-project-instructions.pdf`. The build log contains no reported overfull-box or unresolved-reference warnings. Earlier concerns listed below should not be treated as current requests where this latest section marks them fixed.

## Earlier reread — retained as history

Reviewed on 12 November 2026. Target: `report/build/main.pdf`, compiled at approximately 01:48 Singapore time on 12 November. SHA-256: `676e2b2f07dd19c44c66480da5ad95c50393ee8dbe427f5436a1414a6f85dffb`. This review supersedes the earlier feedback wherever the report has been revised.

I reread all 18 pages, visually inspected every page, reread the project README and the official mini-project instructions, and checked the relevant source and selected saved results. The report is substantially improved. Its structure meets the write-up brief, and most earlier technical and methodological concerns have been addressed. The remaining points are mainly consistency, evidence preservation and presentation.

## Earlier concerns now addressed

| Earlier concern | Current assessment |
| --- | --- |
| TDI sentence omitted integral right-hand side | Corrected on page 10. The system is defined and the integral-`b` hypothesis is explicit. |
| IPM pseudocode promised an exact optimum and moved a finite iterate within the optimal face | Substantially addressed on pages 7–8: Algorithm 4 is labelled schematic, returns a near-optimal point without crossover, preserves positive slacks, and describes basis recovery followed by simplex. The prose distinguishes the central-path limit from a finite run. |
| Simplex description ignored degeneracy and anti-cycling | Addressed in the page 7 explanation: the objective need not improve strictly, and termination is qualified by an anti-cycling rule. The added [Bland reference](https://pubsonline.informs.org/doi/10.1287/moor.2.2.103) supports this qualification. |
| Pivot-rule explanation treated Devex weights as exact edge lengths | Corrected on page 7, including the possible dual switch to Devex. |
| E1 and E3 settings important to interpretation were deferred | Presolve is now explicitly off in the relevant main-text setups; E1 states the zero-gap ILP criterion. |
| E3 implied independent checking on all 18 graphs | Corrected: page 8 explicitly says 16 graphs with at most 2,000 vertices. |
| Free-vertex argument stopped before proving that the remaining vertices were free | Addressed beside Algorithm 5 on page 9 by constructing two minimum covers from the remaining matching edges. |
| Numerical conventions were not documented | The one-half statistic now gives its `1e-4` tolerance on page 9; Table 6 states the rounding cutoff `1/2 - 1e-6`. |
| Main timing explanation and recognition conclusion were too broad | Corrected in the main text. Degeneracy is explicitly an unmeasured possible explanation, and the conclusion recognises early obstructions in larger matrices. One old timing statement remains in Appendix B, noted below. |
| Saved environments were conflated with recommended reproduction versions | Page 14 now distinguishes them and describes the E1 verification rerun, including the B&B node-count differences. Preservation of that rerun's evidence is still worth improving. |
| Table headings, caption placement and rotated E2 page | Improved: table captions are above tables, Tables 2 and 3 have grouped headings, and page 17 opens in landscape with its appendix heading and caption. |
| Disclosure was lengthy and retained a confirmation TODO | The paragraph on page 18 is shorter and the source TODO is removed. Its statement about human review still needs to reflect the group's actual review, which cannot be assessed from the PDF. |

## Remaining feedback

1. **Update the old timing statement in Appendix B — page 15.**

   It still says that every run put the LP “about two orders of magnitude behind the compiled code”. Pages 9–10 correctly qualify this by instance and implementation. Apply the same qualification in Appendix B. The saved dual-simplex/Dinic ratios on grids are approximately 12.8, 22.5 and 31.3; they do not support an unqualified 100-fold summary. This is a consistency fix, not a reason to change the measurements.

2. **Distinguish timing scopes within E4 — page 9 versus page 16.**

   E4's setup now describes solve time excluding model building, while Table 9 explicitly says that the scheduling timings include model building. Both conventions can be reasonable, but the setup should identify which applies where. Suggested replacement: “For flow and matching we report solve time excluding model building; scheduling times include model construction. We use up to three runs, without repeating runs exceeding two seconds.” Qualify Appendix B's general statement about LP timing in the same way if it is intended to cover scheduling too.

3. **Preserve the evidence behind the new E1 rerun paragraph — page 14.**

   The distinction between original and reproduction environments is now clear. The new statement about agreement on 1,012 instances and differences in 114 B&B node counts is specific enough to deserve a saved comparison summary and version record. I could not locate such an artifact in the inspected E1 folder; its saved metadata still describes the original run. Add a linked verification artifact or identify its existing location. This is a traceability recommendation, not a claim that the rerun was not performed. I did not rerun E1 in this review.

4. **Make the anti-cycling assumption visible in Algorithm 3 itself — page 8; minor polish.**

   The surrounding explanation now supplies the missing qualification, so this is no longer the earlier unqualified termination claim. For a reader looking only at the box, add “use an anti-cycling pivot/tie-breaking rule” to the input or a short note. There is no need to expand the pseudocode into a full solver.

5. **Keep Algorithm 4 explicitly conceptual.**

   Its schematic label is appropriate for the report's scope. It omits centrality control, a full stopping test and the details of obtaining a suitable basis. Preserve that label and avoid presenting the box as a complete executable implementation or as the derivation of Karmarkar's complexity bound. A brief “centrality and stopping details omitted” note would make this boundary even clearer, but a full IPM proof is not required by the assignment.

## Formatting still worth improving

- **Table 7, page 15:** the nine-column flow table remains small. Splitting compiled and Python baselines would improve readability. This is an appendix readability improvement, not a detected structural violation of the course brief.
- **Figure 8, page 17:** the landscape orientation is fixed and the overall layout is better. The even-cycle tick labels around orders 8, 10 and 12 are still crowded. Use fewer ticks if revising the plot.
- **Page breaks:** Section 4.1 begins near the bottom of page 5 and its opening paragraph continues on page 6. The introduction's final paragraph still continues onto page 2. These are less important than the content fixes; shorten nearby prose or reserve space for the short opening paragraph while preserving the main-body limit.
- **Optional space use:** page 13 contains only the final references, and page 16 has substantial empty space. Neither is an error. There is no need to compress the appendices merely to reduce the total page count.

## Current assessment against the mini-project instructions

The controlling source is [the official instructions](../../mini-project-instructions.pdf), especially “Types of Projects” on page 2 and “On Preparing your Write-up” on page 3.

| Requirement | Current assessment |
| --- | --- |
| Up to ten main-body pages, single column, 11pt | Met for this build: the main body ends on page 10 and the source specifies 11pt single-column text. |
| Introduction, relevant preliminaries, two to three main sections, conclusion and marked appendix | Met. Sections 3–5 are the three technical sections; Appendices A–C provide supporting detail. |
| Focused question and depth of explanation | The three questions form a coherent argument. Proofs and worked examples provide depth; the free-vertex explanation is stronger in this version. No additional experiment or theorem is needed just to satisfy the brief. |
| Experimental setup, meaningful baselines and interpretation linked to theory | Substantially met. The main text now includes important controls and verification limits. Resolve the timing-scope inconsistency above. |
| Accessible code and data, linked in the report | The repository link remains on page 2. Public access was verified during the previous review; this reread did not repeat that network-access check. Preserve the final version and supporting verification evidence in the repository. |
| Conclusion includes accomplishments, lessons and relevant work beyond scope | Present on page 10, with better qualifications and the corrected TDI statement. This reread is not a complete fresh audit of every cited paper or the latest literature. |
| Short, honest AI Disclosure at the end | Present as one paragraph on page 18. Actual understanding and human review remain the group's responsibility. |

I found no remaining structural mismatch with the write-up requirements in the reviewed build. This does not certify every citation, reproducibility claim or group member's understanding. The first ten pages remain the primary basis for grading, so keep the main methodological qualifications already added there.

## Saved-result checks repeated during this reread

- E1: 1,000 random instances, 288 exact relaxations, and 46 exact cases with fractional simplex output.
- E2: 3,060 recorded calls, including 1,020 completed CMR calls.
- E3: 18 recorded instances with matching predicted/free fractional sets; 16 have the additional LP verification.
- E4: 24 positive-gap cases among 200 random overnight instances.

No experiment was rerun and no report source, PDF or experimental output was changed. This reread and the feedback files are AI-assisted review work; account for that assistance if it is used in the submission.
