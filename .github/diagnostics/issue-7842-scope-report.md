# Z3 issue #7842: combination-scope diagnostic

This report records the completed CI experiment used to distinguish a datatype-local bug from a generic floating-point/core congruence bug.

## Reproducibility

- Branch: `investigate-7842-root-cause`
- Diagnostic commit: `a0086c5a606b9ad019b51b56452413ac9913bd90`
- Workflow run: `33575451125`
- Job: `100078302295`
- Exact upstream commit checked out by the job: `d7777e2ddd5be9c55b376db4ebebbb33b39bf45f`
- Z3 reported version: `5.1.0`
- Artifact: `issue-7842-combination-scope`
- Artifact id: `9826801882`
- Artifact SHA-256: `05f3407571500b7274dac0cb4de43f7a974a4095ed7c0dd14697c4516475818d`
- Workflow conclusion: success

All invalid-model checks below ran with `model_validate=true`.

## Results

| Case | Formula shape | Result | Model validation |
|---|---|---:|---|
| 12 | Two hidden datatype values, each constrained to contain a NaN | `unsat` | model unavailable, as expected |
| 13 | Disequality between two explicit datatype constructors containing NaNs | `unsat` | no model requested |
| 14 | Uninterpreted function applied to two NaN-constrained FP terms, outputs distinct | `sat` | **invalid model** |
| 15 | Predicate true on one NaN-constrained FP term and false on another | `sat` | **invalid model** |
| 16 | Array selects at two NaN-constrained FP indices, values distinct | `sat` | **invalid model** |
| 17 | Direct core disequality between two NaN-constrained FP terms | `unsat` | no model requested |
| 18 | Same UF case as 14 plus explicit core equality between FP arguments | `unsat` | no model requested |
| 19 | UF distinguishes a NaN-constrained variable from the built-in NaN literal | `sat` | **invalid model** |
| 20 | UF distinguishes an FP expression forced to NaN from the built-in NaN literal | `unsat` | model unavailable, as expected |
| 21 | UF distinguishes `+zero` from `-zero` | `sat` | valid model |

The concrete invalid model in case 14 assigns both FP arguments the abstract value `(_ NaN 8 24)` while the asserted UF outputs remain distinct. Cases 15 and 16 reproduce the same semantic inconsistency without datatypes. Case 17 confirms that explicit FP disequality is already handled. Case 18 confirms that once the core receives the FP equality, ordinary congruence closes the formula. Case 21 is a semantic control: core equality must continue to distinguish signed zeros even though IEEE `fp.eq` does not.

## Scope conclusion supported by the matrix

The failure does not require datatype selectors, datatype injectivity, or datatype disequality propagation. It appears whenever semantically equal floating-point values are shared with a congruence-owning component without a core equality edge. The minimal missing bridge is therefore between the FPA theory's abstract equality and the core e-graph/EUF arrangement, not between FPA and datatypes specifically.
