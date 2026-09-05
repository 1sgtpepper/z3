; Preserved regression: Z3Prover/z3test aa6caf7238b09d28f76a002446619beacfd86a43
; regressions/smt2/6728-2-simp.smt2.disabled, still disabled after the #6993 revert.
; fp.add is commutative for the same rounding mode, including its zero and NaN cases.
(set-logic ALL)
(declare-const x (_ FloatingPoint 8 24))
(declare-fun f ((_ FloatingPoint 8 24)) Bool)
(assert (not (= (f (fp.add RNE x (_ +zero 8 24)))
                (f (fp.add RNE (_ +zero 8 24) x)))))
(check-sat)
