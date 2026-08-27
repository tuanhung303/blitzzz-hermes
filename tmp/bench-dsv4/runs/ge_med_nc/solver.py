#!/usr/bin/env python3
import sys
import heapq

class Clause:
    __slots__ = ("lits", "lbd", "deleted")
    def __init__(self, lits):
        self.lits = lits
        self.lbd = len(lits)
        self.deleted = False

def solve(filename):
    nvars = 0
    raw_clauses = []
    
    with open(filename, "r") as f:
        for line in f:
            line = line.split("%")[0].strip()
            if not line or line.startswith("c"):
                continue
            tokens = line.split()
            if tokens[0] == "p":
                nvars = int(tokens[2])
            else:
                for t in tokens:
                    lit = int(t)
                    if lit == 0:
                        if "cur" in locals() and cur:
                            raw_clauses.append(cur)
                        cur = []
                    else:
                        if "cur" not in locals():
                            cur = []
                        cur.append(lit)
        if "cur" in locals() and cur:
            raw_clauses.append(cur)

    val = [0] * (2 * nvars + 1)
    level = [0] * (nvars + 1)
    reason = [None] * (nvars + 1)
    saved_phase = [-1] * (nvars + 1)
    activity = [0.0] * (nvars + 1)
    var_inc = 1.0
    var_decay = 0.95
    order_heap = []
    
    trail = []
    trail_lim = []
    qhead = 0
    
    watches = [[] for _ in range(2 * nvars + 1)]
    learnt_clauses = []
    
    for cl_lits in raw_clauses:
        s = set(cl_lits)
        tautology = False
        for l in s:
            if -l in s:
                tautology = True
                break
        if tautology:
            continue
        cleaned = list(s)
        if len(cleaned) == 0:
            print("UNSAT")
            return
        
        for lit in cleaned:
            activity[abs(lit)] += 1.0
            
        if len(cleaned) == 1:
            unit_lit = cleaned[0]
            if val[unit_lit + nvars] == -1:
                print("UNSAT")
                return
            if val[unit_lit + nvars] == 0:
                val[unit_lit + nvars] = 1
                val[-unit_lit + nvars] = -1
                level[abs(unit_lit)] = 0
                reason[abs(unit_lit)] = None
                trail.append(unit_lit)
        else:
            cl = Clause(cleaned)
            watches[cl.lits[0] + nvars].append(cl)
            watches[cl.lits[1] + nvars].append(cl)

    for v in range(1, nvars + 1):
        heapq.heappush(order_heap, (-activity[v], v))

    def rescale_activity():
        nonlocal var_inc
        for v in range(1, nvars + 1):
            activity[v] *= 1e-100
        var_inc *= 1e-100
        order_heap.clear()
        for v in range(1, nvars + 1):
            if val[v + nvars] == 0:
                heapq.heappush(order_heap, (-activity[v], v))

    def propagate():
        nonlocal qhead
        while qhead < len(trail):
            p = trail[qhead]
            qhead += 1
            false_lit = -p
            wlist = watches[false_lit + nvars]
            if not wlist:
                continue
            
            new_wlist = []
            conflict = None
            
            for i in range(len(wlist)):
                cl = wlist[i]
                if cl.deleted:
                    continue
                if conflict is not None:
                    new_wlist.append(cl)
                    continue
                
                lits = cl.lits
                if lits[0] == false_lit:
                    lits[0], lits[1] = lits[1], lits[0]
                
                first = lits[0]
                if val[first + nvars] == 1:
                    new_wlist.append(cl)
                    continue
                
                found = False
                for k in range(2, len(lits)):
                    if val[lits[k] + nvars] != -1:
                        lits[1], lits[k] = lits[k], lits[1]
                        watches[lits[1] + nvars].append(cl)
                        found = True
                        break
                
                if found:
                    continue
                
                new_wlist.append(cl)
                if val[first + nvars] == -1:
                    conflict = cl
                elif val[first + nvars] == 0:
                    val[first + nvars] = 1
                    val[-first + nvars] = -1
                    v = abs(first)
                    level[v] = len(trail_lim)
                    reason[v] = cl
                    trail.append(first)
                    
            watches[false_lit + nvars] = new_wlist
            if conflict is not None:
                return conflict
        return None

    def analyze(confl):
        nonlocal var_inc
        dlevel = len(trail_lim)
        if dlevel == 0:
            return None, -1
            
        seen = [False] * (nvars + 1)
        learnt = [0]
        path_count = 0
        backtrack_level = 0
        trail_idx = len(trail) - 1
        
        p = None
        curr_clause = confl.lits
        
        while True:
            for lit in curr_clause:
                v = abs(lit)
                if p is not None and v == abs(p):
                    continue
                if not seen[v]:
                    seen[v] = True
                    activity[v] += var_inc
                    if activity[v] > 1e100:
                        rescale_activity()
                    heapq.heappush(order_heap, (-activity[v], v))
                    
                    if level[v] == dlevel:
                        path_count += 1
                    elif level[v] > 0:
                        learnt.append(lit)
                        if level[v] > backtrack_level:
                            backtrack_level = level[v]
                            
            while True:
                p = trail[trail_idx]
                trail_idx -= 1
                v = abs(p)
                if seen[v]:
                    break
                    
            seen[v] = False
            path_count -= 1
            
            if path_count == 0:
                learnt[0] = -p
                break
                
            curr_clause = reason[v].lits
                
        var_inc /= var_decay
        
        if len(learnt) > 1:
            max_idx = 1
            for k in range(2, len(learnt)):
                if level[abs(learnt[k])] > level[abs(learnt[max_idx])]:
                    max_idx = k
            learnt[1], learnt[max_idx] = learnt[max_idx], learnt[1]
            
        return learnt, backtrack_level

    def backtrack(b_level):
        nonlocal qhead
        target = trail_lim[b_level] if b_level < len(trail_lim) else len(trail)
        while len(trail) > target:
            p = trail.pop()
            v = abs(p)
            saved_phase[v] = 1 if p > 0 else -1
            val[p + nvars] = 0
            val[-p + nvars] = 0
            level[v] = 0
            reason[v] = None
            heapq.heappush(order_heap, (-activity[v], v))
        del trail_lim[b_level:]
        qhead = len(trail)

    def luby(i):
        size = 1
        while size < i + 1:
            size = 2 * size + 1
        while size - 1 != i:
            size = (size - 1) >> 1
            if i >= size:
                i -= size
        return size

    if propagate() is not None:
        print("UNSAT")
        return

    conflicts = 0
    restart_idx = 1
    restart_limit = 100 * luby(restart_idx)
    conflicts_since_restart = 0
    max_learnts = 2000

    def reduce_db():
        nonlocal max_learnts
        learnt_clauses.sort(key=lambda cl: (cl.lbd, len(cl.lits)))
        keep_count = len(learnt_clauses) // 2
        for i in range(keep_count, len(learnt_clauses)):
            cl = learnt_clauses[i]
            if cl.lbd > 2:
                cl.deleted = True
        learnt_clauses[:] = [cl for cl in learnt_clauses if not cl.deleted]
        max_learnts = int(max_learnts * 1.1)

    while True:
        confl = propagate()
        if confl is not None:
            conflicts += 1
            conflicts_since_restart += 1
            
            learnt_lits, b_level = analyze(confl)
            if b_level < 0:
                print("UNSAT")
                return
                
            backtrack(b_level)
            
            levels_seen = {level[abs(lit)] for lit in learnt_lits}
            lbd = len(levels_seen)
            
            if len(learnt_lits) == 1:
                lit = learnt_lits[0]
                val[lit + nvars] = 1
                val[-lit + nvars] = -1
                v = abs(lit)
                level[v] = 0
                reason[v] = None
                trail.append(lit)
            else:
                cl = Clause(learnt_lits)
                cl.lbd = lbd
                learnt_clauses.append(cl)
                watches[cl.lits[0] + nvars].append(cl)
                watches[cl.lits[1] + nvars].append(cl)
                
                asserting_lit = cl.lits[0]
                val[asserting_lit + nvars] = 1
                val[-asserting_lit + nvars] = -1
                v = abs(asserting_lit)
                level[v] = b_level
                reason[v] = cl
                trail.append(asserting_lit)
                
            if len(learnt_clauses) >= max_learnts:
                reduce_db()
                
            if conflicts_since_restart >= restart_limit:
                restart_idx += 1
                restart_limit = 100 * luby(restart_idx)
                conflicts_since_restart = 0
                backtrack(0)
        else:
            dec_var = 0
            while order_heap:
                _, v = heapq.heappop(order_heap)
                if val[v + nvars] == 0:
                    dec_var = v
                    break
            if dec_var == 0:
                for v in range(1, nvars + 1):
                    if val[v + nvars] == 0:
                        dec_var = v
                        break
            if dec_var == 0:
                model = [v if val[v + nvars] > 0 else -v for v in range(1, nvars + 1)]
                print("SAT " + " ".join(str(l) for l in model))
                return
                
            trail_lim.append(len(trail))
            dec_lit = dec_var if saved_phase[dec_var] > 0 else -dec_var
            val[dec_lit + nvars] = 1
            val[-dec_lit + nvars] = -1
            level[dec_var] = len(trail_lim)
            reason[dec_var] = None
            trail.append(dec_lit)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        solve(sys.argv[1])
