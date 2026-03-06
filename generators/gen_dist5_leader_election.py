"""
Parameterized generator for DIST5: Bully Leader Election.

Each seed produces a Bully election implementation with a simulated network.
3 bugs:
  1. No handling of simultaneous elections (race condition)
  2. Heartbeat timeout check inverted (last_heartbeat > timeout vs
     current_time - last_heartbeat > timeout)
  3. New node join doesn't trigger re-election when it has higher ID

2 edge cases:
  4. Network partition — both sides elect leaders
  5. Partition heal — stale leader must step down

Seed variation: node counts (3/5/7), timeout values, node ID schemes.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized pools ──────────────────────────────────────────────

NODE_COUNTS = [3, 5, 7]
TIMEOUT_VALUES = [2.0, 3.0, 1.5]
ELECTION_TIMEOUTS = [1.0, 1.5, 0.8]
HEARTBEAT_INTERVALS = [0.5, 0.8, 0.4]

# ID scheme: sequential from 1, even numbers, powers of 10
ID_SCHEMES = ["sequential", "even", "decimal"]
ID_GENERATORS = {
    "sequential": lambda n: list(range(1, n + 1)),
    "even": lambda n: list(range(2, 2 * n + 1, 2)),
    "decimal": lambda n: [10 * (i + 1) for i in range(n)],
}

CLUSTER_NAMES = ["alpha_cluster", "beta_cluster", "gamma_cluster"]


class Generator(TaskGenerator):
    task_id = "DIST5_leader_election"
    domain = "Distributed"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(NODE_COUNTS)

        node_count = NODE_COUNTS[idx]
        timeout = TIMEOUT_VALUES[idx]
        election_timeout = ELECTION_TIMEOUTS[idx]
        heartbeat_interval = HEARTBEAT_INTERVALS[idx]
        id_scheme = ID_SCHEMES[idx]
        node_ids = ID_GENERATORS[id_scheme](node_count)
        cluster_name = CLUSTER_NAMES[idx]

        workspace_files = self._make_workspace(
            node_count=node_count,
            node_ids=node_ids,
            timeout=timeout,
            election_timeout=election_timeout,
            heartbeat_interval=heartbeat_interval,
            id_scheme=id_scheme,
            cluster_name=cluster_name,
        )

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "DIST5_leader_election"
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="DIST5_leader_election",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": [
                    "simultaneous_election",
                    "heartbeat_timeout_inverted",
                    "new_node_join_election",
                ],
                "edge_cases": [
                    "partition_split_brain",
                    "partition_heal_stepdown",
                ],
                "seed": seed,
                "node_count": node_count,
                "node_ids": node_ids,
                "id_scheme": id_scheme,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Distributed"},
        )

    def _make_workspace(
        self,
        node_count: int,
        node_ids: list[int],
        timeout: float,
        election_timeout: float,
        heartbeat_interval: float,
        id_scheme: str,
        cluster_name: str,
    ) -> dict:
        files = {}

        max_id = max(node_ids)
        ids_repr = repr(node_ids)

        files["cluster/__init__.py"] = ""
        files["tests/__init__.py"] = ""

        # ── cluster/config.py ─────────────────────────────────────────────
        files["cluster/config.py"] = f'''\
"""Cluster configuration for {cluster_name}."""

NODE_COUNT = {node_count}
NODE_IDS = {ids_repr}
HEARTBEAT_TIMEOUT = {timeout}
ELECTION_TIMEOUT = {election_timeout}
HEARTBEAT_INTERVAL = {heartbeat_interval}
'''

        # ── cluster/network.py — simulated network ────────────────────────
        files["cluster/network.py"] = f'''\
"""
Simulated network for the {cluster_name} Bully election.

