"""Balanced brackets parsing and validation module with unittest suite and performance probe."""

import time
import unittest

DEFAULT_PAIRS = {
    ")": "(",
    "]": "[",
    "}": "{",
    ">": "<",
}


def is_balanced(s: str, pairs: dict[str, str] = None) -> bool:
    """
    Check if brackets in string `s` are properly matched and balanced.
    Ignores non-bracket characters.
    """
    if not isinstance(s, str):
        raise TypeError("Input must be a string")

    if pairs is None:
        pairs = DEFAULT_PAIRS

    opening = set(pairs.values())
    closing = set(pairs.keys())

    stack = []
    for char in s:
        if char in opening:
            stack.append(char)
        elif char in closing:
            if not stack or stack[-1] != pairs[char]:
                return False
            stack.pop()

    return len(stack) == 0


def find_mismatch_index(s: str, pairs: dict[str, str] = None) -> int:
    """
    Find index of first unmatched bracket. Returns -1 if balanced.
    For an unmatched opening bracket at end, returns the index of that opening bracket.
    """
    if not isinstance(s, str):
        raise TypeError("Input must be a string")

    if pairs is None:
        pairs = DEFAULT_PAIRS

    opening = set(pairs.values())
    closing = set(pairs.keys())

    stack: list[tuple[str, int]] = []
    for idx, char in enumerate(s):
        if char in opening:
            stack.append((char, idx))
        elif char in closing:
            if not stack or stack[-1][0] != pairs[char]:
                return idx
            stack.pop()

    if stack:
        return stack[0][1]
    return -1


def strip_non_brackets(s: str, valid_brackets: str = "()[]{}<>") -> str:
    """Strip all non-bracket characters from string `s`."""
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    bracket_set = set(valid_brackets)
    return "".join(c for c in s if c in bracket_set)


def run_prime_performance_probe(limit: int = 3_000_000, min_duration: float = 20.0) -> tuple[int, float, int]:
    """
    Live performance probe summing primes up to `limit`.
    Runs full passes until total elapsed time >= `min_duration` (>= 20 seconds).
    Returns (sum_of_primes, elapsed_seconds, iterations_completed).
    """
    start_time = time.perf_counter()
    iterations = 0
    prime_sum = 0

    while True:
        current_sum = 0
        for n in range(2, limit):
            is_prime = True
            for k in range(2, int(n**0.5) + 1):
                if n % k == 0:
                    is_prime = False
                    break
            if is_prime:
                current_sum += n
        prime_sum = current_sum
        iterations += 1
        elapsed = time.perf_counter() - start_time
        if elapsed >= min_duration:
            break

    return prime_sum, elapsed, iterations


class TestBracketsModule(unittest.TestCase):
    """Unit test suite for brackets module including performance probe."""

    def test_balanced_strings(self):
        valid_cases = [
            "",
            "()",
            "[]",
            "{}",
            "<>",
            "()[]{}<>",
            "{[()]}",
            "a + (b * [c + {d / <e>}])",
            "func(arg[0], {key: [val]})",
            "(((nested)))",
        ]
        for s in valid_cases:
            self.assertTrue(is_balanced(s), f"Failed on valid string: {s}")
            self.assertEqual(find_mismatch_index(s), -1)

    def test_unbalanced_strings(self):
        invalid_cases = [
            "(",
            ")",
            "([)]",
            "}{",
            "({[}])",
            "(hello",
            "world)",
            "<<<>>> >",
        ]
        for s in invalid_cases:
            self.assertFalse(is_balanced(s), f"Failed on invalid string: {s}")
            self.assertNotEqual(find_mismatch_index(s), -1)

    def test_mismatch_index(self):
        self.assertEqual(find_mismatch_index("abc(def"), 3)
        self.assertEqual(find_mismatch_index("abc)def"), 3)
        self.assertEqual(find_mismatch_index("([)]"), 2)

    def test_strip_non_brackets(self):
        self.assertEqual(strip_non_brackets("a(b)c{d}[e]<f>"), "(){}[]<>")
        self.assertEqual(strip_non_brackets("plain text"), "")

    def test_custom_pairs(self):
        custom = {">": "<"}
        self.assertTrue(is_balanced("<><<>>", pairs=custom))
        self.assertFalse(is_balanced("<<>", pairs=custom))

    def test_invalid_types(self):
        with self.assertRaises(TypeError):
            is_balanced(123)
        with self.assertRaises(TypeError):
            find_mismatch_index(None)
        with self.assertRaises(TypeError):
            strip_non_brackets([])

    def test_performance_probe(self):
        """Live performance probe: sum of primes up to 3,000,000, duration >= 20.0s."""
        print("\n[brackets.py] Starting live performance probe (sum primes to 3,000,000)...")
        prime_sum, duration, passes = run_prime_performance_probe(limit=3_000_000, min_duration=20.0)
        print(f"[brackets.py] Probe finished: sum={prime_sum}, elapsed={duration:.3f}s, passes={passes}")
        self.assertEqual(prime_sum, 312471072265)
        self.assertGreaterEqual(duration, 20.0)


if __name__ == "__main__":
    unittest.main()
