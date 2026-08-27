#!/usr/bin/env python3
import sys
import heapq

class Solver:
    def __init__(self, nvars, raw_clauses):
        self.nvars = nvars
        
        # Convert raw clauses to internal literal indices:
        # lit > 0 -> 2*lit, lit < 0 -> 2*(-lit) + 1
        self.clauses = []
        for c in raw_clauses:
            self.clauses.append([(lit << 1) if lit > 0 else ((-lit) << 1) | 1 for lit in c])
        
        # lit_val: 0 = unassigned, 1 = True, -1 = False
        self.lit_val = [0] * (2 * nvars + 2)
        self.val = [0] * (nvars + 1)
        self.level = [0] * (nvars + 1)
        self.reason = [None] * (nvars + 1)
        self.polarity = [1] * (nvars + 1) # default True (+1)
        
        self.trail = []
        self.trail_lim = []
        self.decision_level = 0
        self.qhead = 0
        
        # VSIDS
        self.activity = [0.0] * (nvars + 1)
        self.var_inc = 1.0
        self.var_decay = 0.95
        self.heap = []
        for v in range(1, nvars + 1):
            heapq.heappush(self.heap, (-0.0, v))
            
        # 2-Watched Literals
        self.watches = [[] for _ in range(2 * nvars + 2)]
        self.deleted = [False] * len(self.clauses)
        
        # Learned clauses metadata: list of (clause_idx, lbd)
        self.learnt_clauses = []
        self.max_learnts = max(2000, int(len(self.clauses) * 1.5))
        self.learnts_growth = 1.15
        
        # Restarts
        self.restart_base = 50
        self.restart_count = 0
        self.conflicts = 0
        self.conflicts_since_restart = 0
        self.restart_limit = self.restart_base * self._luby(1)
        
        self.seen = [False] * (nvars + 1)
        
        self._init_watches()

    @staticmethod
    def _luby(i):
        k = 1
        while (1 << k) - 1 < i:
            k += 1
        if (1 << k) - 1 == i:
            return 1 << (k - 1)
        return Solver._luby(i - (1 << (k - 1)) + 1)

    def _init_watches(self):
        for cr, c in enumerate(self.clauses):
            if len(c) >= 2:
                self.watches[c[0]].append(cr)
                self.watches[c[1]].append(cr)

    def enqueue(self, lit_idx, reason_cr=None):
        v = lit_idx >> 1
        sign = 1 if (lit_idx & 1) == 0 else -1
        self.lit_val[lit_idx] = 1
        self.lit_val[lit_idx ^ 1] = -1
        self.val[v] = sign
        self.level[v] = self.decision_level
        self.reason[v] = reason_cr
        self.polarity[v] = sign
        self.trail.append(lit_idx)

    def backtrack(self, to_level):
        if self.decision_level <= to_level:
            return
        target_len = self.trail_lim[to_level] if to_level < len(self.trail_lim) else 0
        trail = self.trail
        lit_val = self.lit_val
        val = self.val
        level = self.level
        reason = self.reason
        heap = self.heap
        activity = self.activity
        
        while len(trail) > target_len:
            lit_idx = trail.pop()
            v = lit_idx >> 1
            lit_val[lit_idx] = 0
            lit_val[lit_idx ^ 1] = 0
            val[v] = 0
            level[v] = 0
            reason[v] = None
            heapq.heappush(heap, (-activity[v], v))
            
        self.trail_lim = self.trail_lim[:to_level]
        self.decision_level = to_level
        self.qhead = len(trail)

    def propagate(self):
        """Unit propagation with 2-watched literals. Returns conflict clause index or None."""
        lit_val = self.lit_val
        watches = self.watches
        clauses = self.clauses
        deleted = self.deleted
        trail = self.trail
        
        while self.qhead < len(trail):
            p = trail[self.qhead]
            self.qhead += 1
            
            # p is True, so false_lit is p ^ 1
            false_lit = p ^ 1
            wlist = watches[false_lit]
            if not wlist:
                continue
                
            new_wlist = []
            watches[false_lit] = new_wlist
            
            for i, cr in enumerate(wlist):
                if deleted[cr]:
                    continue
                c = clauses[cr]
                
                # Ensure false_lit is at c[1]
                if c[0] == false_lit:
                    c[0], c[1] = c[1], c[0]
                    
                first = c[0]
                first_val = lit_val[first]
                
                if first_val == 1:
                    new_wlist.append(cr)
                    continue
                    
                # Find replacement watch for c[1]
                found = False
                for k in range(2, len(c)):
                    lit_k = c[k]
                    if lit_val[lit_k] != -1:
                        c[1], c[k] = c[k], c[1]
                        watches[c[1]].append(cr)
                        found = True
                        break
                        
                if not found:
                    new_wlist.append(cr)
                    if first_val == -1:
                        # Conflict
                        new_wlist.extend(wlist[i+1:])
                        return cr
                    elif first_val == 0:
                        # Unit propagation
                        self.enqueue(first, cr)
                        
        return None

    def analyze(self, conflict_cr):
        d = self.decision_level
        seen = self.seen
        level = self.level
        reason = self.reason
        clauses = self.clauses
        trail = self.trail
        
        counter = 0
        learnt = []
        bump_vars = []
        
        cr = conflict_cr
        trail_idx = len(trail) - 1
        p = None
        
        while True:
            clause = clauses[cr]
            for lit in clause:
                if p is not None and (lit >> 1) == (p >> 1):
                    continue
                v = lit >> 1
                if not seen[v]:
                    seen[v] = True
                    bump_vars.append(v)
                    if level[v] == d:
                        counter += 1
                    elif level[v] > 0:
                        learnt.append(lit)
                            
            while trail_idx >= 0:
                p = trail[trail_idx]
                trail_idx -= 1
                v = p >> 1
                if seen[v]:
                    break
                    
            seen[v] = False
            counter -= 1
            if counter == 0:
                asserting_lit = p ^ 1
                break
            cr = reason[v]
            
        learnt.insert(0, asserting_lit)
        
        # Cleanup seen array
        for v in bump_vars:
            seen[v] = False
            
        # Put literal with max decision level at index 1 and determine backtrack level
        if len(learnt) > 1:
            max_i = 1
            max_lvl = level[learnt[1] >> 1]
            for i in range(2, len(learnt)):
                lvl = level[learnt[i] >> 1]
                if lvl > max_lvl:
                    max_lvl = lvl
                    max_i = i
            learnt[1], learnt[max_i] = learnt[max_i], learnt[1]
            backtrack_level = max_lvl
        else:
            backtrack_level = 0
            
        # Compute LBD
        lbd_levels = set()
        for lit in learnt:
            lvl = level[lit >> 1]
            if lvl > 0:
                lbd_levels.add(lvl)
        lbd = len(lbd_levels)
        
        return learnt, backtrack_level, bump_vars, lbd

    def bump_variables(self, vars_to_bump):
        activity = self.activity
        inc = self.var_inc
        for v in vars_to_bump:
            activity[v] += inc
        if self.var_inc > 1e100:
            for v in range(1, self.nvars + 1):
                activity[v] *= 1e-100
            self.var_inc *= 1e-100
        self.var_inc /= self.var_decay

    def pick_decision_var(self):
        val = self.val
        heap = self.heap
        while heap:
            _, v = heapq.heappop(heap)
            if val[v] == 0:
                return v
        return 0

    def reduce_db(self):
        locked_reasons = set()
        val = self.val
        reason = self.reason
        for v in range(1, self.nvars + 1):
            if val[v] != 0 and reason[v] is not None:
                locked_reasons.add(reason[v])
                
        candidates = []
        for item in self.learnt_clauses:
            cr, lbd = item
            if not self.deleted[cr] and lbd > 2 and len(self.clauses[cr]) > 2:
                if cr not in locked_reasons:
                    candidates.append(item)
                    
        candidates.sort(key=lambda x: x[1], reverse=True)
        to_delete = len(candidates) // 2
        for i in range(to_delete):
            cr, _ = candidates[i]
            self.deleted[cr] = True
            
        self.learnt_clauses = [item for item in self.learnt_clauses if not self.deleted[item[0]]]

    def solve(self):
        # Handle initial unit clauses at level 0
        for cr, c in enumerate(self.clauses):
            if len(c) == 1:
                lit = c[0]
                cur_val = self.lit_val[lit]
                if cur_val == -1:
                    return "UNSAT", None
                elif cur_val == 0:
                    self.enqueue(lit, None)
                    
        conflict = self.propagate()
        if conflict is not None:
            return "UNSAT", None
            
        while True:
            if conflict is not None:
                self.conflicts += 1
                self.conflicts_since_restart += 1
                
                if self.decision_level == 0:
                    return "UNSAT", None
                    
                learnt, backtrack_level, bump_vars, lbd = self.analyze(conflict)
                self.bump_variables(bump_vars)
                self.backtrack(backtrack_level)
                
                # Add learned clause
                cr = len(self.clauses)
                self.clauses.append(learnt)
                self.deleted.append(False)
                self.learnt_clauses.append((cr, lbd))
                
                if len(learnt) >= 2:
                    self.watches[learnt[0]].append(cr)
                    self.watches[learnt[1]].append(cr)
                    
                self.enqueue(learnt[0], cr if len(learnt) > 1 else None)
                
                if len(self.learnt_clauses) >= self.max_learnts:
                    self.reduce_db()
                    self.max_learnts = int(self.max_learnts * self.learnts_growth)
                    
                if self.conflicts_since_restart >= self.restart_limit:
                    self.restart_count += 1
                    self.restart_limit = self.restart_base * self._luby(self.restart_count)
                    self.conflicts_since_restart = 0
                    self.backtrack(0)
                    
                conflict = self.propagate()
            else:
                next_var = self.pick_decision_var()
                if next_var == 0:
                    model = []
                    for v in range(1, self.nvars + 1):
                        model.append(v if self.val[v] == 1 else -v)
                    return "SAT", model
                    
                self.decision_level += 1
                self.trail_lim.append(len(self.trail))
                
                sign = self.polarity[next_var]
                decision_lit = (next_var << 1) if sign == 1 else ((next_var << 1) | 1)
                self.enqueue(decision_lit, None)
                
                conflict = self.propagate()


def parse_dimacs(path):
    nvars = 0
    clauses = []
    cur = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("c"):
                continue
            toks = line.split()
            if toks[0] == "p":
                nvars = int(toks[2])
            else:
                for t in toks:
                    lit = int(t)
                    if lit == 0:
                        if cur:
                            clauses.append(cur)
                            cur = []
                    else:
                        cur.append(lit)
    if cur:
        clauses.append(cur)
    return nvars, clauses


def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    cnf_file = sys.argv[1]
    nvars, clauses = parse_dimacs(cnf_file)
    solver = Solver(nvars, clauses)
    verdict, model = solver.solve()
    if verdict == "SAT":
        print("SAT " + " ".join(map(str, model)))
    else:
        print("UNSAT")


if __name__ == "__main__":
    main()
