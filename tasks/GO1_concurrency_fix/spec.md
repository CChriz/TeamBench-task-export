# GO1: Concurrency Fix (Full Specification — Planner Only)

## Overview

The workspace contains a Go concurrent job processor using a worker pool pattern. The program has **three real concurrency bugs** that must be identified and fixed. The executor only sees the brief; the planner has this full analysis.

## Program Structure

`main.go` implements a `JobProcessor` struct with:
- A worker pool of N goroutines
- A `stats` map tracking per-worker completion counts
- Two mutexes: `mu1` (protects the job queue) and `mu2` (protects the stats map)
- A `results` channel for collecting completed job results
- A `processJobs(ctx)` method that orchestrates the pool

## Bug Analysis

### Bug 1 — Data Race on Shared Statistics

**Location:** `worker()` function

**Symptom:** Running `go test -race` reports a data race on the stats map. The program may also panic under concurrent execution.

**Requirement:** The statistics tracking structure shared among worker goroutines must be protected against concurrent access. All reads and writes to this shared state from worker goroutines must be properly synchronized so that no two goroutines can modify it simultaneously. The final statistics must accurately reflect the true number of jobs completed by each worker.

### Bug 2 — Goroutine Leak Under Cancellation

**Location:** `processJobs()` and `worker()` functions

**Symptom:** After context cancellation, one or more goroutines remain blocked and never exit. Under certain scheduling conditions the program hangs.

**Requirement:** When the context is cancelled, all goroutines must be able to exit cleanly without blocking forever. Any goroutine that has produced a result must be able to complete its send operation or be unblocked through an alternative mechanism. The program must not leak goroutines after `processJobs` returns.

### Bug 3 — Deadlock via Inconsistent Lock Ordering

**Location:** The two functions that acquire both mutexes (`mu1` and `mu2`)

**Symptom:** The program deadlocks non-deterministically; the Go runtime prints `all goroutines are asleep - deadlock!`. The bug may not appear on every run, making it appear intermittent.

**Requirement:** Whenever multiple locks must be acquired together, the acquisition order must be identical across all code paths. Inconsistent ordering between two or more functions that each acquire both locks will eventually cause a deadlock. The fix must establish and consistently enforce a single canonical lock acquisition order.

## Expected Behavior After Fix

- `go build ./...` succeeds
- `go vet ./...` produces no warnings
- `go test -race -count=1 -timeout 30s ./...` passes with zero races detected
- `go run .` completes within 10 seconds and prints "All 10 jobs completed"

## Acceptance Criteria

1. No data races detected by the Go race detector
2. No goroutine leaks (program exits cleanly)
3. No deadlocks (program never hangs)
4. All three test cases in `main_test.go` pass
5. Shared statistics state is protected by synchronization in the worker function
6. Lock acquisition order is consistent across all functions that acquire multiple locks
7. The results channel or cancellation path is implemented such that goroutines cannot block indefinitely
