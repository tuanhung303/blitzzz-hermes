"""Caesar cipher encoding, decoding, and analysis module with unit tests and performance probe."""

import math
import string
import time
import unittest


def caesar_encrypt(text: str, shift: int) -> str:
    """Encrypt plain text using Caesar cipher with given shift."""
    shift = shift % 26
    result = []
    for char in text:
        if 'a' <= char <= 'z':
            result.append(chr((ord(char) - ord('a') + shift) % 26 + ord('a')))
        elif 'A' <= char <= 'Z':
            result.append(chr((ord(char) - ord('A') + shift) % 26 + ord('A')))
        else:
            result.append(char)
    return "".join(result)


def caesar_decrypt(text: str, shift: int) -> str:
    """Decrypt cipher text using Caesar cipher with given shift."""
    return caesar_encrypt(text, -shift)


def caesar_crack_all(text: str) -> dict[int, str]:
    """Return all 26 possible shift decryptions for text."""
    return {shift: caesar_decrypt(text, shift) for shift in range(26)}


def compute_sum_primes(limit: int = 3_000_000) -> int:
    """Calculate sum of primes below limit using trial division."""
    total = 0
    for n in range(2, limit):
        is_p = True
        root = math.isqrt(n)
        for d in range(2, root + 1):
            if n % d == 0:
                is_p = False
                break
        if is_p:
            total += n
    return total


def run_prime_performance_probe(limit: int = 3_000_000, min_seconds: float = 20.0) -> dict:
    """Run performance probe summing primes up to limit until at least min_seconds elapsed."""
    start = time.perf_counter()
    iterations = 0
    prime_sum = 0
    while True:
        prime_sum = compute_sum_primes(limit)
        iterations += 1
        elapsed = time.perf_counter() - start
        if elapsed >= min_seconds:
            break
    return {
        "module": "caesar",
        "prime_sum": prime_sum,
        "limit": limit,
        "iterations": iterations,
        "elapsed_seconds": elapsed,
    }


class TestCaesar(unittest.TestCase):
    def test_encrypt_basic(self):
        self.assertEqual(caesar_encrypt("abc", 3), "def")
        self.assertEqual(caesar_encrypt("XYZ", 3), "ABC")
        self.assertEqual(caesar_encrypt("Hello, World!", 13), "Uryyb, Jbeyq!")

    def test_decrypt_basic(self):
        self.assertEqual(caesar_decrypt("def", 3), "abc")
        self.assertEqual(caesar_decrypt("ABC", 3), "XYZ")
        self.assertEqual(caesar_decrypt("Uryyb, Jbeyq!", 13), "Hello, World!")

    def test_roundtrip(self):
        msg = "The quick brown fox jumps over the lazy dog."
        for s in range(50):
            encrypted = caesar_encrypt(msg, s)
            decrypted = caesar_decrypt(encrypted, s)
            self.assertEqual(decrypted, msg)

    def test_crack_all(self):
        encrypted = caesar_encrypt("Secret Message", 7)
        candidates = caesar_crack_all(encrypted)
        self.assertEqual(len(candidates), 26)
        self.assertEqual(candidates[7], "Secret Message")

    def test_performance_probe(self):
        result = run_prime_performance_probe(limit=3_000_000, min_seconds=20.0)
        self.assertEqual(result["prime_sum"], 312471072265)
        self.assertGreaterEqual(result["elapsed_seconds"], 20.0)
        print(f"\n[PROBE caesar.py] Elapsed: {result['elapsed_seconds']:.3f}s, Iterations: {result['iterations']}, Sum: {result['prime_sum']}")


if __name__ == "__main__":
    unittest.main()