Supports message passing between nodes and network partition simulation.
"""
import threading
import time
from collections import defaultdict
from typing import Any


class Message:
    """A message passed between nodes."""

    def __init__(self, msg_type: str, sender_id: int, data: dict | None = None):
        self.msg_type = msg_type  # ELECTION, ALIVE, COORDINATOR, HEARTBEAT
        self.sender_id = sender_id
        self.data = data or {{}}
        self.timestamp = time.time()

    def __repr__(self):
        return f"Message({{self.msg_type}}, from={{self.sender_id}}, data={{self.data}})"


class SimulatedNetwork:
    """
    Simulated network with partition support.

    Nodes register callbacks. Messages are delivered unless a partition
    blocks the sender->receiver path.
    """

    def __init__(self):
        self._callbacks: dict[int, callable] = {{}}
        self._lock = threading.Lock()
        # Partition: set of frozenset pairs that CANNOT communicate
        self._blocked_pairs: set[frozenset] = set()
        self._message_log: list[Message] = []

    def register(self, node_id: int, callback) -> None:
        """Register a node's message handler."""
        with self._lock:
            self._callbacks[node_id] = callback

    def unregister(self, node_id: int) -> None:
        """Remove a node from the network."""
        with self._lock:
            self._callbacks.pop(node_id, None)

    def send(self, msg: Message, target_id: int) -> bool:
        """Send a message to a specific node. Returns False if blocked."""
        with self._lock:
            pair = frozenset([msg.sender_id, target_id])
            if pair in self._blocked_pairs:
                return False
            cb = self._callbacks.get(target_id)
        if cb:
            self._message_log.append(msg)
            cb(msg)
            return True
        return False

    def broadcast(self, msg: Message, exclude: set[int] | None = None) -> int:
        """Broadcast a message to all registered nodes except excluded ones.
        Returns count of successful deliveries."""
        exclude = exclude or set()
        delivered = 0
        with self._lock:
            targets = [nid for nid in self._callbacks if nid != msg.sender_id and nid not in exclude]
        for target_id in targets:
            if self.send(msg, target_id):
                delivered += 1
        return delivered

    def partition(self, group_a: set[int], group_b: set[int]) -> None:
        """Create a network partition between two groups of nodes."""
        with self._lock:
            for a in group_a:
                for b in group_b:
                    self._blocked_pairs.add(frozenset([a, b]))

    def heal_partition(self) -> None:
        """Remove all network partitions."""
        with self._lock:
            self._blocked_pairs.clear()

    def is_blocked(self, node_a: int, node_b: int) -> bool:
        """Check if two nodes are blocked from communicating."""
        with self._lock:
            return frozenset([node_a, node_b]) in self._blocked_pairs

    @property
    def registered_nodes(self) -> list[int]:
        with self._lock:
            return list(self._callbacks.keys())
'''

        # ── cluster/election.py — Bully algorithm with 3 bugs ────────────
        files["cluster/election.py"] = f'''\
"""
Bully Leader Election Algorithm for {cluster_name}.

Implements the Bully election protocol where the node with the highest
ID becomes the leader.

Known issues:
  - Bug 1: Does not handle simultaneous elections
  - Bug 2: Heartbeat timeout check is inverted
  - Bug 3: New node join does not trigger re-election
"""
import threading
import time
from typing import Optional

from cluster.network import SimulatedNetwork, Message
from cluster.config import HEARTBEAT_TIMEOUT, ELECTION_TIMEOUT, HEARTBEAT_INTERVAL


