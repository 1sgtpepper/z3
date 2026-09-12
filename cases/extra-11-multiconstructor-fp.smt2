(set-logic ALL)
(declare-datatype Expr
  ((Flt (getFlt (_ FloatingPoint 8 24))) (Other)))
(declare-fun x () Expr)
(assert ((_ is Flt) x))
(assert (distinct x (Flt (_ NaN 8 24))))
(assert (fp.isNaN (getFlt x)))
(check-sat)
