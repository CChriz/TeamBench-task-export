"""
Parameterized generator for GO1: Concurrency Fix.

Each seed produces:
  - Different domain (job processor / request handler / message broker /
    task scheduler / event dispatcher)
  - Different struct/type/function names matching the domain
  - Different number of workers (3-8)
  - Different number of items to process (8-20)
  - Same 3 bug TYPES (data race, goroutine leak, deadlock) with matching names

The 3 bugs are always:
  1. Data race: worker writes to shared stats map without holding mu2
  2. Goroutine leak: results channel is unbuffered, workers block after ctx cancel
  3. Deadlock: addItem() and getStats() acquire mu1+mu2 in opposite order

Generated Go code uses only standard library and MUST compile with `go build`.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Domain configurations:
# (domain_label, item_type, result_type, processor_type, worker_verb,
#  item_noun, result_noun, queue_field, verb_past)
DOMAIN_CONFIGS = [
    {
        "domain": "job processor",
        "Item": "Job",
        "Result": "Result",
        "Processor": "JobProcessor",
        "Constructor": "NewProcessor",
        "add_method": "addJob",
        "process_method": "processJobs",
        "item_field": "Payload",
        "item_field_type": "string",
        "result_output_field": "Output",
        "result_output_type": "string",
        "result_id_field": "JobID",
        "result_worker_field": "WorkerID",
        "queue_field": "queue",
        "stats_comment": "per-worker completion counts",
        "worker_verb": "done",
        "print_msg": "All %d jobs completed",
        "main_count_var": "jobs",
        "module": "jobprocessor",
    },
    {
        "domain": "request handler",
        "Item": "Request",
        "Result": "Response",
        "Processor": "RequestHandler",
        "Constructor": "NewHandler",
        "add_method": "addRequest",
        "process_method": "handleRequests",
        "item_field": "Path",
        "item_field_type": "string",
        "result_output_field": "Body",
        "result_output_type": "string",
        "result_id_field": "RequestID",
        "result_worker_field": "WorkerID",
        "queue_field": "pending",
        "stats_comment": "per-worker request counts",
        "worker_verb": "handled",
        "print_msg": "All %d requests handled",
        "main_count_var": "requests",
        "module": "requesthandler",
    },
    {
        "domain": "message broker",
        "Item": "Message",
        "Result": "Ack",
        "Processor": "MessageBroker",
        "Constructor": "NewBroker",
        "add_method": "enqueue",
        "process_method": "processMessages",
        "item_field": "Topic",
        "item_field_type": "string",
        "result_output_field": "Status",
        "result_output_type": "string",
        "result_id_field": "MsgID",
        "result_worker_field": "ConsumerID",
        "queue_field": "inbox",
        "stats_comment": "per-consumer ack counts",
        "worker_verb": "acked",
        "print_msg": "All %d messages processed",
        "main_count_var": "messages",
        "module": "messagebroker",
    },
    {
        "domain": "task scheduler",
        "Item": "Task",
        "Result": "TaskResult",
        "Processor": "Scheduler",
        "Constructor": "NewScheduler",
        "add_method": "scheduleTask",
        "process_method": "runScheduled",
        "item_field": "Name",
        "item_field_type": "string",
        "result_output_field": "Summary",
        "result_output_type": "string",
        "result_id_field": "TaskID",
        "result_worker_field": "RunnerID",
        "queue_field": "backlog",
        "stats_comment": "per-runner task counts",
        "worker_verb": "completed",
        "print_msg": "All %d tasks completed",
        "main_count_var": "tasks",
        "module": "taskscheduler",
    },
    {
        "domain": "event dispatcher",
        "Item": "Event",
        "Result": "Dispatch",
        "Processor": "Dispatcher",
        "Constructor": "NewDispatcher",
        "add_method": "emit",
        "process_method": "dispatch",
        "item_field": "Type",
        "item_field_type": "string",
        "result_output_field": "Log",
        "result_output_type": "string",
        "result_id_field": "EventID",
        "result_worker_field": "HandlerID",
        "queue_field": "events",
        "stats_comment": "per-handler dispatch counts",
        "worker_verb": "dispatched",
        "print_msg": "All %d events dispatched",
        "main_count_var": "events",
        "module": "eventdispatcher",
    },
]


class Generator(TaskGenerator):
    task_id = "GO1_concurrency_fix"
    domain = "go"
    difficulty = "hard"
    languages = ["go"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        cfg = rng.choice(DOMAIN_CONFIGS)
        num_workers = rng.randint(3, 8)
        num_items = rng.randint(8, 20)

        main_go = self._gen_main_go(cfg, num_workers, num_items)
        test_go = self._gen_test_go(cfg, num_workers, num_items)
        go_mod = self._gen_go_mod(cfg["module"])

        workspace_files = {
            "main.go": main_go,
            "main_test.go": test_go,
            "go.mod": go_mod,
        }

        expected = {
            "domain": cfg["domain"],
            "module": cfg["module"],
            "Item": cfg["Item"],
            "Result": cfg["Result"],
            "Processor": cfg["Processor"],
            "num_workers": num_workers,
            "num_items": num_items,
            "print_msg": cfg["print_msg"] % num_items,
            "bugs": [
                f"Bug 1 (data race): worker writes p.stats[id]++ without holding mu2",
                f"Bug 2 (goroutine leak): results channel is unbuffered, workers block on ctx cancel",
                f"Bug 3 (deadlock): {cfg['add_method']} acquires mu1 then mu2, getStats acquires mu2 then mu1",
            ],
            "fixes": [
                "Fix 1: wrap p.stats[id]++ in mu2.Lock() / mu2.Unlock()",
                "Fix 2: make results channel buffered with capacity = len(items)",
                "Fix 3: make getStats acquire mu1 then mu2 (same order as add method)",
            ],
        }

        spec_md = self._gen_spec(cfg, num_workers, num_items)
        brief_md = self._gen_brief(cfg, num_workers, num_items)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── File generators ────────────────────────────────────────────────────

    def _gen_main_go(self, cfg: dict, num_workers: int, num_items: int) -> str:
        Item = cfg["Item"]
        Result = cfg["Result"]
        Proc = cfg["Processor"]
        Ctor = cfg["Constructor"]
        add = cfg["add_method"]
        process = cfg["process_method"]
        item_field = cfg["item_field"]
        item_field_type = cfg["item_field_type"]
        out_field = cfg["result_output_field"]
        out_type = cfg["result_output_type"]
        rid_field = cfg["result_id_field"]
        rwid_field = cfg["result_worker_field"]
        queue_field = cfg["queue_field"]
        stats_comment = cfg["stats_comment"]
        worker_verb = cfg["worker_verb"]
        print_msg = cfg["print_msg"]
        main_count_var = cfg["main_count_var"]

        # item_payload varies by domain
        item_payload_field = item_field
        item_format_str = f"payload-%d"

        return f"""package main

