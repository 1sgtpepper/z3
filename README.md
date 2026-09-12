# Issue 7842 raw NaN identity experiment

Compare unchanged Z3, a raw-node NaN identity rule, and the previous broad semantic
implication at upstream `f85ec6c198b4ba8dd95c33005731f8a3a5c13f88`.
The production source is checked out separately. Patches are applied only in CI.
This branch contains diagnostic material and is not a proposed production fix.

The raw rule asserts that a raw FP term with an all-ones exponent and nonzero
significand equals its sort's NaN. The converter supplies the existing component
predicate. The rule does not equate the source sign or payload bits. Existing
nonraw bridges remain unchanged. The broad rule is a positive diagnostic control.

The 38 historical fixtures and their expected answers are preserved. Twelve
additional SAT fixtures exercise independent raw NaN arguments and shared nested
FP applications at sizes 1, 2, 4, 8, 16, and 32. In the first family, a constant-zero
interpretation of `f` satisfies every application. In the second, `x0 = NaN` and
constant-NaN `h` satisfy every constraint. These witnesses justify the SAT oracles
independently of the tested solver. Both families have linear-size AST DAGs.

Every variant runs all 50 fixtures in four configurations: 600 process records in
total. Debug builds run serially and reuse the configured build directory. Each
process has a 30-second timeout; the job has a 60-minute timeout. The final gate
checks both interventions only after collecting all three variants. Baseline
failures are expected diagnostic data. No error, timeout, or unknown counts as a
passing semantic result.

An identical trace-only patch registers its tag in `util/trace_tags.def` and records
effective relevancy and raw-node callbacks
in every variant. Requested relevancy 2 may be lowered by solver setup. An empty
effective-mode list means unobserved, not disabled. Node IDs are observed runtime
identifiers, not a proof of unique formulas across deletion, reuse, or scopes.
Callback counts are not assertion counts, global allocation bounds, or proof of
asymptotic performance. Durations include diagnostic tracing and process startup.
Five focused fixtures additionally preserve native FP/core traces in every mode.

Evidence includes exact inputs and oracles, source/harness identities, patches,
build logs, binary hashes, commands, outputs, exit statuses, durations, and traces.
Interpret any passing result as coverage of these finite cases on the classical
SMT engine; production readiness and the separate SAT/EUF engine remain unproven.
