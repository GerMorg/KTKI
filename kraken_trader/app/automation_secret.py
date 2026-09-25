import hashlib,hmac

def hash_automation_secret(secret):
    secret=str(secret or '')
    return hashlib.sha256(secret.encode('utf-8')).hexdigest() if secret else ''

def sync_automation_secret(db, options):
    """Synchronize the internal hash from the single user-facing secret.

    The add-on user never configures the hash. A changed secret replaces the
    old hash; clearing the secret disables autonomous secret authorization.
    """
    secret=str((options or {}).get('real_balancing_automation_secret') or '')
    desired=hash_automation_secret(secret)
    current=str(db.value('real_balancing_automation_secret_hash','') or '')
    if desired != current:
        db.set_setting('real_balancing_automation_secret_hash',desired)
        db.audit('REAL_AUTOMATION_SECRET_UPDATED','Automation secret hash synchronized','warning','REAL')
    return bool(secret)

def automation_secret_valid(db, secret):
    wanted=str(db.value('real_balancing_automation_secret_hash','') or '')
    candidate=hash_automation_secret(secret)
    return bool(wanted and candidate) and hmac.compare_digest(candidate,wanted)
