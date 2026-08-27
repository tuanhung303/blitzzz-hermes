import sys
def parse_cnf(path):
    nv, clauses = None, []
    cur = []
    for line in open(path):
        line = line.split('%')[0].strip()
        if not line or line.startswith('c'): continue
        toks = line.split()
        if toks[0] == 'p': nv, ncl = int(toks[2]), int(toks[3])
        else:
            for t in toks:
                x = int(t)
                if x == 0:
                    if cur: clauses.append(cur)
                    cur = []
                else: cur.append(x)
    if cur: clauses.append(cur)
    return nv, clauses

def main():
    cnf = sys.argv[1]
    nv, clauses = parse_cnf(cnf)
    out = open(sys.argv[2]).read().split()
    if out[0].upper() == 'UNSAT':
        print('UNSAT'); return
    asn = {}
    for t in out[1:]:
        l = int(t); asn[abs(l)] = l > 0
    ok = len(asn) == nv
    for cl in clauses:
        if not any((l > 0) == asn[abs(l)] for l in cl):
            ok = False; print('VIOLATED:', cl); break
    print('model covers %d/%d vars, all clauses satisfied: %s' % (len(asn), nv, ok))
main()
