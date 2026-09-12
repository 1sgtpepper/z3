"""Record issue 7842 outcomes without suppressing baseline or diagnostic failures."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

stage, source_arg, output_arg = sys.argv[1:]
assert stage in {"baseline", "raw", "broad"}
source = Path(source_arg).resolve()
output = Path(output_arg).resolve() / stage
output.mkdir(parents=True, exist_ok=True)
cases = Path(__file__).resolve().parent / "cases"
solver = source / "build/z3"
expected = json.loads((cases / "expected.json").read_text())
configurations = {
    "default": ["model_validate=true"],
    "relevancy-0": ["auto_config=false", "smt.relevancy=0", "model_validate=true"],
    "relevancy-2": ["auto_config=false", "smt.relevancy=2", "model_validate=true"],
    "no-model": ["model=false", "model_validate=false"],
}
focused = {"01-issue-7842.smt2", "19-selector-core-equality.smt2",
           "26-symbolic-payloads-uf.smt2", "30-nan-round-trip-payloads.smt2",
           "31-field-reuse-push-pop.smt2", "34-live-distinct-nan-payloads.smt2"}
rows = []
for name, oracle in expected.items():
    for configuration, options in configurations.items():
        directory = output / Path(name).stem / configuration
        directory.mkdir(parents=True, exist_ok=True)
        # Compact node events are collected in every process. Full traces are focused.
        tags = ["-tr:issue_7842"]
        if name in focused:
            tags += ["-tr:t_fpa", "-tr:t_fpa_detail", "-tr:t_fpa_internalize",
                     "-tr:add_eq", "-tr:add_diseq", "-tr:final_check", "-tr:get_model"]
        command = [str(solver), *tags, *options, str(cases / name)]
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=directory, capture_output=True,
                                    text=True, timeout=30)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as error:
            stdout = (error.stdout or b"").decode(errors="replace")
            stderr = (error.stderr or b"").decode(errors="replace") + "\nTIMEOUT\n"
            code = 124
        elapsed = time.monotonic() - started
        actual = [line for line in stdout.splitlines() if line in {"sat", "unsat", "unknown"}]
        passed = code == 0 and actual == oracle and "(error" not in stdout and not stderr
        trace = directory / ".z3-trace"
        levels, nodes, raw_nodes, events = set(), set(), set(), 0
        if trace.exists():
            trace = trace.rename(directory / "trace.log")
            with trace.open(errors="replace") as stream:
                for line in stream:
                    match = re.search(r"relevant node=(\d+) raw=([01]) level=(\d+)", line)
                    if match:
                        node, raw, level = map(int, match.groups())
                        events += 1
                        nodes.add(node)
                        levels.add(level)
                        if raw:
                            raw_nodes.add(node)
        row = dict(case=name, configuration=configuration, expected=oracle, actual=actual,
                   exit_code=code, passed=passed, elapsed_seconds=elapsed, command=command,
                   stdout=stdout, stderr=stderr, effective_relevancy=sorted(levels),
                   relevance_events=events, distinct_observed_node_ids=len(nodes),
                   distinct_observed_raw_node_ids=len(raw_nodes),
                   trace_bytes=trace.stat().st_size if trace.exists() else 0)
        rows.append(row)
        (directory / "result.json").write_text(json.dumps(row, indent=2) + "\n")
        print(f"{stage} {configuration} {name}: {actual} expected={oracle} "
              f"{'PASS' if passed else 'FAIL'} {elapsed:.3f}s levels={sorted(levels)}", flush=True)
(output / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
(output / "identity.json").write_text(json.dumps({
    "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip(),
    "binary_sha256": hashlib.sha256(solver.read_bytes()).hexdigest(),
    "passed": sum(row["passed"] for row in rows), "total": len(rows),
}, indent=2) + "\n")
# The workflow evaluates both interventions only after every variant has run.
