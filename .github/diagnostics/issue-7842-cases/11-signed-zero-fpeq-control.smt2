(set-logic ALL)
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(declare-fun g ((_ FloatingPoint 8 24)) Int)
; fp.eq identifies +0 and -0, while SMT equality deliberately does not.
(assert (fp.eq a (_ +zero 8 24)))
(assert (fp.eq b (_ +zero 8 24)))
(assert (distinct (g a) (g b)))
(check-sat)
