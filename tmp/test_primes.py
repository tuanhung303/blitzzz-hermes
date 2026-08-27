import unittest
from primes import sieve_of_eratosthenes


def is_prime_brute_force(num: int) -> bool:
    if num < 2:
        return False
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True


class TestPrimes(unittest.TestCase):
    def test_edge_cases(self):
        self.assertEqual(sieve_of_eratosthenes(0), [])
        self.assertEqual(sieve_of_eratosthenes(1), [])
        self.assertEqual(sieve_of_eratosthenes(2), [2])

    def test_known_values(self):
        self.assertEqual(sieve_of_eratosthenes(10), [2, 3, 5, 7])
        primes_100 = sieve_of_eratosthenes(100)
        self.assertEqual(len(primes_100), 25)
        self.assertEqual(
            primes_100,
            [
                2, 3, 5, 7, 11, 13, 17, 19, 23, 29,
                31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
                73, 79, 83, 89, 97,
            ],
        )

    def test_input_validation(self):
        with self.assertRaises(TypeError):
            sieve_of_eratosthenes(3.14)  # type: ignore
        with self.assertRaises(TypeError):
            sieve_of_eratosthenes("10")  # type: ignore
        with self.assertRaises(TypeError):
            sieve_of_eratosthenes(True)  # type: ignore
        with self.assertRaises(ValueError):
            sieve_of_eratosthenes(-1)
        with self.assertRaises(ValueError):
            sieve_of_eratosthenes(-100)

    def test_brute_force_cross_check(self):
        for limit in range(0, 201):
            expected = [x for x in range(limit + 1) if is_prime_brute_force(x)]
            actual = sieve_of_eratosthenes(limit)
            self.assertEqual(actual, expected, f"Mismatch at limit={limit}")


if __name__ == "__main__":
    unittest.main()
