#!/usr/bin/env python3
"""Check exact FP(4,3) division results with an independent Fraction oracle.

The oracle enumerates the positive finite FP(4,3) lattice and rounds exact
rational quotients without importing Z3 or the candidate implementation.
"""

from __future__ import annotations

import json
from bisect import bisect_left
from dataclasses import dataclass
from fractions import Fraction


ROUNDING_MODES = ("RNE", "RNA", "RTP", "RTN", "RTZ")


@dataclass(frozen=True, order=True)
class Encoding:
    exp: int
    frac: int


@dataclass(frozen=True)
class Rounded:
    sign: int
    encoding: Encoding | None
    infinite: bool = False


class FPFormat:
    def __init__(self, ebits: int, sbits: int) -> None:
        self.ebits = ebits
        self.sbits = sbits
        self.frac_bits = sbits - 1
        self.bias = (1 << (ebits - 1)) - 1
        self.top_exp = (1 << ebits) - 1
        self._finite = [
            Encoding(exp, frac)
            for exp in range(self.top_exp)
            for frac in range(1 << self.frac_bits)
        ]
        self._values = [self.value(enc) for enc in self._finite]

    @staticmethod
    def pow2(exp: int) -> Fraction:
        if exp >= 0:
            return Fraction(1 << exp, 1)
        return Fraction(1, 1 << -exp)

    def value(self, enc: Encoding) -> Fraction:
        if enc.exp == 0:
            return Fraction(enc.frac, 1 << self.frac_bits) * self.pow2(
                1 - self.bias
            )
        significand = (1 << self.frac_bits) + enc.frac
        return Fraction(significand, 1 << self.frac_bits) * self.pow2(
            enc.exp - self.bias
        )

    @property
    def max_finite(self) -> Encoding:
        return Encoding(self.top_exp - 1, (1 << self.frac_bits) - 1)

    @property
    def max_finite_value(self) -> Fraction:
        return self.value(self.max_finite)

    @staticmethod
    def lsb_even(enc: Encoding) -> bool:
        return (enc.frac & 1) == 0

    def smt(self, rounded: Rounded) -> str:
        if rounded.infinite:
            return f"(_ {'-' if rounded.sign else '+'}oo {self.ebits} {self.sbits})"
        assert rounded.encoding is not None
        enc = rounded.encoding
        return (
            f"(fp #b{rounded.sign} #b{enc.exp:0{self.ebits}b} "
            f"#b{enc.frac:0{self.frac_bits}b})"
        )


def round_fraction(fmt: FPFormat, value: Fraction, mode: str) -> Rounded:
    sign = int(value < 0)
    magnitude = -value if sign else value

    if magnitude > fmt.max_finite_value:
        outward = (not sign and mode == "RTP") or (sign and mode == "RTN")
        inward = mode == "RTZ" or (not sign and mode == "RTN") or (
            sign and mode == "RTP"
        )
        if outward:
            return Rounded(sign, None, True)
        if inward:
            return Rounded(sign, fmt.max_finite)

        next_power = fmt.pow2((fmt.top_exp - 1) - fmt.bias + 1)
        midpoint = (fmt.max_finite_value + next_power) / 2
        if magnitude >= midpoint:
            return Rounded(sign, None, True)
        return Rounded(sign, fmt.max_finite)

    position = bisect_left(fmt._values, magnitude)
    if position < len(fmt._values) and fmt._values[position] == magnitude:
        return Rounded(sign, fmt._finite[position])

    lower_i = max(0, position - 1)
    upper_i = min(len(fmt._values) - 1, position)
    lower = fmt._finite[lower_i]
    upper = fmt._finite[upper_i]

    toward_upper = (not sign and mode == "RTP") or (sign and mode == "RTN")
    toward_lower = mode == "RTZ" or (not sign and mode == "RTN") or (
        sign and mode == "RTP"
    )
    if toward_upper:
        return Rounded(sign, upper)
    if toward_lower:
        return Rounded(sign, lower)

    lower_distance = magnitude - fmt._values[lower_i]
    upper_distance = fmt._values[upper_i] - magnitude
    if lower_distance < upper_distance:
        chosen = lower
    elif upper_distance < lower_distance:
        chosen = upper
    elif mode == "RNA":
        chosen = upper
    else:
        chosen = lower if fmt.lsb_even(lower) else upper
    return Rounded(sign, chosen)


