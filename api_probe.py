"""CI-only lifecycle evidence for raw floating-point NaN congruence."""

import json
import sys
import z3


configuration = sys.argv[1]
assert configuration in {"default", "relevancy-0", "relevancy-2", "relevancy-2-structural", "euf"}
if configuration == "euf":
    z3.set_param("sat.euf", True)
elif configuration.startswith("relevancy-"):
    z3.set_param("auto_config", False)
    z3.set_param("smt.relevancy", int(configuration.split("-")[1]))
    if configuration == "relevancy-2-structural":
        z3.set_param("smt.case_split", 3)

records = []


def setup(ctx):
    solver = z3.Solver(ctx=ctx)
    solver.set(timeout=10000, unsat_core=True)
    p, q = z3.BitVecs("p q", 2, ctx=ctx)
    s, t = z3.BitVecs("s t", 1, ctx=ctx)
    f = z3.Function("f", z3.FPSort(3, 3, ctx), z3.IntSort(ctx))
    top = z3.BitVecVal(7, 3, ctx)
    left = f(z3.fpFP(s, top, p, ctx=ctx))
    right = f(z3.fpFP(t, top, q, ctx=ctx))
    guard = z3.Bool("guard", ctx)
    solver.add(p != 0, q != 0, z3.Implies(guard, left != right))
    return solver, guard, p, q, left, right


def check(name, solver, expected, *assumptions):
    result = solver.check(*assumptions)
    row = dict(name=name, expected=expected, actual=str(result),
               passed=str(result) == expected)
    if result == z3.unknown:
        row["reason"] = solver.reason_unknown()
    records.append(row)
    return result


def assumptions_and_scopes():
    ctx = z3.Context()
    solver, guard, p, q, left, right = setup(ctx)
    for index in range(3):
        result = check(f"assumption-{index}", solver, "unsat", guard)
        if result == z3.unsat:
            core = solver.unsat_core()
            records.append(dict(name=f"core-{index}",
                                passed=len(core) == 1 and core[0].eq(guard)))
        check(f"opposite-assumption-{index}", solver, "sat", z3.Not(guard))
    solver.push()
    solver.add(guard)
    check("pushed-guard", solver, "unsat")
    solver.pop()
    check("after-pop", solver, "sat")
    solver.push()
    solver.add(guard)
    check("repushed-guard", solver, "unsat")
    solver.pop()
    solver.reset()
    solver.add(p == 0, q == 1, left != right)
    check("reset-infinity-versus-nan", solver, "sat")


def translated_context():
    ctx = z3.Context()
    solver, guard, _, _, _, _ = setup(ctx)
    check("before-translation", solver, "unsat", guard)
    target = z3.Context()
    translated = solver.translate(target)
    translated.set(timeout=10000)
    target_guard = guard.translate(target)
    check("translated-guard", translated, "unsat", target_guard)
    check("translated-opposite", translated, "sat", z3.Not(target_guard))


def proof_context():
    ctx = z3.Context(proof=True)
    solver, guard, _, _, _, _ = setup(ctx)
    solver.add(guard)
    result = check("proof-enabled", solver, "unsat")
    if result == z3.unsat:
        proof = solver.proof()
        records.append(dict(name="proof-concludes-false",
                            passed=proof.num_args() > 0 and
                            z3.is_false(proof.arg(proof.num_args() - 1))))


for scenario in (assumptions_and_scopes, translated_context, proof_context):
    try:
        scenario()
    except z3.Z3Exception as error:
        records.append(dict(name=scenario.__name__, passed=False, error=str(error)))

json.dump(dict(configuration=configuration, version=z3.get_full_version(),
               records=records), sys.stdout, indent=2)
print()
sys.exit(0 if all(row["passed"] for row in records) else 1)
