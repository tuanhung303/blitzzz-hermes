#!/usr/bin/env python3
"""
CDCL SAT Solver from scratch in Python 3 standard library.
Features:
- Two-watched-literals (2WL) unit propagation
- 1-UIP conflict analysis with non-chronological backjumping
- VSIDS decision heuristic with Luby restarts and phase saving
- Learned clause management (LBD-based DB reduction)
"""

import sys
import heapq

def luby(u):
    k = 1
    while (1 << k) - 1 < u:
        k += 1
    if u == (1 << k) - 1:
        return 1 << (k - 1)
    return luby(u - (1 << (k - 1)) + 1)

def parse_dimacs(path):
    n_vars = 0
    clauses = []
    with open(path, "r") as f:
        for line in f:
            line = line.split("%")[0].strip()
            if not line or line.startswith("c"):
                continue
            if line.startswith("p"):
                parts = line.split()
                if len(parts) >= 3 and parts[1] == "cnf":
                    n_vars = int(parts[2])
                continue
            # Read clauses
            toks = line.split()
            cur = []
            for t in toks:
                lit = int(t)
                if lit == 0:
                    if cur:
                        clauses.append(cur)
                        cur = []
                else:
                    cur.append(lit)
                    if abs(lit) > n_vars:
                        n_vars = abs(lit)
            if cur:
                clauses.append(cur)
    return n_vars, clauses

