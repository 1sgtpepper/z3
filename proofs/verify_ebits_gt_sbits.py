#!/usr/bin/env python3
"""Check width invariants used by fp.div when ebits is greater than sbits.

This independent arithmetic harness uses only the Python standard library. It
does not import Z3 or execute the candidate implementation.
"""

from __future__ import annotations

import json
from collections import Counter
from fractions import Fraction


def signed(value: int, width: int) -> int:
    sign = 1 << (width - 1)
    return value - (1 << width) if value & sign else value


def check_format(ebits: int, sbits: int) -> dict[str, int | str | bool]:
    assert 2 <= sbits < ebits <= 63

    exp_width = ebits + 2
    correction_width = sbits + 4
    shift_width = 2 * correction_width

    # The ebits-wide count returned by unpack represents 0..sbits-1 exactly.
    assert sbits - 1 < 1 << ebits

    # Bounds after exact operand and quotient normalization.
    min_exp = 3 - (1 << ebits) - sbits
    max_exp = (1 << ebits) + sbits - 4
    signed_min = -(1 << (exp_width - 1))
    signed_max = (1 << (exp_width - 1)) - 1
    assert signed_min <= min_exp <= max_exp <= signed_max

    # The quotient's upper reduction is empty only at minimum precision.
    quotient_width = 3 * sbits + 2
    upper_low = 2 * sbits + 4
    upper_width = max(0, quotient_width - upper_low)
    assert upper_width == sbits - 2

    if exp_width < correction_width:
        correction = "extract"
    elif exp_width == correction_width:
        correction = "equal"
    else:
        correction = "zero_extend"

    # Normalized nonzero a/b is strictly between 1/2 and 2. The fixed-point
    # quotient therefore selects one of two adjacent normalization positions.
    a_min = 1 << (sbits - 1)
    a_max = (1 << sbits) - 1
    ratio_min = Fraction(a_min, a_max)
    ratio_max = Fraction(a_max, a_min)
    assert Fraction(1, 2) < ratio_min <= ratio_max < 2
    scale = 1 << (2 * sbits + 2)
    min_quotient = (a_min * scale) // a_max
    max_quotient = (a_max * scale) // a_min
    assert min_quotient >= 1 << (2 * sbits + 1)
    assert max_quotient < 1 << (2 * sbits + 3)
    assert max_quotient < 1 << upper_low

    # Every selected normalization correction fits the local exponent.
    assert sbits + 3 < 1 << exp_width
    assert sbits + 2 < shift_width
    assert sbits + 4 < shift_width

    return {
        "ebits": ebits,
        "sbits": sbits,
        "exp_width": exp_width,
        "correction_width": correction_width,
        "correction": correction,
        "shift_width": shift_width,
        "round_crossing": exp_width > shift_width,
        "min_exp": min_exp,
        "max_exp": max_exp,
        "upper_width": upper_width,
    }


def exhaust_normalized_quotients(sbits: int) -> set[int]:
    """Check the two-position quotient-normalization invariant."""

    scale = 1 << (2 * sbits + 2)
    retained_width = sbits + 4
    retained_low = sbits + 1
    retained_mask = (1 << (sbits + 3)) - 1
    sticky_mask = (1 << (sbits + 1)) - 1
    counts: set[int] = set()

    for numerator in range(1 << (sbits - 1), 1 << sbits):
        for denominator in range(1 << (sbits - 1), 1 << sbits):
            quotient = (numerator * scale) // denominator
            retained = (
                ((quotient >> retained_low) & retained_mask) << 1
            ) | int(bool(quotient & sticky_mask))
            lz = retained_width - retained.bit_length()
            assert lz in (1, 2)
            counts.add(lz)

    return counts


def exhaust_round_boundary(ebits: int, sbits: int) -> int:
    """Check every modular count source and legal lz at a width crossing."""

    source_width = ebits + 2
    shift_width = 2 * (sbits + 4)
    assert source_width > shift_width

    mask = (1 << source_width) - 1
    cap = sbits + 2
    states = 0

    # sigma_add is an affine translation of exp modulo 2^source_width, so
    # ranging over it covers every possible exponent bit pattern.
    for sigma_add in range(1 << source_width):
        for lz in range(sbits + 5):
            tiny = signed((sigma_add - lz) & mask, source_width) <= -1
            sigma = sigma_add if tiny else lz

            if signed(sigma, source_width) <= -1:
                selected = min((-sigma) & mask, cap)
            else:
                selected = sigma

            assert selected < shift_width
            assert selected == (selected & ((1 << shift_width) - 1))
            states += 1

    return states


def check_wide_cap_regression() -> dict[str, int]:
    """Check the FP(2,16) count whose cap wraps at exponent width."""

    ebits = 2
    sbits = 16
    sigma_width = ebits + 2
    sigma = -6
    cap = sbits + 2
    old_cap = cap & ((1 << sigma_width) - 1)
    selected = min(-sigma, cap)

    assert old_cap == 2
    assert selected == 6
    assert selected < 2 * (sbits + 4)
    return {
        "ebits": ebits,
        "sbits": sbits,
        "sigma": sigma,
        "cap": cap,
        "wrapped_cap": old_cap,
        "selected_shift": selected,
    }


