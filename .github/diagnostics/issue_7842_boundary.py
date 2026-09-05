"""Record semantic oracles and native traces for the FP equality boundary."""

import json
from pathlib import Path
import subprocess
import sys

stage = sys.argv[1]
assert stage in {"baseline", "intervention"}
solver = Path("build/z3").resolve()
cases = Path(".github/diagnostics/issue-7842-cases")
expected = json.loads((cases / "expected.json").read_text())
output_dir = Path("issue-7842-evidence") / stage
output_dir.mkdir(parents=True, exist_ok=True)
configurations = {
    "default": ["model_validate=true"],
    "relevancy-0": ["auto_config=false", "smt.relevancy=0", "model_validate=true"],
    "relevancy-2": ["auto_config=false", "smt.relevancy=2", "model_validate=true"],
    "no-model": ["model=false", "model_validate=false"],
}
rows = []
for name, oracle in expected.items():
    for configuration, options in configurations.items():
        command = [str(solver), *options, str((cases / name).resolve())]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as error:
            stdout = (error.stdout or b"").decode(errors="replace")
            stderr = (error.stderr or b"").decode(errors="replace") + "\nTIMEOUT\n"
            code = 124
        actual = [line for line in stdout.splitlines() if line in {"sat", "unsat", "unknown"}]
        passed = code == 0 and actual == oracle and "(error" not in stdout and not stderr
        row = dict(case=name, configuration=configuration, expected=oracle, actual=actual,
                   exit_code=code, passed=passed, command=command, stdout=stdout, stderr=stderr)
        rows.append(row)
        print(f"{stage} {configuration} {name}: {actual} expected={oracle} exit={code} {'PASS' if passed else 'FAIL'}", flush=True)
(output_dir / "results.json").write_text(json.dumps(rows, indent=2) + "\n")

traces = ["01-issue-7842.smt2", "19-selector-core-equality.smt2",
          "extra-04-finite-fp-semantic-equality.smt2", "03-predicate-nan.smt2",
          "26-symbolic-payloads-uf.smt2"]
for name in traces:
    directory = output_dir / Path(name).stem
    directory.mkdir(exist_ok=True)
    command = [str(solver), "-tr:t_fpa", "-tr:t_fpa_detail", "-tr:t_fpa_internalize",
               "-tr:datatype", "-tr:add_eq", "-tr:add_eq_detail", "-tr:add_diseq", "-tr:final_check",
               "-tr:final_check_step", "-tr:final_check_result", "-tr:after_search",
               "-tr:fixed_var_eh", "-tr:get_model", "model_validate=true",
               str((cases / name).resolve())]
    result = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=30)
    (directory / "stdout.txt").write_text(result.stdout)
    (directory / "stderr.txt").write_text(result.stderr)
    (directory / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    (directory / ".z3-trace").rename(directory / "trace.log")
    assert (directory / "trace.log").stat().st_size > 0, "native trace not captured"

if stage == "intervention" and any(not row["passed"] for row in rows):
    raise SystemExit("Semantic intervention did not satisfy every oracle; inspect all recorded outcomes.")
