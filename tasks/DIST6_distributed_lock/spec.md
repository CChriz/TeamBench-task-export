# DIST6: Distributed Lock

## Goal

A Python implementation of a Redis-style distributed lock has 4 correctness
bugs that cause data corruption under real-world conditions (GC pauses, network
delays, concurrent access). Fix all bugs while keeping existing tests green.

## Requirements

1. Fix all 4 bugs in `distributed_lock.py`
2. All existing tests must continue to pass: `pytest tests/`
3. The lock must be safe under GC pauses, network delays, and concurrent clients

## Bug 1: No Fencing Token

The `acquire()` method returns `True`/`False` but does not return a fencing
token (monotonically increasing integer). Without a fencing token, a client
that experiences a GC pause cannot prove it still holds the lock when it
resumes. A second client may have acquired and released the lock during the
pause, and the first client's writes corrupt shared state.

Fix: `acquire()` must return a fencing token (or `None` on failure). The token
must be a monotonically increasing integer stored alongside the lock. Protected
resources should reject operations with stale fencing tokens.

## Bug 2: Stale TTL Calculation

The `acquire()` method captures `start_time = time.time()` at the beginning,
then sets the lock with `ttl = start_time + lock_timeout`. If the network
round-trip to the backend takes significant time, the actual TTL remaining
after the lock is set is shorter than expected. Under high latency, the lock
may expire before the client finishes its critical section.

Fix: capture the time AFTER the lock is successfully set, or subtract the
elapsed time from the TTL.

## Bug 3: Fixed Retry Delay

When `acquire()` fails due to contention, it retries after a fixed delay
(e.g., 100ms). Under high contention, multiple clients retry simultaneously,
creating thundering herd. The retry should use exponential backoff with jitter.

Fix: replace fixed delay with exponential backoff (e.g., `base * 2^attempt`)
plus random jitter.

## Bug 4: Release Without Ownership Check

The `release()` method deletes the lock key without checking whether the
calling client is the current lock holder. If Client A's lock expires, Client B
acquires it, then Client A calls `release()`, it deletes Client B's lock.

Fix: store the owner identity with the lock and only delete if the caller
matches the current owner.

## Supporting Files

- `distributed_lock.py` — lock implementation (4 bugs)
- `mock_redis.py` — simulated Redis backend for testing
- `tests/test_lock.py` — existing tests (must all pass)
- `config.py` — lock configuration (TTL, retry settings, node names)
