# TEST6: Property-Based Testing with Hypothesis

## Goal
Write Hypothesis property-based tests that verify 10 invariants for a data
structure library (`datastructs.py`) containing SortedList, BoundedQueue, and LRUCache.

## Data Structures

### SortedList
A sorted list that maintains non-decreasing order after every insertion.
- `insert(value)`: insert maintaining sorted order
- `remove(value)`: remove first occurrence, raises ValueError if not found
- `contains(value)`: binary search lookup
- `to_list()`: returns a copy of internal list
- `len()`: number of elements

### BoundedQueue (capacity=10)
A bounded FIFO queue.
- `enqueue(value)`: add to back, raises OverflowError if full
- `dequeue()`: remove from front, raises IndexError if empty
- `peek()`: view front without removing
- Properties: `size`, `capacity`, `is_full`, `is_empty`

### LRUCache (capacity=10)
A Least-Recently-Used cache.
- `put(key, value)`: insert or update. Evicts LRU when at capacity
- `get(key)`: returns value or None. Marks as recently used
- `delete(key)`: remove key, returns True/False
- `keys()`: return keys from least to most recently used
- Properties: `size`, `capacity`

## 10 Invariants (from spec_invariants.txt)

1. SortedList: `to_list()` always sorted after any insert sequence
2. SortedList: `len()` tracks inserts/removals correctly including duplicates
3. SortedList: `contains(v)` returns True for every v in `to_list()`
4. SortedList: `remove(v)` removes exactly one occurrence
5. BoundedQueue: `size` never exceeds `capacity`
6. BoundedQueue: FIFO ordering preserved
7. BoundedQueue: `enqueue` on full queue raises OverflowError, size unchanged
8. LRUCache: `size` never exceeds `capacity`
9. LRUCache: `get(k)` returns value after `put(k, v)` (cache consistency)
10. LRUCache: LRU eviction policy correct (least recently used key evicted)

## Known Issue
Some implementations have subtle bugs that only emerge under random testing
with edge cases (duplicates, capacity boundaries, access patterns). Your
property tests should reliably detect these issues.

## Deliverables
- `tests/test_properties.py` with Hypothesis `@given` property tests
- At least 10 test functions (one per invariant)
- Tests must use Hypothesis strategies
- Run: `python -m pytest tests/test_properties.py -v`
- Verifier writes `attestation.json` with verdict

## Grading
- Each invariant checked for a corresponding test function
- Tests run on the provided (buggy) code: bug-revealing tests that fail count as valid
- Tests also run on a fixed version: tests must PASS on correct implementations
