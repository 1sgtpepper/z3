# Issue 7842 search relevance replay

This focused follow-up keeps the exact guarded paired NaN patch at source
`2d2fb04fe3f1ab2111b550645f7c49198a3165f6`. It reuses the debug baseline
cache, compares baseline with paired, and records six bounded search controls
per variant. No production code or earlier fixture oracle changes.

The first disjunct uses infinity versus NaN through a UF disequality, then an
independent impossible pigeonhole constraint. Unlike the previous equality
branch, this requires the raw FP argument to become relevant before the conflict.
After backtracking, the second disjunct requires either an impossible NaN/NaN
disequality (UNSAT) or a valid infinity/NaN disequality (SAT). Structural
relevancy 2 and phase choices 0, 1 and 3 are preserved. Inspect actual callbacks
and scope pops before claiming the intended replay path.

The final regression/release run continues separately at harness
`a2c6125590dce868557f079098aae99d4e742430` (run 34986521906). Its debug
artifact already establishes 330/330 targeted results, 945/945 upstream SMT2
regressions and 106/106 native tests on paired. The original search controls
returned the right selected answers, but the raw callback occurred only after
the first branch had been rejected; that was not a replay witness.