import (
\t"context"
\t"fmt"
\t"sync"
\t"time"
)

// {Item} represents a unit of work.
type {Item} struct {{
\tID      int
\t{item_payload_field} {item_field_type}
}}

// {Result} holds the outcome of a processed {Item.lower()}.
type {Result} struct {{
\t{rid_field}    int
\t{rwid_field} int
\t{out_field}   {out_type}
}}

// {Proc} manages a pool of workers that process {Item.lower()}s concurrently.
type {Proc} struct {{
\tworkers int
\t{queue_field}   []{Item}
\tstats   map[int]int // {stats_comment}
\tmu1     sync.Mutex  // protects {queue_field}
\tmu2     sync.Mutex  // protects stats
}}

// {Ctor} creates a {Proc} with the given number of workers.
func {Ctor}(workers int) *{Proc} {{
\treturn &{Proc}{{
\t\tworkers: workers,
\t\t{queue_field}:   make([]{Item}, 0),
\t\tstats:   make(map[int]int),
\t}}
}}

// {add} appends a {Item.lower()} to the {queue_field} and updates the stats entry for bookkeeping.
// BUG 3: acquires mu1 then mu2 — opposite order from getStats (mu2 then mu1).
func (p *{Proc}) {add}({Item.lower()} {Item}) {{
\tp.mu1.Lock()
\tp.{queue_field} = append(p.{queue_field}, {Item.lower()})
\tp.mu2.Lock()
\t// initialise stats slot so workers don't have to create it
\tif _, ok := p.stats[{Item.lower()}.ID%p.workers]; !ok {{
\t\tp.stats[{Item.lower()}.ID%p.workers] = 0
\t}}
\tp.mu2.Unlock()
\tp.mu1.Unlock()
}}

