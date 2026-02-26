"""
Parameterized generator for GO2: Race Condition.

Each seed produces a different race pattern from the 5 available patterns:
  1. shared_map    – multiple goroutines write to a map without synchronization
  2. counter       – unsynchronized shared integer counter (classic data race)
  3. channel_close – multiple goroutines close the same channel (panic)
  4. slice_append  – concurrent appends to a shared slice without protection
  5. lazy_init     – double-checked locking without atomic or sync.Once

Domain configurations vary struct/function names so each instance reads as a
different program even when the underlying race pattern is the same.

TNI Pattern:
  D – Cross-System Contract: goroutine interaction contracts hidden in spec
  A – Hidden Constraints: specific sync primitives required by spec, not brief

Workspace files per instance:
  main.go       – buggy concurrent program
  go.mod        – module declaration
  race_test.go  – test that surfaces the race (run with -race or stress test)

Expected keys:
  race_type        – one of the 5 pattern names above
  fix_primitives   – list of primitives needed (mutex / channel / atomic / sync.Once)
  affected_functions – list of function names that must be modified
  domain           – human-readable domain label
  module           – Go module name
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ---------------------------------------------------------------------------
# Domain configurations
# Each domain uses consistent naming so the generated code is idiomatic.
# ---------------------------------------------------------------------------
DOMAIN_CONFIGS = [
    {
        "domain": "metrics collector",
        "Processor": "MetricsCollector",
        "Constructor": "NewMetricsCollector",
        "module": "metricscollector",
        "item": "metric",
        "Item": "Metric",
        "item_field": "Name",
        "item_field_type": "string",
        "item_value_field": "Value",
        "item_value_type": "float64",
        "process_verb": "Record",
        "result_noun": "snapshot",
        "query_method": "Snapshot",
        "worker_method": "collectMetrics",
        "run_method": "Run",
    },
    {
        "domain": "cache manager",
        "Processor": "CacheManager",
        "Constructor": "NewCacheManager",
        "module": "cachemanager",
        "item": "entry",
        "Item": "Entry",
        "item_field": "Key",
        "item_field_type": "string",
        "item_value_field": "Data",
        "item_value_type": "string",
        "process_verb": "Store",
        "result_noun": "dump",
        "query_method": "Dump",
        "worker_method": "populateCache",
        "run_method": "Run",
    },
    {
        "domain": "request aggregator",
        "Processor": "RequestAggregator",
        "Constructor": "NewRequestAggregator",
        "module": "requestaggregator",
        "item": "request",
        "Item": "Request",
        "item_field": "Path",
        "item_field_type": "string",
        "item_value_field": "Body",
        "item_value_type": "string",
        "process_verb": "Aggregate",
        "result_noun": "summary",
        "query_method": "Summary",
        "worker_method": "aggregateRequests",
        "run_method": "Run",
    },
    {
        "domain": "event logger",
        "Processor": "EventLogger",
        "Constructor": "NewEventLogger",
        "module": "eventlogger",
        "item": "event",
        "Item": "Event",
        "item_field": "Tag",
        "item_field_type": "string",
        "item_value_field": "Payload",
        "item_value_type": "string",
        "process_verb": "Log",
        "result_noun": "log",
        "query_method": "GetLog",
        "worker_method": "logEvents",
        "run_method": "Run",
    },
    {
        "domain": "task tracker",
        "Processor": "TaskTracker",
        "Constructor": "NewTaskTracker",
        "module": "tasktracker",
        "item": "task",
        "Item": "Task",
        "item_field": "Label",
        "item_field_type": "string",
        "item_value_field": "Detail",
        "item_value_type": "string",
        "process_verb": "Track",
        "result_noun": "report",
        "query_method": "Report",
        "worker_method": "trackTasks",
        "run_method": "Run",
    },
]

# ---------------------------------------------------------------------------
# Race patterns
# Each entry describes the bug and what the fix requires.
# ---------------------------------------------------------------------------
RACE_PATTERNS = [
    {
        "race_type": "shared_map",
        "fix_primitives": ["mutex"],
        "description": "multiple goroutines write to a shared map without holding a mutex",
        "spec_symptom": (
            "Running `go test -race` reports a concurrent map read/write. "
            "The program may panic with 'concurrent map iteration and map write' "
            "or 'concurrent map writes'."
        ),
        "spec_requirement": (
            "All reads and writes to the shared map must be guarded by a single "
            "`sync.Mutex` (or `sync.RWMutex`). Writers must hold the exclusive lock; "
            "readers may use `RLock` if an RWMutex is chosen. The fix must ensure "
            "no two goroutines can modify the map simultaneously."
        ),
        "brief_symptom": "the shared data structure is sometimes corrupted or causes a panic",
    },
    {
        "race_type": "counter",
        "fix_primitives": ["atomic", "mutex"],
        "description": "multiple goroutines increment a shared integer counter without synchronization",
        "spec_symptom": (
            "Running `go test -race` reports a data race on the shared counter variable. "
            "The final count is non-deterministic and usually lower than expected."
        ),
        "spec_requirement": (
            "The shared counter must be incremented atomically. Use either "
            "`sync/atomic.AddInt64` (or `AddInt32`) or protect the increment with a "
            "`sync.Mutex`. The final count printed by `main` must exactly equal the "
            "total number of increments performed."
        ),
        "brief_symptom": "the final count is sometimes wrong after concurrent operations",
    },
    {
        "race_type": "channel_close",
        "fix_primitives": ["channel", "sync.Once"],
        "description": "multiple goroutines attempt to close the same channel, causing a panic",
        "spec_symptom": (
            "The program panics intermittently with 'close of closed channel'. "
            "Only one goroutine should close a channel; all others must signal "
            "through a different mechanism."
        ),
        "spec_requirement": (
            "Exactly one goroutine must be responsible for closing the done channel. "
            "Use `sync.Once` to guarantee the channel is closed at most once, or "
            "restructure so only the coordinator goroutine issues the close. "
            "Worker goroutines must signal completion without closing shared channels."
        ),
        "brief_symptom": "the program occasionally panics during shutdown",
    },
    {
        "race_type": "slice_append",
        "fix_primitives": ["mutex", "channel"],
        "description": "concurrent goroutines append to a shared slice without synchronization",
        "spec_symptom": (
            "Running `go test -race` reports a data race on the shared slice header. "
            "The slice may lose elements or corrupt its internal array under concurrent "
            "appends."
        ),
        "spec_requirement": (
            "All appends to the shared results slice must be serialized. Either protect "
            "the append with a `sync.Mutex`, or have workers send results through a "
            "buffered channel that a single collector goroutine drains. The final slice "
            "length must equal the total number of items processed."
        ),
        "brief_symptom": "results are sometimes missing or the final list has the wrong length",
    },
    {
        "race_type": "lazy_init",
        "fix_primitives": ["sync.Once", "atomic"],
        "description": "a singleton is initialised with an unsafe double-checked pattern causing a data race",
        "spec_symptom": (
            "Running `go test -race` reports a data race on the instance pointer check. "
            "Two goroutines may both observe nil and both initialise the singleton, "
            "leading to inconsistent state."
        ),
        "spec_requirement": (
            "Singleton initialisation must be race-free. Replace the double-checked "
            "locking pattern with `sync.Once.Do(...)`. The singleton instance must be "
            "initialised exactly once regardless of how many goroutines call the "
            "constructor concurrently."
        ),
        "brief_symptom": "the shared singleton is occasionally initialised more than once",
    },
]


class Generator(TaskGenerator):
    task_id = "GO2_race_condition"
    domain = "go"
    difficulty = "hard"
    languages = ["go", "python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        cfg = rng.choice(DOMAIN_CONFIGS)
        pattern = rng.choice(RACE_PATTERNS)
        num_workers = rng.randint(4, 10)
        num_items = rng.randint(10, 30)

        main_go = self._gen_main_go(cfg, pattern, num_workers, num_items)
        race_test_go = self._gen_race_test(cfg, pattern, num_workers, num_items)
        go_mod = self._gen_go_mod(cfg["module"])

        workspace_files = {
            "main.go": main_go,
            "race_test.go": race_test_go,
            "go.mod": go_mod,
        }

        expected = {
            "domain": cfg["domain"],
            "module": cfg["module"],
            "Processor": cfg["Processor"],
            "num_workers": num_workers,
            "num_items": num_items,
            "race_type": pattern["race_type"],
            "fix_primitives": pattern["fix_primitives"],
            "affected_functions": self._affected_functions(cfg, pattern),
        }

        spec_md = self._gen_spec(cfg, pattern, num_workers, num_items)
        brief_md = self._gen_brief(cfg, pattern, num_workers, num_items)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _affected_functions(self, cfg: dict, pattern: dict) -> list[str]:
        race = pattern["race_type"]
        if race == "shared_map":
            return [cfg["worker_method"], cfg["query_method"]]
        elif race == "counter":
            return [cfg["worker_method"], "main"]
        elif race == "channel_close":
            return [cfg["worker_method"], cfg["run_method"]]
        elif race == "slice_append":
            return [cfg["worker_method"], cfg["query_method"]]
        elif race == "lazy_init":
            return [cfg["Constructor"]]
        return [cfg["worker_method"]]

    # ── File generators ──────────────────────────────────────────────────────

    def _gen_go_mod(self, module: str) -> str:
        return f"module {module}\n\ngo 1.21\n"

    def _gen_main_go(self, cfg: dict, pattern: dict, num_workers: int, num_items: int) -> str:
        race = pattern["race_type"]
        if race == "shared_map":
            return self._main_shared_map(cfg, num_workers, num_items)
        elif race == "counter":
            return self._main_counter(cfg, num_workers, num_items)
        elif race == "channel_close":
            return self._main_channel_close(cfg, num_workers, num_items)
        elif race == "slice_append":
            return self._main_slice_append(cfg, num_workers, num_items)
        elif race == "lazy_init":
            return self._main_lazy_init(cfg, num_workers, num_items)
        return ""

    # ---- shared_map --------------------------------------------------------

    def _main_shared_map(self, cfg: dict, nw: int, ni: int) -> str:
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        Item = cfg["Item"]
        field = cfg["item_field"]
        val_field = cfg["item_value_field"]
        val_type = cfg["item_value_type"]
        query = cfg["query_method"]
        worker = cfg["worker_method"]
        run = cfg["run_method"]
        item = cfg["item"]
        domain = cfg["domain"]

        return f'''package main

import (
\t"fmt"
\t"sync"
\t"time"
)

// {Item} is a unit of data processed by the {domain}.
type {Item} struct {{
\t{field} string
\t{val_field} {val_type}
}}

// {P} processes {item}s concurrently and stores results in a shared map.
type {P} struct {{
\tworkers int
\t// BUG: store is written by multiple goroutines without a lock.
\tstore   map[string]{val_type}
}}

// {Ctor} initialises a new {P}.
func {Ctor}(workers int) *{P} {{
\treturn &{P}{{
\t\tworkers: workers,
\t\tstore:   make(map[string]{val_type}),
\t}}
}}

// {worker} is run by each worker goroutine and writes to the shared map.
// BUG: no mutex protects store — concurrent writes cause a data race.
func (p *{P}) {worker}(id int, items <-chan {Item}, wg *sync.WaitGroup) {{
\tdefer wg.Done()
\tfor it := range items {{
\t\ttime.Sleep(time.Millisecond) // simulate processing
\t\t// BUG: concurrent map write without synchronisation.
\t\tp.store[it.{field}] = it.{val_field}
\t}}
}}

// {query} returns a snapshot of all stored values.
// BUG: reads the map while workers may still be writing — data race.
func (p *{P}) {query}() map[string]{val_type} {{
\tsnap := make(map[string]{val_type}, len(p.store))
\tfor k, v := range p.store {{
\t\tsnap[k] = v
\t}}
\treturn snap
}}

// {run} fans out {item}s to {nw} worker goroutines and waits for completion.
func (p *{P}) {run}(items []{Item}) {{
\tch := make(chan {Item}, len(items))
\tvar wg sync.WaitGroup
\tfor i := 0; i < p.workers; i++ {{
\t\twg.Add(1)
\t\tgo p.{worker}(i, ch, &wg)
\t}}
\tfor _, it := range items {{
\t\tch <- it
\t}}
\tclose(ch)
\twg.Wait()
}}

func main() {{
\tp := {Ctor}({nw})
\titems := make([]{Item}, {ni})
\tfor i := range items {{
\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t}}
\tp.{run}(items)
\tsnap := p.{query}()
\tfmt.Printf("Stored %d {item}s\\n", len(snap))
}}
'''

    # ---- counter -----------------------------------------------------------

    def _main_counter(self, cfg: dict, nw: int, ni: int) -> str:
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        Item = cfg["Item"]
        field = cfg["item_field"]
        val_field = cfg["item_value_field"]
        val_type = cfg["item_value_type"]
        worker = cfg["worker_method"]
        run = cfg["run_method"]
        item = cfg["item"]
        domain = cfg["domain"]

        return f'''package main

import (
\t"fmt"
\t"sync"
\t"time"
)

// {Item} is a unit of data processed by the {domain}.
type {Item} struct {{
\t{field} string
\t{val_field} {val_type}
}}

// {P} processes {item}s and tracks a shared count of completed operations.
type {P} struct {{
\tworkers int
\t// BUG: count is written by multiple goroutines without synchronisation.
\tcount   int64
}}

// {Ctor} initialises a new {P}.
func {Ctor}(workers int) *{P} {{
\treturn &{P}{{workers: workers}}
}}

// {worker} processes {item}s and increments the shared counter.
// BUG: count++ is not atomic — concurrent increments lose updates.
func (p *{P}) {worker}(id int, items <-chan {Item}, wg *sync.WaitGroup) {{
\tdefer wg.Done()
\tfor range items {{
\t\ttime.Sleep(time.Millisecond) // simulate processing
\t\t// BUG: non-atomic read-modify-write on shared counter.
\t\tp.count++
\t}}
}}

// {run} fans out {item}s to {nw} worker goroutines and waits for completion.
func (p *{P}) {run}(items []{Item}) {{
\tch := make(chan {Item}, len(items))
\tvar wg sync.WaitGroup
\tfor i := 0; i < p.workers; i++ {{
\t\twg.Add(1)
\t\tgo p.{worker}(i, ch, &wg)
\t}}
\tfor _, it := range items {{
\t\tch <- it
\t}}
\tclose(ch)
\twg.Wait()
}}

func main() {{
\tp := {Ctor}({nw})
\titems := make([]{Item}, {ni})
\tfor i := range items {{
\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t}}
\tp.{run}(items)
\t// BUG: read of p.count races with any still-running goroutine.
\tfmt.Printf("Processed %d {item}s\\n", p.count)
}}
'''

    # ---- channel_close -----------------------------------------------------

    def _main_channel_close(self, cfg: dict, nw: int, ni: int) -> str:
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        Item = cfg["Item"]
        field = cfg["item_field"]
        val_field = cfg["item_value_field"]
        val_type = cfg["item_value_type"]
        worker = cfg["worker_method"]
        run = cfg["run_method"]
        item = cfg["item"]
        domain = cfg["domain"]

        return f'''package main

import (
\t"fmt"
\t"sync"
\t"time"
)

// {Item} is a unit of data processed by the {domain}.
type {Item} struct {{
\t{field} string
\t{val_field} {val_type}
}}

// {P} processes {item}s and signals completion through a shared done channel.
type {P} struct {{
\tworkers int
\tdone    chan struct{{}}
}}

// {Ctor} initialises a new {P}.
func {Ctor}(workers int) *{P} {{
\treturn &{P}{{
\t\tworkers: workers,
\t\tdone:    make(chan struct{{}}),
\t}}
}}

// {worker} processes {item}s and closes done when finished.
// BUG: every worker goroutine calls close(p.done), but a channel may only
// be closed once — subsequent closes panic with "close of closed channel".
func (p *{P}) {worker}(id int, items <-chan {Item}, wg *sync.WaitGroup) {{
\tdefer wg.Done()
\tfor range items {{
\t\ttime.Sleep(time.Millisecond) // simulate processing
\t}}
\t// BUG: multiple goroutines all close the same channel.
\tclose(p.done)
}}

// {run} fans out {item}s to {nw} worker goroutines and waits for the done signal.
func (p *{P}) {run}(items []{Item}) {{
\tch := make(chan {Item}, len(items))
\tvar wg sync.WaitGroup
\tfor i := 0; i < p.workers; i++ {{
\t\twg.Add(1)
\t\tgo p.{worker}(i, ch, &wg)
\t}}
\tfor _, it := range items {{
\t\tch <- it
\t}}
\tclose(ch)
\t<-p.done
\twg.Wait()
}}

func main() {{
\tp := {Ctor}({nw})
\titems := make([]{Item}, {ni})
\tfor i := range items {{
\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t}}
\tp.{run}(items)
\tfmt.Printf("Processed %d {item}s\\n", {ni})
}}
'''

    # ---- slice_append ------------------------------------------------------

    def _main_slice_append(self, cfg: dict, nw: int, ni: int) -> str:
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        Item = cfg["Item"]
        field = cfg["item_field"]
        val_field = cfg["item_value_field"]
        val_type = cfg["item_value_type"]
        query = cfg["query_method"]
        worker = cfg["worker_method"]
        run = cfg["run_method"]
        item = cfg["item"]
        domain = cfg["domain"]

        return f'''package main

import (
\t"fmt"
\t"sync"
\t"time"
)

// {Item} is a unit of data processed by the {domain}.
type {Item} struct {{
\t{field} string
\t{val_field} {val_type}
}}

// {P} processes {item}s and accumulates results in a shared slice.
type {P} struct {{
\tworkers int
\t// BUG: results is appended to by multiple goroutines without a lock.
\tresults []{Item}
}}

// {Ctor} initialises a new {P}.
func {Ctor}(workers int) *{P} {{
\treturn &{P}{{workers: workers}}
}}

// {worker} processes {item}s and appends to the shared results slice.
// BUG: concurrent appends to p.results cause a data race on the slice header.
func (p *{P}) {worker}(id int, items <-chan {Item}, wg *sync.WaitGroup) {{
\tdefer wg.Done()
\tfor it := range items {{
\t\ttime.Sleep(time.Millisecond) // simulate processing
\t\t// BUG: unsynchronised append — may corrupt slice internals.
\t\tp.results = append(p.results, it)
\t}}
}}

// {query} returns the collected results.
// BUG: reads p.results without synchronisation while workers may still append.
func (p *{P}) {query}() []{Item} {{
\tout := make([]{Item}, len(p.results))
\tcopy(out, p.results)
\treturn out
}}

// {run} fans out {item}s to {nw} worker goroutines and waits for completion.
func (p *{P}) {run}(items []{Item}) {{
\tch := make(chan {Item}, len(items))
\tvar wg sync.WaitGroup
\tfor i := 0; i < p.workers; i++ {{
\t\twg.Add(1)
\t\tgo p.{worker}(i, ch, &wg)
\t}}
\tfor _, it := range items {{
\t\tch <- it
\t}}
\tclose(ch)
\twg.Wait()
}}

func main() {{
\tp := {Ctor}({nw})
\titems := make([]{Item}, {ni})
\tfor i := range items {{
\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t}}
\tp.{run}(items)
\tres := p.{query}()
\tfmt.Printf("Collected %d {item}s\\n", len(res))
}}
'''

    # ---- lazy_init ---------------------------------------------------------

    def _main_lazy_init(self, cfg: dict, nw: int, ni: int) -> str:
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        Item = cfg["Item"]
        field = cfg["item_field"]
        val_field = cfg["item_value_field"]
        val_type = cfg["item_value_type"]
        run = cfg["run_method"]
        item = cfg["item"]
        domain = cfg["domain"]

        return f'''package main

import (
\t"fmt"
\t"sync"
\t"time"
)

// {Item} is a unit of data processed by the {domain}.
type {Item} struct {{
\t{field} string
\t{val_field} {val_type}
}}

// {P} is a lazily-initialised singleton that processes {item}s.
type {P} struct {{
\tworkers int
\tready   bool
}}

// global singleton state — initialised on first use.
var (
\tinstance *{P}
\tinstMu   sync.Mutex
)

// {Ctor} returns the singleton {P}, creating it if necessary.
// BUG: classic double-checked locking without atomics or sync.Once.
// The nil-check on instance races with the assignment inside the lock.
func {Ctor}(workers int) *{P} {{
\t// BUG: first read of instance is unsynchronised — data race with the write below.
\tif instance == nil {{
\t\tinstMu.Lock()
\t\tdefer instMu.Unlock()
\t\tif instance == nil {{
\t\t\ttime.Sleep(time.Millisecond) // simulate expensive init
\t\t\tinstance = &{P}{{workers: workers, ready: true}}
\t\t}}
\t}}
\treturn instance
}}

// {run} processes all {item}s using the singleton.
func (p *{P}) {run}(items []{Item}) {{
\tvar wg sync.WaitGroup
\tch := make(chan {Item}, len(items))
\tfor i := 0; i < p.workers; i++ {{
\t\twg.Add(1)
\t\tgo func() {{
\t\t\tdefer wg.Done()
\t\t\tfor range ch {{
\t\t\t\ttime.Sleep(time.Millisecond)
\t\t\t}}
\t\t}}()
\t}}
\tfor _, it := range items {{
\t\tch <- it
\t}}
\tclose(ch)
\twg.Wait()
}}

func main() {{
\tvar wg sync.WaitGroup
\t// Spawn goroutines that all try to obtain the singleton concurrently.
\tfor i := 0; i < {nw}; i++ {{
\t\twg.Add(1)
\t\tgo func() {{
\t\t\tdefer wg.Done()
\t\t\t// BUG: concurrent calls to {Ctor} race on the instance pointer.
\t\t\t{Ctor}({nw})
\t\t}}()
\t}}
\twg.Wait()
\tp := {Ctor}({nw})
\titems := make([]{Item}, {ni})
\tfor i := range items {{
\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t}}
\tp.{run}(items)
\tfmt.Printf("Processed %d {item}s\\n", {ni})
}}
'''

    # ── Test generators ──────────────────────────────────────────────────────

    def _gen_race_test(self, cfg: dict, pattern: dict, num_workers: int, num_items: int) -> str:
        race = pattern["race_type"]
        if race == "shared_map":
            return self._test_shared_map(cfg, num_workers, num_items)
        elif race == "counter":
            return self._test_counter(cfg, num_workers, num_items)
        elif race == "channel_close":
            return self._test_channel_close(cfg, num_workers, num_items)
        elif race == "slice_append":
            return self._test_slice_append(cfg, num_workers, num_items)
        elif race == "lazy_init":
            return self._test_lazy_init(cfg, num_workers, num_items)
        return ""

    def _test_shared_map(self, cfg: dict, nw: int, ni: int) -> str:
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        Item = cfg["Item"]
        field = cfg["item_field"]
        val_field = cfg["item_value_field"]
        val_type = cfg["item_value_type"]
        query = cfg["query_method"]
        run = cfg["run_method"]
        item = cfg["item"]

        return f'''package main

import (
\t"fmt"
\t"testing"
)

// TestSharedMapRace exercises the concurrent map writes.
// Run with: go test -race -count=5 -timeout 30s ./...
func TestSharedMapRace(t *testing.T) {{
\tp := {Ctor}({nw})
\titems := make([]{Item}, {ni})
\tfor i := range items {{
\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t}}
\tp.{run}(items)
\tsnap := p.{query}()
\tif len(snap) != {ni} {{
\t\tt.Errorf("expected {ni} entries, got %d", len(snap))
\t}}
}}

// TestSharedMapStress hammers the processor with repeated runs to surface races.
func TestSharedMapStress(t *testing.T) {{
\tfor round := 0; round < 10; round++ {{
\t\tp := {Ctor}({nw})
\t\titems := make([]{Item}, {ni})
\t\tfor i := range items {{
\t\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d-%d", round, i), {val_field}: {val_type}(i)}}
\t\t}}
\t\tp.{run}(items)
\t\tsnap := p.{query}()
\t\tif len(snap) != {ni} {{
\t\t\tt.Errorf("round %d: expected {ni} entries, got %d", round, len(snap))
\t\t}}
\t}}
}}
'''

    def _test_counter(self, cfg: dict, nw: int, ni: int) -> str:
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        Item = cfg["Item"]
        field = cfg["item_field"]
        val_field = cfg["item_value_field"]
        val_type = cfg["item_value_type"]
        run = cfg["run_method"]
        item = cfg["item"]

        return f'''package main

import (
\t"fmt"
\t"testing"
)

// TestCounterRace verifies that the final count equals the number of items processed.
// Run with: go test -race -count=5 -timeout 30s ./...
func TestCounterRace(t *testing.T) {{
\tp := {Ctor}({nw})
\titems := make([]{Item}, {ni})
\tfor i := range items {{
\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t}}
\tp.{run}(items)
\tif p.count != {ni} {{
\t\tt.Errorf("expected count={ni}, got %d (lost updates due to race?)", p.count)
\t}}
}}

// TestCounterStress repeats the test many times to increase race probability.
func TestCounterStress(t *testing.T) {{
\tfor round := 0; round < 20; round++ {{
\t\tp := {Ctor}({nw})
\t\titems := make([]{Item}, {ni})
\t\tfor i := range items {{
\t\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t\t}}
\t\tp.{run}(items)
\t\tif p.count != {ni} {{
\t\t\tt.Errorf("round %d: expected count={ni}, got %d", round, p.count)
\t\t}}
\t}}
}}
'''

    def _test_channel_close(self, cfg: dict, nw: int, ni: int) -> str:
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        Item = cfg["Item"]
        field = cfg["item_field"]
        val_field = cfg["item_value_field"]
        val_type = cfg["item_value_type"]
        run = cfg["run_method"]
        item = cfg["item"]

        return f'''package main

import (
\t"fmt"
\t"testing"
\t"time"
)

// TestChannelCloseRace exercises the concurrent channel-close bug.
// Run with: go test -race -count=5 -timeout 30s ./...
func TestChannelCloseRace(t *testing.T) {{
\tdone := make(chan struct{{}})
\tgo func() {{
\t\tp := {Ctor}({nw})
\t\titems := make([]{Item}, {ni})
\t\tfor i := range items {{
\t\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t\t}}
\t\tp.{run}(items)
\t\tclose(done)
\t}}()
\tselect {{
\tcase <-done:
\t\t// good — returned without panic
\tcase <-time.After(10 * time.Second):
\t\tt.Fatal("Run timed out — possible deadlock after panic recovery")
\t}}
}}

// TestChannelCloseStress repeats many times to trigger the intermittent panic.
func TestChannelCloseStress(t *testing.T) {{
\tfor round := 0; round < 10; round++ {{
\t\tfunc() {{
\t\t\tdefer func() {{
\t\t\t\tif r := recover(); r != nil {{
\t\t\t\t\tt.Errorf("round %d panicked: %v (close of closed channel?)", round, r)
\t\t\t\t}}
\t\t\t}}()
\t\t\tp := {Ctor}({nw})
\t\t\titems := make([]{Item}, {ni})
\t\t\tfor i := range items {{
\t\t\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d-%d", round, i), {val_field}: {val_type}(i)}}
\t\t\t}}
\t\t\tp.{run}(items)
\t\t}}()
\t}}
}}
'''

    def _test_slice_append(self, cfg: dict, nw: int, ni: int) -> str:
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        Item = cfg["Item"]
        field = cfg["item_field"]
        val_field = cfg["item_value_field"]
        val_type = cfg["item_value_type"]
        query = cfg["query_method"]
        run = cfg["run_method"]
        item = cfg["item"]

        return f'''package main

import (
\t"fmt"
\t"testing"
)

// TestSliceAppendRace verifies the final result count equals the number of items.
// Run with: go test -race -count=5 -timeout 30s ./...
func TestSliceAppendRace(t *testing.T) {{
\tp := {Ctor}({nw})
\titems := make([]{Item}, {ni})
\tfor i := range items {{
\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t}}
\tp.{run}(items)
\tres := p.{query}()
\tif len(res) != {ni} {{
\t\tt.Errorf("expected {ni} results, got %d (lost appends due to race?)", len(res))
\t}}
}}

// TestSliceAppendStress repeats the test many times to surface the data race.
func TestSliceAppendStress(t *testing.T) {{
\tfor round := 0; round < 20; round++ {{
\t\tp := {Ctor}({nw})
\t\titems := make([]{Item}, {ni})
\t\tfor i := range items {{
\t\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d-%d", round, i), {val_field}: {val_type}(i)}}
\t\t}}
\t\tp.{run}(items)
\t\tres := p.{query}()
\t\tif len(res) != {ni} {{
\t\t\tt.Errorf("round %d: expected {ni} results, got %d", round, len(res))
\t\t}}
\t}}
}}
'''

    def _test_lazy_init(self, cfg: dict, nw: int, ni: int) -> str:
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        Item = cfg["Item"]
        field = cfg["item_field"]
        val_field = cfg["item_value_field"]
        val_type = cfg["item_value_type"]
        run = cfg["run_method"]
        item = cfg["item"]

        return f'''package main

import (
\t"fmt"
\t"sync"
\t"testing"
)

// TestLazyInitRace exercises concurrent calls to {Ctor} to surface the data race.
// Run with: go test -race -count=5 -timeout 30s ./...
func TestLazyInitRace(t *testing.T) {{
\t// Reset singleton so the test starts clean.
\tinstance = nil
\tvar wg sync.WaitGroup
\tresults := make([]*{P}, {nw})
\tfor i := 0; i < {nw}; i++ {{
\t\twg.Add(1)
\t\tgo func(idx int) {{
\t\t\tdefer wg.Done()
\t\t\tresults[idx] = {Ctor}({nw})
\t\t}}(i)
\t}}
\twg.Wait()
\t// All results must be the same pointer.
\tfor i, r := range results {{
\t\tif r != results[0] {{
\t\t\tt.Errorf("goroutine %d got different instance (%p vs %p)", i, r, results[0])
\t\t}}
\t}}
}}

// TestLazyInitFunctionality verifies the singleton processes items correctly.
func TestLazyInitFunctionality(t *testing.T) {{
\tinstance = nil
\tp := {Ctor}({nw})
\tif !p.ready {{
\t\tt.Fatal("singleton not marked ready after init")
\t}}
\titems := make([]{Item}, {ni})
\tfor i := range items {{
\t\titems[i] = {Item}{{{field}: fmt.Sprintf("{item}-%d", i), {val_field}: {val_type}(i)}}
\t}}
\tp.{run}(items)
\tfmt.Printf("Processed %d {item}s\\n", {ni})
}}
'''

    # ── Spec / Brief generators ──────────────────────────────────────────────

    def _gen_spec(self, cfg: dict, pattern: dict, num_workers: int, num_items: int) -> str:
        domain = cfg["domain"]
        P = cfg["Processor"]
        Ctor = cfg["Constructor"]
        race = pattern["race_type"]
        symptom = pattern["spec_symptom"]
        requirement = pattern["spec_requirement"]
        primitives = ", ".join(f"`{p}`" for p in pattern["fix_primitives"])
        affected = ", ".join(f"`{f}`" for f in self._affected_functions(cfg, pattern))

        return f"""# GO2: Race Condition (Full Specification — Planner Only)