class BullyNode:
    """A node participating in Bully leader election."""

    def __init__(self, node_id: int, network: SimulatedNetwork):
        self.node_id = node_id
        self.network = network
        self.leader_id: Optional[int] = None
        self._lock = threading.Lock()
        self._last_heartbeat: dict[int, float] = {{}}
        self._alive = True
        self._heartbeat_thread: Optional[threading.Thread] = None

        # Register with network
        self.network.register(self.node_id, self._handle_message)

    def _handle_message(self, msg: Message) -> None:
        """Handle incoming messages."""
        if not self._alive:
            return

        if msg.msg_type == "COORDINATOR":
            with self._lock:
                self.leader_id = msg.sender_id

        elif msg.msg_type == "HEARTBEAT":
            with self._lock:
                self._last_heartbeat[msg.sender_id] = time.time()

        elif msg.msg_type == "ELECTION":
            # BUG 1: No handling of simultaneous elections.
            # When we receive an ELECTION from a lower-ID node, we should
            # respond with ALIVE and start our own election if not already
            # running one. Currently we just ignore it.
            pass

        elif msg.msg_type == "ALIVE":
            # Another higher-ID node is alive — we lose the election
            pass

    def start_election(self) -> None:
        """Start a Bully election."""
        with self._lock:
            self.leader_id = None

        # Send ELECTION to all nodes with higher IDs
        higher_nodes = [
            nid for nid in self.network.registered_nodes
            if nid > self.node_id
        ]

        if not higher_nodes:
            # We have the highest ID — declare ourselves leader
            self._declare_victory()
            return

        # Send ELECTION to higher-ID nodes
        got_alive = False
        for nid in higher_nodes:
            msg = Message("ELECTION", self.node_id)
            if self.network.send(msg, nid):
                # Wait briefly for ALIVE response
                time.sleep(0.1)

        # If no higher node responded, we win
        # (Simplified: in real impl we'd track ALIVE responses)
        if not got_alive:
            # Check again if any higher node is reachable
            for nid in higher_nodes:
                if not self.network.is_blocked(self.node_id, nid):
                    got_alive = True
                    break

        if not got_alive:
            self._declare_victory()

    def _declare_victory(self) -> None:
        """Declare this node as the leader."""
        with self._lock:
            self.leader_id = self.node_id

        # Broadcast COORDINATOR message
        msg = Message("COORDINATOR", self.node_id)
        self.network.broadcast(msg)

    def check_leader_alive(self) -> bool:
        """Check if the current leader is still alive.

        BUG 2: The timeout check is inverted. It checks
        last_heartbeat > timeout instead of
        (current_time - last_heartbeat) > timeout.
        """
        with self._lock:
            if self.leader_id is None or self.leader_id == self.node_id:
                return True

            last_hb = self._last_heartbeat.get(self.leader_id, 0)

            # BUG: This checks if the timestamp value is greater than timeout,
            # which is almost always True since timestamps are large numbers.
            # Should be: time.time() - last_hb > HEARTBEAT_TIMEOUT
            if last_hb > HEARTBEAT_TIMEOUT:
                return False

            return True

    def send_heartbeat(self) -> None:
        """Send a heartbeat to all nodes (leader only)."""
        if self.leader_id == self.node_id:
            msg = Message("HEARTBEAT", self.node_id)
            self.network.broadcast(msg)

    def join_cluster(self, existing_nodes: list[int]) -> None:
        """Join an existing cluster.

        BUG 3: Does not trigger re-election when this node has a higher
        ID than the current leader. A new high-ID node should start an
        election to become leader.
        """
        # Register with network (already done in __init__)
        # Just record that we know about existing nodes
        with self._lock:
            for nid in existing_nodes:
                self._last_heartbeat[nid] = time.time()

        # BUG: Should check if our ID is higher than current leader
        # and start an election if so. Currently just joins silently.

    def start_heartbeat_loop(self) -> None:
        """Start periodic heartbeat sending (leader only)."""
        def _loop():
            while self._alive and self.leader_id == self.node_id:
                self.send_heartbeat()
                time.sleep(HEARTBEAT_INTERVAL)

        self._heartbeat_thread = threading.Thread(target=_loop, daemon=True)
        self._heartbeat_thread.start()

    def stop(self) -> None:
        """Stop this node."""
        self._alive = False
        self.network.unregister(self.node_id)

    @property
    def is_leader(self) -> bool:
        return self.leader_id == self.node_id

    @property
    def is_alive(self) -> bool:
        return self._alive
'''

        # ── tests/test_basic.py — happy-path tests (pass even with bugs) ──
        files["tests/test_basic.py"] = f'''\
"""
Basic Bully election tests.

These tests pass even with the bugs because they don't exercise
concurrent elections, inverted timeouts, or node joins.
"""
import pytest
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cluster.network import SimulatedNetwork, Message
from cluster.election import BullyNode
from cluster.config import NODE_IDS