def main() -> None:
    fmt = FPFormat(4, 3)
    cases = {
        "exact_below_one": (Encoding(0, 1), Encoding(0, 2), False),
        "exact_above_one": (Encoding(0, 2), Encoding(0, 1), False),
        "denormal_self": (Encoding(0, 1), Encoding(0, 1), False),
        "inexact_positive": (Encoding(0, 1), Encoding(0, 3), False),
        "inexact_negative": (Encoding(0, 1), Encoding(0, 3), True),
        "subnormal_tie_positive": (Encoding(0, 1), Encoding(8, 0), False),
        "subnormal_tie_negative": (Encoding(0, 1), Encoding(8, 0), True),
        "underflow_positive": (Encoding(0, 1), Encoding(7, 1), False),
        "underflow_negative": (Encoding(0, 1), Encoding(7, 1), True),
        "overflow_positive": (Encoding(7, 0), Encoding(0, 1), False),
        "overflow_negative": (Encoding(7, 0), Encoding(0, 1), True),
    }
    expected = {
        "exact_below_one": {
            mode: "(fp #b0 #b0110 #b00)" for mode in ROUNDING_MODES
        },
        "exact_above_one": {
            mode: "(fp #b0 #b1000 #b00)" for mode in ROUNDING_MODES
        },
        "denormal_self": {
            mode: "(fp #b0 #b0111 #b00)" for mode in ROUNDING_MODES
        },
        "inexact_positive": {
            "RNE": "(fp #b0 #b0101 #b01)",
            "RNA": "(fp #b0 #b0101 #b01)",
            "RTP": "(fp #b0 #b0101 #b10)",
            "RTN": "(fp #b0 #b0101 #b01)",
            "RTZ": "(fp #b0 #b0101 #b01)",
        },
        "inexact_negative": {
            "RNE": "(fp #b1 #b0101 #b01)",
            "RNA": "(fp #b1 #b0101 #b01)",
            "RTP": "(fp #b1 #b0101 #b01)",
            "RTN": "(fp #b1 #b0101 #b10)",
            "RTZ": "(fp #b1 #b0101 #b01)",
        },
        "subnormal_tie_positive": {
            "RNE": "(fp #b0 #b0000 #b00)",
            "RNA": "(fp #b0 #b0000 #b01)",
            "RTP": "(fp #b0 #b0000 #b01)",
            "RTN": "(fp #b0 #b0000 #b00)",
            "RTZ": "(fp #b0 #b0000 #b00)",
        },
        "subnormal_tie_negative": {
            "RNE": "(fp #b1 #b0000 #b00)",
            "RNA": "(fp #b1 #b0000 #b01)",
            "RTP": "(fp #b1 #b0000 #b00)",
            "RTN": "(fp #b1 #b0000 #b01)",
            "RTZ": "(fp #b1 #b0000 #b00)",
        },
        "underflow_positive": {
            "RNE": "(fp #b0 #b0000 #b01)",
            "RNA": "(fp #b0 #b0000 #b01)",
            "RTP": "(fp #b0 #b0000 #b01)",
            "RTN": "(fp #b0 #b0000 #b00)",
            "RTZ": "(fp #b0 #b0000 #b00)",
        },
        "underflow_negative": {
            "RNE": "(fp #b1 #b0000 #b01)",
            "RNA": "(fp #b1 #b0000 #b01)",
            "RTP": "(fp #b1 #b0000 #b00)",
            "RTN": "(fp #b1 #b0000 #b01)",
            "RTZ": "(fp #b1 #b0000 #b00)",
        },
        "overflow_positive": {
            "RNE": "(_ +oo 4 3)",
            "RNA": "(_ +oo 4 3)",
            "RTP": "(_ +oo 4 3)",
            "RTN": "(fp #b0 #b1110 #b11)",
            "RTZ": "(fp #b0 #b1110 #b11)",
        },
        "overflow_negative": {
            "RNE": "(_ -oo 4 3)",
            "RNA": "(_ -oo 4 3)",
            "RTP": "(fp #b1 #b1110 #b11)",
            "RTN": "(_ -oo 4 3)",
            "RTZ": "(fp #b1 #b1110 #b11)",
        },
    }

    actual: dict[str, dict[str, str]] = {}
    for name, (numerator, denominator, negate) in cases.items():
        quotient = fmt.value(numerator) / fmt.value(denominator)
        if negate:
            quotient = -quotient
        actual[name] = {
            mode: fmt.smt(round_fraction(fmt, quotient, mode))
            for mode in ROUNDING_MODES
        }

    assert actual == expected
    print(
        json.dumps(
            {
                "verdict": "PASS",
                "format": {"ebits": 4, "sbits": 3},
                "rounding_modes": list(ROUNDING_MODES),
                "cases": len(cases),
                "rounding_checks": len(cases) * len(ROUNDING_MODES),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
