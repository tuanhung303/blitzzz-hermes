"""
Caesar and Vigenere cipher module with comprehensive unit tests
and a live performance probe.
"""

import time
import unittest


def caesar_encrypt(text: str, shift: int) -> str:
    """Encrypt text using Caesar cipher with given shift."""
    if not isinstance(text, str):
        raise TypeError("Text must be a string")
    if not isinstance(shift, int):
        raise TypeError("Shift must be an integer")

    shift = shift % 26
    result = []
    for ch in text:
        if "a" <= ch <= "z":
            result.append(chr((ord(ch) - ord("a") + shift) % 26 + ord("a")))
        elif "A" <= ch <= "Z":
            result.append(chr((ord(ch) - ord("A") + shift) % 26 + ord("A")))
        else:
            result.append(ch)
    return "".join(result)


def caesar_decrypt(text: str, shift: int) -> str:
    """Decrypt text encrypted with Caesar cipher."""
    if not isinstance(shift, int):
        raise TypeError("Shift must be an integer")
    return caesar_encrypt(text, -shift)


def caesar_brute_force(text: str) -> dict[int, str]:
    """Return all 26 possible Caesar cipher shifts for analysis."""
    if not isinstance(text, str):
        raise TypeError("Text must be a string")
    return {shift: caesar_decrypt(text, shift) for shift in range(26)}


def vigenere_encrypt(text: str, key: str) -> str:
    """Encrypt text using the Vigenere cipher with a key."""
    if not isinstance(text, str) or not isinstance(key, str):
        raise TypeError("Both text and key must be strings")
    clean_key = [ord(k.upper()) - ord("A") for k in key if k.isalpha()]
    if not clean_key:
        raise ValueError("Key must contain at least one alphabetic character")

    result = []
    key_idx = 0
    for ch in text:
        if "a" <= ch <= "z":
            shift = clean_key[key_idx % len(clean_key)]
            result.append(chr((ord(ch) - ord("a") + shift) % 26 + ord("a")))
            key_idx += 1
        elif "A" <= ch <= "Z":
            shift = clean_key[key_idx % len(clean_key)]
            result.append(chr((ord(ch) - ord("A") + shift) % 26 + ord("A")))
            key_idx += 1
        else:
            result.append(ch)
    return "".join(result)


def vigenere_decrypt(text: str, key: str) -> str:
    """Decrypt text encrypted with Vigenere cipher."""
    if not isinstance(text, str) or not isinstance(key, str):
        raise TypeError("Both text and key must be strings")
    clean_key = [ord(k.upper()) - ord("A") for k in key if k.isalpha()]
    if not clean_key:
        raise ValueError("Key must contain at least one alphabetic character")

    result = []
    key_idx = 0
    for ch in text:
        if "a" <= ch <= "z":
            shift = clean_key[key_idx % len(clean_key)]
            result.append(chr((ord(ch) - ord("a") - shift) % 26 + ord("a")))
            key_idx += 1
        elif "A" <= ch <= "Z":
            shift = clean_key[key_idx % len(clean_key)]
            result.append(chr((ord(ch) - ord("A") - shift) % 26 + ord("A")))
            key_idx += 1
        else:
            result.append(ch)
    return "".join(result)


def compute_sum_of_primes(limit: int = 3_000_000) -> int:
    """Compute the sum of all prime numbers strictly up to `limit` via trial division."""
    total = 0
    for i in range(2, limit + 1):
        is_prime = True
        limit_d = int(i ** 0.5)
        for d in range(2, limit_d + 1):
            if i % d == 0:
                is_prime = False
                break
        if is_prime:
            total += i
    return total


class TestCaesar(unittest.TestCase):
    """Test suite for Caesar & Vigenere cipher functions and performance probe."""

    def test_caesar_basic(self):
        plain = "Hello, World! 123"
        cipher = caesar_encrypt(plain, 3)
        self.assertEqual(cipher, "Khoor, Zruog! 123")
        self.assertEqual(caesar_decrypt(cipher, 3), plain)

    def test_caesar_rot13(self):
        msg = "The Quick Brown Fox Jumps Over The Lazy Dog."
        self.assertEqual(caesar_decrypt(caesar_encrypt(msg, 13), 13), msg)

    def test_caesar_brute_force(self):
        plain = "Secret Message"
        cipher = caesar_encrypt(plain, 7)
        candidates = caesar_brute_force(cipher)
        self.assertIn(7, candidates)
        self.assertEqual(candidates[7], plain)

    def test_vigenere(self):
        msg = "ATTACKATDAWN"
        key = "LEMON"
        enc = vigenere_encrypt(msg, key)
        self.assertEqual(enc, "LXFOPVEFRNHR")
        self.assertEqual(vigenere_decrypt(enc, key), msg)

    def test_vigenere_invalid_key(self):
        with self.assertRaises(ValueError):
            vigenere_encrypt("Hello", "123!@#")

    def test_type_errors(self):
        with self.assertRaises(TypeError):
            caesar_encrypt(123, 5)  # type: ignore
        with self.assertRaises(TypeError):
            caesar_encrypt("text", "five")  # type: ignore

    def test_performance_probe(self):
        """Live performance probe >= 20 seconds computing sum of primes up to 3,000,000."""
        target_limit = 3_000_000
        min_seconds = 20.0
        start_time = time.perf_counter()
        iterations = 0
        prime_sum = 0

        while True:
            prime_sum = compute_sum_of_primes(target_limit)
            iterations += 1
            elapsed = time.perf_counter() - start_time
            if elapsed >= min_seconds:
                break

        print(
            f"\n[caesar.py PROBE] Sum of primes up to {target_limit:,}: {prime_sum} "
            f"| Iterations: {iterations} | Time: {elapsed:.2f}s"
        )
        self.assertEqual(prime_sum, 312471072265)
        self.assertGreaterEqual(elapsed, min_seconds)


if __name__ == "__main__":
    unittest.main()
