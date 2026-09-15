"""CI-only, untraced cost observations from identified candidate binaries."""

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


executables, output = map(lambda p: Path(p).resolve(), sys.argv[1:])
output.mkdir(parents=True, exist_ok=True)
stages = ["baseline", "raw", "guarded", "paired"]
binary_hashes = {stage: hashlib.sha256((executables / stage / "z3").read_bytes()).hexdigest()
                 for stage in stages}
configurations = {
    "euf": ["sat.euf=true", "model=false", "model_validate=false"],
    "default": ["model=false", "model_validate=false"],
    "structural": ["auto_config=false", "smt.relevancy=2", "smt.case_split=3",
                   "model=false", "model_validate=false"],
}
fixtures = {}
for kind, sizes in (("nan", (16, 128, 512, 4096)), ("finite", (128, 512, 4096)),
                    ("infinity", (128, 512, 4096))):
    for size in sizes:
        lines = ["(set-logic ALL)", "(declare-fun f ((_ FloatingPoint 3 3)) Int)"]
        for i in range(size):
            lines.extend([f"(declare-const s{i} (_ BitVec 1))",
                          f"(declare-const p{i} (_ BitVec 2))"])
            if kind == "nan":
                lines.append(f"(assert (distinct p{i} #b00))")
            exponent = "#b011" if kind == "finite" else "#b111"
            payload = "#b00" if kind == "infinity" else f"p{i}"
            lines.append(f"(assert (= (f (fp s{i} {exponent} {payload})) 0))")
        fixtures[f"{kind}-{size}"] = "\n".join([*lines, "(check-sat)", ""])
for size in (8, 16, 32, 64):
    lines = ["(set-logic ALL)", "(declare-const x0 (_ FloatingPoint 3 3))",
             "(declare-fun h ((_ FloatingPoint 3 3) (_ FloatingPoint 3 3)) (_ FloatingPoint 3 3))",
             "(assert (fp.isNaN x0))"]
    for i in range(1, size + 1):
        lines.extend([f"(define-fun x{i} () (_ FloatingPoint 3 3) (h x{i-1} x{i-1}))",
                      f"(assert (fp.isNaN x{i}))"])
    fixtures[f"shared-{size}"] = "\n".join([*lines, "(check-sat)", ""])

assert Path("/usr/bin/time").is_file()
rows = []
for number, (name, text) in enumerate(fixtures.items()):
    fixture = output / f"{name}.smt2"
    fixture.write_text(text)
    for configuration, options in configurations.items():
        for repeat in range(3):
            offset = (number + repeat) % len(stages)
            for stage in stages[offset:] + stages[:offset]:
                directory = output / name / configuration / str(repeat) / stage
                directory.mkdir(parents=True)
                solver = executables / stage / "z3"
                resources = directory / "resources.txt"
                command = ["/usr/bin/time", "-o", str(resources), "-f", "%U\n%S\n%M\n%e",
                           str(solver), "-st", *options, str(fixture)]
                environment = dict(os.environ, LD_LIBRARY_PATH=str(solver.parent))
                started = time.monotonic()
                process = subprocess.Popen(command, cwd=directory, env=environment,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True, start_new_session=True)
                timed_out = False
                try:
                    stdout, stderr = process.communicate(timeout=20)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    stdout, stderr = process.communicate()
                elapsed = time.monotonic() - started
                actual = [line for line in stdout.splitlines() if line in {"sat", "unsat", "unknown"}]
                passed = (not timed_out and process.returncode == 0 and actual == ["sat"]
                          and "(error" not in stdout and not stderr)
                row = dict(case=name, configuration=configuration, repeat=repeat, stage=stage,
                           expected=["sat"], actual=actual, passed=passed, timed_out=timed_out,
                           exit_code=process.returncode, elapsed_seconds=elapsed,
                           stdout=stdout, stderr=stderr, command=command,
                           binary_sha256=binary_hashes[stage],
                           resources=resources.read_text() if resources.exists() else None)
                (directory / "result.json").write_text(json.dumps(row, indent=2) + "\n")
                rows.append(row)
                print(name, configuration, repeat, stage, f"{elapsed:.4f}s", "PASS" if passed else "FAIL", flush=True)
(output / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
