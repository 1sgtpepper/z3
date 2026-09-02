#!/usr/bin/env python3
"""Diagnostic harness for the semantic NaN/EUF boundary in Z3 issue #7842."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path("issue7842-nan-anchor")
Z3 = Path("build/z3")

TESTS: dict[str, tuple[str, str]] = {
    "01-issue-7842.smt2": (
        "unsat",
        """(set-logic ALL)
(declare-datatype Expr ((Flt (getFlt_1 (_ FloatingPoint 8 24)))))
(declare-fun x () Expr)
(assert (distinct x (Flt (_ NaN 8 24))))
(assert (fp.isNaN (getFlt_1 x)))
(check-sat)
(get-model)
""",
    ),
    "02-uf-nan.smt2": (
        "unsat",
        """(set-logic ALL)
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(declare-fun g ((_ FloatingPoint 8 24)) Int)
(assert (fp.isNaN a))
(assert (fp.isNaN b))
(assert (distinct (g a) (g b)))
(check-sat)
(get-model)
""",
    ),
    "03-predicate-nan.smt2": (
        "unsat",
        """(set-logic ALL)
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(declare-fun p ((_ FloatingPoint 8 24)) Bool)
(assert (fp.isNaN a))
(assert (fp.isNaN b))
(assert (p a))
(assert (not (p b)))
(check-sat)
(get-model)
""",
    ),
    "04-array-nan.smt2": (
        "unsat",
        """(set-logic ALL)
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(declare-fun A () (Array (_ FloatingPoint 8 24) Int))
(assert (fp.isNaN a))
(assert (fp.isNaN b))
(assert (distinct (select A a) (select A b)))
(check-sat)
(get-model)
""",
    ),
    "05-nested-datatype.smt2": (
        "unsat",
        """(set-logic ALL)
(declare-datatype Inner ((I (iv (_ FloatingPoint 8 24)))))
(declare-datatype Outer ((O (ov Inner))))
(declare-fun x () Outer)
(assert (distinct x (O (I (_ NaN 8 24)))))
(assert (fp.isNaN (iv (ov x))))
(check-sat)
(get-model)
""",
    ),
    "06-two-nan-payloads-through-uf.smt2": (
        "unsat",
        """(set-logic ALL)
