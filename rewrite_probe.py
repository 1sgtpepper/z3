"""Measure repeated simplification without treating stability as semantic correctness."""

import json
import sys
import z3


def dag_size(root):
    seen = set()
    pending = [root]
    while pending:
        node = pending.pop()
        if node.get_id() not in seen:
            seen.add(node.get_id())
            pending.extend(node.children())
    return len(seen)


raw = z3.fpFP(z3.BitVec('s', 1), z3.BitVec('e', 3), z3.BitVec('p', 2))
results = []
term = raw
status = 'completed'
error = None
try:
    for iteration in range(8):
        reduced = z3.simplify(term, max_steps=10000)
        results.append(dict(iteration=iteration, before_nodes=dag_size(term),
                            after_nodes=dag_size(reduced), unchanged=term.eq(reduced)))
        term = reduced
except z3.Z3Exception as exc:
    status = 'error'
    error = str(exc)

json.dump(dict(status=status, error=error, iterations=results), sys.stdout, indent=2)
print()
sys.exit(0 if status == 'completed' else 1)
