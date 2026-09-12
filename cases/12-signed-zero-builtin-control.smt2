(set-logic ALL)
(declare-fun g ((_ FloatingPoint 8 24)) Int)
(assert (distinct (g (_ +zero 8 24)) (g (_ -zero 8 24))))
(check-sat)