// getStats returns a snapshot of per-worker completion counts.
// BUG 3: acquires mu2 then mu1 — opposite order from {add} (mu1 then mu2).
func (p *{Proc}) getStats() map[int]int {{
\tp.mu2.Lock()
\tdefer p.mu2.Unlock()
\tp.mu1.Lock()
\tdefer p.mu1.Unlock()

\tsnapshot := make(map[int]int, len(p.stats))
\tfor k, v := range p.stats {{
\t\tsnapshot[k] = v
\t}}
\treturn snapshot
}}

// worker pulls {Item.lower()}s from the {Item.lower()}s channel and sends results to results channel.
// BUG 1: writes p.stats[id]++ without holding mu2 — data race with other workers.
func (p *{Proc}) worker(id int, {Item.lower()}s <-chan {Item}, results chan<- {Result}) {{
\tfor {Item.lower()} := range {Item.lower()}s {{
\t\t// Simulate work.
\t\ttime.Sleep(time.Millisecond * 10)

\t\t// BUG 1: unsynchronised write to shared map.
\t\tp.stats[id]++

\t\tresults <- {Result}{{
\t\t\t{rid_field}:    {Item.lower()}.ID,
\t\t\t{rwid_field}: id,
\t\t\t{out_field}:   fmt.Sprintf("{Item.lower()}-%d {worker_verb} by worker-%d", {Item.lower()}.ID, id),
\t\t}}
\t}}
}}

// {process} distributes queued {Item.lower()}s across workers and collects results.
// BUG 2: results channel is unbuffered; if ctx is cancelled the receive loop
// exits early, leaving workers blocked forever on "results <- result".
func (p *{Proc}) {process}(ctx context.Context) ([]{Result}, error) {{
\tp.mu1.Lock()
\t{Item.lower()}s := make([]{Item}, len(p.{queue_field}))
\tcopy({Item.lower()}s, p.{queue_field})
\tp.mu1.Unlock()

\t{Item.lower()}Ch := make(chan {Item}, len({Item.lower()}s))
\t// BUG 2: unbuffered — senders block if receiver stops early.
\tresults := make(chan {Result})

\tvar wg sync.WaitGroup
\tfor i := 0; i < p.workers; i++ {{
\t\twg.Add(1)
\t\tgo func(id int) {{
\t\t\tdefer wg.Done()
\t\t\tp.worker(id, {Item.lower()}Ch, results)
\t\t}}(i)
\t}}

\t// Feed {Item.lower()}s.
\tgo func() {{
\t\tfor _, j := range {Item.lower()}s {{
\t\t\t{Item.lower()}Ch <- j
\t\t}}
\t\tclose({Item.lower()}Ch)
\t}}()

\t// Close results once all workers finish.
\tgo func() {{
\t\twg.Wait()
\t\tclose(results)
\t}}()

\tvar collected []{Result}
\tfor {{
\t\tselect {{
\t\tcase res, ok := <-results:
\t\t\tif !ok {{
\t\t\t\treturn collected, nil
\t\t\t}}
\t\t\tcollected = append(collected, res)
\t\tcase <-ctx.Done():
\t\t\t// BUG 2: returns immediately, leaving workers blocked on results<-result.
\t\t\treturn collected, ctx.Err()
\t\t}}
\t}}
}}