## Overview

The workspace contains a Go `{domain}` program (`{P}`) that runs {num_workers}
goroutines to process {num_items} items concurrently. The program has a **real
goroutine race condition** ({race}) that causes intermittent failures. The
executor sees only the brief; this document provides the full diagnosis.

## Program Structure

- `{Ctor}(workers int) *{P}` — constructor
- `main.go` — buggy concurrent implementation
- `race_test.go` — tests that surface the race (use `-race` flag)
- `go.mod` — module definition

## Race Condition Analysis

### Race Type: `{race}`

**Description:** {pattern["description"]}.

**Symptom:**
{symptom}

**Goroutine Interaction Contract (Hidden from Executor):**
{requirement}

## Required Fix Primitives

The fix **must** use one or more of the following Go synchronisation primitives:
{primitives}

No other approach (e.g. busy-wait loops, sleeping to avoid the race) is
acceptable.

## Affected Functions

The following functions must be modified to eliminate the race:
{affected}

## Acceptance Criteria

1. `go build ./...` succeeds with zero errors
2. `go vet ./...` reports no warnings
3. `go test -race -count=5 -timeout 60s ./...` passes with **zero** data races
   detected and all test cases green
4. The program produces the correct output count (no lost updates or items)
5. All required synchronisation primitives ({primitives}) are present in `main.go`
6. No goroutines are leaked; the program exits cleanly

## TNI Patterns

- **D (Cross-System Contract):** The goroutine interaction contract — which
  goroutines share which data and how — is only spelled out in this spec.
- **A (Hidden Constraint):** The specific sync primitives required are named
  here but not in the brief. An executor working alone might choose a different
  (incorrect or insufficient) fix.
"""

    def _gen_brief(self, cfg: dict, pattern: dict, num_workers: int, num_items: int) -> str:
        domain = cfg["domain"]
        P = cfg["Processor"]
        symptom = pattern["brief_symptom"]

        return f"""# GO2: Race Condition (Brief)

Fix a concurrency bug in a Go `{domain}` (`{P}`).

The program uses {num_workers} goroutines to process {num_items} items
concurrently. It works correctly most of the time, but {symptom}.

Run: `go test -race -count=5 -timeout 60s ./...`
All tests must pass with zero data races detected.

Files to fix: `main.go`
Do NOT modify `race_test.go`.
"""
