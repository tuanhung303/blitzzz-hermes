import sys, time, importlib.util, os
spec = importlib.util.spec_from_file_location("solver", os.path.join(os.path.dirname(os.path.abspath(__file__)), "solver.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

# args: seed random_freq rand_phase var_decay restart_base
seed = int(sys.argv[1]); rf = float(sys.argv[2]); rp = float(sys.argv[3]); vd = float(sys.argv[4]); rb = int(sys.argv[5])
import random
insts = [("task/grader/instances/rand250.cnf","rand250"), ("task/grader/hidden/rand220.cnf","rand220")]
for path,name in insts:
    nvars, clauses = m.parse_dimacs(path)
    s = m.Solver(nvars)
    s.rng = random.Random(seed)
    s.random_freq = rf
    s.rand_phase_on_restart = rp
    s.var_decay = vd
    s.restart_base = rb
    for cl in clauses: s.add_clause(cl)
    t = time.time(); sat = s.solve(); dt = time.time()-t
    print(f"cfg(seed={seed},rf={rf},rp={rp},vd={vd},rb={rb}) {name}: sat={sat} t={dt:.2f}s conf={s.nconflicts}", flush=True)
