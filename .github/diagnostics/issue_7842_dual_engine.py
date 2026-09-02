#!/usr/bin/env python3
"""Run issue #7842's semantic oracle through both Z3 SMT backends."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path("issue7842-nan-anchor")
Z3 = Path("build/z3")
ENGINES: dict[str, list[str]] = {
    "legacy": [],
    "sat-smt": ["sat.smt=true"],
}


def expected_cases() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in (ROOT / "expected.tsv").read_text().splitlines():
        name, expected = line.split("\t", 1)
        rows.append((name, expected))
    return rows


def run_suite(stage: str, strict: bool) -> None:
    failures = 0
    chunks: list[str] = []
    for engine, engine_args in ENGINES.items():
        for name, expected in expected_cases():
            command = [str(Z3), "model_validate=true", *engine_args, str(ROOT / name)]
            try:
                completed = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=180,
                    check=False,
                )
                output = completed.stdout
                status = completed.returncode
            except subprocess.TimeoutExpired as exc:
                output = (exc.stdout or "") + "\n<TIMEOUT>\n"
                status = 124

            actual = ",".join(
                line.strip()
                for line in output.splitlines()
                if line.strip() in {"sat", "unsat", "unknown"}
            )
            invalid = "invalid model was generated" in output
            ok = actual == expected and not invalid
            chunks.append(
                f"===== {engine}: {name} (expected {expected}) =====\n"
                f"command={' '.join(command)}\n"
                f"{output}"
                f"actual={actual or '<none>'} exit={status} "
                f"invalid_model={'yes' if invalid else 'no'}\n"
                f"oracle={'PASS' if ok else 'FAIL'}\n\n"
            )
            if strict and not ok:
                failures += 1

    result_path = ROOT / f"dual-engine-{stage}-results.txt"
    result_path.write_text("".join(chunks))
    print(result_path.read_text())
    if failures:
        raise SystemExit(f"{failures} patched dual-engine oracle case(s) failed")


def patch_sat_smt_backend() -> None:
    path = Path("src/sat/smt/fpa_solver.cpp")
    source = path.read_text()
    old = (
        "        else if (m_fpa_util.is_float(n) || m_fpa_util.is_rm(n)) {\n"
        "            expr* a = nullptr, * b = nullptr, * c = nullptr;\n"
    )
    new = (
        "        else if (m_fpa_util.is_float(n) || m_fpa_util.is_rm(n)) {\n"
        "            // The SMT floating-point domain has one abstract NaN value,\n"
        "            // although the BV encoding has many NaN representations.\n"
        "            // Merge the abstract term with NaN without constraining its\n"
        "            // wrapped sign/payload bits. This exposes semantic equality\n"
        "            // to EUF congruence while retaining representation freedom.\n"
        "            if (m_fpa_util.is_float(n)) {\n"
        "                unsigned ebits = m_fpa_util.get_ebits(n->get_sort());\n"
        "                unsigned sbits = m_fpa_util.get_sbits(n->get_sort());\n"
        "                sat::literal is_nan = mk_literal(m_fpa_util.mk_is_nan(n));\n"
        "                sat::literal nan_eq =\n"
        "                    eq_internalize(n, m_fpa_util.mk_nan(ebits, sbits));\n"
        "                add_clause(~is_nan, nan_eq);\n"
        "            }\n\n"
        "            expr* a = nullptr, * b = nullptr, * c = nullptr;\n"
    )
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected one SAT/SMT insertion site, found {count}")
    path.write_text(source.replace(old, new, 1))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: issue_7842_dual_engine.py baseline|patch|patched")
    command = sys.argv[1]
    if command == "baseline":
        run_suite("baseline", strict=False)
    elif command == "patch":
        patch_sat_smt_backend()
    elif command == "patched":
        run_suite("patched", strict=True)
    else:
        raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
