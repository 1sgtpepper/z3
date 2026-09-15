# Issue 7842 scoped NaN congruence validation

Validate the raw FP NaN identity rule at Z3
`2d2fb04fe3f1ab2111b550645f7c49198a3165f6`, using separately checked-out
source and transient diagnostic patches. This branch is an experiment, not a
production patch or an upstream publication.

Four variants are recorded: baseline; the previous classical raw-term rule;
that rule with a guard that skips definitely non-NaN terms; and a separate
extension of the guarded rule to the SAT/EUF activation owner. The last variant
investigates alternate-engine model behavior; it is not assumed to be a repair.
No shared converter or general-rewriter change is applied in this comparison.

All 55 existing fixtures and oracles are preserved. Six configurations cover
default, explicit relevancy 0/2, no models, SAT/EUF, and relevancy 2 with structural
branching. The latter uses auto_config=false and case_split=3 to prevent the
quantifier-free BV setup from disabling relevancy. Native traces must establish
actual level 2 for the raw counterexample, payload control and scope-reuse case.
Requested options alone are not coverage evidence. Focused traces include the
previously regressed two-field datatype SAT control.

A common native C API regression runs on baseline and every candidate. It uses
solver-local parameters, distinct source payloads, a live SAT control, and repeated
push/pop on persistent solvers. Its baseline failure is expected evidence.
Separate API processes exercise assumptions, cores, scopes, reset, translation and
proof construction. Unsupported or failing alternate-engine behavior is retained.

Baseline and the guarded classical candidate run the conventional complete SMT2
suite at z3test `d43c5f777aa736714639741fd3f352df27520d72`: 945 enabled
fixtures, two workers, a 60-second limit per fixture, and retained produced outputs.
The guarded candidate also runs the native suite. Exact build, executable, library,
input and patch identities are preserved; cached builds are reused only when
source identity matches. No local solver build or execution is required.

Untraced debug cost probes rotate the four executable variants over three repeats
and two configurations. Independent NaN/finite/infinity terms and shared NaN DAGs
have explicit SAT witnesses. Each process has a 20-second limit; native statistics,
wall time, CPU time and peak memory are saved, including failures and timeouts.
This is bounded debug-build evidence, not a release-performance claim.

The workflow's final checks establish acquisition completeness. A successful run
does not mean every candidate passes. Production readiness requires review of all
failures, differences, lifecycle evidence, costs and source identities.

Earlier evidence: raw/broad run 34699671443; unwrap-only run 34973444790;
repair comparison run 34976868892 at harness
`5a24bc944f4de9ca547add74fb6328492f5c9f87`. In that comparison, raw and extended
bridge passed all 220 classical checks. The bridge introduced an alternate-engine
SAT model regression; static constructor normalization exhausted the rewrite-step
limit on the second simplification. Neither alternative is carried forward here.
