"""
Adversarial Verification — Attack Script
Tests all 6 spec bugs + extended attacks against the fixed codebase.
Does NOT modify source files. Produces clear PASS/FAIL per attack.
"""
import sys
import os
import json
import time
import threading
import base64
import hmac
import hashlib

# Work from the workspace directory so imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import auth
import refresh
import middleware
from config import SECRET_KEY, ALLOWED_ISSUERS, TOKEN_LIFETIME

RESULTS = []

def record(bug_num, bug_name, passed, description, detail=""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((bug_num, bug_name, status, description, detail))
    print(f"\n{'='*60}")
    print(f"Bug {bug_num}: {bug_name} — {status}")
    print(f"  {description}")
    if detail:
        print(f"  Detail: {detail}")
    print(f"{'='*60}")

# ============================================================
# Bug 1: Algorithm "none" accepted
# ============================================================
def attack_bug1_none_alg():
    print("\n" + "#"*60)
    print("# ATTACK 1: Algorithm 'none' / missing alg / wrong alg")
    print("#"*60)

    # Attack 1a: Forge a token with alg="none" and no real signature
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": "attacker", "iss": "auth.myapp.com", "iat": int(time.time()), "exp": int(time.time())+3600}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    fake_sig = base64.urlsafe_b64encode(b"fakesig").rstrip(b"=").decode()
    forged_token_none = f"{header_b64}.{payload_b64}.{fake_sig}"

    result = auth.decode_token(forged_token_none)
    passed = result is None
    record(1, "Algorithm 'none' accepted (forged none-alg token)",
           passed,
           "Forged token with alg:'none' and fake signature",
           f"decode_token returned: {result}")

    # Attack 1b: Token with missing alg header
    header_no_alg = {"typ": "JWT"}
    header_b64_noalg = base64.urlsafe_b64encode(json.dumps(header_no_alg).encode()).rstrip(b"=").decode()
    payload_b64_2 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    forged_token_noalg = f"{header_b64_noalg}.{payload_b64_2}.{fake_sig}"

    result2 = auth.decode_token(forged_token_noalg)
    passed2 = result2 is None
    record("1b", "Missing alg header defaults to 'none'?",
           passed2,
           "Token header has no 'alg' field — should be rejected",
           f"decode_token returned: {result2}")

    # Attack 1c: Token with alg="RS256" (wrong algorithm)
    header_wrong_alg = {"alg": "RS256", "typ": "JWT"}
    header_b64_wrong = base64.urlsafe_b64encode(json.dumps(header_wrong_alg).encode()).rstrip(b"=").decode()
    forged_token_wrongalg = f"{header_b64_wrong}.{payload_b64_2}.{fake_sig}"

    result3 = auth.decode_token(forged_token_wrongalg)
    passed3 = result3 is None
    record("1c", "Wrong algorithm (RS256) accepted?",
           passed3,
           "Token with alg:'RS256' — should be rejected by whitelist",
           f"decode_token returned: {result3}")

    # Attack 1d: alg="None" (capitalized variant)
    header_cap_none = {"alg": "None", "typ": "JWT"}
    header_b64_cap = base64.urlsafe_b64encode(json.dumps(header_cap_none).encode()).rstrip(b"=").decode()
    forged_token_capnone = f"{header_b64_cap}.{payload_b64_2}.{fake_sig}"

    result4 = auth.decode_token(forged_token_capnone)
    passed4 = result4 is None
    record("1d", "Algorithm 'None' (capitalized) accepted?",
           passed4,
           "Token with alg:'None' — should still be rejected",
           f"decode_token returned: {result4}")

    return all([passed, passed2, passed3, passed4])


# ============================================================
# Bug 2: Expiration off-by-one
# ============================================================
def attack_bug2_exp_offbyone():
    print("\n" + "#"*60)
    print("# ATTACK 2: Expiration off-by-one")
    print("#"*60)

    # Create a token that expires RIGHT NOW
    now = int(time.time())
    expiring_token = auth.create_token(
        {"sub": "user1", "iss": "auth.myapp.com"},
        expires_in=1  # 1 second lifetime
    )
    # Wait for it to expire
    time.sleep(1.5)

    result = auth.validate_token(expiring_token)
    passed = result is None
    record(2, "Expiration off-by-one (exact boundary)",
           passed,
           "Token with 1s lifetime validated after 1.5s wait",
           f"validate_token on expired token returned: {result}")

    # Also test: token that expires in the future should still work
    future_token = auth.create_token(
        {"sub": "user1", "iss": "auth.myapp.com"},
        expires_in=300
    )
    result2 = auth.validate_token(future_token)
    passed2 = result2 is not None
    record("2b", "Valid (non-expired) token should pass",
           passed2,
           "Token with 300s lifetime validated immediately",
           f"validate_token returned: {'OK' if result2 else 'None'}")

    return all([passed, passed2])


# ============================================================
# Bug 3: Grace window should be zero
# ============================================================
def attack_bug3_grace_window():
    print("\n" + "#"*60)
    print("# ATTACK 3: Grace window zero")
    print("#"*60)

    # Verify GRACE_WINDOW is 0
    from config import GRACE_WINDOW
    gw_ok = GRACE_WINDOW == 0
    if not gw_ok:
        record(3, "Grace window zero",
               False,
               f"GRACE_WINDOW is {GRACE_WINDOW}, should be 0")
        return False

    # Create token with immediate expiration, validate after expiry
    now = int(time.time())
    short_token = auth.create_token(
        {"sub": "user1", "iss": "auth.myapp.com"},
        expires_in=1
    )
    time.sleep(1.5)  # It should be expired now

    result = auth.validate_token(short_token)
    passed = result is None
    record(3, "Grace window zero (expired token rejected immediately)",
           passed,
           f"GRACE_WINDOW={GRACE_WINDOW}, token expired ~0.5s ago",
           f"validate_token returned: {result}")

    # Also check that is_expired() is being used (not raw grace logic)
    # The old code did: `if now > exp + GRACE_WINDOW`
    # With GRACE_WINDOW=0, that's equivalent, but we verify the fixed code uses is_expired()
    import inspect
    source = inspect.getsource(auth.validate_token)
    uses_is_expired = "is_expired" in source
    record("3b", "validate_token uses is_expired() (not inline grace window logic)",
           uses_is_expired,
           "is_expired() is called in validate_token" if uses_is_expired else "is_expired() NOT called in validate_token",
           "")

    return passed and uses_is_expired


# ============================================================
# Bug 4: Missing issuer validation
# ============================================================
def attack_bug4_issuer():
    print("\n" + "#"*60)
    print("# ATTACK 4: Issuer validation")
    print("#"*60)

    # Attack 4a: Token with unallowed issuer
    evil_token = auth.create_token(
        {"sub": "attacker", "iss": "evil.com"}
    )
    result = auth.validate_token(evil_token)
    passed = result is None
    record(4, "Missing issuer validation (evil.com rejected)",
           passed,
           "Token with iss:'evil.com' (not in ALLOWED_ISSUERS)",
           f"validate_token returned: {result}")

    # Attack 4b: Token with no iss claim
    no_iss_token = auth.create_token(
        {"sub": "attacker"}
    )
    # Remove iss from the created token payload
    # Actually, create_token adds iat and exp. Let me decode, remove iss, and manually sign.
    # Better: just create_token without iss, and check if validate rejects it
    result2 = auth.validate_token(no_iss_token)
    passed2 = result2 is None
    record("4b", "Token with missing iss claim rejected",
           passed2,
           "Token created without 'iss' — validate_token should reject",
           f"validate_token returned: {result2}")

    # Attack 4c: Valid issuer should pass
    valid_token = auth.create_token(
        {"sub": "user1", "iss": "auth.myapp.com"}
    )
    result3 = auth.validate_token(valid_token)
    passed3 = result3 is not None
    record("4c", "Token with valid issuer accepted",
           passed3,
           "Token with iss:'auth.myapp.com' (in ALLOWED_ISSUERS)",
           f"validate_token returned: {'OK' if result3 else 'None'}")

    return all([passed, passed2, passed3])


# ============================================================
# RC1: No token blacklisting
# ============================================================
def attack_rc1_blacklist():
    print("\n" + "#"*60)
    print("# ATTACK 5 (RC1): Token blacklisting")
    print("#"*60)

    # Clear blacklist for clean test
    refresh._blacklist.clear()

    # Create a token
    token = auth.create_token(
        {"sub": "user1", "iss": "auth.myapp.com"},
        expires_in=300
    )

    # Verify it's valid
    v1 = auth.validate_token(token)
    assert v1 is not None, "Token should be valid initially"

    # Refresh it
    new_token = refresh.refresh_token(token)
    assert new_token is not None, "Refresh should succeed"

    # Now check if old token is blacklisted
    is_bl = refresh.is_blacklisted(token)
    passed_bl = is_bl is True
    record("5a", "Token blacklisting (old token in blacklist after refresh)",
           passed_bl,
           "After refresh, old token should be in _blacklist",
           f"is_blacklisted: {is_bl}")

    # Now check if middleware rejects the old token
    result = middleware.authenticate_request(f"Bearer {token}")
    passed_mw = result is None
    record("5b", "Middleware rejects blacklisted old token",
           passed_mw,
           "authenticate_request should return None for blacklisted token",
           f"authenticate_request returned: {result}")

    # Check new token works
    result_new = middleware.authenticate_request(f"Bearer {new_token}")
    passed_new = result_new is not None
    record("5c", "Middleware accepts new (unblacklisted) token",
           passed_new,
           "authenticate_request should return payload for new token",
           f"authenticate_request returned: {'OK' if result_new else 'None'}")

    return all([passed_bl, passed_mw, passed_new])


# ============================================================
# RC2: Duplicate concurrent refresh
# ============================================================
def attack_rc2_concurrent():
    print("\n" + "#"*60)
    print("# ATTACK 6 (RC2): Concurrent refresh race")
    print("#"*60)

    # Clear blacklist and active refreshes
    refresh._blacklist.clear()
    refresh._active_refreshes.clear()

    # Create a token
    token = auth.create_token(
        {"sub": "user1", "iss": "auth.myapp.com"},
        expires_in=300
    )

    # Launch concurrent refresh attempts
    results_lock = threading.Lock()
    new_tokens = []

    def do_refresh():
        result = refresh.refresh_token(token)
        with results_lock:
            if result is not None:
                new_tokens.append(result)

    threads = []
    for _ in range(10):
        t = threading.Thread(target=do_refresh)
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    unique_tokens = set(new_tokens)
    n_issued = len(new_tokens)
    n_unique = len(unique_tokens)

    # Attack assessment:
    # The lock serializes access but doesn't prevent duplicate issuance.
    # Since decode happens OUTSIDE the lock, all 10 threads can decode
    # successfully before any enters the lock. All 10 will then enter
    # the lock sequentially and each create a new token.
    # So we expect 10 tokens issued, all likely different.

    # This is the key vulnerability: the lock alone does NOT prevent duplicates.
    # An atomic check-and-set (e.g. checking if old_token is already blacklisted
    # INSIDE the lock before creating a new token) is needed.

    passed = n_unique == 1  # Should be 1 if truly preventing duplicates
    record(6, "Concurrent refresh — single new token issued",
           passed,
           f"10 concurrent refreshes → {n_unique} unique tokens issued (of {n_issued} total)",
           f"Unique tokens: {n_unique}, Total issued: {n_issued}. {'PASS: only 1 unique' if passed else 'FAIL: multiple unique tokens issued'}")

    return passed


# ============================================================
# Extended Attacks
# ============================================================
def extended_attacks():
    print("\n" + "#"*60)
    print("# EXTENDED ATTACKS")
    print("#"*60)
    all_passed = []

    # ---------- Extended 1: Compound attack — forged none-alg token → refresh ----------
    print("\n--- Extended 1: Compound forged-none → refresh ---")
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": "attacker", "iss": "auth.myapp.com", "iat": int(time.time()), "exp": int(time.time())+3600}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    fake_sig = base64.urlsafe_b64encode(b"fakesig").rstrip(b"=").decode()
    forged = f"{header_b64}.{payload_b64}.{fake_sig}"

    # Try to refresh the forged token
    result = refresh.refresh_token(forged)
    passed = result is None
    all_passed.append(passed)
    record("E1", "Compound: forged none-alg token → refresh",
           passed,
           "Forged token with alg:'none' should be rejected by decode_token before refresh can use it",
           f"refresh_token returned: {result}")

    # ---------- Extended 2: Token without exp claim ----------
    print("\n--- Extended 2: Token without exp claim ---")
    # Manually construct a signed token without exp
    header = {"alg": "HS256", "typ": "JWT"}
    payload_no_exp = {"sub": "user1", "iss": "auth.myapp.com", "iat": int(time.time())}
    hb64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    pb64 = base64.urlsafe_b64encode(json.dumps(payload_no_exp).encode()).rstrip(b"=").decode()
    msg = f"{hb64}.{pb64}".encode()
    sig = hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    no_exp_token = f"{hb64}.{pb64}.{sig_b64}"

    result2 = auth.validate_token(no_exp_token)
    # is_expired uses payload.get("exp", 0) → 0, and now >= 0 → True → rejected
    passed2 = result2 is None
    all_passed.append(passed2)
    record("E2", "Token without 'exp' claim rejected",
           passed2,
           "Signed token with no 'exp' claim — should be rejected as expired (defaults to exp=0)",
           f"validate_token returned: {result2}")

    # ---------- Extended 3: Empty signature ----------
    print("\n--- Extended 3: Empty signature attack ---")
    header = {"alg": "HS256", "typ": "JWT"}
    payload_v = {"sub": "user1", "iss": "auth.myapp.com", "iat": int(time.time()), "exp": int(time.time())+3600}
    hb64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    pb64 = base64.urlsafe_b64encode(json.dumps(payload_v).encode()).rstrip(b"=").decode()
    # Empty signature — the token ends with a dot, so split gives ["hb64", "pb64", ""]
    empty_sig_token = f"{hb64}.{pb64}."

    result3 = auth.decode_token(empty_sig_token)
    # split gives 3 parts, then _b64_decode("") might fail or signature comparison fails
    passed3 = result3 is None
    all_passed.append(passed3)
    record("E3", "Empty signature rejected",
           passed3,
           "Token with empty signature (trailing dot) — should be rejected",
           f"decode_token returned: {result3}")

    # ---------- Extended 4: Refresh already-blacklisted token ----------
    print("\n--- Extended 4: Refresh of already-blacklisted token ---")
    refresh._blacklist.clear()
    token = auth.create_token({"sub": "user1", "iss": "auth.myapp.com"}, expires_in=300)
    # Refresh once
    new1 = refresh.refresh_token(token)
    assert new1 is not None
    # Now try to refresh the SAME old token again (it should be blacklisted now)
    new2 = refresh.refresh_token(token)
    # The old token IS in the blacklist, but refresh_token uses decode_token (not validate_token),
    # and decode_token doesn't check the blacklist! So it might still succeed.
    # This is a design flaw — refresh should check blacklist before re-decoding.
    passed4 = new2 is None
    all_passed.append(passed4)
    record("E4", "Cannot refresh already-blacklisted token",
           passed4,
           "Old token was refreshed once (blacklisted); second refresh should fail",
           f"Second refresh returned: {new2} ({'FAIL: allowed re-refresh' if not passed4 else 'PASS: rejected'})")

    return all(all_passed)


# ============================================================
# Run all attacks
# ============================================================
if __name__ == "__main__":
    print("="*60)
    print("ADVERSARIAL VERIFICATION — ATTACK SUITE")
    print("="*60)

    all_results = {}

    all_results["bug1"] = attack_bug1_none_alg()
    all_results["bug2"] = attack_bug2_exp_offbyone()
    all_results["bug3"] = attack_bug3_grace_window()
    all_results["bug4"] = attack_bug4_issuer()
    all_results["rc1"] = attack_rc1_blacklist()
    all_results["rc2"] = attack_rc2_concurrent()
    all_results["extended"] = extended_attacks()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for bug_num, bug_name, status, desc, detail in RESULTS:
        status_mark = "✓" if status == "PASS" else "✗"
        print(f"  [{status_mark}] Bug {bug_num}: {bug_name} — {status}")

    print("\n---")
    spec_bugs_pass = all([all_results.get(k, False) for k in ["bug1","bug2","bug3","bug4","rc1","rc2"]])
    extended_pass = all_results.get("extended", False)
    print(f"Spec bugs (6): {'ALL PASS' if spec_bugs_pass else 'SOME FAIL'}")
    print(f"Extended attacks: {'PASS' if extended_pass else 'FAIL'}")
    print(f"Overall verdict: {'SHIP' if spec_bugs_pass and extended_pass else 'FIX-REQUIRED'}")
