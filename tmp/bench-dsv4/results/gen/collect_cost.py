#!/usr/bin/env python3
"""Collect per-session token usage from codex rollout jsonl files and price them.
Usage: python3 collect_cost.py <session.jsonl> [more.jsonl...]
       or:  python3 collect_cost.py --since HH:MM   (auto-detect today's sessions)
Pricing source: https://api-docs.deepseek.com/quick_start/pricing/ (2026-08-13)
"""
import json, sys, glob, os, datetime

PRICES = {
    "deepseek-v4-flash": {"in_miss": 0.14, "in_hit": 0.0028, "out": 0.28},
    "deepseek-v4-pro":   {"in_miss": 0.435, "in_hit": 0.003625, "out": 0.87},
}

def totals_from_file(path):
    """Return (last_total_usage dict, model name)."""
    last = None
    model = None
    with open(path) as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("type") == "turn_context" and not model:
                model = (o.get("payload") or {}).get("model") or model
            if o.get("type") == "event_msg":
                p = o.get("payload") or {}
                if p.get("type") == "token_count":
                    tot = (p.get("info") or {}).get("total_token_usage")
                    if tot:                      # last non-null cumulative total
                        last = tot
    return last, model

def price(usage, model):
    if not usage:
        return None
    p = PRICES.get(model)
    if not p:
        return None
    inp = usage.get("input_tokens", 0)
    cached = usage.get("cached_input_tokens", 0)
    cache_write = usage.get("cache_write_input_tokens", 0)
    out = usage.get("output_tokens", 0) + usage.get("reasoning_output_tokens", 0)
    miss = max(0, inp - cached)          # includes cache writes (billed at miss rate)
    cost = miss * p["in_miss"] / 1e6 + cached * p["in_hit"] / 1e6 + out * p["out"] / 1e6
    return {
        "input": inp, "cached": cached, "cache_write": cache_write,
        "output": out, "reasoning": usage.get("reasoning_output_tokens", 0),
        "cost_usd": cost,
        "cost_breakdown": f"in_miss {miss* p['in_miss']/1e6:.4f} + cache_hit {cached*p['in_hit']/1e6:.4f} + out {out*p['out']/1e6:.4f}",
    }

def main():
    args = sys.argv[1:]
    if args and args[0] == "--since":
        day = datetime.date.today().strftime("%Y/%m/%d")
        files = sorted(glob.glob(os.path.expanduser(f"~/.codex/sessions/{day}/rollout-*.jsonl")))
        since = args[1]
        files = [f for f in files if os.path.basename(f).split("T")[1][:5] >= since]
    elif args:
        files = args
    else:
        day = datetime.date.today().strftime("%Y/%m/%d")
        files = sorted(glob.glob(os.path.expanduser(f"~/.codex/sessions/{day}/rollout-*.jsonl")))
    out = {}
    for f in files:
        usage, model = totals_from_file(f)
        r = price(usage, model)
        out[os.path.basename(f)] = {"model": model, "usage": usage, "price": r}
        if r and usage:
            print(f"{os.path.basename(f)[:46]} | {model} | in={usage['input_tokens']} "
                  f"(hit {usage['cached_input_tokens']}, wr {usage.get('cache_write_input_tokens',0)}) "
                  f"out={usage['output_tokens']} rsn={usage.get('reasoning_output_tokens',0)} "
                  f"| ${r['cost_usd']:.4f} [{r['cost_breakdown']}]")
        else:
            print(f"{os.path.basename(f)[:46]} | {model} | no usage data")
    if files:
        json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "cost_raw.json"), "w"), indent=1, default=str)

if __name__ == "__main__":
    main()