def test_highest_id_becomes_leader():
    """The node with the highest ID should become leader."""
    net = SimulatedNetwork()
    nodes = [BullyNode(nid, net) for nid in NODE_IDS]

    # Lowest ID node starts election
    nodes[0].start_election()
    time.sleep(0.5)

    # Highest ID should be leader
    expected_leader = max(NODE_IDS)
    # At least the initiating node should know the leader after election
    # (In buggy version, this still works because highest node gets ELECTION
    #  and declares itself leader)
    assert nodes[-1].is_leader or nodes[-1].leader_id == expected_leader, (
        f"Expected node {{expected_leader}} to be leader"
    )

    for n in nodes:
        n.stop()


def test_single_node_becomes_leader():
    """A single node should immediately become leader."""
    net = SimulatedNetwork()
    node = BullyNode(1, net)
    node.start_election()
    time.sleep(0.2)
    assert node.is_leader, "Single node must become leader"
    node.stop()


def test_leader_sends_coordinator():
    """Leader should broadcast COORDINATOR message."""
    net = SimulatedNetwork()
    nodes = [BullyNode(nid, net) for nid in NODE_IDS[:3]]

    nodes[-1].start_election()
    time.sleep(0.5)

    # Other nodes should know the leader
    expected = max(n.node_id for n in nodes)
    for n in nodes:
        if n.node_id != expected:
            assert n.leader_id == expected, (
                f"Node {{n.node_id}} should know leader is {{expected}}, "
                f"but thinks leader is {{n.leader_id}}"
            )

    for n in nodes:
        n.stop()


def test_heartbeat_sent():
    """Leader should send heartbeat messages."""
    net = SimulatedNetwork()
    leader = BullyNode(max(NODE_IDS), net)
    follower = BullyNode(min(NODE_IDS), net)

    leader.start_election()
    time.sleep(0.2)
    leader.send_heartbeat()
    time.sleep(0.2)

    assert follower._last_heartbeat.get(leader.node_id) is not None, (
        "Follower should have received heartbeat from leader"
    )

    leader.stop()
    follower.stop()


def test_network_message_delivery():
    """Messages should be delivered between registered nodes."""
    net = SimulatedNetwork()
    received = []
    net.register(1, lambda msg: received.append(msg))
    net.register(2, lambda msg: None)

    msg = Message("ELECTION", sender_id=2)
    net.send(msg, 1)

    assert len(received) == 1
    assert received[0].msg_type == "ELECTION"

    net.unregister(1)
    net.unregister(2)
'''

        # ── tests/test_simultaneous_election.py ───────────────────────────
        files["tests/test_simultaneous_election.py"] = f'''\
"""
Simultaneous election tests.

Bug 1: Two nodes starting elections at the same time should not both
become leader. The higher-ID node must win.
"""
import pytest
import time
import threading
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cluster.network import SimulatedNetwork
from cluster.election import BullyNode


def test_simultaneous_election_higher_wins():
    """When two nodes start elections simultaneously, higher ID wins."""
    net = SimulatedNetwork()
    node_low = BullyNode(1, net)
    node_mid = BullyNode(5, net)
    node_high = BullyNode(10, net)

    # Both low and mid start elections at the same time
    t1 = threading.Thread(target=node_low.start_election)
    t2 = threading.Thread(target=node_mid.start_election)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    time.sleep(1.0)

    # Only the highest node should be leader
    leaders = [n for n in [node_low, node_mid, node_high] if n.is_leader]
    assert len(leaders) == 1, (
        f"Expected exactly 1 leader, found {{len(leaders)}}: "
        f"{{[n.node_id for n in leaders]}}"
    )
    assert leaders[0].node_id == 10, (
        f"Expected node 10 to be leader, got node {{leaders[0].node_id}}"
    )

    for n in [node_low, node_mid, node_high]:
        n.stop()


def test_election_message_triggers_higher_node():
    """Receiving ELECTION from lower node should trigger higher node's own election."""
    net = SimulatedNetwork()
    node_low = BullyNode(1, net)
    node_high = BullyNode(10, net)

    # Low node starts election
    node_low.start_election()
    time.sleep(1.0)

    # High node should have become leader (it should respond and take over)
    assert node_high.is_leader, (
        "Higher ID node should become leader after receiving ELECTION from lower node"
    )

    node_low.stop()
    node_high.stop()