func main() {{
\tctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
\tdefer cancel()

\tp := {Ctor}({num_workers})

\tfor i := 1; i <= {num_items}; i++ {{
\t\tp.{add}({Item}{{ID: i, {item_payload_field}: fmt.Sprintf("{item_format_str}", i)}})
\t}}

\t{main_count_var}, err := p.{process}(ctx)
\tif err != nil {{
\t\tfmt.Printf("processing error: %v\\n", err)
\t\treturn
\t}}

\tfmt.Printf("{print_msg}\\n", len({main_count_var}))

\tstats := p.getStats()
\tfor workerID, count := range stats {{
\t\tfmt.Printf("Worker %d: %d {Item.lower()}s\\n", workerID, count)
\t}}
}}
"""

    def _gen_test_go(self, cfg: dict, num_workers: int, num_items: int) -> str:
        Item = cfg["Item"]
        Result = cfg["Result"]
        Proc = cfg["Processor"]
        Ctor = cfg["Constructor"]
        add = cfg["add_method"]
        process = cfg["process_method"]

        # Use a fixed concurrency test worker count of 4
        conc_workers = min(num_workers, 4)
        # Context cancellation test uses more items to ensure workers are blocked
        cancel_items = max(num_items * 2, 20)

        return f"""package main

import (
\t"context"
\t"testing"
\t"time"
)

// TestProcess{Result}s verifies that all {num_items} {Item.lower()}s complete successfully.
func TestProcess{Result}s(t *testing.T) {{
\tp := {Ctor}({num_workers})
\tfor i := 1; i <= {num_items}; i++ {{
\t\tp.{add}({Item}{{ID: i, {cfg["item_field"]}: "test"}})
\t}}

\tctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
\tdefer cancel()

\tresults, err := p.{process}(ctx)
\tif err != nil {{
\t\tt.Fatalf("{process} returned error: %v", err)
\t}}
\tif len(results) != {num_items} {{
\t\tt.Fatalf("expected {num_items} results, got %d", len(results))
\t}}
}}

// TestConcurrentAccess hammers {add} and getStats from multiple goroutines
// to surface data races and lock-ordering deadlocks.
func TestConcurrentAccess(t *testing.T) {{
\tp := {Ctor}({conc_workers})

\tdone := make(chan struct{{}})
\tgo func() {{
\t\tfor i := 0; i < 50; i++ {{
\t\t\tp.{add}({Item}{{ID: i, {cfg["item_field"]}: "concurrent"}})
\t\t}}
\t\tclose(done)
\t}}()

\tgo func() {{
\t\tfor i := 0; i < 50; i++ {{
\t\t\t_ = p.getStats()
\t\t}}
\t}}()

\tselect {{
\tcase <-done:
\t\t// ok
\tcase <-time.After(5 * time.Second):
\t\tt.Fatal("TestConcurrentAccess timed out — likely deadlock")
\t}}
}}

// TestContextCancellation verifies that cancelling the context does not leak
// goroutines — the program must not hang after the test function returns.
// With the buggy unbuffered channel, workers block forever on "results <- result"
// once the receiver exits, causing this test to time out.
func TestContextCancellation(t *testing.T) {{
\tp := {Ctor}({num_workers})
\t// Enough {Item.lower()}s that workers will have computed results and be blocked
\t// on the unbuffered send when we cancel.
\tfor i := 1; i <= {cancel_items}; i++ {{
\t\tp.{add}({Item}{{ID: i, {cfg["item_field"]}: "cancel-test"}})
\t}}

\tctx, cancel := context.WithCancel(context.Background())
\t// Let one batch of workers finish and queue up on the channel before cancel.
\tgo func() {{
\t\ttime.Sleep(15 * time.Millisecond)
\t\tcancel()
\t}}()

\tdone := make(chan struct{{}})
\tgo func() {{
\t\tp.{process}(ctx) //nolint:errcheck
\t\tclose(done)
\t}}()

\tselect {{
\tcase <-done:
\t\t// Good — returned without hanging.
\tcase <-time.After(5 * time.Second):
\t\tt.Fatal("TestContextCancellation timed out — goroutine leak suspected")
\t}}
}}
"""

    def _gen_go_mod(self, module: str) -> str:
        return f"""module {module}

