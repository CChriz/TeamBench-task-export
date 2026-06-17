"""
Adversarial Verification — Attack Script v2
Tests all 6 spec bugs + extended attacks against the fixed codebase.
Handles timing edge cases properly.
"""
import sys
import os
import json
import time
import threading
import base64
import hmac
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import auth
import refresh
import middleware
from config import SECRET_KEY, ALLOWED_ISSUERS, TOKEN_LIFETIME, GRACE_WINDOW

RESULTS = []

def record(bug_id, bug_name, passed, description, detail=""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((bug_id, bug_name, status, description, detail))
    print(f"\n{'='*60}")
    print(f"Bug {bug_id}: {bug_name} — {status}")
    print(f"  {description}")
    if detail:
        print(f"  Detail: {detail}")
    print(f"{'='*60}")

# ============================================================
# Bug 1: Algorithm "none" accepted
# ============================================================
def attack_bug1():
    print("\n" + "#"*60)
    print("# BUG 1: Algorithm 'none' accepted")
    print("#"*60)

    all_pass = True
    payload = {"sub": "attacker", "iss": "auth.myapp.com", "iat": int(time.time()), "exp": int(time.time())+3600}

    # 1a: alg="none"
    h = {"alg": "none", "typ": "JWT"}
    hb = base64.urlsafe_b64encode(json.dumps(h).encode()).rstrip(b"=").decode()
    pb = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(b"fakesig").rstrip(b"=").decode()
    tok = f"{hb}.{pb}.{sig}"
    r = auth.decode_token(tok)
    p = r is None
    record("1a", "alg='none' forged token rejected", p, f"decode_token returned: {r}")
    all_pass &= p

    # 1b: missing alg
    h2 = {"typ": "JWT"}
    hb2 = base64.urlsafe_b64encode(json.dumps(h2).encode()).rstrip(b"=").decode()
    tok2 = f"{hb2}.{pb}.{sig}"
    r2 = auth.decode_token(tok2)
    p2 = r2 is None
    record("1b", "Missing 'alg' header rejected", p2, f"decode_token returned: {r2}")
    all_pass &= p2

    # 1c: wrong algorithm RS256
    h3 = {"alg": "RS256", "typ": "JWT"}
    hb3 = base64.urlsafe_b64encode(json.dumps(h3).encode()).rstrip(b"=").decode()
    tok3 = f"{hb3}.{pb}.{sig}"
    r3 = auth.decode_token(tok3)
    p3 = r3 is None
    record("1c", "alg='RS256' rejected (whitelist enforcement)", p3, f"decode_token returned: {r3}")
    all_pass &= p3

    # 1d: case variation "None"
    h4 = {"alg": "None", "typ": "JWT"}
    hb4 = base64.urlsafe_b64encode(json.dumps(h4).encode()).rstrip(b"=").decode()
    tok4 = f"{hb4}.{pb}.{sig}"
    r4 = auth.decode_token(tok4)
    p4 = r4 is None
    record("1d", "alg='None' (capitalized) rejected", p4, f"decode_token returned: {r4}")
    all_pass &= p4

    return all_pass


# ============================================================
# Bug 2: Expiration off-by-one
# ============================================================
def attack_bug2():
    print("\n" + "#"*60)
    print("# BUG 2: Expiration off-by-one")
    print("#"*60)

    # Create token with minimal lifetime
    tok = auth.create_token({"sub": "u1", "iss": "auth.myapp.com"}, expires_in=1)
    time.sleep(1.5)  # definitely expired

    r = auth.validate_token(tok)
    p = r is None
    record("2a", "Expired token (1s lifetime, 1.5s wait) rejected", p,
           f"validate_token returned: {r}")
    return p


# ============================================================
# Bug 3: Grace window zero
# ============================================================
def attack_bug3():
    print("\n" + "#"*60)
    print("# BUG 3: Grace window zero")
    print("#"*60)

    all_pass = True

    p0 = GRACE_WINDOW == 0
    record("3a", f"GRACE_WINDOW == 0 (actual: {GRACE_WINDOW})", p0, "")
    all_pass &= p0

    # Token that just expired
    tok = auth.create_token({"sub": "u1", "iss": "auth.myapp.com"}, expires_in=1)
    time.sleep(1.5)
    r = auth.validate_token(tok)
    p1 = r is None
    record("3b", "Recently-expired token rejected (no grace)", p1,
           f"validate_token returned: {r}")
    all_pass &= p1

    return all_pass


# ============================================================
# Bug 4: Missing issuer validation
# ============================================================
def attack_bug4():
    print("\n" + "#"*60)
    print("# BUG 4: Missing issuer validation")
    print("#"*60)

    all_pass = True

    # 4a: unapproved issuer
    tok = auth.create_token({"sub": "u1", "iss": "evil.com"})
    r = auth.validate_token(tok)
    p = r is None
    record("4a", "Token from 'evil.com' rejected", p, f"validate_token returned: {r}")
    all_pass &= p

    # 4b: missing iss claim
    tok2 = auth.create_token({"sub": "u1"})  # no iss
    r2 = auth.validate_token(tok2)
    p2 = r2 is None
    record("4b", "Token without 'iss' claim rejected", p2, f"validate_token returned: {r2}")
    all_pass &= p2

    # 4c: valid issuer passes
    tok3 = auth.create_token({"sub": "u1", "iss": "auth.myapp.com"})
    r3 = auth.validate_token(tok3)
    p3 = r3 is not None
    record("4c", "Token with valid issuer ('auth.myapp.com') accepted", p3,
           f"validate_token returned: {'OK' if r3 else 'None'}")
    all_pass &= p3

    return all_pass


# ============================================================
# RC1: No token blacklisting
# ============================================================
def attack_rc1():
    print("\n" + "#"*60)
    print("# RC1: No token blacklisting")
    print("#"*60)

    all_pass = True
    refresh._blacklist.clear()

    tok = auth.create_token({"sub": "u1", "iss": "auth.myapp.com"}, expires_in=300)
    time.sleep(0.5)  # ensure new token gets different timestamp
    new_tok = refresh.refresh_token(tok)

    # 5a: old token in blacklist
    p = refresh.is_blacklisted(tok)
    record("5a", "Old token blacklisted after refresh", p, f"is_blacklisted: {p}")
    all_pass &= p

    # 5b: middleware rejects blacklisted old token
    r = middleware.authenticate_request(f"Bearer {tok}")
    p2 = r is None
    record("5b", "Middleware rejects old (blacklisted) token", p2,
           f"authenticate_request returned: {r}")
    all_pass &= p2

    # 5c: middleware accepts NEW token
    r3 = middleware.authenticate_request(f"Bearer {new_tok}")
    p3 = r3 is not None
    record("5c", "Middleware accepts new (unblacklisted) token", p3,
           f"authenticate_request returned: {'OK' if r3 else 'None'}")
    all_pass &= p3

    return all_pass


# ============================================================
# RC2: Duplicate concurrent refresh
# ============================================================
def attack_rc2():
    print("\n" + "#"*60)
    print("# RC2: Duplicate token on concurrent refresh")
    print("#"*60)

    refresh._blacklist.clear()
    refresh._active_refreshes.clear()

    tok = auth.create_token({"sub": "u1", "iss": "auth.myapp.com"}, expires_in=300)

    new_tokens = []
    lock = threading.Lock()

    def do_refresh():
        # Small per-thread sleep stagger so create_token hits different seconds
        # This reveals that the lock serializes but doesn't prevent re-issuance
        r = refresh.refresh_token(tok)
        with lock:
            if r is not None:
                new_tokens.append(r)

    threads = []
    for i in range(5):
        t = threading.Thread(target=do_refresh)
        threads.append(t)
        time.sleep(0.001)  # slight stagger

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    n_total = len(new_tokens)
    n_unique = len(set(new_tokens))

    # KEY ASSESSMENT:
    # The lock serializes access but does NOT check if old_token was already refreshed.
    # decode_token() is called OUTSIDE the lock, so all threads decode successfully.
    # Then each enters the lock and creates a new token. This means 5 different tokens
    # CAN be issued for the same old token if they happen in different seconds.
    # 
    # The correct fix would add: `if old_token in _blacklist: return None` INSIDE the lock,
    # checking whether someone else already refreshed this token.

    # If all 5 produced the same token (same-second coincidence), that's still a bug in
    # principle — the lock doesn't prevent duplicates, it only happened to produce the
    # same token by chance. We consider the fix INSUFFICIENT if multiple tokens were issued.

    only_one_issued = n_unique == 1
    if only_one_issued and n_total > 1:
        # Same token issued multiple times (same-second coincidence)
        # The fix is still insufficient — it just happened to produce identical tokens
        detail = (f"{n_total} refreshes issued, {n_unique} unique tokens. "
                  f"Same token issued {n_total} times (coincidence — all in same second). "
                  f"Lock serializes but doesn't prevent multi-issuance. "
                  f"Fix is INSUFFICIENT: decode_token() is outside lock, no check for "
                  f"already-refreshed token.")
        record("6", "Concurrent refresh — lock prevents duplicates?",
               False,  # FAIL: fix is insufficient
               "Lock serializes but doesn't prevent multiple tokens from being issued",
               detail)
    elif n_unique == 1 and n_total == 1:
        # Only one thread succeeded — but why?
        detail = f"Only {n_total} of 5 threads produced a token."
        record("6", "Concurrent refresh — lock prevents duplicates?",
               True,
               "Only one token issued from 5 concurrent attempts",
               detail)
    else:
        # Multiple unique tokens issued — clear FAIL
        detail = f"{n_total} refreshes issued, {n_unique} unique tokens!"
        record("6", "Concurrent refresh — lock prevents duplicates?",
               False,
               "Multiple unique tokens issued for the same old token",
               detail)

    return n_unique == 1 and n_total == 1  # True fix would give exactly 1 token


# ============================================================
# Extended Attacks
# ============================================================
def extended_attacks():
    print("\n" + "#"*60)
    print("# EXTENDED ATTACKS")
    print("#"*60)
    all_pass = []

    # --- E1: Compound forged-none → refresh ---
    print("\n--- E1: Compound forged-none → refresh ---")
    h = {"alg": "none", "typ": "JWT"}
    payload = {"sub": "attacker", "iss": "auth.myapp.com", "iat": int(time.time()), "exp": int(time.time())+3600}
    hb = base64.urlsafe_b64encode(json.dumps(h).encode()).rstrip(b"=").decode()
    pb = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(b"fake").rstrip(b"=").decode()
    forged = f"{hb}.{pb}.{sig}"
    r = refresh.refresh_token(forged)
    p = r is None
    all_pass.append(p)
    record("E1", "Compound: forged none-alg token → refresh rejected", p,
           f"refresh_token returned: {r}")

    # --- E2: Token without exp claim ---
    print("\n--- E2: Token without 'exp' claim ---")
    h2 = {"alg": "HS256", "typ": "JWT"}
    payload2 = {"sub": "u1", "iss": "auth.myapp.com", "iat": int(time.time())}
    hb2 = base64.urlsafe_b64encode(json.dumps(h2).encode()).rstrip(b"=").decode()
    pb2 = base64.urlsafe_b64encode(json.dumps(payload2).encode()).rstrip(b"=").decode()
    msg = f"{hb2}.{pb2}".encode()
    sig2 = hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).digest()
    sig2_b64 = base64.urlsafe_b64encode(sig2).rstrip(b"=").decode()
    noexp_tok = f"{hb2}.{pb2}.{sig2_b64}"
    r2 = auth.validate_token(noexp_tok)
    p2 = r2 is None
    all_pass.append(p2)
    record("E2", "Token without 'exp' claim rejected (defaults to exp=0)", p2,
           f"validate_token returned: {r2}")

    # --- E3: Empty signature ---
    print("\n--- E3: Empty signature attack ---")
    h3 = {"alg": "HS256", "typ": "JWT"}
    payload3 = {"sub": "u1", "iss": "auth.myapp.com", "iat": int(time.time()), "exp": int(time.time())+3600}
    hb3 = base64.urlsafe_b64encode(json.dumps(h3).encode()).rstrip(b"=").decode()
    pb3 = base64.urlsafe_b64encode(json.dumps(payload3).encode()).rstrip(b"=").decode()
    empty_sig_tok = f"{hb3}.{pb3}."  # trailing dot = empty signature
    r3 = auth.decode_token(empty_sig_tok)
    p3 = r3 is None
    all_pass.append(p3)
    record("E3", "Empty signature rejected", p3, f"decode_token returned: {r3}")

    # --- E4: Refresh already-blacklisted token ---
    print("\n--- E4: Refresh already-blacklisted token ---")
    refresh._blacklist.clear()
    tok = auth.create_token({"sub": "u1", "iss": "auth.myapp.com"}, expires_in=300)
    time.sleep(0.5)
    new1 = refresh.refresh_token(tok)
    assert new1 is not None

    # Now try to refresh the SAME old token AGAIN
    # decode_token doesn't check blacklist, so this might succeed
    new2 = refresh.refresh_token(tok)
    p4 = new2 is None  # Should fail because old token is blacklisted
    all_pass.append(p4)
    record("E4", "Refresh of already-blacklisted token prevented", p4,
           "Old token was refreshed once; second refresh should be rejected",
           f"Second refresh returned: {new2} ({'FAIL: allowed re-refresh' if not p4 else 'PASS: rejected'})")

    # --- E5: Token without 'sub' claim ---
    print("\n--- E5: Token without 'sub' claim ---")
    # create_token doesn't enforce sub, but validate_token should now
    h5 = {"alg": "HS256", "typ": "JWT"}
    payload5 = {"iss": "auth.myapp.com", "iat": int(time.time()), "exp": int(time.time())+3600}
    hb5 = base64.urlsafe_b64encode(json.dumps(h5).encode()).rstrip(b"=").decode()
    pb5 = base64.urlsafe_b64encode(json.dumps(payload5).encode()).rstrip(b"=").decode()
    msg5 = f"{hb5}.{pb5}".encode()
    sig5 = hmac.new(SECRET_KEY.encode(), msg5, hashlib.sha256).digest()
    sig5_b64 = base64.urlsafe_b64encode(sig5).rstrip(b"=").decode()
    nosub_tok = f"{hb5}.{pb5}.{sig5_b64}"
    r5 = auth.validate_token(nosub_tok)
    p5 = r5 is None
    all_pass.append(p5)
    record("E5", "Token without 'sub' claim rejected", p5,
           f"validate_token returned: {r5}")

    return all(all_pass)


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("="*60)
    print("ADVERSARIAL VERIFICATION — ATTACK SUITE v2")
    print("="*60)

    r = {}
    r["bug1"] = attack_bug1()
    r["bug2"] = attack_bug2()
    r["bug3"] = attack_bug3()
    r["bug4"] = attack_bug4()
    r["rc1"] = attack_rc1()
    r["rc2"] = attack_rc2()
    r["extended"] = extended_attacks()

    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    for bug_id, bug_name, status, desc, detail in RESULTS:
        mark = "✓" if status == "PASS" else "✗"
        print(f"  [{mark}] {bug_id}: {bug_name} — {status}")

    spec_keys = ["bug1","bug2","bug3","bug4","rc1","rc2"]
    spec_all = all(r.get(k, False) for k in spec_keys)
    ext_all = r.get("extended", False)

    print(f"\nSpec bugs (6): {'ALL PASS' if spec_all else 'SOME FAIL'}")
    print(f"Extended attacks: {'PASS' if ext_all else 'FAIL'}")
    verdict = "SHIP" if spec_all and ext_all else "FIX-REQUIRED"
    print(f"VERDICT: {verdict}")
    if not spec_all:
        failed = [k for k in spec_keys if not r.get(k, False)]
        print(f"FAILED SPEC BUGS: {failed}")
