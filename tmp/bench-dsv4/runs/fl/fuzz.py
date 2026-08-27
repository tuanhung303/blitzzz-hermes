import random, subprocess, sys
from itertools import product

def brute(nv, clauses):
    for asn in product([False, True], repeat=nv):
        if all(any(asn[abs(l)-1] == (l > 0) for l in cl) for cl in clauses):
            return True, asn
    return False, None

random.seed(int(sys.argv[1]))
for trial in range(300):
    nv = random.randint(2, 8)
    ncl = random.randint(1, 20)
    clauses = []
    for _ in range(ncl):
        k = random.randint(1, nv)
        lits = set()
        while len(lits) < k:
            v = random.randint(1, nv)
            lits.add(v if random.random() < 0.5 else -v)
        clauses.append(list(lits))
    with open('./fz.cnf', 'w') as f:
        f.write(f'p cnf {nv} {len(clauses)}\n')
        for cl in clauses:
            f.write(' '.join(map(str, cl)) + ' 0\n')
    exp_sat, model = brute(nv, clauses)
    r = subprocess.run(['python3', 'solver.py', './fz.cnf'], capture_output=True, text=True)
    out = r.stdout.split()
    got = out[0].upper() if out else 'ERR'
    if got == 'SAT':
        asn = {}
        for t in out[1:]:
            l = int(t); asn[abs(l)] = l > 0
        if len(asn) != nv or not all(any(asn[abs(l)] == (l > 0) for l in cl) for cl in clauses):
            print('INVALID MODEL trial', trial, nv, clauses, out[:10]); sys.exit(1)
        if not exp_sat:
            print('FALSE SAT trial', trial, nv, clauses); sys.exit(1)
    elif got == 'UNSAT':
        if exp_sat:
            print('FALSE UNSAT trial', trial, nv, clauses); sys.exit(1)
    else:
        print('NO VERDICT trial', trial, r.stdout, r.stderr); sys.exit(1)
print('all 300 trials OK')