def check_deep_underflow_shift() -> dict[str, int]:
    """Prove the local deep-underflow shift and extraction bounds."""

    minimum: tuple[int, int] | None = None
    minimum_width_margin: int | None = None
    first_source_loss_ebits: int | None = None
    minimum_remaining_leading_position: int | None = None
    for ebits in range(2, 64):
        round_min = -(1 << (ebits + 1))
        first_below_range = round_min - 1
        min_normal_exp = 2 - (1 << (ebits - 1))
        shift = min_normal_exp - first_below_range - 1
        assert shift == 2 + 3 * (1 << (ebits - 1))
        assert shift >= 8
        if minimum is None or shift < minimum[1]:
            minimum = (ebits, shift)

        # exp_bits exceeds ebits + 2 first at sbits = 2^ebits + 4. The
        # maximum shift grows once per additional significand bit, while the
        # extended significand width grows twice, so the narrowest such format
        # has the smallest safety margin for every larger sbits.
        minimum_sbits = (1 << ebits) + 4
        maximum_shift = minimum_sbits + (1 << (ebits - 1)) - 2
        extended_sig_width = 2 * (minimum_sbits + 4)
        width_margin = extended_sig_width - maximum_shift
        assert width_margin > 0
        if minimum_width_margin is None or width_margin < minimum_width_margin:
            minimum_width_margin = width_margin

        # The normalized res_sig leading one is at bit sbits + 2 and moves to
        # bit 2*sbits + 6 after zero padding. If the right shift passes that
        # padding, the leading one remains in the reduced low slice, making
        # sticky one before any lower source bits can be lost. The relevant
        # margins grow or stay constant as sbits grows, so the first
        # exceptional sbits proves every larger format at the same ebits.
        padding_width = minimum_sbits + 4
        leading_position = 2 * minimum_sbits + 6
        discarded_high = minimum_sbits + 5
        if maximum_shift > padding_width:
            first_source_loss_shift = padding_width + 1
            leading_at_first_loss = leading_position - first_source_loss_shift
            leading_at_maximum_shift = leading_position - maximum_shift
            assert 0 <= leading_at_maximum_shift
            assert leading_at_maximum_shift <= leading_at_first_loss
            assert leading_at_first_loss <= discarded_high
            if first_source_loss_ebits is None:
                first_source_loss_ebits = ebits
            if (
                minimum_remaining_leading_position is None
                or leading_at_maximum_shift < minimum_remaining_leading_position
            ):
                minimum_remaining_leading_position = leading_at_maximum_shift

    assert minimum is not None
    assert minimum_width_margin is not None
    assert first_source_loss_ebits is not None
    assert minimum_remaining_leading_position is not None
    return {
        "ebits": minimum[0],
        "first_source_loss_ebits": first_source_loss_ebits,
        "minimum_remaining_leading_position": minimum_remaining_leading_position,
        "shift": minimum[1],
        "minimum_width_margin": minimum_width_margin,
    }


def main() -> None:
    formats = [
        check_format(ebits, sbits)
        for ebits in range(2, 64)
        for sbits in range(2, ebits)
    ]
    assert len(formats) == 1891

    correction_counts = Counter(row["correction"] for row in formats)
    assert correction_counts == {
        "extract": 61,
        "equal": 60,
        "zero_extend": 1770,
    }

    crossings = [row for row in formats if row["round_crossing"]]
    assert len(crossings) == 729
    assert sum(int(row["sbits"]) >= 3 for row in crossings) == 676

    first_crossings: dict[int, int] = {}
    for row in crossings:
        sbits = int(row["sbits"])
        first_crossings.setdefault(sbits, int(row["ebits"]))
    assert all(ebits == 2 * sbits + 7 for sbits, ebits in first_crossings.items())

    boundaries = [(11, 2), (13, 3), (15, 4)]
    exhaustive_states = sum(
        exhaust_round_boundary(ebits, sbits) for ebits, sbits in boundaries
    )

    quotient_lz_counts: set[int] = set()
    for sbits in range(2, 13):
        quotient_lz_counts.update(exhaust_normalized_quotients(sbits))
    assert quotient_lz_counts == {1, 2}

    widest = check_format(63, 2)
    widest_c_api = check_format(63, 3)
    width_ratio = Fraction(int(widest["exp_width"]), int(widest["shift_width"]))
    c_api_ratio = Fraction(
        int(widest_c_api["exp_width"]), int(widest_c_api["shift_width"])
    )
    wide_cap = check_wide_cap_regression()
    minimum_deep_underflow_shift = check_deep_underflow_shift()

    output = {
        "verdict": "PASS",
        "accepted_ebits_gt_sbits_formats": len(formats),
        "c_api_formats_with_sbits_at_least_3": sum(
            int(row["sbits"]) >= 3 for row in formats
        ),
        "correction_width_categories": dict(sorted(correction_counts.items())),
        "round_width_crossings": len(crossings),
        "c_api_round_width_crossings": sum(
            int(row["sbits"]) >= 3 for row in crossings
        ),
        "first_round_crossings": {
            str(sbits): first_crossings[sbits]
            for sbits in sorted(first_crossings)[:8]
        },
        "exhaustive_round_boundaries": [
            {"ebits": ebits, "sbits": sbits} for ebits, sbits in boundaries
        ],
        "exhaustive_modular_states": exhaustive_states,
        "exhaustive_normalized_quotient_sbits": {"min": 2, "max": 12},
        "finite_quotient_res_sig_lz": sorted(quotient_lz_counts),
        "minimum_deep_underflow_shift": minimum_deep_underflow_shift,
        "maximum_format": {
            "ebits": 63,
            "sbits": 2,
            "source_count_width": widest["exp_width"],
            "shift_data_width": widest["shift_width"],
            "widening_ratio": f"{width_ratio.numerator}/{width_ratio.denominator}",
        },
        "maximum_c_api_relative_width_format": {
            "ebits": 63,
            "sbits": 3,
            "source_count_width": widest_c_api["exp_width"],
            "shift_data_width": widest_c_api["shift_width"],
            "widening_ratio": f"{c_api_ratio.numerator}/{c_api_ratio.denominator}",
        },
        "wide_cap_regression": wide_cap,
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
