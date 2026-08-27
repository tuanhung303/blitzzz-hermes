#!/usr/bin/env python3
import sys
import heapq

class Clause:
    __slots__ = ('lits', 'lbd', 'learnt', 'deleted')
    def __init__(self, lits, lbd=0, learnt=False):
        self.lits = lits
        self.lbd = lbd
        self.learnt = learnt
        self.deleted = False

class Watcher:
    __slots__ = ('clause', 'blocker')
    def __init__(self, clause, blocker):
        self.clause = clause
        self.blocker = blocker

def luby_seq():
    u, v = 1, 1
    while True:
        yield v
        if (u & -u) == v:
            u += 1
            v = 1
        else:
            v <<= 1

class CDCLSolver:
    def __init__(self, num_vars, clauses):
        self.num_vars = num_vars
        self.num_lits = 2 * (num_vars + 1)
        
        # 0: unassigned, 1: True, -1: False
        self.assign = [0] * self.num_lits
        self.level = [-1] * (num_vars + 1)
        self.reason = [None] * (num_vars + 1)
        self.trail = []
        self.trail_lim = []
        self.qhead = 0
        
        self.watches = [[] for _ in range(self.num_lits)]
        self.clauses = []
        self.learnts = []
        
        # VSIDS
        self.activity = [0.0] * (num_vars + 1)
        self.var_inc = 1.0
        self.var_decay = 0.95
        self.saved_phase = [1] * (num_vars + 1)
        
        self.seen = [0] * (num_vars + 1)
        self.seen_token = 0
        self.lbd_seen = [0] * (num_vars + 2)
        self.lbd_token = 0
        
        self.order_heap = []
        self.ok = True
        
        # Initial clause processing
        init_counts = [0] * (num_vars + 1)
        for raw_cl in clauses:
            seen_lits = set()
            tautology = False
            norm_cl = []
            for d in raw_cl:
                if d == 0:
                    continue
                lit = (abs(d) << 1) | (1 if d < 0 else 0)
                if (lit ^ 1) in seen_lits:
                    tautology = True
                    break
                if lit not in seen_lits:
                    seen_lits.add(lit)
                    norm_cl.append(lit)
                    init_counts[abs(d)] += 1
            
            if tautology:
                continue
            if len(norm_cl) == 0:
                self.ok = False
                return
            if len(norm_cl) == 1:
                lit = norm_cl[0]
                if self.assign[lit] == -1:
                    self.ok = False
                    return
                elif self.assign[lit] == 0:
                    self.enqueue(lit, None)
            else:
                cl_obj = Clause(norm_cl, lbd=len(norm_cl), learnt=False)
                self.watches[norm_cl[0]].append(Watcher(cl_obj, norm_cl[1]))
                self.watches[norm_cl[1]].append(Watcher(cl_obj, norm_cl[0]))
                self.clauses.append(cl_obj)
        
        for v in range(1, num_vars + 1):
            self.activity[v] = float(init_counts[v])
            self.order_heap.append((-self.activity[v], v))
        heapq.heapify(self.order_heap)

    def enqueue(self, lit, reason_clause=None):
        var = lit >> 1
        self.assign[lit] = 1
        self.assign[lit ^ 1] = -1
        self.level[var] = len(self.trail_lim)
        self.reason[var] = reason_clause
        self.trail.append(lit)
        self.saved_phase[var] = 1 if (lit & 1) == 0 else -1

    def bump_var_activity(self, var):
        self.activity[var] += self.var_inc
        if self.activity[var] > 1e100:
            for v in range(1, self.num_vars + 1):
                self.activity[v] *= 1e-100
            self.var_inc *= 1e-100

    def decay_var_activity(self):
        self.var_inc *= (1.0 / self.var_decay)

    def pick_branch_var(self):
        if len(self.order_heap) > 4 * self.num_vars:
            self.order_heap = [(-self.activity[v], v) for v in range(1, self.num_vars + 1) if self.assign[2 * v] == 0]
            heapq.heapify(self.order_heap)
            
        while self.order_heap:
            _, var = heapq.heappop(self.order_heap)
            if self.assign[2 * var] == 0:
                return var
        return 0

    def propagate(self):
        assign = self.assign
        watches = self.watches
        trail = self.trail
        level = self.level
        reason = self.reason
        saved_phase = self.saved_phase
        curr_level = len(self.trail_lim)
        
        while self.qhead < len(trail):
            p = trail[self.qhead]
            self.qhead += 1
            false_lit = p ^ 1
            old_watches = watches[false_lit]
            if not old_watches:
                continue
            
            new_watches = []
            confl = None
            
            for i, w in enumerate(old_watches):
                cl = w.clause
                if cl.deleted:
                    continue
                
                # Blocker literal check
                if assign[w.blocker] == 1:
                    new_watches.append(w)
                    continue
                
                c_lits = cl.lits
                if c_lits[0] == false_lit:
                    c_lits[0], c_lits[1] = c_lits[1], c_lits[0]
                
                first = c_lits[0]
                if assign[first] == 1:
                    w.blocker = first
                    new_watches.append(w)
                    continue
                
                found = False
                for k in range(2, len(c_lits)):
                    lk = c_lits[k]
                    if assign[lk] != -1:
                        c_lits[1], c_lits[k] = lk, false_lit
                        watches[lk].append(Watcher(cl, first))
                        found = True
                        break
                
                if found:
                    continue
                
                w.blocker = first
                new_watches.append(w)
                if assign[first] == -1:
                    confl = cl
                    new_watches.extend(old_watches[i + 1:])
                    break
                elif assign[first] == 0:
                    var = first >> 1
                    assign[first] = 1
                    assign[first ^ 1] = -1
                    level[var] = curr_level
                    reason[var] = cl
                    trail.append(first)
                    saved_phase[var] = 1 if (first & 1) == 0 else -1
            
            watches[false_lit] = new_watches
            if confl is not None:
                return confl
        return None

    def backtrack_to(self, target_level):
        if len(self.trail_lim) <= target_level:
            return
        target_len = self.trail_lim[target_level]
        heap = self.order_heap
        assign = self.assign
        activity = self.activity
        lev = self.level
        reas = self.reason
        tr = self.trail
        
        while len(tr) > target_len:
            p = tr.pop()
            var = p >> 1
            assign[2 * var] = 0
            assign[2 * var + 1] = 0
            lev[var] = -1
            reas[var] = None
            heapq.heappush(heap, (-activity[var], var))
            
        self.trail_lim = self.trail_lim[:target_level]
        self.qhead = len(tr)

    def analyze(self, confl):
        self.seen_token += 1
        stoken = self.seen_token
        seen = self.seen
        level = self.level
        trail = self.trail
        reason = self.reason
        
        learned = [0]
        counter = 0
        confl_lits = confl.lits
        trail_idx = len(trail) - 1
        curr_level = len(self.trail_lim)
        
        while True:
            for lit in confl_lits:
                var = lit >> 1
                if seen[var] != stoken:
                    seen[var] = stoken
                    self.bump_var_activity(var)
                    if level[var] == curr_level:
                        counter += 1
                    elif level[var] > 0:
                        learned.append(lit)
            
            while True:
                p = trail[trail_idx]
                trail_idx -= 1
                pv = p >> 1
                if seen[pv] == stoken:
                    break
            
            counter -= 1
            if counter == 0:
                learned[0] = p ^ 1
                break
            
            confl_lits = reason[pv].lits

        # Fast local clause minimization
        if len(learned) > 2:
            i = 1
            while i < len(learned):
                lit = learned[i]
                r = reason[lit >> 1]
                if r is not None:
                    redundant = True
                    for l in r.lits:
                        lv = l >> 1
                        if lv == (lit >> 1):
                            continue
                        if seen[lv] != stoken and level[lv] > 0:
                            redundant = False
                            break
                    if redundant:
                        learned.pop(i)
                        continue
                i += 1

        if len(learned) == 1:
            backtrack_level = 0
        else:
            max_i = 1
            max_lvl = level[learned[1] >> 1]
            for i in range(2, len(learned)):
                lvl = level[learned[i] >> 1]
                if lvl > max_lvl:
                    max_lvl = lvl
                    max_i = i
            learned[1], learned[max_i] = learned[max_i], learned[1]
            backtrack_level = max_lvl

        self.lbd_token += 1
        ltoken = self.lbd_token
        lseen = self.lbd_seen
        lbd = 0
        for lit in learned:
            lvl = level[lit >> 1]
            if lvl > 0 and lseen[lvl] != ltoken:
                lseen[lvl] = ltoken
                lbd += 1

        return learned, backtrack_level, lbd

    def reduce_db(self):
        locked_reasons = set()
        for v in range(1, self.num_vars + 1):
            r = self.reason[v]
            if r is not None and r.learnt:
                locked_reasons.add(id(r))
        
        survivors = []
        candidates = []
        for cl in self.learnts:
            if cl.deleted:
                continue
            if id(cl) in locked_reasons or cl.lbd <= 2 or len(cl.lits) <= 2:
                survivors.append(cl)
            else:
                candidates.append(cl)
        
        candidates.sort(key=lambda c: c.lbd, reverse=True)
        num_delete = len(candidates) // 2
        for i in range(num_delete):
            candidates[i].deleted = True
        for i in range(num_delete, len(candidates)):
            survivors.append(candidates[i])
        
        self.learnts = survivors

    def solve(self):
        if not self.ok:
            return "UNSAT", None
        
        if self.propagate() is not None:
            return "UNSAT", None
        
        luby = luby_seq()
        restart_base = 50
        restart_limit = restart_base * next(luby)
        conflicts = 0
        reduce_limit = 2000
        
        while True:
            confl = self.propagate()
            if confl is not None:
                conflicts += 1
                if len(self.trail_lim) == 0:
                    return "UNSAT", None
                
                learned, backtrack_lvl, lbd = self.analyze(confl)
                self.backtrack_to(backtrack_lvl)
                
                cl = Clause(learned, lbd=lbd, learnt=True)
                if len(learned) == 1:
                    self.enqueue(learned[0], None)
                else:
                    self.watches[learned[0]].append(Watcher(cl, learned[1]))
                    self.watches[learned[1]].append(Watcher(cl, learned[0]))
                    self.learnts.append(cl)
                    self.enqueue(learned[0], cl)
                
                self.decay_var_activity()
                
                if conflicts >= restart_limit:
                    self.backtrack_to(0)
                    restart_limit = conflicts + restart_base * next(luby)
                
                if len(self.learnts) >= reduce_limit:
                    self.reduce_db()
                    reduce_limit = int(reduce_limit * 1.15)
            else:
                var = self.pick_branch_var()
                if var == 0:
                    model = []
                    for v in range(1, self.num_vars + 1):
                        if self.assign[2 * v] == 1:
                            model.append(v)
                        elif self.assign[2 * v + 1] == 1:
                            model.append(-v)
                        else:
                            model.append(v)
                    return "SAT", model
                
                self.trail_lim.append(len(self.trail))
                phase = self.saved_phase[var]
                lit = (2 * var) if phase == 1 else (2 * var + 1)
                self.enqueue(lit, None)

def parse_cnf_file(path):
    nvars = 0
    clauses = []
    cur = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.split("%")[0].strip()
            if not line or line.startswith("c"):
                continue
            toks = line.split()
            if not toks:
                continue
            if toks[0] == "p":
                if len(toks) >= 4 and toks[1] == "cnf":
                    nvars = max(nvars, int(toks[2]))
            else:
                for t in toks:
                    lit = int(t)
                    if lit == 0:
                        if cur:
                            clauses.append(cur)
                        cur = []
                    else:
                        nvars = max(nvars, abs(lit))
                        cur.append(lit)
    if cur:
        clauses.append(cur)
    return nvars, clauses

def solve_cnf(path):
    nvars, clauses = parse_cnf_file(path)
    solver = CDCLSolver(nvars, clauses)
    return solver.solve()

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    cnf_path = sys.argv[1]
    verdict, model = solve_cnf(cnf_path)
    if verdict == "SAT":
        print("SAT " + " ".join(str(lit) for lit in model))
    else:
        print("UNSAT")

if __name__ == "__main__":
    main()
