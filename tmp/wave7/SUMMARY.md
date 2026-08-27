# Benchmark Worker Summary

## Execution Overview
- **Working Directory**: `/Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave7`
- **Target Workload**: 4 independent modules with unittest suites and live performance probe (sum of primes up to 3,000,000 >= 20s).
- **Target Sum of Primes (< 3,000,000)**: `312,471,072,265`

## Per-Module Test & Performance Timings

| Module | Unit Tests | Total Suite Time (s) | Probe Time (s) | Probe Iterations | Prime Sum Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [`fib.py`](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave7/fib.py) | 5 passed | 29.402s | 29.402s | 3 | 312471072265 | OK |
| [`roman.py`](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave7/roman.py) | 5 passed | 29.768s | 29.767s | 3 | 312471072265 | OK |
| [`brackets.py`](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave7/brackets.py) | 5 passed | 22.847s | 22.847s | 2 | 312471072265 | OK |
| [`caesar.py`](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave7/caesar.py) | 5 passed | 23.871s | 23.870s | 3 | 312471072265 | OK |

**Total Execution Time**: 105.888s

## Module Details
1. [`fib.py`](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave7/fib.py): Fibonacci sequence generators, base-case calculations, closed-form test functions, and live probe test.
2. [`roman.py`](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave7/roman.py): Roman numeral encoding/decoding with boundary checking, roundtrip testing, and live probe test.
3. [`brackets.py`](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave7/brackets.py): Bracket balance validator, depth calculator, string cleaner, and live probe test.
4. [`caesar.py`](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave7/caesar.py): Caesar cipher encryption, decryption, candidate brute-force cracker, and live probe test.
