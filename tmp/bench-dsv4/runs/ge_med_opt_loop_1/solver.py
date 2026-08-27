#!/usr/bin/env python3
import sys
import heapq

def parse_cnf(path):
    nvars = 0
    clauses = []
    cur = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.split('%')[0].strip()
            if not line or line.startswith('c'):
                continue
            toks = line.split()
            if toks[0] == 'p':
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

def luby_gen():
    u, v = 1, 1
    while True:
        yield v
        if (u & -u) == v:
            u += 1
            v = 1
        else:
            v <<= 1

class CDCLSolver:
    def __init__(self, nvars, input_clauses):
        self.nvars = nvars
        
        self.clauses = []
        self.clause_deleted = []
        self.clause_lbd = []
        self.is_learned = []
        
        num_lits = 2 * (nvars + 1)
        self.watches = [[] for _ in range(num_lits)]
        
        self.lit_val = [0] * num_lits
        self.assign = [0] * (nvars + 1)
        self.level = [0] * (nvars + 1)
        self.reason = [None] * (nvars + 1)
        self.saved_phase = [-1] * (nvars + 1)
        
        self.trail = []
        self.trail_lim = []
        self.qhead = 0
        self.decision_level = 0
        
        # VSIDS
        self.activity = [0.0] * (nvars + 1)
        self.var_inc = 1.0
        self.var_decay = 0.95
        self.in_heap = [True] * (nvars + 1)
        self.in_heap[0] = False
        
        self.seen = [False] * (nvars + 1)
        
        self.conflicts = 0
        self.restarts = 0
        self.luby = luby_gen()
        self.restart_inc = 100
        self.restart_limit = next(self.luby) * self.restart_inc
        self.learned_clauses = []
        self.max_learned = 2000
        self.learned_inc = 500
        
        self.ok = True
        self._init_clauses(input_clauses)

    def _to_lit(self, dimacs_lit):
        v = abs(dimacs_lit)
        return (2 * v) if dimacs_lit > 0 else (2 * v + 1)

    def _from_lit(self, lit):
        v = lit >> 1
        return v if (lit & 1 == 0) else -v

    def _init_clauses(self, input_clauses):
        for raw_cl in input_clauses:
            cl = [self._to_lit(x) for x in raw_cl]
            cl = list(dict.fromkeys(cl))
            var_signs = {}
            tautology = False
            for l in cl:
                v = l >> 1
                s = l & 1
                if v in var_signs and var_signs[v] != s:
                    tautology = True
                    break
                var_signs[v] = s
            if tautology:
                continue
                
            if len(cl) == 0:
                self.ok = False
                return
            elif len(cl) == 1:
                lit = cl[0]
                var = lit >> 1
                if self.lit_val[lit] == -1:
                    self.ok = False
                    return
                if self.lit_val[lit] == 0:
                    self._assign_lit(lit, 0, None)
            else:
                cid = len(self.clauses)
                self.clauses.append(cl)
                self.clause_deleted.append(False)
                self.clause_lbd.append(len(cl))
                self.is_learned.append(False)
                self.watches[cl[0]].append([cid, cl[1]])
                self.watches[cl[1]].append([cid, cl[0]])

        for cl in self.clauses:
            for l in cl:
                self.activity[l >> 1] += 1.0
        
        self.heap = [(-self.activity[v], v) for v in range(1, self.nvars + 1)]
        heapq.heapify(self.heap)

    def _assign_lit(self, lit, lvl, reason_clause_id):
        var = lit >> 1
        self.lit_val[lit] = 1
        self.lit_val[lit ^ 1] = -1
        self.assign[var] = 1 if (lit & 1 == 0) else -1
        self.saved_phase[var] = self.assign[var]
        self.level[var] = lvl
        self.reason[var] = reason_clause_id
        self.trail.append(lit)

    def _propagate(self):
        lit_val = self.lit_val
        clauses = self.clauses
        watches = self.watches
        clause_deleted = self.clause_deleted
        
        while self.qhead < len(self.trail):
            p = self.trail[self.qhead]
            self.qhead += 1
            false_lit = p ^ 1
            
            ws = watches[false_lit]
            i = 0
            j = 0
            n_ws = len(ws)
            conflict_clause = None
            
            while i < n_ws:
                w = ws[i]
                cid = w[0]
                blocker = w[1]
                i += 1
                
                if clause_deleted[cid]:
                    continue
                
                if lit_val[blocker] == 1:
                    ws[j] = w
                    j += 1
                    continue
                
                cl = clauses[cid]
                if cl[0] == false_lit:
                    cl[0], cl[1] = cl[1], cl[0]
                
                first = cl[0]
                if first != blocker and lit_val[first] == 1:
                    w[1] = first
                    ws[j] = w
                    j += 1
                    continue
                
                found = False
                for k in range(2, len(cl)):
                    if lit_val[cl[k]] != -1:
                        cl[1], cl[k] = cl[k], cl[1]
                        watches[cl[1]].append([cid, first])
                        found = True
                        break
                
                if found:
                    continue
                
                ws[j] = w
                j += 1
                
                if lit_val[first] == -1:
                    conflict_clause = cid
                    while i < n_ws:
                        ws[j] = ws[i]
                        j += 1
                        i += 1
                    del ws[j:]
                    return conflict_clause
                elif lit_val[first] == 0:
                    self._assign_lit(first, self.decision_level, cid)
            
            del ws[j:]
            
        return None

    def _bump_var(self, var):
        self.activity[var] += self.var_inc
        if self.activity[var] > 1e100:
            for v in range(1, self.nvars + 1):
                self.activity[v] *= 1e-100
            self.var_inc *= 1e-100
        if not self.in_heap[var] and self.assign[var] == 0:
            heapq.heappush(self.heap, (-self.activity[var], var))
            self.in_heap[var] = True

    def _decay_var_inc(self):
        self.var_inc *= (1.0 / self.var_decay)

    def _analyze_conflict(self, conflict_cid):
        decision_level = self.decision_level
        trail = self.trail
        level = self.level
        reason = self.reason
        seen = self.seen
        clauses = self.clauses
        
        learned = []
        path_count = 0
        p = None
        trail_idx = len(trail) - 1
        cl = clauses[conflict_cid]
        
        while True:
            for lit in cl:
                var = lit >> 1
                if p is not None and var == (p >> 1):
                    continue
                if not seen[var] and level[var] > 0:
                    seen[var] = True
                    self._bump_var(var)
                    if level[var] >= decision_level:
                        path_count += 1
                    else:
                        learned.append(lit)
            
            while trail_idx >= 0 and not seen[trail[trail_idx] >> 1]:
                trail_idx -= 1
            
            if trail_idx < 0:
                break
                
            p = trail[trail_idx]
            p_var = p >> 1
            seen[p_var] = False
            path_count -= 1
            trail_idx -= 1
            
            if path_count == 0:
                break
                
            reason_cid = reason[p_var]
            if reason_cid is None:
                break
            cl = clauses[reason_cid]
        
        asserting_lit = p ^ 1
        learned.insert(0, asserting_lit)
        
        for lit in learned:
            seen[lit >> 1] = False
            
        if len(learned) <= 1:
            backtrack_level = 0
            lbd = 1
        else:
            max_lvl = 0
            max_idx = 1
            levels = {decision_level}
            for k in range(1, len(learned)):
                lvl = level[learned[k] >> 1]
                levels.add(lvl)
                if lvl > max_lvl:
                    max_lvl = lvl
                    max_idx = k
            learned[1], learned[max_idx] = learned[max_idx], learned[1]
            backtrack_level = max_lvl
            lbd = len(levels)
            
        return learned, backtrack_level, lbd

    def _backtrack(self, to_level):
        if self.decision_level <= to_level:
            return
            
        while len(self.trail_lim) > to_level:
            lim = self.trail_lim.pop()
            while len(self.trail) > lim:
                lit = self.trail.pop()
                var = lit >> 1
                self.lit_val[lit] = 0
                self.lit_val[lit ^ 1] = 0
                self.assign[var] = 0
                self.reason[var] = None
                self.level[var] = 0
                if not self.in_heap[var]:
                    heapq.heappush(self.heap, (-self.activity[var], var))
                    self.in_heap[var] = True
                    
        self.decision_level = to_level
        self.qhead = len(self.trail)

    def _pick_decision_var(self):
        heap = self.heap
        assign = self.assign
        in_heap = self.in_heap
        activity = self.activity
        
        while heap:
            neg_act, var = heapq.heappop(heap)
            if assign[var] == 0:
                if -neg_act < activity[var]:
                    heapq.heappush(heap, (-activity[var], var))
                    continue
                in_heap[var] = False
                return var
            in_heap[var] = False
        return None

    def _reduce_db(self):
        locked_reasons = set()
        for v in range(1, self.nvars + 1):
            if self.reason[v] is not None:
                locked_reasons.add(self.reason[v])
                
        candidates = []
        for cid in self.learned_clauses:
            if self.clause_deleted[cid]:
                continue
            if cid in locked_reasons or self.clause_lbd[cid] <= 2 or len(self.clauses[cid]) <= 2:
                continue
            candidates.append(cid)
            
        candidates.sort(key=lambda cid: self.clause_lbd[cid], reverse=True)
        
        num_to_delete = len(candidates) // 2
        for i in range(num_to_delete):
            cid = candidates[i]
            self.clause_deleted[cid] = True
            
        self.learned_clauses = [cid for cid in self.learned_clauses if not self.clause_deleted[cid]]

    def solve(self):
        if not self.ok:
            return "UNSAT", None
            
        conflict = self._propagate()
        if conflict is not None:
            return "UNSAT", None
            
        while True:
            var = self._pick_decision_var()
            if var is None:
                model = []
                for v in range(1, self.nvars + 1):
                    val = self.assign[v]
                    if val == 1:
                        model.append(v)
                    elif val == -1:
                        model.append(-v)
                    else:
                        model.append(v)
                return "SAT", model
                
            self.decision_level += 1
            self.trail_lim.append(len(self.trail))
            
            phase = self.saved_phase[var]
            decide_lit = (2 * var) if (phase == 1) else (2 * var + 1)
            self._assign_lit(decide_lit, self.decision_level, None)
            
            while True:
                conflict_cid = self._propagate()
                if conflict_cid is None:
                    break
                    
                self.conflicts += 1
                if self.decision_level == 0:
                    return "UNSAT", None
                    
                learned, backtrack_lvl, lbd = self._analyze_conflict(conflict_cid)
                self._decay_var_inc()
                
                self._backtrack(backtrack_lvl)
                
                cid = len(self.clauses)
                self.clauses.append(learned)
                self.clause_deleted.append(False)
                self.clause_lbd.append(lbd)
                self.is_learned.append(True)
                self.learned_clauses.append(cid)
                
                asserting_lit = learned[0]
                if len(learned) == 1:
                    self._assign_lit(asserting_lit, 0, None)
                else:
                    self.watches[learned[0]].append([cid, learned[1]])
                    self.watches[learned[1]].append([cid, learned[0]])
                    self._assign_lit(asserting_lit, self.decision_level, cid)
                
                if self.conflicts >= self.restart_limit:
                    self._backtrack(0)
                    self.restarts += 1
                    self.restart_limit = self.conflicts + next(self.luby) * self.restart_inc
                    
                if len(self.learned_clauses) >= self.max_learned:
                    self._reduce_db()
                    self.max_learned += self.learned_inc

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 solver.py <path/to/instance.cnf>")
        sys.exit(1)
        
    cnf_path = sys.argv[1]
    nvars, clauses = parse_cnf(cnf_path)
    solver = CDCLSolver(nvars, clauses)
    verdict, model = solver.solve()
    if verdict == "SAT":
        print(f"SAT {' '.join(str(x) for x in model)}")
    else:
        print("UNSAT")

if __name__ == "__main__":
    main()