class CDCLSolver:
    def __init__(self, n_vars, clauses):
        self.n_vars = n_vars
        self.raw_clauses = clauses
        
        # 1-indexed variables and signed literals
        # Array sizes: 2 * n_vars + 1
        # Positive literal v at index v, negative literal -v at index -v
        self.assigns = [0] * (2 * n_vars + 1)
        self.level = [0] * (n_vars + 1)
        self.reason = [None] * (n_vars + 1)
        self.phase = [-1] * (n_vars + 1)
        
        self.trail = []
        self.trail_lim = []
        self.qhead = 0
        
        self.watches = [[] for _ in range(2 * n_vars + 1)]
        self.original_clauses = []
        self.learned_clauses = [] # list of (clause, lbd)
        
        # VSIDS
        self.activity = [0.0] * (n_vars + 1)
        self.var_inc = 1.0
        self.var_decay = 0.95
        self.order_heap = []
        
        # Stats & Limits
        self.conflicts = 0
        self.restart_inc = 100
        self.restart_idx = 1
        self.next_restart = self.restart_inc * luby(self.restart_idx)
        self.max_learned = 2000
        self.learned_inc = 300

    def init_solver(self):
        # Initial variable activities
        for cl in self.raw_clauses:
            for lit in cl:
                self.activity[abs(lit)] += 1.0
        
        self.order_heap = [(-self.activity[v], v) for v in range(1, self.n_vars + 1)]
        heapq.heapify(self.order_heap)
        
        # Add clauses
        for cl in self.raw_clauses:
            if not cl:
                return False
            if len(cl) == 1:
                lit = cl[0]
                v = abs(lit)
                if self.assigns[lit] == -1: # conflict at root
                    return False
                if self.assigns[lit] == 0:
                    self.assigns[lit] = 1
                    self.assigns[-lit] = -1
                    self.level[v] = 0
                    self.reason[v] = None
                    self.phase[v] = 1 if lit > 0 else -1
                    self.trail.append(lit)
            else:
                self.watches[cl[0]].append(cl)
                self.watches[cl[1]].append(cl)
                self.original_clauses.append(cl)
        return True

    def propagate(self):
        while self.qhead < len(self.trail):
            p = self.trail[self.qhead]
            self.qhead += 1
            false_lit = -p
            ws = self.watches[false_lit]
            
            i = 0
            j = 0
            ws_len = len(ws)
            confl = None
            
            while i < ws_len:
                cl = ws[i]
                i += 1
                
                if cl[0] != false_lit:
                    cl[0], cl[1] = cl[1], cl[0]
                
                w1 = cl[1]
                if self.assigns[w1] == 1:
                    ws[j] = cl
                    j += 1
                    continue
                
                # Search for new watch
                found = False
                for k in range(2, len(cl)):
                    if self.assigns[cl[k]] != -1:
                        cl[0], cl[k] = cl[k], cl[0]
                        self.watches[cl[0]].append(cl)
                        found = True
                        break
                
                if found:
                    continue
                
                ws[j] = cl
                j += 1
                
                if self.assigns[w1] == -1:
                    # Conflict
                    confl = cl
                    while i < ws_len:
                        ws[j] = ws[i]
                        j += 1
                        i += 1
                    break
                elif self.assigns[w1] == 0:
                    # Unit propagation
                    v = abs(w1)
                    self.assigns[w1] = 1
                    self.assigns[-w1] = -1
                    self.level[v] = len(self.trail_lim)
                    self.reason[v] = cl
                    self.phase[v] = 1 if w1 > 0 else -1
                    self.trail.append(w1)
            
            del ws[j:]
            if confl is not None:
                return confl
        return None

    def analyze_conflict(self, confl):
        d = len(self.trail_lim)
        seen = [False] * (self.n_vars + 1)
        counter = 0
        learned = [0]
        c = confl
        trail_idx = len(self.trail) - 1
        curr_var = 0
        
        while True:
            if c is not None:
                for lit in c:
                    v = abs(lit)
                    if v != curr_var and not seen[v]:
                        seen[v] = True
                        self.activity[v] += self.var_inc
                        if self.activity[v] > 1e100:
                            self.rescale_activity()
                        if self.level[v] == d:
                            counter += 1
                        elif self.level[v] > 0:
                            learned.append(lit)
            
            while trail_idx >= 0:
                q = self.trail[trail_idx]
                trail_idx -= 1
                v = abs(q)
                if seen[v]:
                    curr_var = v
                    break
            
            seen[curr_var] = False
            counter -= 1
            if counter == 0:
                learned[0] = -q
                break
            c = self.reason[curr_var]
        
        for lit in learned:
            seen[abs(lit)] = False
            
        if len(learned) == 1:
            return learned, 0, 1
            
        # Find literal with highest decision level among learned[1:]
        max_i = 1
        max_lvl = self.level[abs(learned[1])]
        for i in range(2, len(learned)):
            lvl = self.level[abs(learned[i])]
            if lvl > max_lvl:
                max_lvl = lvl
                max_i = i
        learned[1], learned[max_i] = learned[max_i], learned[1]
        
        # Calculate LBD
        levels = set()
        for lit in learned:
            lvl = self.level[abs(lit)]
            if lvl > 0:
                levels.add(lvl)
        lbd = len(levels)
        
        return learned, max_lvl, lbd

    def rescale_activity(self):
        for i in range(1, self.n_vars + 1):
            self.activity[i] *= 1e-100
        self.var_inc *= 1e-100
        self.order_heap = [(-self.activity[v], v) for v in range(1, self.n_vars + 1) if self.assigns[v] == 0]
        heapq.heapify(self.order_heap)

    def backtrack(self, back_lvl):
        while len(self.trail_lim) > back_lvl:
            lim = self.trail_lim.pop()
            while len(self.trail) > lim:
                p = self.trail.pop()
                v = abs(p)
                self.assigns[p] = 0
                self.assigns[-p] = 0
                heapq.heappush(self.order_heap, (-self.activity[v], v))
        self.qhead = len(self.trail)

    def reduce_db(self):
        # Keep glue clauses (LBD <= 2) and best half of rest
        glue = []
        other = []
        for cl, lbd in self.learned_clauses:
            if lbd <= 2:
                glue.append((cl, lbd))
            else:
                other.append((cl, lbd))
        
        other.sort(key=lambda x: (x[1], len(x[0])))
        kept_other = other[:len(other) // 2]
        self.learned_clauses = glue + kept_other
        
        # Rebuild watches
        self.watches = [[] for _ in range(2 * self.n_vars + 1)]
        for cl in self.original_clauses:
            self.watches[cl[0]].append(cl)
            self.watches[cl[1]].append(cl)
        for cl, _ in self.learned_clauses:
            self.watches[cl[0]].append(cl)
            self.watches[cl[1]].append(cl)

    def pick_branch_lit(self):
        while self.order_heap:
            neg_act, v = heapq.heappop(self.order_heap)
            if self.assigns[v] == 0:
                return v if self.phase[v] == 1 else -v
        return 0

    def solve(self):
        if not self.init_solver():
            return "UNSAT", None
        
        confl = self.propagate()
        if confl is not None:
            return "UNSAT", None
        
        while True:
            # Pick branch lit
            p = self.pick_branch_lit()
            if p == 0:
                # All assigned
                model = [v if self.assigns[v] == 1 else -v for v in range(1, self.n_vars + 1)]
                return "SAT", model
            
            self.trail_lim.append(len(self.trail))
            v = abs(p)
            self.assigns[p] = 1
            self.assigns[-p] = -1
            self.level[v] = len(self.trail_lim)
            self.reason[v] = None
            self.phase[v] = 1 if p > 0 else -1
            self.trail.append(p)
            
            while True:
                confl = self.propagate()
                if confl is None:
                    break
                
                self.conflicts += 1
                if len(self.trail_lim) == 0:
                    return "UNSAT", None
                
                learned, back_lvl, lbd = self.analyze_conflict(confl)
                self.var_inc *= (1.0 / self.var_decay)
                
                self.backtrack(back_lvl)
                
                assert_lit = learned[0]
                v_assert = abs(assert_lit)
                
                if len(learned) > 1:
                    self.watches[learned[0]].append(learned)
                    self.watches[learned[1]].append(learned)
                    self.learned_clauses.append((learned, lbd))
                    
                    self.assigns[assert_lit] = 1
                    self.assigns[-assert_lit] = -1
                    self.level[v_assert] = back_lvl
                    self.reason[v_assert] = learned
                    self.phase[v_assert] = 1 if assert_lit > 0 else -1
                    self.trail.append(assert_lit)
                else:
                    self.assigns[assert_lit] = 1
                    self.assigns[-assert_lit] = -1
                    self.level[v_assert] = 0
                    self.reason[v_assert] = None
                    self.phase[v_assert] = 1 if assert_lit > 0 else -1
                    self.trail.append(assert_lit)
                
                # Check DB reduction
                if len(self.learned_clauses) > self.max_learned:
                    self.reduce_db()
                    self.max_learned += self.learned_inc
                
                # Check restart
                if self.conflicts >= self.next_restart:
                    self.restart_idx += 1
                    self.next_restart = self.conflicts + self.restart_inc * luby(self.restart_idx)
                    self.backtrack(0)
                    break

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    cnf_file = sys.argv[1]
    n_vars, clauses = parse_dimacs(cnf_file)
    solver = CDCLSolver(n_vars, clauses)
    status, model = solver.solve()
    if status == "SAT":
        print(f"SAT {' '.join(map(str, model))}")
    else:
        print("UNSAT")

if __name__ == "__main__":
    main()
