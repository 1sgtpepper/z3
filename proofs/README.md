# Floating-point division proof artifacts

These scripts are supplemental arithmetic evidence for Z3 PR #10216 at source
head `af856fe1f5455156af47a358f9524d9df226aa05`. They use only Python's standard
library and do not import Z3 or trust output from the candidate implementation.

## Replay

The recorded outputs were produced with CPython 3.14.6 on Linux:

```sh
python3 proofs/verify_ebits_gt_sbits.py |
  diff -u proofs/verify_ebits_gt_sbits.expected.json -
python3 proofs/verify_fp_div_semantics.py |
  diff -u proofs/verify_fp_div_semantics.expected.json -
sha256sum -c proofs/SHA256SUMS
```

All three commands exit successfully without third-party dependencies.

## Coverage

`verify_ebits_gt_sbits.py` checks every `2 <= sbits < ebits <= 63` pair: 1,891
relative-width formats. It proves the local leading-zero and signed-exponent
bounds, the quotient extraction boundary at `sbits == 2`, and the correction
width categories. It exhausts 1,499,136 modular round-count states at FP(11,2),
FP(13,3), and FP(15,4), and every normalized significand pair for
`sbits = 2..12`. It also checks the FP(2,16) cap-wrap regression and proves that
the local deep-underflow path shifts by at least eight bits, so rounding cannot
carry into minimum normal.

`verify_fp_div_semantics.py` independently enumerates the positive finite
FP(4,3) value lattice and checks 11 exact rational quotients under all five
rounding modes (55 results). The cases cover exact and inexact results, both
signs, subnormal ties, gradual underflow, and overflow to infinity versus the
maximum finite value. Expected encodings are embedded in the script and a
successful summary is recorded separately.

## Limits

These scripts validate arithmetic invariants, not C++ AST construction,
rewriter routing, or integration. The semantic script does not model NaN,
infinity, or zero as division inputs. Those paths and the actual converter are
covered by the symbolic SMT-LIB regressions at z3test head
`91689f9673135a9196912d43057fa38af39484d4` and by fork CI; the exact positive
and known-bad replay runs are recorded in PR #10216.