'''

        # ── tests/test_heartbeat.py ───────────────────────────────────────
        files["tests/test_heartbeat.py"] = f'''\
"""
Heartbeat timeout detection tests.

Bug 2: The heartbeat timeout check is inverted. It checks
last_heartbeat > timeout instead of (current_time - last_heartbeat) > timeout.
"""
import pytest
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cluster.network import SimulatedNetwork
from cluster.election import BullyNode
from cluster.config import HEARTBEAT_TIMEOUT


def test_leader_detected_alive_when_heartbeating():
    """A heartbeating leader should be detected as alive."""
    net = SimulatedNetwork()
    leader = BullyNode(10, net)
    follower = BullyNode(1, net)

    leader.start_election()
    time.sleep(0.2)
    leader.send_heartbeat()
    time.sleep(0.2)

    assert follower.check_leader_alive(), (
        "Leader just sent heartbeat — should be detected as alive"
    )

    leader.stop()
    follower.stop()


def test_leader_detected_dead_after_timeout():
    """A leader that stops heartbeating should be detected as dead after timeout."""
    net = SimulatedNetwork()
    leader = BullyNode(10, net)
    follower = BullyNode(1, net)

    leader.start_election()
    time.sleep(0.2)
    leader.send_heartbeat()
    time.sleep(0.2)

    # Now stop the leader's heartbeat and wait for timeout
    leader.stop()
    time.sleep(HEARTBEAT_TIMEOUT + 1.0)

    result = follower.check_leader_alive()
    assert not result, (
        f"Leader stopped {{HEARTBEAT_TIMEOUT + 1.0}}s ago — should be detected as dead. "
        f"check_leader_alive() returned True (expected False). "
        "Check if the timeout comparison is correct: "
        "should be (current_time - last_heartbeat) > timeout"
    )

    follower.stop()


def test_no_heartbeat_means_dead():
    """A leader that never sent a heartbeat should be detected as dead."""
    net = SimulatedNetwork()
    leader = BullyNode(10, net)
    follower = BullyNode(1, net)

    # Set leader manually without heartbeat
    follower.leader_id = 10

    time.sleep(HEARTBEAT_TIMEOUT + 0.5)

    result = follower.check_leader_alive()
    assert not result, (
        "Leader never sent heartbeat — should be detected as dead. "
        "check_leader_alive() returned True (expected False)."
    )

    leader.stop()
    follower.stop()
'''

        # ── tests/test_node_join.py ───────────────────────────────────────
        files["tests/test_node_join.py"] = f'''\
"""
Node join election trigger tests.

Bug 3: When a new node with a higher ID than the current leader joins,
it should trigger a re-election and become the new leader.
"""
import pytest
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cluster.network import SimulatedNetwork
from cluster.election import BullyNode


def test_high_id_join_triggers_election():
    """New node with highest ID should trigger election and become leader."""
    net = SimulatedNetwork()
    node1 = BullyNode(1, net)
    node5 = BullyNode(5, net)

    # Node 5 becomes leader
    node5.start_election()
    time.sleep(0.5)
    assert node5.is_leader, "Node 5 should be initial leader"

    # New node with ID 10 joins
    node10 = BullyNode(10, net)
    node10.join_cluster([1, 5])
    time.sleep(1.0)

    assert node10.is_leader, (
        "New node 10 (highest ID) should become leader after joining. "
        "join_cluster() must trigger an election when the joining node "
        "has a higher ID than the current leader."
    )

    for n in [node1, node5, node10]:
        n.stop()


def test_low_id_join_no_election():
    """New node with lower ID than leader should NOT trigger election."""
    net = SimulatedNetwork()
    node5 = BullyNode(5, net)
    node10 = BullyNode(10, net)

    # Node 10 becomes leader
    node10.start_election()
    time.sleep(0.5)
    assert node10.is_leader

    # New node with ID 1 joins — should not displace node 10
    node1 = BullyNode(1, net)
    node1.join_cluster([5, 10])
    time.sleep(0.5)

    assert node10.is_leader, (
        "Node 10 should still be leader after lower-ID node joins"
    )

    for n in [node1, node5, node10]:
        n.stop()
