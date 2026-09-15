# Issue 7842 normalized FP bridge experiment

Compare unchanged Z3 with NaN normalization in the existing FP decode bridge at
upstream `f85ec6c198b4ba8dd95c33005731f8a3a5c13f88`. The production source is
checked out separately. Patches are applied only in CI. This branch contains
diagnostic material and is not a proposed production fix.

The normalization patch changes `unwrap(b, s)` for FP sorts to select the NaN
literal when its decoded FP value has an all-ones exponent and nonzero payload.
It otherwise returns that decoded value. The existing bridge equality consumes
the result; no new assertion site is added, and original BV inputs are unchanged.
Direct raw FP terms bypass this bridge, so this experiment may remain incomplete.
The separate SAT/EUF caller of `unwrap` is outside this execution matrix.

The previous raw/broad diagnostic patches remain as historical inputs. Their
completed comparison is pinned at harness `af7088aa037bb47ce18ed5056b5c2d3f67b90248`
and run https://github.com/1sgtpepper/z3/actions/runs/34699671443 . They are not
combined with the normalization patch or rerun in the current workflow.

The 38 historical fixtures and their expected answers are preserved. Twelve
additional SAT fixtures exercise independent raw NaN arguments and shared nested
FP applications at sizes 1, 2, 4, 8, 16, and 32. In the first family, a constant-zero
interpretation of `f` satisfies every application. In the second, `x0 = NaN` and
constant-NaN `h` satisfy every constraint. These witnesses justify the SAT oracles
independently of the tested solver. Both families have linear-size AST DAGs.

A further SAT control keeps two different nonzero payloads and opposite signs live
through `f(raw_fp) = 0` applications. The witness `p = 1`, `q = 2`, and constant-zero
`f` satisfies it, while trace coverage requires actual FP registration. This closes
the old round-trip SAT control's preprocessing bypass.

Both variants run all 51 fixtures in four configurations: 408 process records in
total. Debug builds run serially and reuse the configured build directory. Each
process has a 30-second timeout; the job has a 60-minute timeout. The final gate
checks record completeness and trace coverage, and rejects normalization errors,
timeouts and unknowns. Wrong answers are reported as unresolved diagnostic data;
a successful workflow does not mean normalization fixes every case. No error,
timeout, unknown or wrong answer counts as a passing semantic result.

An identical trace-only patch registers its tag in `util/trace_tags.def` and records
effective relevancy and raw-node callbacks
in every variant. Requested relevancy 2 may be lowered by solver setup. An empty
effective-mode list means unobserved, not disabled. Node IDs are observed runtime
identifiers, not a proof of unique formulas across deletion, reuse, or scopes.
Callback counts are not assertion counts, global allocation bounds, or proof of
asymptotic performance. Durations include diagnostic tracing and process startup.
Six focused fixtures additionally preserve native FP/core traces in every mode.

Evidence includes exact inputs and oracles, source/harness identities, patches,
build logs, binary hashes, commands, outputs, exit statuses, durations, and traces.
Interpret any passing result as coverage of these finite cases on the classical
SMT engine; production readiness and the separate SAT/EUF engine remain unproven.
