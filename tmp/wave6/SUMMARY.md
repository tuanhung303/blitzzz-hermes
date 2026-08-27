# Benchmark Worker Summary

Benchmark execution summary for four independent Python modules with unittest suites and live performance probes (sum of primes up to 3,000,000, target duration >= 20.0s).

## Module Summary

| Module | Test File / Suite | Tests Run | Result | Total Duration (s) | Probe Elapsed (s) | Prime Sum (up to 3M) | Probe Passes |
|---|---|---|---|---|---|---|---|
| `fib.py` | `TestFibModule` | 6 | PASS | 20.452 | 20.451 | 312,471,072,265 | 2 |
| `roman.py` | `TestRomanModule` | 6 | PASS | 23.924 | 23.914 | 312,471,072,265 | 3 |
| `brackets.py` | `TestBracketsModule` | 7 | PASS | 24.224 | 24.223 | 312,471,072,265 | 3 |
| `caesar.py` | `TestCaesarModule` | 7 | PASS | 27.838 | 27.837 | 312,471,072,265 | 3 |

**Total Suite Execution Time:** 96.438s

## Module Details

### 1. [fib.py](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave6/fib.py)
- **Features:** Iterative Fibonacci (`fib_iterative`), memoized recursive (`fib_memo`), $O(\log n)$ matrix exponentiation (`fib_matrix`), sequence generation (`fib_sequence`).
- **Tests:** Base cases, sequence generator, equivalence between implementations, large Fibonacci ($F(50)$), negative and non-integer input validation, live prime sum probe.
- **Probe Timing:** 20.451s across 2 passes.

### 2. [roman.py](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave6/roman.py)
- **Features:** Integer to Roman numeral (`to_roman`), Roman numeral to integer parser (`from_roman`), regex syntax validator (`validate_roman`).
- **Tests:** Standard subtractive notations, boundary cases (1 to 3999), 1-3999 full roundtrip validation, invalid syntax rejection, live prime sum probe.
- **Probe Timing:** 23.914s across 3 passes.

### 3. [brackets.py](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave6/brackets.py)
- **Features:** Balanced bracket check (`is_balanced`), mismatch index locator (`find_mismatch_index`), bracket stripper (`strip_non_brackets`), configurable bracket pairs.
- **Tests:** Balanced strings, nested expressions with text, unbalanced detection, mismatch index correctness, custom delimiter pairs, type validation, live prime sum probe.
- **Probe Timing:** 24.223s across 3 passes.

### 4. [caesar.py](file:///Users/__blitzzz/Documents/GitHub/blitzzz-hermes/tmp/wave6/caesar.py)
- **Features:** Caesar encryption (`caesar_encrypt`), decryption (`caesar_decrypt`), brute-force cracking (`caesar_crack`).
- **Tests:** Shift transformations, alphabet wrapping, negative & modulo shifts, preservation of whitespace/punctuation/casing, keyword-filtered cracking, type checking, live prime sum probe.
- **Probe Timing:** 27.837s across 3 passes.

