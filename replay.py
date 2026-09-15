"""Record bounded search controls; inspect native traces before claiming replay."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


stage, source_arg, output_arg = sys.argv[1:]
assert stage in {"baseline", "paired"}
source = Path(source_arg).resolve()
output = Path(output_arg).resolve() / stage / "replay"
cases = Path(__file__).resolve().parent / "replay-controls"
solver = source / "build/z3"
binary_hash = hashlib.sha256(solver.read_bytes()).hexdigest()
rows = []
for answer in ("unsat", "sat"):
    fixture = cases / f"search-backtrack-{answer}.smt2"
    for phase in (0, 1, 3):
        directory = output / answer / str(phase)
        directory.mkdir(parents=True, exist_ok=True)
        command = [str(solver), "-tr:issue_7842", "-tr:t_fpa", "-tr:t_fpa_detail",
                   "-tr:decide", "-tr:decide_detail", "-tr:case_split", "-st",
                   "auto_config=false", "smt.relevancy=2", "smt.case_split=3",
                   f"smt.phase_selection={phase}", "model_validate=true", str(fixture)]
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=directory, capture_output=True,
                                    text=True, timeout=30)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as error:
            stdout = (error.stdout or b"").decode(errors="replace")
            stderr = (error.stderr or b"").decode(errors="replace") + "\nTIMEOUT\n"
            code = 124
        actual = [line for line in stdout.splitlines() if line in {"sat", "unsat", "unknown"}]
        row = dict(case=fixture.name, phase=phase, expected=[answer], actual=actual,
                   exit_code=code, elapsed_seconds=time.monotonic() - started,
                   passed=code == 0 and actual == [answer] and not stderr and "(error" not in stdout,
                   stdout=stdout, stderr=stderr, command=command,
                   input_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
                   binary_sha256=binary_hash)
        trace = directory / ".z3-trace"
        if trace.exists():
            trace.rename(directory / "trace.log")
        (directory / "result.json").write_text(json.dumps(row, indent=2) + "\n")
        rows.append(row)
        print(stage, answer, phase, actual, code, flush=True)
(output / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
