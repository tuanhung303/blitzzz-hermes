#!/usr/bin/env python3
"""CDCL SAT solver (from scratch, stdlib only)."""
import sys
import heapq


def luby(i):
    """Luby restart sequence: 1,1,2,1,1,2,4,1,1,2,1,1,2,4,8,..."""
    k = 0
    while (1 << (k + 1)) - 1 <= i:
        k += 1
    m = (1 << k) - 1
    if i == m:
        return 1 << (k - 1)
    return luby(i - m)


class Solver:
    def __init__(self, nvars):
        self.nvars = nvars
        size = 2 * (nvars + 1)
        self.val = [None] * size          # per literal True/False/None
        self.level = [-1] * (nvars + 1)   # decision level, -1 = unassigned, 0 = unit/root
        self.reason = [None] * (nvars + 1)  # clause index that implied var
        self.activity = [0.0] * (nvars + 1)
        self.phase = [1] * (nvars + 1)    # 1 prefer positive, -1 prefer negative
        self.watches = [[] for _ in range(size)]
        self.clauses = []
        self.is_learnt = []
        self.lbd = []
        self.clause_act = []
        self.trail = []
        self.trail_lim = []
        self.qhead = 0
        self.heap = [(0.0, v) for v in range(1, nvars + 1)]
        heapq.heapify(self.heap)
        self.var_inc = 1.0
        self.var_decay = 0.95
        self.clause_inc = 1.0
        self.clause_decay = 0.999
        self.conflicts = 0
        self.decisions = 0
        self.assigned = 0
        self.restart_base = 64
        self.learnt_budget = 1.0          # factor * nvars + 100
        self.max_learnt = 0

    # ---- assignment ----
    def assign(self, lit, reason):
        v = lit >> 1
        self.val[lit] = True
        self.val[lit ^ 1] = False
        self.level[v] = len(self.trail_lim)
        self.reason[v] = reason
        self.phase[v] = 1 if (lit & 1) == 0 else -1
        self.trail.append(lit)
        self.assigned += 1

    def unassign(self, lit):
        self.val[lit] = None
        self.val[lit ^ 1] = None
        v = lit >> 1
        self.level[v] = -1
        self.reason[v] = None
        self.assigned -= 1

    def backtrack(self, bt):
        target = self.trail_lim[bt]
        trail = self.trail
        while len(trail) > target:
            self.unassign(trail.pop())
        del self.trail_lim[bt:]
        self.qhead = len(trail)

    # ---- clause management ----
    def add_clause(self, lits, learnt):
        cid = len(self.clauses)
        self.clauses.append(lits)
        self.is_learnt.append(learnt)
        if learnt:
            lbd = len({self.level[l >> 1] for l in lits})
            self.lbd.append(lbd)
            self.clause_act.append(self.clause_inc)
        else:
            self.lbd.append(0)
            self.clause_act.append(0.0)
        n = len(lits)
        if n >= 2:
            if learnt:
                # put the asserting (UIP) literal at index 1 so it is watched
                lits[1], lits[-1] = lits[-1], lits[1]
            self.watches[lits[0]].append(cid)
            self.watches[lits[1]].append(cid)
        else:
            self.watches[lits[0]].append(cid)
        return cid

    # ---- propagation (two watched literals) ----
    def propagate(self):
        val = self.val
        watches = self.watches
        clauses = self.clauses
        trail = self.trail
        assign = self.assign
        while self.qhead < len(trail):
            p = trail[self.qhead]
            self.qhead += 1
            wl = watches[p ^ 1]
            j = 0
            while j < len(wl):
                cid = wl[j]
                c = clauses[cid]
                if c[0] == (p ^ 1):
                    if len(c) == 1:
                        return cid
                    other = c[1]
                    repl = -1
                    k = 2
                    clen = len(c)
                    while k < clen:
                        if val[c[k]] is not False:
                            repl = k
                            break
                        k += 1
                    if repl >= 0:
                        c[0] = c[repl]
                        c[repl] = p ^ 1
                        watches[c[0]].append(cid)
                        wl[j] = wl[-1]
                        wl.pop()
                        continue
                    if val[other] is True:
                        j += 1
                    elif val[other] is None:
                        assign(other, cid)
                        j += 1
                    else:
                        return cid
                else:
                    if len(c) == 1:
                        return cid
                    other = c[0]
                    repl = -1
                    k = 2
                    clen = len(c)
                    while k < clen:
                        if val[c[k]] is not False:
                            repl = k
                            break
                        k += 1
                    if repl >= 0:
                        c[1] = c[repl]
                        c[repl] = p ^ 1
                        watches[c[1]].append(cid)
                        wl[j] = wl[-1]
                        wl.pop()
                        continue
                    if val[other] is True:
                        j += 1
                    elif val[other] is None:
                        assign(other, cid)
                        j += 1
                    else:
                        return cid
        return -1

    # ---- conflict analysis (1-UIP) ----
    def analyze(self, confl):
        learnt = []
        seen = [False] * (self.nvars + 1)
        level = self.level
        trail = self.trail
        reason = self.reason
        clauses = self.clauses
        activity = self.activity
        var_inc = self.var_inc
        heap = self.heap
        cur = len(self.trail_lim)
        counter = 0
        idx = len(trail) - 1
        clause = clauses[confl]
        p = None
        while True:
            for lit in clause:
                v = lit >> 1
                if not seen[v] and level[v] > 0:
                    seen[v] = True
                    activity[v] += var_inc
                    heapq.heappush(heap, (-activity[v], v))
                    if level[v] == cur:
                        counter += 1
                    else:
                        learnt.append(lit)
            while not seen[trail[idx] >> 1]:
                idx -= 1
            lit = trail[idx]
            v = lit >> 1
            idx -= 1
            if counter == 1:
                p = lit
                break
            counter -= 1
            clause = clauses[reason[v]]
        learnt.append(p ^ 1)
        # backtrack level = max level among learnt[:-1] (exclude the UIP literal)
        bt = 0
        for lit in learnt[:-1]:
            lv = level[lit >> 1]
            if lv > bt:
                bt = lv
        return learnt, bt

    # ---- decision (VSIDS) ----
    def decide(self):
        heap = self.heap
        level = self.level
        activity = self.activity
        while heap:
            neg_act, v = heap[0]
            if level[v] == -1 and -neg_act == activity[v]:
                break
            heapq.heappop(heap)
        if not heap:
            # rebuild from all currently unassigned vars (guarantees completeness)
            unassigned = [v for v in range(1, self.nvars + 1) if level[v] == -1]
            if not unassigned:
                return False
            heap[:] = [(-activity[v], v) for v in unassigned]
            heapq.heapify(heap)
        neg_act, v = heap[0]
        lit = (v << 1) if self.phase[v] >= 0 else (v << 1) | 1
        self.trail_lim.append(len(self.trail))
        self.assign(lit, None)
        self.decisions += 1
        return True

    def bump_var(self, v):
        self.activity[v] += self.var_inc
        if self.activity[v] > 1e100:
            self.rescale_activity()
        heapq.heappush(self.heap, (-self.activity[v], v))

    def rescale_activity(self):
        for v in range(1, self.nvars + 1):
            self.activity[v] *= 1e-100
        self.var_inc *= 1e-100
        self.heap = [(-self.activity[v], v) for v in range(1, self.nvars + 1)]
        heapq.heapify(self.heap)

    # ---- clause DB reduction ----
    def reduce_db(self):
        learnt_ids = [i for i in range(len(self.clauses)) if self.is_learnt[i]]
        # lock clauses that are reasons of currently-assigned literals
        locked = set()
        for v in range(1, self.nvars + 1):
            r = self.reason[v]
            if r is not None:
                locked.add(r)
        keep = []
        discard = []
        for i in learnt_ids:
            if i in locked or self.lbd[i] <= 2:
                keep.append(i)
            else:
                discard.append(i)
        discard.sort(key=lambda i: (self.lbd[i], -self.clause_act[i]))
        keep += discard[len(discard) // 2:]
        keep_set = set(keep)
        remap = {}
        new_clauses = []
        new_learnt = []
        new_lbd = []
        new_act = []
        for i in range(len(self.clauses)):
            if self.is_learnt[i] and i not in keep_set:
                continue
            remap[i] = len(new_clauses)
            new_clauses.append(self.clauses[i])
            new_learnt.append(self.is_learnt[i])
            new_lbd.append(self.lbd[i])
            new_act.append(self.clause_act[i])
        self.clauses = new_clauses
        self.is_learnt = new_learnt
        self.lbd = new_lbd
        self.clause_act = new_act
        size = 2 * (self.nvars + 1)
        self.watches = [[] for _ in range(size)]
        for cid, c in enumerate(self.clauses):
            if len(c) >= 2:
                self.watches[c[0]].append(cid)
                self.watches[c[1]].append(cid)
            else:
                self.watches[c[0]].append(cid)
        for v in range(1, self.nvars + 1):
            r = self.reason[v]
            if r is not None:
                self.reason[v] = remap[r]

    # ---- main search ----
    def solve(self):
        # initial propagation
        if self.propagate() != -1:
            return False
        self.noriginal = len(self.clauses)
        self.max_learnt = int(self.nvars * 1.5) + 200
        luby_idx = 1
        conflicts_since_restart = 0
        while True:
            confl = self.propagate()
            if confl != -1:
                if not self.trail_lim:
                    return False
                self.conflicts += 1
                self.clause_inc *= (1.0 / self.clause_decay)
                learnt, bt = self.analyze(confl)
                asserting = learnt[-1]
                cid = self.add_clause(learnt, True)
                # bump clause activity of reasons used (approximate: conflict clause)
                self.clause_act[cid] = self.clause_inc
                self.backtrack(bt)
                self.assign(asserting, cid)
                self.var_inc *= (1.0 / self.var_decay)
                conflicts_since_restart += 1
                if conflicts_since_restart >= self.restart_base * luby(luby_idx):
                    luby_idx += 1
                    if self.trail_lim:
                        self.backtrack(0)
                    conflicts_since_restart = 0
                nlearnt = sum(self.is_learnt)
                if nlearnt > self.max_learnt:
                    self.reduce_db()
            else:
                if self.assigned == self.nvars:
                    return True
                if not self.decide():
                    # heap exhausted but not all assigned: shouldn't happen
                    return self.assigned == self.nvars


def parse_dimacs(path):
    with open(path) as f:
        data = f.read()
    data = data.split('%')[0]
    tokens = []
    for line in data.splitlines():
        line = line.strip()
        if not line or line[0] == 'c':
            continue
        tokens.extend(line.split())
    it = iter(tokens)
    try:
        assert next(it) == 'p'
        assert next(it) == 'cnf'
        nvars = int(next(it))
        ncl = int(next(it))
    except (StopIteration, AssertionError):
        raise ValueError("bad DIMACS header")
    clauses = []
    cur = []
    for tok in it:
        x = int(tok)
        if x == 0:
            if cur:
                clauses.append(cur)
                cur = []
        else:
            cur.append(x)
    if cur:
        clauses.append(cur)
    return nvars, clauses


def solve_file(path):
    nvars, clauses = parse_dimacs(path)
    s = Solver(nvars)
    for cl in clauses:
        pos = set()
        neg = set()
        for lit in cl:
            (pos if lit > 0 else neg).add(abs(lit))
        if pos & neg:
            continue  # tautology
        vs = sorted(pos.union(neg))
        # convert DIMACS literals to internal encoding: lit = var*2 (pos) / var*2+1 (neg)
        clean = [(a << 1) if a in pos else (a << 1) | 1 for a in vs]
        if not clean:
            print("UNSAT")
            return
        s.add_clause(clean, False)
    if s.solve():
        out = ["SAT"]
        for v in range(1, nvars + 1):
            if s.val[v << 1] is True:
                out.append(str(v))
            else:
                out.append(str(-v))
        print(" ".join(out))
    else:
        print("UNSAT")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: solver.py <file.cnf>", file=sys.stderr)
        sys.exit(2)
    solve_file(sys.argv[1])
