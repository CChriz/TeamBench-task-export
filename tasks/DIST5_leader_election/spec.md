# DIST5: Bully Leader Election

## Goal

Fix a Bully leader election algorithm implementation that has 3 bugs and does not handle
2 network partition edge cases.

## Bugs to Fix

1. **Simultaneous elections**: When two nodes start elections at the same time, they can
   both conclude they are leader. The implementation does not handle concurrent election
   messages — a node that receives an ELECTION message from a lower-ID node while running
   its own election should respond with ALIVE and continue its own election.

2. **Dead node detection timeout**: The heartbeat timeout check is inverted. It checks
   `last_heartbeat > timeout` instead of `current_time - last_heartbeat > timeout`.
   This means nodes are incorrectly detected as dead.

3. **New node join**: When a new node joins the cluster with a higher ID than the current
   leader, it should trigger a re-election. The current implementation does not start
   an election on join.

## Edge Cases to Handle

4. **Network partition — split brain**: When the network partitions, each side should
   elect its own leader. When the partition heals, the side with the highest-ID node
   must win and the stale leader must step down.

5. **Partition heal — stale leader**: After a partition heals, a node that was leader
   of a minority partition must detect that a higher-ID leader exists and step down.

## Requirements

- All 3 bugs must be fixed
- Both partition edge cases must be handled
- All tests must pass: `pytest tests/`
- No regression in happy-path leader election
