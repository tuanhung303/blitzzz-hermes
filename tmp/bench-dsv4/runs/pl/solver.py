#!/usr/bin/env python3
"""CDCL SAT solver (standard library only)."""
import sys
import heapq
import random


class Solver:
    def __init__(self, nvars):
        self.n = nvars
        self.watches = [[] for _ in range(2 * (nvars + 1))]
        self.value = [0] * (nvars + 1)
        self.level = [0] * (nvars + 1)
        self.reason = [None] * (nvars + 1)
        self.trail = []
        self.trail_lim = []
        self.qhead = 0
        self.dlevel = 0
        self.activity = [0.0] * (nvars + 1)
        self.phase = [0] * (nvars + 1)
        self.var_inc = 1.0
        self.var_decay = 0.95
        self.heap = []
        self.learnts = []
        self.units = []
        self.cla_act = {}
        self.cla_lbd = {}
        self.cla_inc = 1.0
        self.cla_decay = 0.999
        self.seen = [0] * (nvars + 1)
        self.stamp = 0
        self.nconflicts = 0
        self.ndecisions = 0
        self.nrestarts = 0
        self.restart_count = 0
        self.last_restart_conf = 0
        self.restart_base = 100
        self.max_learnts = max(1000, nvars * 30)
        self.unsat = False
        self.rng = random.Random(12345)
        self.random_freq = 0.0
        self.rand_phase_on_restart = 0.0

    @staticmethod
    def lit2idx(lit):
        return (lit << 1) if lit > 0 else ((-lit) << 1) | 1

    def lit_value(self, lit):
        return self.value[lit] if lit > 0 else -self.value[-lit]

    def add_clause(self, lits):
        seen = set()
        nl = []
        for l in lits:
            if -l in seen:
                return
            if l not in seen:
                seen.add(l)
                nl.append(l)
        if not nl:
            self.unsat = True
            return
        if len(nl) == 1:
            self._add_unit(nl[0])
        else:
            self._add_watched(nl)

    def _add_unit(self, l):
        v = self.lit_value(l)
        if v == -1:
            self.unsat = True
        elif v == 0:
            self.enqueue(l, None)

    def _add_watched(self, lits):
        self.watches[self.lit2idx(lits[0])].append(lits)
        self.watches[self.lit2idx(lits[1])].append(lits)

    def enqueue(self, lit, reason_clause):
        v = lit if lit > 0 else -lit
        self.value[v] = 1 if lit > 0 else -1
        self.level[v] = self.dlevel
        self.reason[v] = reason_clause
        self.trail.append(lit)

    def decide(self, lit):
        self.ndecisions += 1
        self.trail_lim.append(len(self.trail))
        self.dlevel += 1
        self.enqueue(lit, None)

    def cancel_until(self, blevel):
        while len(self.trail_lim) > blevel:
            lim = self.trail_lim.pop()
            while len(self.trail) > lim:
                p = self.trail.pop()
                v = p if p > 0 else -p
                self.phase[v] = 0 if self.value[v] > 0 else 1
                self.value[v] = 0
                self.level[v] = 0
                self.reason[v] = None
        self.dlevel = blevel
        self.qhead = len(self.trail)

    def propagate(self):
        watches = self.watches
        value = self.value
        trail = self.trail
        reason = self.reason
        level = self.level
        lit2idx = self.lit2idx
        while self.qhead < len(trail):
            p = trail[self.qhead]
            self.qhead += 1
            negp = -p
            ws = watches[lit2idx(negp)]
            i = 0
            n = len(ws)
            while i < n:
                c = ws[i]
                if c[1] == negp:
                    c[0], c[1] = c[1], c[0]
                other = c[1]
                ov = value[other] if other > 0 else -value[-other]
                if ov == 1:
                    i += 1
                    continue
                found = False
                m = len(c)
                for k in range(2, m):
                    lk = c[k]
                    lv = value[lk] if lk > 0 else -value[-lk]
                    if lv != -1:
                        c[0] = lk
                        c[k] = negp
                        watches[lit2idx(lk)].append(c)
                        ws[i] = ws[n - 1]
                        ws.pop()
                        n -= 1
                        found = True
                        break
                if found:
                    continue
                if ov == 0:
                    v = other if other > 0 else -other
                    value[v] = 1 if other > 0 else -1
                    level[v] = self.dlevel
                    reason[v] = c
                    trail.append(other)
                else:
                    return c
                i += 1
        return None

    def analyze(self, confl):
        learnt = [0]
        pathC = 0
        p = 0
        self.stamp += 1
        seen = self.seen
        activity = self.activity
        level = self.level
        trail = self.trail
        reason = self.reason
        dlevel = self.dlevel
        var_inc = self.var_inc
        cla_inc = self.cla_inc
        heap = self.heap
        heappush = heapq.heappush
        idx = len(trail) - 1
        while True:
            self._bump_clause(confl, cla_inc)
            for q in confl:
                v = q if q > 0 else -q
                if seen[v] != self.stamp and level[v] > 0 and q != p:
                    seen[v] = self.stamp
                    activity[v] += var_inc
                    heappush(heap, (-activity[v], v))
                    if level[v] == dlevel:
                        pathC += 1
                    else:
                        learnt.append(q)
            while seen[trail[idx] if trail[idx] > 0 else -trail[idx]] != self.stamp:
                idx -= 1
            p = trail[idx]
            confl = reason[p if p > 0 else -p]
            seen[p if p > 0 else -p] = 0
            pathC -= 1
            if pathC <= 0:
                break
        learnt[0] = -p
        # learned-clause minimization (recursive, self-subsuming resolution)
        lvset = set()
        for q in learnt[1:]:
            lvset.add(level[q if q > 0 else -q])
        toclear = []
        j = 1
        for i in range(1, len(learnt)):
            q = learnt[i]
            v = q if q > 0 else -q
            if reason[v] is None or not self._lit_redundant(q, lvset, toclear):
                learnt[j] = q
                j += 1
        del learnt[j:]
        for v in toclear:
            seen[v] = 0
        lvset = set()
        for q in learnt:
            lvset.add(level[q if q > 0 else -q])
        return learnt, len(lvset)

    def _lit_redundant(self, p, lvset, toclear):
        seen = self.seen
        level = self.level
        reason = self.reason
        stamp = self.stamp
        stack = [p]
        top = len(toclear)
        while stack:
            q = stack.pop()
            c = reason[q if q > 0 else -q]
            if c is None:
                while len(toclear) > top:
                    seen[toclear.pop()] = 0
                return False
            for r in c:
                if r == q:
                    continue
                vr = r if r > 0 else -r
                if level[vr] > 0 and seen[vr] != stamp:
                    if reason[vr] is not None and level[vr] in lvset:
                        seen[vr] = stamp
                        toclear.append(vr)
                        stack.append(r)
                    else:
                        while len(toclear) > top:
                            seen[toclear.pop()] = 0
                        return False
        return True

    def _bump_clause(self, cl, inc):
        if cl is None:
            return
        cid = id(cl)
        self.cla_act[cid] = self.cla_act.get(cid, 0.0) + inc

    def backtrack_level(self, learnt):
        if len(learnt) == 1:
            return 0
        bt = 0
        level = self.level
        for q in learnt[1:]:
            v = q if q > 0 else -q
            if level[v] > bt:
                bt = level[v]
        return bt

    def record_learnt(self, learnt, lbd):
        if len(learnt) == 1:
            self.enqueue(learnt[0], None)
            self.units.append(learnt[0])
            return
        self.learnts.append(learnt)
        self._add_watched(learnt)
        cid = id(learnt)
        self.cla_act[cid] = self.cla_inc
        self.cla_lbd[cid] = lbd
        self.enqueue(learnt[0], learnt)

    def init_heap(self):
        h = [(-self.activity[v], v) for v in range(1, self.n + 1)]
        heapq.heapify(h)
        self.heap = h

    def rebuild_heap(self):
        h = []
        for v in range(1, self.n + 1):
            if self.value[v] == 0:
                h.append((-self.activity[v], v))
        heapq.heapify(h)
        self.heap = h

    def pick_branch(self):
        value = self.value
        activity = self.activity
        phase = self.phase
        heap = self.heap
        rng = self.rng
        if self.random_freq > 0.0 and rng.random() < self.random_freq:
            while True:
                v = rng.randrange(1, self.n + 1)
                if value[v] == 0:
                    return v if rng.random() < 0.5 else -v
        while heap:
            neg, v = heapq.heappop(heap)
            if value[v] == 0 and (-neg) == activity[v]:
                return v if phase[v] == 0 else -v
        for v in range(1, self.n + 1):
            if value[v] == 0:
                return v if phase[v] == 0 else -v
        return 0

    @staticmethod
    def luby(i):
        k = 1
        while (1 << k) - 1 < i:
            k += 1
        if (1 << k) - 1 == i:
            return 1 << (k - 1)
        return Solver.luby(i - ((1 << (k - 1)) - 1))

    def maybe_restart(self):
        limit = self.restart_base * self.luby(self.restart_count + 1)
        if self.nconflicts - self.last_restart_conf >= limit:
            self.cancel_until(0)
            self.nrestarts += 1
            self.restart_count += 1
            self.last_restart_conf = self.nconflicts
            if self.rand_phase_on_restart > 0.0 and self.rng.random() < self.rand_phase_on_restart:
                phase = self.phase
                gb = self.rng.getrandbits
                for v in range(1, self.n + 1):
                    phase[v] = gb(1)
            if len(self.heap) > 4 * self.n + 1000:
                self.rebuild_heap()

    def maybe_reduce(self):
        if len(self.learnts) > self.max_learnts:
            self.reduce_db()

    def reduce_db(self):
        locked = set()
        reason = self.reason
        for v in range(1, self.n + 1):
            r = reason[v]
            if r is not None:
                locked.add(id(r))
        keep = []
        entries = []
        for cl in self.learnts:
            cid = id(cl)
            if cid in locked:
                keep.append(cl)
            else:
                entries.append((self.cla_lbd.get(cid, 0), -self.cla_act.get(cid, 0.0), cl))
        entries.sort()
        nremove = len(entries) // 2
        keep.extend(e[2] for e in entries[: len(entries) - nremove])
        self.learnts = keep
        for e in entries[len(entries) - nremove:]:
            cl = e[2]
            w0 = self.watches[self.lit2idx(cl[0])]
            w1 = self.watches[self.lit2idx(cl[1])]
            try:
                w0.remove(cl)
            except ValueError:
                pass
            try:
                w1.remove(cl)
            except ValueError:
                pass
            cid = id(cl)
            self.cla_act.pop(cid, None)
            self.cla_lbd.pop(cid, None)
        self.rebuild_heap()

    def decay_var(self):
        self.var_inc /= self.var_decay
        self.cla_inc /= self.cla_decay

    def solve(self):
        if self.unsat:
            return False
        self.init_heap()
        while True:
            confl = self.propagate()
            if confl is not None:
                self.nconflicts += 1
                if self.dlevel == 0:
                    return False
                learnt, lbd = self.analyze(confl)
                blevel = self.backtrack_level(learnt)
                self.cancel_until(blevel)
                self.record_learnt(learnt, lbd)
                self.decay_var()
            else:
                self.maybe_restart()
                self.maybe_reduce()
                lit = self.pick_branch()
                if lit == 0:
                    return True
                self.decide(lit)


def parse_dimacs(path):
    nvars = 0
    clauses = []
    cur = []
    with open(path) as f:
        for line in f:
            line = line.split('%', 1)[0].strip()
            if not line:
                continue
            if line[0] == 'c':
                continue
            if line[0] == 'p':
                parts = line.split()
                nvars = int(parts[2])
                continue
            for tok in line.split():
                lit = int(tok)
                if lit == 0:
                    if cur:
                        clauses.append(cur)
                        cur = []
                else:
                    cur.append(lit)
    if cur:
        clauses.append(cur)
    return nvars, clauses


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("Usage: python3 solver.py instance.cnf\n")
        return 1
    nvars, clauses = parse_dimacs(argv[1])
    s = Solver(nvars)
    for cl in clauses:
        s.add_clause(cl)
    sat = s.solve()
    if sat:
        out = ["SAT"]
        for v in range(1, nvars + 1):
            out.append(str(v if s.value[v] == 1 else -v))
        sys.stdout.write(" ".join(out) + "\n")
    else:
        sys.stdout.write("UNSAT\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
