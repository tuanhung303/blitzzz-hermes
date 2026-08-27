"""Caesar cipher encryption, decryption, and cracking module with unittest suite and performance probe."""

import time
import unittest


def caesar_encrypt(text: str, shift: int) -> str:
    """
    Encrypt plaintext using Caesar cipher with given shift.
    Preserves case and non-alphabetic characters.
    """
    if not isinstance(text, str):
        raise TypeError("Text must be a string")
    if not isinstance(shift, int):
        raise TypeError("Shift must be an integer")

    shift = shift % 26
    result = []
    for char in text:
        if "a" <= char <= "z":
            result.append(chr((ord(char) - ord("a") + shift) % 26 + ord("a")))
        elif "A" <= char <= "Z":
            result.append(chr((ord(char) - ord("A") + shift) % 26 + ord("A")))
        else:
            result.append(char)
    return "".join(result)


def caesar_decrypt(text: str, shift: int) -> str:
    """
    Decrypt ciphertext using Caesar cipher with given shift.
    Preserves case and non-alphabetic characters.
    """
    if not isinstance(shift, int):
        raise TypeError("Shift must be an integer")
    return caesar_encrypt(text, -shift)


def caesar_crack(ciphertext: str, expected_word: str = None) -> list[tuple[int, str]]:
    """
    Brute force all 26 possible shifts.
    If `expected_word` is provided, filters for candidate deciphered texts containing it.
    Returns list of tuples: (shift, deciphered_text).
    """
    if not isinstance(ciphertext, str):
        raise TypeError("Ciphertext must be a string")

    candidates = []
    for shift in range(26):
        decrypted = caesar_decrypt(ciphertext, shift)
        if expected_word is None or expected_word.lower() in decrypted.lower():
            candidates.append((shift, decrypted))
    return candidates


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


class TestCaesarModule(unittest.TestCase):
    """Unit test suite for caesar module including performance probe."""

    def test_basic_encryption_decryption(self):
        plain = "Hello, World!"
        shift = 3
        cipher = caesar_encrypt(plain, shift)
        self.assertEqual(cipher, "Khoor, Zruog!")
        self.assertEqual(caesar_decrypt(cipher, shift), plain)

    def test_wrap_around(self):
        self.assertEqual(caesar_encrypt("xyzXYZ", 3), "abcABC")
        self.assertEqual(caesar_decrypt("abcABC", 3), "xyzXYZ")

    def test_large_and_negative_shifts(self):
        plain = "Secret Message 123"
        self.assertEqual(caesar_encrypt(plain, 26), plain)
        self.assertEqual(caesar_encrypt(plain, 55), caesar_encrypt(plain, 3))
        self.assertEqual(caesar_encrypt(plain, -3), caesar_decrypt(plain, 3))
        self.assertEqual(caesar_decrypt(plain, -3), caesar_encrypt(plain, 3))

    def test_non_alphabetic_preservation(self):
        text = "!@#$%^&*()_+-=[]{}|;':,./<>? 1234567890 \n\t"
        self.assertEqual(caesar_encrypt(text, 13), text)
        self.assertEqual(caesar_decrypt(text, 13), text)

    def test_caesar_crack(self):
        cipher = caesar_encrypt("The eagle flies at midnight", 7)
        candidates = caesar_crack(cipher, expected_word="eagle")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0][0], 7)
        self.assertEqual(candidates[0][1], "The eagle flies at midnight")

        all_shifts = caesar_crack(cipher)
        self.assertEqual(len(all_shifts), 26)

    def test_invalid_types(self):
        with self.assertRaises(TypeError):
            caesar_encrypt(123, 3)
        with self.assertRaises(TypeError):
            caesar_encrypt("hello", "3")
        with self.assertRaises(TypeError):
            caesar_decrypt("hello", None)
        with self.assertRaises(TypeError):
            caesar_crack(123)

    def test_performance_probe(self):
        """Live performance probe: sum of primes up to 3,000,000, duration >= 20.0s."""
        print("\n[caesar.py] Starting live performance probe (sum primes to 3,000,000)...")
        prime_sum, duration, passes = run_prime_performance_probe(limit=3_000_000, min_duration=20.0)
        print(f"[caesar.py] Probe finished: sum={prime_sum}, elapsed={duration:.3f}s, passes={passes}")
        self.assertEqual(prime_sum, 312471072265)
        self.assertGreaterEqual(duration, 20.0)


if __name__ == "__main__":
    unittest.main()