(define-fun n1 () (_ FloatingPoint 8 24)
  (fp #b0 #xff #b00000000000000000000001))
(define-fun n2 () (_ FloatingPoint 8 24)
  (fp #b1 #xff #b10000000000000000000000))
(declare-fun g ((_ FloatingPoint 8 24)) Int)
(assert (distinct (g n1) (g n2)))
(check-sat)
(get-model)
""",
    ),
    "07-two-nan-payloads-direct.smt2": (
        "unsat",
        """(set-logic ALL)
(define-fun n1 () (_ FloatingPoint 8 24)
  (fp #b0 #xff #b00000000000000000000001))
(define-fun n2 () (_ FloatingPoint 8 24)
  (fp #b1 #xff #b10000000000000000000000))
(assert (distinct n1 n2))
(check-sat)
""",
    ),
    "08-issue-6728.smt2": (
        "unsat",
        """(set-logic ALL)
(declare-const c RoundingMode)
(declare-const x Float64)
(declare-sort T 0)
(declare-fun f (Float64) T)
(assert (not (= (f (fp.add c x (_ NaN 11 53)))
                (f (fp.add c (_ NaN 11 53) x)))))
(check-sat)
(get-model)
""",
    ),
    "09-finite-equality-through-uf.smt2": (
        "unsat",
        """(set-logic ALL)
(define-fun one () (_ FloatingPoint 8 24)
  (fp #b0 #x7f #b00000000000000000000000))
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(declare-fun g ((_ FloatingPoint 8 24)) Int)
(assert (fp.eq a one))
(assert (fp.eq b one))
(assert (distinct (g a) (g b)))
(check-sat)
(get-model)
""",
    ),
    "10-infinity-equality-through-uf.smt2": (
        "unsat",
        """(set-logic ALL)
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(declare-fun g ((_ FloatingPoint 8 24)) Int)
(assert (fp.eq a (_ +oo 8 24)))
(assert (fp.eq b (_ +oo 8 24)))
(assert (distinct (g a) (g b)))
(check-sat)
(get-model)
""",
    ),
    "11-signed-zero-fpeq-control.smt2": (
        "sat",
        """(set-logic ALL)
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(declare-fun g ((_ FloatingPoint 8 24)) Int)
; fp.eq identifies +0 and -0, while SMT equality deliberately does not.
(assert (fp.eq a (_ +zero 8 24)))
(assert (fp.eq b (_ +zero 8 24)))
(assert (distinct (g a) (g b)))
(check-sat)
(get-model)
""",
    ),
    "12-signed-zero-builtin-control.smt2": (
        "sat",
        """(set-logic ALL)
(declare-fun g ((_ FloatingPoint 8 24)) Int)
(assert (distinct (g (_ +zero 8 24)) (g (_ -zero 8 24))))
(check-sat)
(get-model)
""",
    ),
    "13-unconstrained-uf-control.smt2": (
        "sat",
        """(set-logic ALL)
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(declare-fun g ((_ FloatingPoint 8 24)) Int)
(assert (distinct (g a) (g b)))
(check-sat)
(get-model)
""",
    ),
    "14-direct-nan-disequality-control.smt2": (
        "unsat",
        """(set-logic ALL)
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(assert (fp.isNaN a))
(assert (fp.isNaN b))
(assert (distinct a b))
(check-sat)
""",
    ),
    "15-explicit-equality-bridge-control.smt2": (
        "unsat",
        """(set-logic ALL)
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(declare-fun g ((_ FloatingPoint 8 24)) Int)
(assert (fp.isNaN a))
(assert (fp.isNaN b))
(assert (= a b))
(assert (distinct (g a) (g b)))
(check-sat)
""",
    ),
    "16-incremental-nan-uf.smt2": (
        "unsat,sat",
        """(set-logic ALL)
(declare-fun a () (_ FloatingPoint 8 24))
(declare-fun b () (_ FloatingPoint 8 24))
(declare-fun g ((_ FloatingPoint 8 24)) Int)
(push)
(assert (fp.isNaN a))
(assert (fp.isNaN b))
(assert (distinct (g a) (g b)))
(check-sat)
(pop)
(assert (distinct (g a) (g b)))
(check-sat)
""",
    ),
}


def fetch_issue_6972() -> str:
    token = os.environ.get("GH_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        "https://api.github.com/repos/Z3Prover/z3/issues/6972", headers=headers
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)["body"]
    blocks = re.findall(r"```(?:smt|smt2)?\s*\n(.*?)```", body, flags=re.S | re.I)
    if not blocks:
        raise RuntimeError("could not recover issue #6972 SMT block")
    return blocks[0].replace("\r\n", "\n").replace("\r", "\n")


def prepare() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    all_tests = dict(TESTS)
    all_tests["17-issue-6972-regression.smt2"] = ("unsat", fetch_issue_6972())
    for name, (_, source) in all_tests.items():
        (ROOT / name).write_text(source)
    (ROOT / "expected.tsv").write_text(
        "".join(f"{name}\t{expected}\n" for name, (expected, _) in all_tests.items())
    )


def expected_cases() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in (ROOT / "expected.tsv").read_text().splitlines():
        name, expected = line.split("\t", 1)
        rows.append((name, expected))
    return rows


def run_suite(stage: str, strict: bool) -> None:
    result_path = ROOT / f"{stage}-results.txt"
    failures = 0
    chunks: list[str] = []
    for name, expected in expected_cases():
        command = [str(Z3), "model_validate=true", str(ROOT / name)]
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
            f"===== {name} (expected {expected}) =====\n"
            f"{output}"
            f"actual={actual or '<none>'} exit={status} invalid_model={'yes' if invalid else 'no'}\n"
            f"oracle={'PASS' if ok else 'FAIL'}\n\n"
        )
        if strict and not ok:
            failures += 1
    result_path.write_text("".join(chunks))
    print(result_path.read_text())
    if failures:
        raise SystemExit(f"{failures} patched oracle case(s) failed")


def apply_patch() -> None:
    path = Path("src/smt/theory_fpa.cpp")
    source = path.read_text()
    old = (
        "        if (m_fpa_util.is_float(n) || m_fpa_util.is_rm(n)) {\n"
        "            if (!m_fpa_util.is_fp(n)) {\n"
    )
    new = (
        "        if (m_fpa_util.is_float(n) || m_fpa_util.is_rm(n)) {\n"
        "            // SMT-LIB has one abstract NaN value, while the BV encoding has\n"
        "            // many NaN payloads. Expose this quotient equality to the core so\n"
        "            // EUF congruence cannot distinguish semantically equal NaN terms.\n"
        "            // This constrains only abstract equality, not the wrapped payload.\n"
        "            if (m_fpa_util.is_float(n)) {\n"
        "                unsigned ebits = m_fpa_util.get_ebits(n->get_sort());\n"
        "                unsigned sbits = m_fpa_util.get_sbits(n->get_sort());\n"
        "                expr_ref is_nan(m), nan_eq(m);\n"
        "                is_nan = m_fpa_util.mk_is_nan(n);\n"
        "                nan_eq = m.mk_eq(n, m_fpa_util.mk_nan(ebits, sbits));\n"
        "                assert_cnstr(m.mk_implies(is_nan, nan_eq));\n"
        "            }\n\n"
        "            if (!m_fpa_util.is_fp(n)) {\n"
    )
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected one insertion site, found {count}")
    path.write_text(source.replace(old, new, 1))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: issue_7842_nan_anchor.py prepare|baseline|patch|patched")
    command = sys.argv[1]
    if command == "prepare":
        prepare()
    elif command == "baseline":
        run_suite("baseline", strict=False)
    elif command == "patch":
        apply_patch()
    elif command == "patched":
        run_suite("patched", strict=True)
    else:
        raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
