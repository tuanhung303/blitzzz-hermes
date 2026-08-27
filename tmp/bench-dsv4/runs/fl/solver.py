#!/usr/bin/env python3
"""Fast inline CDCL core (single-function search loop)."""

import sys
import heapq


def parse_cnf(path):
    nv = 0
    clauses = []
    cur = []
    pos = {}
    neg = {}
    with open(path) as f:
        for line in f:
            if "%" in line:
                line = line.split("%", 1)[0]
            line = line.strip()
            if not line or line.startswith("c"):
                continue
            toks = line.split()
            if toks[0] == "p":
                nv = int(toks[2])
                continue
            for t in toks:
                x = int(t)
                if x == 0:
                    if cur:
                        clauses.append(cur)
                        cur = []
                else:
                    cur.append(2 * abs(x) + (0 if x > 0 else 1))
                    if x > 0:
                        pos[x] = pos.get(x, 0) + 1
                    else:
                        neg[-x] = neg.get(-x, 0) + 1
    if cur:
        clauses.append(cur)
    return nv, clauses, pos, neg


def cdcl(nv, clauses, pos, neg, luby_unit=200, decay=0.95, dec_flip=64,
         rephase_every=0, max_learnts=3000):
    """Run CDCL search. Returns (True, model_list) or (False, None).
    model_list: per-variable value in {-1, 1}."""
    val = [0] * (nv + 1)
    level = [0] * (nv + 1)
    reason = [-1] * (nv + 1)
    phase = [1] * (nv + 1)
    if pos and neg:
        for v in range(1, nv + 1):
            phase[v] = 1 if pos.get(v, 0) >= neg.get(v, 0) else -1
    activity = [0.0] * (nv + 1)
    trail = []
    trail_lim = []
    watches = [[] for _ in range(2 * nv + 2)]
    clauses_db = []
    learnts = []
    clause_act = []
    seen = [0] * (nv + 1)
    seen_stamp = 0
    seen2 = bytearray(2 * nv + 2)
    heap = []
    var_inc = 1.0
    head = 0
    cur_level = 0
    conflicts = 0
    restarts = 0
    confl_since_restart = 0
    dec_count = 0
    unsat = False

    def luby(x):
        size = 1
        seq = 0
        while size < x + 1:
            seq += 1
            size = 2 * size + 1
        while size - 1 != x:
            size = (size - 1) >> 1
            seq -= 1
            x = x % size
        return 1 << seq

    # attach initial clauses
    for cl in clauses:
        cid = len(clauses_db)
        clauses_db.append(cl)
        clause_act.append(0.0)
        if len(cl) == 1:
            l = cl[0]
            v = l >> 1
            want = 1 - 2 * (l & 1)
            cur = val[v]
            if cur != 0:
                if cur != want:
                    unsat = True
            else:
                val[v] = want
                level[v] = 0
                reason[v] = cid
                trail.append(l)
        else:
            watches[cl[0]].append([cl[1], cid])
            watches[cl[1]].append([cl[0], cid])
    if unsat:
        return False, None

    def minimize(learnt):
        if len(learnt) <= 2:
            return [learnt[-1]] + learnt[:-1]
        uip = learnt[-1]
        for l in learnt:
            seen2[l] = 1
        kept = []
        extra = []
        steps = 0
        for p in learnt[:-1]:
            seen2[p] = 0
            ok = True
            stack = [p]
            while stack:
                steps += 1
                if steps > 20000:
                    ok = False
                    break
                q = stack.pop()
                if seen2[q]:
                    continue
                r = reason[q >> 1]
                if r == -1:
                    ok = False
                    break
                cl = clauses_db[r]
                if cl is None:
                    ok = False
                    break
                seen2[q] = 1
                extra.append(q)
                nq = q ^ 1
                for l in cl:
                    if l != nq:
                        stack.append(l)
            if not ok:
                kept.append(p)
            seen2[p] = 1
        for l in learnt:
            seen2[l] = 0
        for q in extra:
            seen2[q] = 0
        return [uip] + kept

    def reduce_db():
        nonlocal learnts
        keep = []
        cands = []
        for cid in learnts:
            cl = clauses_db[cid]
            if cl is None:
                continue
            locked = False
            for l in cl:
                if reason[l >> 1] == cid:
                    locked = True
                    break
            if len(cl) <= 2 or locked:
                keep.append(cid)
            else:
                cands.append(cid)
        cands.sort(key=lambda c: len(clauses_db[c]))
        doomed = set(cands[: len(cands) // 2])
        new_learnts = []
        for cid in learnts:
            if cid in doomed:
                cl = clauses_db[cid]
                for wl in (watches[cl[0]], watches[cl[1]]):
                    for i, e in enumerate(wl):
                        if e[1] == cid:
                            wl[i] = wl[-1]
                            wl.pop()
                            break
                clauses_db[cid] = None
            else:
                new_learnts.append(cid)
        learnts = new_learnts

    # --- main loop (everything inline for speed) ---
    # initial propagation
    while head < len(trail):
        p = trail[head]
        head += 1
        flit = p ^ 1
        wl = watches[flit]
        i = 0
        nwl = len(wl)
        while i < nwl:
            entry = wl[i]
            cid = entry[1]
            cl = clauses_db[cid]
            if cl is None:
                nwl -= 1
                wl[i] = wl[nwl]
                wl.pop()
                continue
            blocker = entry[0]
            if val[blocker >> 1] == 1 - 2 * (blocker & 1):
                i += 1
                continue
            if cl[0] == flit:
                pos0 = 0
                other = cl[1]
            elif cl[1] == flit:
                pos0 = 1
                other = cl[0]
            else:
                nwl -= 1
                wl[i] = wl[nwl]
                wl.pop()
                continue
            ov = other >> 1
            ovv = val[ov]
            if ovv == 1 - 2 * (other & 1):
                entry[0] = other
                i += 1
                continue
            j = 2
            m = len(cl)
            nl = -1
            while j < m:
                l = cl[j]
                if val[l >> 1] != (l & 1) * 2 - 1:
                    nl = j
                    break
                j += 1
            if nl >= 0:
                cl[pos0] = cl[nl]
                cl[nl] = flit
                nwl -= 1
                wl[i] = wl[nwl]
                wl.pop()
                watches[cl[pos0]].append([other, cid])
                continue
            if ovv == (other & 1) * 2 - 1:
                return False, None          # conflict at level 0
            val[ov] = 1 - 2 * (other & 1)
            level[ov] = cur_level
            reason[ov] = cid
            trail.append(other)
            entry[0] = other
            i += 1

    for v in range(1, nv + 1):
        heapq.heappush(heap, (0.0, v))

    while True:
        # -------- propagate --------
        conflict = -1
        while head < len(trail):
            p = trail[head]
            head += 1
            flit = p ^ 1
            wl = watches[flit]
            i = 0
            nwl = len(wl)
            while i < nwl:
                entry = wl[i]
                cid = entry[1]
                cl = clauses_db[cid]
                if cl is None:
                    nwl -= 1
                    wl[i] = wl[nwl]
                    wl.pop()
                    continue
                blocker = entry[0]
                if val[blocker >> 1] == 1 - 2 * (blocker & 1):
                    i += 1
                    continue
                if cl[0] == flit:
                    pos0 = 0
                    other = cl[1]
                elif cl[1] == flit:
                    pos0 = 1
                    other = cl[0]
                else:
                    nwl -= 1
                    wl[i] = wl[nwl]
                    wl.pop()
                    continue
                ov = other >> 1
                ovv = val[ov]
                if ovv == 1 - 2 * (other & 1):
                    entry[0] = other
                    i += 1
                    continue
                j = 2
                m = len(cl)
                nl = -1
                while j < m:
                    l = cl[j]
                    if val[l >> 1] != (l & 1) * 2 - 1:
                        nl = j
                        break
                    j += 1
                if nl >= 0:
                    cl[pos0] = cl[nl]
                    cl[nl] = flit
                    nwl -= 1
                    wl[i] = wl[nwl]
                    wl.pop()
                    watches[cl[pos0]].append([other, cid])
                    continue
                if ovv == (other & 1) * 2 - 1:
                    conflict = cid
                    break
                val[ov] = 1 - 2 * (other & 1)
                level[ov] = cur_level
                reason[ov] = cid
                trail.append(other)
                entry[0] = other
                i += 1
            if conflict >= 0:
                break

        if conflict >= 0:
            conflicts += 1
            confl_since_restart += 1
            if cur_level == 0:
                return False, None
            # -------- analyze (1-UIP) --------
            seen_stamp += 1
            learnt = []
            btlevel = 0
            counter = 0
            idx = len(trail) - 1
            skip = -1
            cl = clauses_db[conflict]
            for l in cl:
                v = l >> 1
                activity[v] += var_inc
                heapq.heappush(heap, (-activity[v], v))
            while True:
                for l in cl:
                    if l == skip:
                        continue
                    v = l >> 1
                    if seen[v] != seen_stamp:
                        seen[v] = seen_stamp
                        lv = level[v]
                        if lv == cur_level:
                            counter += 1
                        elif lv > 0:
                            learnt.append(l)
                            if lv > btlevel:
                                btlevel = lv
                while True:
                    p = trail[idx]
                    idx -= 1
                    v = p >> 1
                    if seen[v] == seen_stamp:
                        break
                seen[v] = 0
                counter -= 1
                if counter == 0:
                    break
                skip = p
                r = reason[v]
                cl = clauses_db[r]
            learnt.append(p ^ 1)
            # minimize
            if len(learnt) > 2:
                learnt = minimize(learnt)
            else:
                learnt = [learnt[-1]] + learnt[:-1]
            for l in learnt:
                v = l >> 1
                activity[v] += var_inc
                heapq.heappush(heap, (-activity[v], v))
            var_inc *= 1.0 / decay
            if var_inc > 1e100:
                for v in range(1, nv + 1):
                    activity[v] *= 1e-100
                var_inc *= 1e-100
                heap = []
                for v in range(1, nv + 1):
                    if val[v] == 0:
                        heapq.heappush(heap, (-activity[v], v))
            # -------- backtrack --------
            while len(trail_lim) > btlevel:
                lim = trail_lim.pop()
                for i in range(len(trail) - 1, lim - 1, -1):
                    l = trail[i]
                    v = l >> 1
                    val[v] = 0
                    level[v] = 0
                    phase[v] = 1 - 2 * (l & 1)
                    heapq.heappush(heap, (-activity[v], v))
                del trail[lim:]
            cur_level = len(trail_lim)
            if head > len(trail):
                head = len(trail)
            # -------- assert learnt clause --------
            cid = len(clauses_db)
            clauses_db.append(learnt)
            clause_act.append(0.0)
            learnts.append(cid)
            if len(learnt) >= 2:
                watches[learnt[0]].append([learnt[1], cid])
                watches[learnt[1]].append([learnt[0], cid])
            l = learnt[0]
            v = l >> 1
            want = 1 - 2 * (l & 1)
            if val[v] != 0:
                if val[v] != want:
                    return False, None
            else:
                val[v] = want
                level[v] = cur_level
                reason[v] = cid
                trail.append(l)
            # -------- restart --------
            do_restart = confl_since_restart >= luby_unit * luby(restarts + 1)
            if do_restart:
                restarts += 1
                confl_since_restart = 0
                while len(trail_lim) > 0:
                    lim = trail_lim.pop()
                    for i in range(len(trail) - 1, lim - 1, -1):
                        l = trail[i]
                        v = l >> 1
                        val[v] = 0
                        level[v] = 0
                        phase[v] = 1 - 2 * (l & 1)
                        heapq.heappush(heap, (-activity[v], v))
                    del trail[lim:]
                cur_level = 0
                if head > len(trail):
                    head = len(trail)
                if rephase_every and restarts % rephase_every == 0:
                    for v in range(1, nv + 1):
                        phase[v] = -phase[v]
                if len(learnts) > max_learnts:
                    reduce_db()
        else:
            if len(trail) == nv:
                return True, val
            # -------- decide --------
            v = -1
            while heap:
                nact, cand = heapq.heappop(heap)
                if val[cand] == 0 and nact == -activity[cand]:
                    v = cand
                    break
            if v < 0:
                for cand in range(1, nv + 1):
                    if val[cand] == 0:
                        v = cand
                        break
                else:
                    return True, val
            dec_count += 1
            ph = phase[v]
            if dec_flip and dec_count % dec_flip == 0:
                ph = -ph
            cur_level += 1
            trail_lim.append(len(trail))
            val[v] = ph
            level[v] = cur_level
            reason[v] = -1
            trail.append(2 * v if ph == 1 else 2 * v + 1)


def main():
    nv, clauses, pos, neg = parse_cnf(sys.argv[1])
    res, val = cdcl(nv, clauses, pos, neg)
    if res:
        out = " ".join(str(v) if val[v] == 1 else str(-v) for v in range(1, nv + 1))
        sys.stdout.write("SAT " + out + "\n")
    else:
        sys.stdout.write("UNSAT\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
