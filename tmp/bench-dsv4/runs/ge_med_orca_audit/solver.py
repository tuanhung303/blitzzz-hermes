#!/usr/bin/env python3
import sys
import heapq
import time

def parse_cnf(path):
    nvars = 0
    clauses = []
    cur = []
    with open(path, "r") as f:
        for line in f:
            line = line.split("%")[0].strip()
            if not line or line.startswith("c"):
                continue
            toks = line.split()
            if toks[0] == "p":
                assert toks[1] == "cnf"
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

def luby(i):
    k = 1
    while True:
        p = 1 << k
        if i == p - 1:
            return 1 << (k - 1)
        if (p >> 1) <= i < p - 1:
            return luby(i - (p >> 1) + 1)
        k += 1

class CDCLSolver:
    def __init__(self, num_vars, clauses):
        self.num_vars = num_vars
        self.raw_clauses = clauses
        
        num_lits = 2 * (num_vars + 1)
        self.value = [0] * num_lits
        self.level = [-1] * (num_vars + 1)
        self.reason = [None] * (num_vars + 1)
        self.seen = [False] * (num_vars + 1)
        self.saved_phase = [0] * (num_vars + 1)
        
        self.trail = []
        self.trail_lim = []
        self.qhead = 0
        self.decision_level = 0
        
        self.watches = [[] for _ in range(num_lits)]
        self.clauses = []
        self.learned_clauses = []
        
        # VSIDS
        self.activity = [0.0] * (num_vars + 1)
        self.var_inc = 1.0
        self.var_decay = 0.95
        self.in_heap = [True] * (num_vars + 1)
        self.order_heap = []
        
        # Restarts & Clause DB
        self.conflicts = 0
        self.restart_inc = 1
        self.restart_base = 100
        self.next_restart = self.restart_base * luby(self.restart_inc)
        self.max_learned = 2000
        self.learned_decay = 300
        
        self.init_clauses(clauses)
        
    def to_lit(self, dimacs_lit):
        v = abs(dimacs_lit)
        return (v << 1) | (1 if dimacs_lit < 0 else 0)
        
    def init_clauses(self, raw_clauses):
        for cl in raw_clauses:
            for l in cl:
                v = abs(l)
                self.activity[v] += 1.0
                
        for v in range(1, self.num_vars + 1):
            self.order_heap.append((-self.activity[v], v))
        heapq.heapify(self.order_heap)
        
        for cl in raw_clauses:
            norm_cl = [self.to_lit(l) for l in cl]
            if len(norm_cl) == 0:
                pass
            elif len(norm_cl) == 1:
                self.clauses.append(norm_cl)
                lit = norm_cl[0]
                if self.value[lit] == -1:
                    self.decision_level = 0
                    return
                elif self.value[lit] == 0:
                    self.enqueue(lit, None)
            else:
                self.clauses.append(norm_cl)
                self.watches[norm_cl[0]].append([norm_cl, norm_cl[1]])
                self.watches[norm_cl[1]].append([norm_cl, norm_cl[0]])

    def enqueue(self, lit, reason=None):
        v = lit >> 1
        self.value[lit] = 1
        self.value[lit ^ 1] = -1
        self.level[v] = self.decision_level
        self.reason[v] = reason
        self.saved_phase[v] = lit & 1
        self.trail.append(lit)
        
    def var_bump_activity(self, v):
        self.activity[v] += self.var_inc
        if self.activity[v] > 1e100:
            for i in range(1, self.num_vars + 1):
                self.activity[i] *= 1e-100
            self.var_inc *= 1e-100
        heapq.heappush(self.order_heap, (-self.activity[v], v))
        self.in_heap[v] = True
        
    def var_decay_activity(self):
        self.var_inc *= (1.0 / self.var_decay)

    def propagate(self):
        while self.qhead < len(self.trail):
            p = self.trail[self.qhead]
            self.qhead += 1
            false_lit = p ^ 1
            ws = self.watches[false_lit]
            if not ws:
                continue
            
            new_ws = []
            i = 0
            confl = None
            
            while i < len(ws):
                entry = ws[i]
                c = entry[0]
                blocker = entry[1]
                
                if self.value[blocker] == 1:
                    new_ws.append(entry)
                    i += 1
                    continue
                
                if c[0] == false_lit:
                    c[0], c[1] = c[1], c[0]
                
                first = c[0]
                if self.value[first] == 1:
                    entry[1] = first
                    new_ws.append(entry)
                    i += 1
                    continue
                
                found = False
                for k in range(2, len(c)):
                    if self.value[c[k]] != -1:
                        c[1], c[k] = c[k], c[1]
                        self.watches[c[1]].append([c, first])
                        found = True
                        break
                
                if found:
                    i += 1
                    continue
                
                new_ws.append(entry)
                i += 1
                
                if self.value[first] == -1:
                    confl = c
                    new_ws.extend(ws[i:])
                    break
                elif self.value[first] == 0:
                    self.enqueue(first, c)
                    
            self.watches[false_lit] = new_ws
            if confl is not None:
                return confl
                
        return None

    def analyze(self, confl):
        learned = [0]
        seen = self.seen
        counter = 0
        p = None
        c = confl
        trail_idx = len(self.trail) - 1
        pv = None
        
        while True:
            for lit in c:
                v = lit >> 1
                if v != pv and not seen[v] and self.level[v] > 0:
                    self.var_bump_activity(v)
                    seen[v] = True
                    if self.level[v] >= self.decision_level:
                        counter += 1
                    else:
                        learned.append(lit)
                        
            while not seen[self.trail[trail_idx] >> 1]:
                trail_idx -= 1
                
            p = self.trail[trail_idx]
            pv = p >> 1
            seen[pv] = False
            counter -= 1
            trail_idx -= 1
            
            if counter == 0:
                break
                
            c = self.reason[pv]
            
        asserting_lit = p ^ 1
        learned[0] = asserting_lit
        
        if len(learned) == 1:
            bt_level = 0
        else:
            max_i = 1
            max_lvl = self.level[learned[1] >> 1]
            for i in range(2, len(learned)):
                lvl = self.level[learned[i] >> 1]
                if lvl > max_lvl:
                    max_lvl = lvl
                    max_i = i
            learned[1], learned[max_i] = learned[max_i], learned[1]
            bt_level = max_lvl
            
        for lit in learned:
            seen[lit >> 1] = False
            
        return learned, bt_level

    def backtrack(self, bt_level):
        if self.decision_level <= bt_level:
            return
        while len(self.trail_lim) > bt_level:
            target_len = self.trail_lim.pop()
            while len(self.trail) > target_len:
                lit = self.trail.pop()
                v = lit >> 1
                self.value[lit] = 0
                self.value[lit ^ 1] = 0
                self.level[v] = -1
                self.reason[v] = None
                if not self.in_heap[v]:
                    self.in_heap[v] = True
                    heapq.heappush(self.order_heap, (-self.activity[v], v))
        self.decision_level = bt_level
        self.qhead = len(self.trail)

    def pick_branch_var(self):
        while self.order_heap:
            act, v = heapq.heappop(self.order_heap)
            if self.value[v << 1] == 0:
                self.in_heap[v] = False
                return v
        for v in range(1, self.num_vars + 1):
            if self.value[v << 1] == 0:
                return v
        return None

    def reduce_db(self):
        self.learned_clauses.sort(key=lambda c: len(c))
        keep_count = len(self.learned_clauses) // 2
        to_remove = self.learned_clauses[keep_count:]
        self.learned_clauses = self.learned_clauses[:keep_count]
        
        for c in to_remove:
            if len(c) > 2:
                l0, l1 = c[0], c[1]
                self.watches[l0] = [w for w in self.watches[l0] if w[0] is not c]
                self.watches[l1] = [w for w in self.watches[l1] if w[0] is not c]

    def solve(self):
        if self.propagate() is not None:
            return "UNSAT", None
            
        while True:
            confl = self.propagate()
            if confl is not None:
                self.conflicts += 1
                if self.decision_level == 0:
                    return "UNSAT", None
                    
                learned, bt_level = self.analyze(confl)
                self.backtrack(bt_level)
                
                if len(learned) == 1:
                    self.enqueue(learned[0], reason=None)
                else:
                    self.learned_clauses.append(learned)
                    self.watches[learned[0]].append([learned, learned[1]])
                    self.watches[learned[1]].append([learned, learned[0]])
                    self.enqueue(learned[0], reason=learned)
                    
                self.var_decay_activity()
                
                if self.conflicts >= self.next_restart:
                    self.restart_inc += 1
                    self.next_restart = self.conflicts + self.restart_base * luby(self.restart_inc)
                    self.backtrack(0)
                    
                if len(self.learned_clauses) > self.max_learned:
                    self.reduce_db()
                    self.max_learned += self.learned_decay
            else:
                v = self.pick_branch_var()
                if v is None:
                    model = []
                    for var in range(1, self.num_vars + 1):
                        if self.value[var << 1] == 1:
                            model.append(var)
                        else:
                            model.append(-var)
                    return "SAT", model
                    
                self.decision_level += 1
                self.trail_lim.append(len(self.trail))
                phase = self.saved_phase[v]
                dec_lit = (v << 1) | phase
                self.enqueue(dec_lit, reason=None)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 solver.py <instance.cnf>")
        sys.exit(1)
        
    cnf_file = sys.argv[1]
    nvars, clauses = parse_cnf(cnf_file)
    solver = CDCLSolver(nvars, clauses)
    verdict, model = solver.solve()
    
    if verdict == "SAT":
        print(f"SAT {' '.join(map(str, model))}")
    else:
        print("UNSAT")
    sys.exit(0)

if __name__ == "__main__":
    main()
