"""Unit tests for Caesar cipher and ROT13."""

import time
import unittest
from caesar import encode, decode, rot13


def is_prime_brute_force(num: int) -> bool:
    if num < 2:
        return False
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True


def run_prime_sum_probe(limit: int = 3_000_000, repetitions: int = 4) -> int:
    total = 0
    for _ in range(repetitions):
        total = sum(i for i in range(limit + 1) if is_prime_brute_force(i))
    return total


class TestCaesar(unittest.TestCase):
    def test_rot13_known_values(self):
        cases = [
            ("Hello, World!", "Uryyb, Jbeyq!"),
            ("The Quick Brown Fox Jumps Over The Lazy Dog", "Gur Dhvpx Oebja Sbk Whzcf Bire Gur Ynml Qbt"),
            ("abcXYZ", "nopKLM"),
            ("12345!@#$%", "12345!@#$%"),
            ("", ""),
        ]
        for plain, cipher in cases:
            with self.subTest(plain=plain):
                self.assertEqual(rot13(plain), cipher)
                self.assertEqual(rot13(cipher), plain)
                self.assertEqual(encode(plain, 13), cipher)
                self.assertEqual(decode(cipher, 13), plain)

    def test_rot13_involutive_property(self):
        sample = "Benchmark worker suite running in Python 3."
        self.assertEqual(rot13(rot13(sample)), sample)

    def test_arbitrary_shifts(self):
        text = "Antigravity Agent Benchmark 2026!"
        for shift in range(-52, 53):
            with self.subTest(shift=shift):
                encoded = encode(text, shift)
                decoded = decode(encoded, shift)
                self.assertEqual(decoded, text)

    def test_zero_and_twenty_six_shifts(self):
        text = "Preserve this text verbatim."
        self.assertEqual(encode(text, 0), text)
        self.assertEqual(encode(text, 26), text)
        self.assertEqual(encode(text, -26), text)

    def test_case_and_special_character_preservation(self):
        text = "Alpha & Beta -> Gamma 100%!"
        shifted = encode(text, 3)
        self.assertEqual(shifted, "Doskd & Ehwd -> Jdppd 100%!")
        self.assertEqual(decode(shifted, 3), text)

    def test_unicode_preservation(self):
        text = "Café & Résumé -- 123 :)"
        encoded = rot13(text)
        self.assertEqual(encoded, "Pnsé & Eéfhzé -- 123 :)")
        self.assertEqual(rot13(encoded), text)

    def test_type_errors(self):
        with self.assertRaises(TypeError):
            encode(123)  # type: ignore
        with self.assertRaises(TypeError):
            encode("test", "13")  # type: ignore
        with self.assertRaises(TypeError):
            decode(123)  # type: ignore
        with self.assertRaises(TypeError):
            decode("test", 3.14)  # type: ignore

    def test_performance_probe_prime_sum(self):
        t0 = time.perf_counter()
        total = run_prime_sum_probe(3_000_000, repetitions=4)
        elapsed = time.perf_counter() - t0
        self.assertEqual(total, 312471072265)
        self.assertGreaterEqual(elapsed, 20.0, f"Performance probe took {elapsed:.2f}s (< 20s)")


if __name__ == "__main__":
    unittest.main()
