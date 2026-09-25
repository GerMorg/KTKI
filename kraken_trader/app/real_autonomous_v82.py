"""Small v82 secret lifecycle helpers.

Kept separate so the secret-rotation behavior can be unit-tested without
starting the Flask application.
"""
import hashlib
import hmac


def secret_hash(secret):
    value = str(secret or "")
    return hashlib.sha256(value.encode()).hexdigest() if value else ""


def secret_matches(secret, stored_hash):
    expected = secret_hash(secret)
    actual = str(stored_hash or "")
    return bool(expected and actual) and hmac.compare_digest(expected, actual)


def secret_state(secret, stored_hash):
    expected = secret_hash(secret)
    actual = str(stored_hash or "")
    if not expected:
        return {"configured": False, "matches": False}
    return {"configured": True, "matches": bool(actual) and hmac.compare_digest(expected, actual)}
