# Issue 7842 final NaN congruence validation

Validate the selected guarded raw-NaN rule in both existing FP owners at Z3
`2d2fb04fe3f1ab2111b550645f7c49198a3165f6`. Source is checked out
separately and patches are applied transiently. This is a diagnostic branch.

The debug job reuses the exact instrumented baseline cache, records baseline and
paired search controls, and runs the paired candidate through all 55 existing
fixtures in six configurations. Additional native scope traces distinguish
search backtracking from user push/pop. A trace must show the actual replay
before that path is considered covered. The job runs all 945 enabled SMT2 cases
at z3test `d43c5f777aa736714639741fd3f352df27520d72`, preserving expected
and produced-output identities, and runs the complete native suite with the
previously verified C API regression.

The release job uses the ordinary optimized build without tracing. It records
the full semantic matrix for baseline and paired, and compares unguarded raw,
guarded classical and paired variants against baseline on 14 SAT families.
Independent NaN, finite and infinity families reach N=4096; shared NaN DAGs reach
N=64. Three configurations (default, structural relevancy 2, SAT/EUF), three
rotated-order repetitions and four variants yield 504 cost records. Every process
has a 20-second limit. Failures and timeouts remain in the artifact alongside
wall/CPU time, peak memory, native statistics, source identities and build flags.
The jobs run on separate machines so native tests do not compete with cost probes.

The original candidate, native-test and fixture bytes are unchanged from harness
`346155e4d2c6e62a98903f7d41a3856b3694ac27`. Run 34981229254 established
330/330 targeted results for paired, supported API lifecycle behavior in both
engines, and full upstream/native success for guarded classical. Unsupported
SAT/EUF proof production remains a baseline limitation. This phase fills the
selected paired patch's broad-suite and optimized-cost gaps.

The checks require selected-candidate semantic and regression success, while
preserving baseline failures and cost limits for inspection. Finite measurements
do not prove a bound on all solver search. Review recorded outcomes and provenance
before drawing a readiness or performance conclusion.