go 1.21
"""

    def _gen_spec(self, cfg: dict, num_workers: int, num_items: int) -> str:
        domain = cfg["domain"]
        Item = cfg["Item"]
        Result = cfg["Result"]
        Proc = cfg["Processor"]
        add = cfg["add_method"]
        process = cfg["process_method"]
        queue_field = cfg["queue_field"]

        return f"""# GO1: Concurrency Fix (Full Specification — Planner Only)

## Overview

The workspace contains a Go concurrent {domain} using a worker pool pattern. The program has **three real concurrency bugs** that must be identified and fixed. The executor only sees the brief; the planner has this full analysis.

## Program Structure

`main.go` implements a `{Proc}` struct with:
- A worker pool of {num_workers} goroutines
- A `stats` map tracking per-worker completion counts
- Two mutexes: `mu1` (protects the {queue_field}) and `mu2` (protects the stats map)
- A `results` channel for collecting completed {Item.lower()} results
- A `{process}(ctx)` method that orchestrates the pool

## Bug Analysis

### Bug 1 — Data Race on Shared Statistics

**Location:** `worker()` function

**Symptom:** Running `go test -race` reports a data race on the stats map. The program may also panic under concurrent execution.

**Requirement:** The statistics tracking structure shared among worker goroutines must be protected against concurrent access. All reads and writes to this shared state from worker goroutines must be properly synchronized so that no two goroutines can modify it simultaneously. The final statistics must accurately reflect the true number of {Item.lower()}s completed by each worker.

### Bug 2 — Goroutine Leak Under Cancellation

**Location:** `{process}()` and `worker()` functions

**Symptom:** After context cancellation, one or more goroutines remain blocked and never exit. Under certain scheduling conditions the program hangs.

**Requirement:** When the context is cancelled, all goroutines must be able to exit cleanly without blocking forever. Any goroutine that has produced a result must be able to complete its send operation or be unblocked through an alternative mechanism. The program must not leak goroutines after `{process}` returns.

### Bug 3 — Deadlock via Inconsistent Lock Ordering

**Location:** The two functions that acquire both mutexes (`{add}` and `getStats`)

**Symptom:** The program deadlocks non-deterministically; the Go runtime prints `all goroutines are asleep - deadlock!`. The bug may not appear on every run.

**Requirement:** Whenever multiple locks must be acquired together, the acquisition order must be identical across all code paths. `{add}` acquires mu1 then mu2; `getStats` acquires mu2 then mu1 — this inversion causes deadlock. The fix must establish and consistently enforce a single canonical lock acquisition order.

## Expected Behavior After Fix

- `go build ./...` succeeds
- `go vet ./...` produces no warnings
- `go test -race -count=1 -timeout 30s ./...` passes with zero races detected
- `go run .` completes within 10 seconds and prints "All {num_items} {Item.lower()}s completed"

## Acceptance Criteria

1. No data races detected by the Go race detector
2. No goroutine leaks (program exits cleanly)
3. No deadlocks (program never hangs)
4. All three test cases in `main_test.go` pass
5. Shared statistics state is protected by synchronization in the worker function
6. Lock acquisition order is consistent across all functions that acquire multiple locks
7. The results channel or cancellation path is implemented such that goroutines cannot block indefinitely
"""

    def _gen_brief(self, cfg: dict, num_workers: int, num_items: int) -> str:
        domain = cfg["domain"]
        Item = cfg["Item"]
        Proc = cfg["Processor"]

        return f"""# GO1: Concurrency Fix (Brief)

Fix 3 concurrency bugs in a Go {domain} (`{Proc}`).
The program uses a worker pool of {num_workers} goroutines to process {num_items} {Item.lower()}s.

Run: `go test -race -count=1 -timeout 30s ./...`
All 3 tests must pass with zero data races.

Files to fix: `main.go`
Do NOT modify `main_test.go`.
"""
