import hashlib
import hmac

from real_autonomous_v82 import secret_hash, secret_matches, secret_state


def test_secret_hash_is_sha256():
    assert secret_hash("abc") == hashlib.sha256(b"abc").hexdigest()


def test_empty_secret_is_not_configured():
    assert secret_hash("") == ""
    assert secret_state("", "") == {"configured": False, "matches": False}


def test_secret_matches_hash_without_exposing_secret():
    hashed = secret_hash("correct-secret")
    assert secret_matches("correct-secret", hashed)
    assert not secret_matches("wrong-secret", hashed)
    assert hmac.compare_digest(hashed, secret_hash("correct-secret"))


def test_secret_rotation_produces_different_hash():
    assert secret_hash("old") != secret_hash("new")
