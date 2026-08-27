import time, sys
from solver import CDCLSolver, parse_cnf

def test_file(path):
    nvars, clauses = parse_cnf(path)
    t0 = time.time()
    s = CDCLSolver(nvars, clauses)
    verdict, model = s.solve()
    dt = time.time() - t0
    print(f"{path}: {verdict} in {dt:.3f}s (conflicts={s.conflicts}, decisions={s.decisions}, props={s.propagations})")

if __name__ == "__main__":
    for p in sys.argv[1:]:
        test_file(p)