'''

        # ── tests/test_partition.py ───────────────────────────────────────
        files["tests/test_partition.py"] = f'''\
"""
Network partition tests.

Edge case 4: Split brain — each side elects its own leader.
Edge case 5: Partition heal — stale leader steps down.
"""
import pytest
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cluster.network import SimulatedNetwork
from cluster.election import BullyNode


def test_partition_each_side_elects_leader():
    """During a partition, each side should be able to elect a leader."""
    net = SimulatedNetwork()
    node1 = BullyNode(1, net)
    node3 = BullyNode(3, net)
    node5 = BullyNode(5, net)
    node7 = BullyNode(7, net)

    # Initial election — node 7 should be leader
    node7.start_election()
    time.sleep(0.5)
    assert node7.is_leader

    # Create partition: {{1, 3}} vs {{5, 7}}
    net.partition({{1, 3}}, {{5, 7}})

    # Side A (1, 3) detects leader 7 is unreachable and elects node 3
    node3.leader_id = None
    node1.leader_id = None
    node3.start_election()
    time.sleep(0.5)

    assert node3.is_leader or node3.leader_id == 3, (
        "In partition {{1,3}}, node 3 should be elected as local leader"
    )

    # Side B (5, 7) still has node 7 as leader
    assert node7.is_leader, "Node 7 should still be leader on its side"

    for n in [node1, node3, node5, node7]:
        n.stop()


def test_partition_heal_stale_leader_steps_down():
    """After partition heals, stale leader from minority must step down."""
    net = SimulatedNetwork()
    node1 = BullyNode(1, net)
    node3 = BullyNode(3, net)
    node5 = BullyNode(5, net)
    node7 = BullyNode(7, net)

    # Initial: node 7 is leader
    node7.start_election()
    time.sleep(0.5)
    assert node7.is_leader

    # Partition: {{1, 3}} vs {{5, 7}}
    net.partition({{1, 3}}, {{5, 7}})

    # Side A elects node 3 as leader
    node3.leader_id = None
    node1.leader_id = None
    node3.start_election()
    time.sleep(0.5)
    assert node3.is_leader or node3.leader_id == 3

    # Heal partition
    net.heal_partition()

    # Trigger re-election to resolve split brain
    node1.start_election()
    time.sleep(1.0)

    # After heal, node 7 (highest ID) should be the only leader
    leaders = [n for n in [node1, node3, node5, node7] if n.is_leader]
    assert len(leaders) == 1 and leaders[0].node_id == 7, (
        f"After partition heal, only node 7 should be leader. "
        f"Found leaders: {{[n.node_id for n in leaders]}}"
    )

    # Node 3 must have stepped down
    assert not node3.is_leader, (
        "Node 3 (stale leader from minority partition) must step down"
    )

    for n in [node1, node3, node5, node7]:
        n.stop()


def test_partition_heal_highest_id_wins():
    """After heal, the globally highest-ID node must be the sole leader."""
    net = SimulatedNetwork()
    nodes = [BullyNode(nid, net) for nid in [2, 4, 6, 8, 10]]

    # Node 10 is initial leader
    nodes[-1].start_election()
    time.sleep(0.5)
    assert nodes[-1].is_leader

    # Partition: {{2, 4}} vs {{6, 8, 10}}
    net.partition({{2, 4}}, {{6, 8, 10}})

    # {{2, 4}} elects node 4
    nodes[1].leader_id = None
    nodes[0].leader_id = None
    nodes[1].start_election()
    time.sleep(0.5)

    # Heal
    net.heal_partition()
    nodes[0].start_election()
    time.sleep(1.0)

    # Node 10 should be sole leader
    assert nodes[-1].is_leader, "Node 10 should be leader after partition heal"
    for n in nodes[:-1]:
        assert not n.is_leader, (
            f"Node {{n.node_id}} should not be leader after partition heal"
        )

    for n in nodes:
        n.stop()
'''

        files["requirements.txt"] = "pytest\n"

        return files
