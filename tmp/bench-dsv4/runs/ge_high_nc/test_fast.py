import time
import heapq

def parse_cnf(path):
    nvars = 0
    clauses = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("c"):
                continue
            if line.startswith("p"):
                parts = line.split()
                nvars = int(parts[2])
                continue
            parts = line.split()
            cur = []
            for p in parts:
                lit = int(p)
                if lit == 0:
                    if cur:
                        clauses.append(cur)
                        cur = []
                else:
                    cur.append(lit)
            if cur:
                clauses.append(cur)
    return nvars, clauses


class FastCDCL:
    def __init__(self, nvars, clauses, var_decay=0.95, restart_unit=100, use_minimization=True):
        self.nvars = nvars
        self.clauses = []
        self.clause_deleted = []
        self.clause_lbd = []
        self.is_learnt = []

        self.watches = [[] for _ in range(2 * (nvars + 1))]
        self.assign = [-1] * (nvars + 1)
        self.lit_val = [-1] * (2 * (nvars + 1))
        self.decision_level = [-1] * (nvars + 1)
        self.reason = [-1] * (nvars + 1)
        self.saved_phase = [False] * (nvars + 1)

        self.trail = []
        self.trail_lim = []
        self.qhead = 0
        self.current_level = 0

        self.activity = [0.0] * (nvars + 1)
        self.var_inc = 1.0
        self.var_decay = var_decay
        self.heap = []
        self.in_heap = [False] * (nvars + 1)

        self.conflicts = 0
        self.decisions = 0
        self.propagations = 0

        self.learnt_clauses = []
        self.max_learnts = max(2000, int(len(clauses) * 0.5))

        self.restart_unit = restart_unit
        self.luby_u = 1
        self.luby_v = 1
        self.next_restart = self._next_luby() * self.restart_unit
        self.use_minimization = use_minimization

        self.seen = [False] * (nvars + 1)
        self.toclear = []

        self.ok = True
        self._init_clauses(clauses)

    def _to_lit(self, l):
        return (l << 1) if l > 0 else ((-l << 1) | 1)

    def _next_luby(self):
        v = self.luby_v
        if (self.luby_u & -self.luby_u) == self.luby_v:
            self.luby_u += 1
            self.luby_v = 1
        else:
            self.luby_v <<= 1
        return v

    def _init_clauses(self, raw_clauses):
        for raw in raw_clauses:
            for l in raw:
                v = abs(l)
                if 1 <= v <= self.nvars:
                    self.activity[v] += 1.0

        for v in range(1, self.nvars + 1):
            heapq.heappush(self.heap, (-self.activity[v], v))
            self.in_heap[v] = True

        for raw in raw_clauses:
            if not self.ok:
                return
            c = [self._to_lit(l) for l in raw]
            seen_lits = set()
            tautology = False
            unique_c = []
            for lit in c:
                if lit ^ 1 in seen_lits:
                    tautology = True
                    break
                if lit not in seen_lits:
                    seen_lits.add(lit)
                    unique_c.append(lit)
            if tautology:
                continue
            if len(unique_c) == 0:
                self.ok = False
                return
            if len(unique_c) == 1:
                lit = unique_c[0]
                if self.lit_val[lit] == 0:
                    self.ok = False
                    return
                if self.lit_val[lit] == -1:
                    self._enqueue(lit, -1)
                continue

            c_idx = len(self.clauses)
            self.clauses.append(unique_c)
            self.clause_deleted.append(False)
            self.clause_lbd.append(len(unique_c))
            self.is_learnt.append(False)

            self.watches[unique_c[0]].append((c_idx, unique_c[1]))
            self.watches[unique_c[1]].append((c_idx, unique_c[0]))

    def _enqueue(self, lit, reason_c_idx):
        v = lit >> 1
        self.lit_val[lit] = 1
        self.lit_val[lit ^ 1] = 0
        self.assign[v] = 1 if (lit & 1) == 0 else 0
        self.decision_level[v] = self.current_level
        self.reason[v] = reason_c_idx
        self.trail.append(lit)

    def _var_bump_activity(self, v):
        self.activity[v] += self.var_inc
        if self.activity[v] > 1e100:
            for i in range(1, self.nvars + 1):
                self.activity[i] *= 1e-100
            self.var_inc *= 1e-100
        # If unassigned and not in heap, push
        if self.assign[v] == -1 and not self.in_heap[v]:
            heapq.heappush(self.heap, (-self.activity[v], v))
            self.in_heap[v] = True

    def _var_decay_activity(self):
        self.var_inc /= self.var_decay

    def _propagate(self):
        val = self.lit_val
        cls = self.clauses
        watches = self.watches
        deleted = self.clause_deleted

        while self.qhead < len(self.trail):
            p = self.trail[self.qhead]
            self.qhead += 1
            self.propagations += 1

            false_lit = p ^ 1
            ws = watches[false_lit]
            if not ws:
                continue

            new_ws = []
            confl = -1
            n_ws = len(ws)
            i = 0

            while i < n_ws:
                c_idx, blocker = ws[i]
                if deleted[c_idx]:
                    i += 1
                    continue

                if val[blocker] == 1:
                    new_ws.append((c_idx, blocker))
                    i += 1
                    continue

                c = cls[c_idx]
                if c[0] == false_lit:
                    c[0], c[1] = c[1], c[0]

                first_lit = c[0]
                if val[first_lit] == 1:
                    new_ws.append((c_idx, first_lit))
                    i += 1
                    continue

                found = False
                for k in range(2, len(c)):
                    lit_k = c[k]
                    if val[lit_k] != 0:
                        c[1], c[k] = lit_k, c[1]
                        watches[lit_k].append((c_idx, first_lit))
                        found = True
                        break

                if found:
                    i += 1
                    continue

                new_ws.append((c_idx, first_lit))
                if val[first_lit] == 0:
                    confl = c_idx
                    i += 1
                    while i < n_ws:
                        if not deleted[ws[i][0]]:
                            new_ws.append(ws[i])
                        i += 1
                    break
                else:
                    self._enqueue(first_lit, c_idx)
                    i += 1

            watches[false_lit] = new_ws
            if confl != -1:
                return confl
        return -1

    def _lit_redundant(self, lit):
        seen = self.seen
        dec_lvl = self.decision_level
        reason = self.reason
        cls = self.clauses
        v = lit >> 1
        r_idx = reason[v]
        if r_idx == -1:
            return False

        stack = [v]
        while stack:
            var = stack.pop()
            r = reason[var]
            if r == -1:
                return False
            c = cls[r]
            for q in c:
                qv = q >> 1
                if qv == var or dec_lvl[qv] == 0:
                    continue
                if not seen[qv]:
                    if reason[qv] != -1:
                        seen[qv] = True
                        self.toclear.append(qv)
                        stack.append(qv)
                    else:
                        return False
        return True

    def _analyze(self, confl):
        seen = self.seen
        counter = 0
        learnt = [0]
        bt_level = 0
        cur_level = self.current_level
        dec_lvl = self.decision_level
        cls = self.clauses
        reasons = self.reason

        c = cls[confl]
        for lit in c:
            v = lit >> 1
            if not seen[v]:
                seen[v] = True
                self._var_bump_activity(v)
                lv = dec_lvl[v]
                if lv == cur_level:
                    counter += 1
                elif lv > 0:
                    learnt.append(lit)
                    if lv > bt_level:
                        bt_level = lv

        trail_idx = len(self.trail) - 1
        while counter > 0:
            p = self.trail[trail_idx]
            trail_idx -= 1
            v = p >> 1
            if seen[v]:
                seen[v] = False
                counter -= 1
                if counter == 0:
                    learnt[0] = p ^ 1
                    break

                r_idx = reasons[v]
                if r_idx != -1:
                    r_c = cls[r_idx]
                    for q in r_c:
                        qv = q >> 1
                        if qv != v and not seen[qv]:
                            seen[qv] = True
                            self._var_bump_activity(qv)
                            qlv = dec_lvl[qv]
                            if qlv == cur_level:
                                counter += 1
                            elif qlv > 0:
                                learnt.append(q)
                                if qlv > bt_level:
                                    bt_level = qlv

        # Clause minimization
        if self.use_minimization and len(learnt) > 2:
            self.toclear = []
            j = 1
            for i in range(1, len(learnt)):
                lit = learnt[i]
                if not self._lit_redundant(lit):
                    learnt[j] = lit
                    j += 1
            del learnt[j:]
            for v in self.toclear:
                seen[v] = False

        for lit in learnt:
            seen[lit >> 1] = False

        # Put literal from bt_level at position 1
        if len(learnt) > 1:
            for k in range(1, len(learnt)):
                if dec_lvl[learnt[k] >> 1] == bt_level:
                    learnt[1], learnt[k] = learnt[k], learnt[1]
                    break

        # Compute LBD
        lbd_seen = set()
        for lit in learnt:
            lbd_seen.add(dec_lvl[lit >> 1])
        lbd = len(lbd_seen)

        return learnt, bt_level, lbd

    def _cancel_until(self, level):
        if self.current_level <= level:
            return
        limit = self.trail_lim[level]
        while len(self.trail) > limit:
            p = self.trail.pop()
            v = p >> 1
            self.saved_phase[v] = (p & 1) == 0
            self.lit_val[p] = -1
            self.lit_val[p ^ 1] = -1
            self.assign[v] = -1
            self.decision_level[v] = -1
            self.reason[v] = -1
            if not self.in_heap[v]:
                heapq.heappush(self.heap, (-self.activity[v], v))
                self.in_heap[v] = True

        self.trail_lim = self.trail_lim[:level]
        self.current_level = level
        self.qhead = limit

    def _reduce_db(self):
        learnts = []
        reason_set = set(self.reason[v] for v in range(1, self.nvars + 1) if self.reason[v] != -1)
        for c_idx in self.learnt_clauses:
            if not self.clause_deleted[c_idx]:
                # Keep LBD <= 2 or length <= 2 or active reasons
                if self.clause_lbd[c_idx] > 2 and len(self.clauses[c_idx]) > 2 and c_idx not in reason_set:
                    learnts.append(c_idx)

        learnts.sort(key=lambda idx: self.clause_lbd[idx], reverse=True)
        num_to_delete = len(learnts) // 2
        for i in range(num_to_delete):
            c_idx = learnts[i]
            self.clause_deleted[c_idx] = True

        self.learnt_clauses = [idx for idx in self.learnt_clauses if not self.clause_deleted[idx]]
        self.max_learnts = int(self.max_learnts * 1.1)

    def _pick_branch_lit(self):
        while self.heap:
            _, v = heapq.heappop(self.heap)
            self.in_heap[v] = False
            if self.assign[v] == -1:
                phase = self.saved_phase[v]
                return (v << 1) if phase else ((v << 1) | 1)
        return None

    def solve(self):
        if not self.ok:
            return "UNSAT", None

        confl = self._propagate()
        if confl != -1:
            return "UNSAT", None

        while True:
            if self.conflicts >= self.next_restart:
                self._cancel_until(0)
                self.next_restart = self.conflicts + self._next_luby() * self.restart_unit

            if len(self.learnt_clauses) >= self.max_learnts:
                self._reduce_db()

            dec_lit = self._pick_branch_lit()
            if dec_lit is None:
                model = []
                for v in range(1, self.nvars + 1):
                    if self.assign[v] == 1:
                        model.append(v)
                    else:
                        model.append(-v)
                return "SAT", model

            self.decisions += 1
            self.current_level += 1
            self.trail_lim.append(len(self.trail))
            self._enqueue(dec_lit, -1)

            while True:
                confl = self._propagate()
                if confl == -1:
                    break

                self.conflicts += 1
                if self.current_level == 0:
                    return "UNSAT", None

                learnt, bt_level, lbd = self._analyze(confl)
                self._cancel_until(bt_level)
                self._var_decay_activity()

                if len(learnt) == 1:
                    self._enqueue(learnt[0], -1)
                else:
                    c_idx = len(self.clauses)
                    self.clauses.append(learnt)
                    self.clause_deleted.append(False)
                    self.clause_lbd.append(lbd)
                    self.is_learnt.append(True)
                    self.learnt_clauses.append(c_idx)

                    self.watches[learnt[0]].append((c_idx, learnt[1]))
                    self.watches[learnt[1]].append((c_idx, learnt[0]))
                    self._enqueue(learnt[0], c_idx)


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        nvars, clauses = parse_cnf(p)
        t0 = time.time()
        s = FastCDCL(nvars, clauses, var_decay=0.85, restart_unit=50, use_minimization=True)
        v, m = s.solve()
        dt = time.time() - t0
        print(f"{p}: {v} in {dt:.3f}s (conflicts={s.conflicts}, decisions={s.decisions}, props={s.propagations})")
