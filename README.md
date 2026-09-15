# Issue 7842 NaN identity repair comparison

Compare baseline Z3, the prior raw-node equality rule, an expanded normalized decode
bridge, and static raw-constructor normalization at upstream
`2d2fb04fe3f1ab2111b550645f7c49198a3165f6`. Source is checked out separately;
semantic patches are applied only in fork CI. This is an experiment, not a
production patch or a claim that any candidate is complete.

The bridge candidate normalizes decoded NaN values and admits raw FP terms to the
existing bridge in both FP engines. It simplifies the BV extracts first, so a raw
wrap/decode round trip refers back to the original raw term. The conditional bridge
on a raw term imposes the same semantic implication as the raw-node rule; it is not
axiom-free. The static candidate returns a conditional NaN value from the general
raw-constructor rewriter. Its repeated-rewrite behavior is an explicit risk.

The raw-node rule changes only the classical SMT engine. SAT/EUF runs expose that
scope rather than implying the classical patch fixes both engines. Shared converter
and general-rewriter edits must also account for their alternate-engine consumers.

The 51 existing fixtures and their oracles are retained. Four additions exercise
raw terms alongside nonlinear arithmetic (to investigate actual relevancy 2), live
distinct payloads with that arithmetic, raw-term push/pop reuse, and distinct
payloads linked through FP-returning UF applications. The arithmetic SAT witness
is a = 2. The payload SAT witnesses use p = 1, q = 2, constant-NaN g and constant-zero
f. Raw NaN disequalities have UNSAT oracles by singleton NaN and congruence.

Each completed variant runs 55 fixtures in five configurations: default, explicit
relevancy 0/2, no model generation, and sat.euf=true. Commands, actual modes and
observed FP engines are recorded. A requested mode is never proof of effective
mode. Ten focused cases retain native FP/core traces; all cases retain compact
classical relevance events. Unobserved engine/mode means unobserved.

Before the sweep, a bounded Python probe repeatedly simplifies a symbolic raw FP
term and records DAG sizes and structural stability. It has a 10,000-step limit
per simplification and a 15-second process timeout. Failure rejects that candidate
before the full sweep; partial evidence is preserved. Probe stability alone does
not prove semantic correctness. Each solver process has a 30-second timeout.

The workflow records all wrong answers, errors, unknowns and timeouts as failures
in the data. Its final check establishes acquisition completeness, not that every
candidate is a repair. Successful CI does not mean all semantic cases pass. Native
builds run serially, reuse the build cache where valid, and preserve exact source,
patch, binary and process identities. The current-source cache is saved before
applying any semantic candidate. Old-source cache objects are rebuilt normally.

The earlier raw/broad comparison is run 34699671443 at harness
`af7088aa037bb47ce18ed5056b5c2d3f67b90248`. Bridge-only normalization is run
34973444790 at harness `3bd4d5a4ca523b91dba400aefbd07e17f326ad32`; it passed
200/204 executions and left the direct raw FP/UF case unresolved.

Callback counts are not assertion counts or a global allocation bound. Traced
single-run durations are not performance benchmarks. Production readiness requires
further semantic/lifecycle proof, relevant upstream tests and measured efficiency.
