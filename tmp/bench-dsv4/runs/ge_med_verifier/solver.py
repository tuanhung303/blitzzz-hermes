#!/usr/bin/env python3
import sys
import heapq
import time

def parse_cnf(path):
    nvars = 0
    clauses = []
    cur = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.split("%")[0].strip()
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

class Clause:
    __slots__ = ('lits', 'lbd', 'act', 'is_learned', 'deleted')
    def __init__(self, lits, is_learned=False, lbd=0):
        self.lits = lits
        self.lbd = lbd
        self.act = 0.0
        self.is_learned = is_learned
        self.deleted = False

def solve(nvars, raw_clauses):
    num_lits = 2 * (nvars + 1)
    watches = [[] for _ in range(num_lits)]
    
    lit_val = [0] * num_lits
    assign = [0] * (nvars + 1)
    level = [-1] * (nvars + 1)
    reason = [None] * (nvars + 1)
    
    pos_count = [0] * (nvars + 1)
    neg_count = [0] * (nvars + 1)
    
    activity = [0.0] * (nvars + 1)
    var_inc = 1.0
    var_decay = 0.95
    
    clauses = []
    units = []
    learned_clauses = []
    
    for cl in raw_clauses:
        c_lits = [2 * lit if lit > 0 else 2 * (-lit) + 1 for lit in cl]
        c_set = set(c_lits)
        if any((lit ^ 1) in c_set for lit in c_lits):
            continue # tautology
        c_lits = list(c_set)
        if len(c_lits) == 0:
            return "UNSAT", None
        elif len(c_lits) == 1:
            units.append(c_lits[0])
        else:
            cl_obj = Clause(c_lits, is_learned=False)
            clauses.append(cl_obj)
            watches[c_lits[0]].append([cl_obj, c_lits[1]])
            watches[c_lits[1]].append([cl_obj, c_lits[0]])
            for lit in c_lits:
                v = lit >> 1
                activity[v] += 1.0
                if (lit & 1) == 0:
                    pos_count[v] += 1
                else:
                    neg_count[v] += 1

    saved_phase = [-1] * (nvars + 1)

    trail = []
    trail_lim = [0]
    qhead = 0
    decision_level = 0
    
    def enqueue(lit, r, lvl):
        v = lit >> 1
        a = 1 if (lit & 1) == 0 else -1
        assign[v] = a
        lit_val[2 * v] = a
        lit_val[2 * v + 1] = -a
        level[v] = lvl
        reason[v] = r
        saved_phase[v] = a
        trail.append(lit)

    def propagate():
        nonlocal qhead
        while qhead < len(trail):
            p = trail[qhead]
            qhead += 1
            p_false = p ^ 1
            ws = watches[p_false]
            if not ws:
                continue
            
            i = 0
            j = 0
            ws_len = len(ws)
            conflict = None
            
            while i < ws_len:
                entry = ws[i]
                cl_obj = entry[0]
                if cl_obj.deleted:
                    i += 1
                    continue
                
                blocker = entry[1]
                if lit_val[blocker] == 1:
                    ws[j] = entry
                    j += 1
                    i += 1
                    continue
                
                c = cl_obj.lits
                if c[0] != p_false:
                    c[0], c[1] = c[1], c[0]
                
                c1 = c[1]
                if lit_val[c1] == 1:
                    entry[1] = c1
                    ws[j] = entry
                    j += 1
                    i += 1
                    continue
                
                found = False
                for k in range(2, len(c)):
                    ck = c[k]
                    if lit_val[ck] != -1:
                        c[0], c[k] = c[k], c[0]
                        watches[c[0]].append([cl_obj, c1])
                        found = True
                        break
                
                if not found:
                    ws[j] = entry
                    j += 1
                    if lit_val[c1] == -1:
                        conflict = cl_obj
                        i += 1
                        while i < ws_len:
                            if not ws[i][0].deleted:
                                ws[j] = ws[i]
                                j += 1
                            i += 1
                        break
                    elif lit_val[c1] == 0:
                        enqueue(c1, cl_obj, decision_level)
                i += 1
            
            del ws[j:]
            if conflict is not None:
                return conflict
        return None

    # Enqueue initial units
    for u in units:
        v = u >> 1
        if lit_val[u] == -1:
            return "UNSAT", None
        elif lit_val[u] == 0:
            enqueue(u, None, 0)

    if propagate() is not None:
        return "UNSAT", None

    heap = [(-activity[v], v) for v in range(1, nvars + 1)]
    heapq.heapify(heap)

    def pick_branch_lit():
        while heap:
            _, v = heapq.heappop(heap)
            if assign[v] == 0:
                phase = saved_phase[v]
                return 2 * v if phase == 1 else 2 * v + 1
        return None

    def luby(i):
        size = 1
        while size <= i:
            size <<= 1
        size -= 1
        while size > 1:
            half = size >> 1
            if i == size:
                return half + 1
            if i > half:
                i -= half
                size = half
            else:
                size = half
        return 1

    restart_base = 100
    luby_idx = 1
    max_conflicts_restart = restart_base * luby(luby_idx)
    num_conflicts = 0

    seen = [0] * (nvars + 1)
    to_clear = []
    
    reduce_db_limit = 2000
    reduce_db_inc = 500

    def lit_redundant(lit):
        # Check if literal lit in learned clause can be pruned (local minimization)
        v = lit >> 1
        cl = reason[v]
        if cl is None:
            return False
        for l in cl.lits:
            lv = l >> 1
            if lv == v:
                continue
            if seen[lv] == 0 and level[lv] > 0:
                return False
        return True

    while True:
        confl = propagate()
        if confl is not None:
            num_conflicts += 1
            if decision_level == 0:
                return "UNSAT", None
            
            # Conflict analysis (1-UIP)
            learned = [None]
            bt_level = 0
            path_cnt = 0
            curr_cl = confl
            trail_idx = len(trail) - 1
            to_clear.clear()
            levels_in_learned = set()
            
            while True:
                if curr_cl is not None:
                    curr_cl.act += 1.0
                    for lit in curr_cl.lits:
                        v = lit >> 1
                        if not seen[v]:
                            seen[v] = 1
                            to_clear.append(v)
                            activity[v] += var_inc
                            heapq.heappush(heap, (-activity[v], v))
                            lvl = level[v]
                            if lvl == decision_level:
                                path_cnt += 1
                            elif lvl > 0:
                                learned.append(lit)
                                levels_in_learned.add(lvl)
                                if lvl > bt_level:
                                    bt_level = lvl
                
                while trail_idx >= 0:
                    p = trail[trail_idx]
                    trail_idx -= 1
                    v = p >> 1
                    if seen[v]:
                        path_cnt -= 1
                        if path_cnt == 0:
                            learned[0] = p ^ 1
                            levels_in_learned.add(decision_level)
                            break
                        curr_cl = reason[v]
                        break
                if path_cnt == 0:
                    break

            # Local clause minimization
            if len(learned) > 2:
                minimized = [learned[0]]
                for lit in learned[1:]:
                    if not lit_redundant(lit):
                        minimized.append(lit)
                learned = minimized
                # Recompute bt_level
                bt_level = 0
                for lit in learned[1:]:
                    lvl = level[lit >> 1]
                    if lvl > bt_level:
                        bt_level = lvl

            for v in to_clear:
                seen[v] = 0

            # Rescale activities if too large
            var_inc *= (1.0 / var_decay)
            if var_inc > 1e100:
                for v in range(1, nvars + 1):
                    activity[v] *= 1e-100
                var_inc *= 1e-100
                heap = [(-activity[v], v) for v in range(1, nvars + 1) if assign[v] == 0]
                heapq.heapify(heap)

            if len(heap) > 4 * nvars:
                heap = [(-activity[v], v) for v in range(1, nvars + 1) if assign[v] == 0]
                heapq.heapify(heap)

            # Backtrack to bt_level
            while len(trail) > trail_lim[bt_level + 1]:
                p = trail.pop()
                v = p >> 1
                assign[v] = 0
                lit_val[2 * v] = 0
                lit_val[2 * v + 1] = 0
                reason[v] = None
                heapq.heappush(heap, (-activity[v], v))
            del trail_lim[bt_level + 1:]
            decision_level = bt_level
            qhead = len(trail)

            lbd = len(levels_in_learned)
            if len(learned) == 1:
                enqueue(learned[0], None, 0)
            else:
                for i in range(1, len(learned)):
                    if level[learned[i] >> 1] == bt_level:
                        learned[1], learned[i] = learned[i], learned[1]
                        break
                learned_cl = Clause(learned, is_learned=True, lbd=lbd)
                learned_clauses.append(learned_cl)
                watches[learned[0]].append([learned_cl, learned[1]])
                watches[learned[1]].append([learned_cl, learned[0]])
                enqueue(learned[0], learned_cl, bt_level)

            # Clause DB reduction
            if len(learned_clauses) >= reduce_db_limit:
                reduce_db_limit += reduce_db_inc
                locked = set()
                for v in range(1, nvars + 1):
                    if reason[v] is not None:
                        locked.add(id(reason[v]))
                
                candidates = []
                survivors = []
                for cl in learned_clauses:
                    if cl.deleted:
                        continue
                    if id(cl) in locked or cl.lbd <= 2 or len(cl.lits) <= 2:
                        survivors.append(cl)
                    else:
                        candidates.append(cl)
                
                candidates.sort(key=lambda c: (-c.lbd, c.act))
                num_to_delete = len(candidates) // 2
                for i in range(num_to_delete):
                    candidates[i].deleted = True
                for i in range(num_to_delete, len(candidates)):
                    survivors.append(candidates[i])
                learned_clauses = survivors

            # Check restart
            if num_conflicts >= max_conflicts_restart:
                luby_idx += 1
                max_conflicts_restart = num_conflicts + restart_base * luby(luby_idx)
                # Backtrack to level 0
                if decision_level > 0:
                    while len(trail) > trail_lim[1]:
                        p = trail.pop()
                        v = p >> 1
                        assign[v] = 0
                        lit_val[2 * v] = 0
                        lit_val[2 * v + 1] = 0
                        reason[v] = None
                        heapq.heappush(heap, (-activity[v], v))
                    del trail_lim[1:]
                    decision_level = 0
                    qhead = len(trail)

        else:
            dec_lit = pick_branch_lit()
            if dec_lit is None:
                model = []
                for v in range(1, nvars + 1):
                    if assign[v] == 1:
                        model.append(v)
                    else:
                        model.append(-v)
                return "SAT", model
            
            decision_level += 1
            trail_lim.append(len(trail))
            enqueue(dec_lit, None, decision_level)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 solver.py <path/to/instance.cnf>")
        sys.exit(1)
    cnf_file = sys.argv[1]
    nvars, clauses = parse_cnf(cnf_file)
    verdict, model = solve(nvars, clauses)
    if verdict == "SAT":
        print(f"SAT {' '.join(map(str, model))}")
    else:
        print("UNSAT")
