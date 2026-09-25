import hashlib
import hmac
import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
from real_autonomous_v82 import secret_hash, secret_matches, secret_state


class V82AutomationSecretTests(unittest.TestCase):
    def test_secret_hash_is_sha256(self):
        self.assertEqual(secret_hash("abc"), hashlib.sha256(b"abc").hexdigest())

    def test_empty_secret_is_not_configured(self):
        self.assertEqual(secret_hash(""), "")
        self.assertEqual(secret_state("", ""), {"configured": False, "matches": False})

    def test_secret_matches_hash_without_exposing_secret(self):
        hashed = secret_hash("correct-secret")
        self.assertTrue(secret_matches("correct-secret", hashed))
        self.assertFalse(secret_matches("wrong-secret", hashed))
        self.assertTrue(hmac.compare_digest(hashed, secret_hash("correct-secret")))

    def test_secret_rotation_produces_different_hash(self):
        self.assertNotEqual(secret_hash("old"), secret_hash("new"))


if __name__ == "__main__":
    unittest.main()
