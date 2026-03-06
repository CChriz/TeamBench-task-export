# NEG5: SLA Tradeoff — Full Specification (Planner Only)

## Overview

A service tier configuration system defines 5 tiers, each with latency, consistency, and availability targets. Three of the tiers have **impossible SLA combinations** that violate the CAP-theorem-inspired constraints. Fix the tier definitions in `tiers.py` so all tiers are achievable, then `python3 test_tiers.py` passes.

---

## Application Architecture

```
workspace/
  tiers.py             # Service tier definitions (buggy)
  constraints.py       # SLA constraint checker (do not modify)
  test_tiers.py        # Test suite (do not modify)
```

---

## Constraint Rules (from `constraints.py`)

The system enforces these physical constraints:
1. **Latency + Strong Consistency**: If consistency is "strong", latency cannot be below 50ms (consensus overhead)
2. **Availability + Strong Consistency**: If consistency is "strong", availability cannot exceed 99.9% (partition tolerance tradeoff)
3. **Latency + High Availability**: If availability is >= 99.99%, latency cannot be below 100ms (multi-region replication)

---

## Bug Inventory

### Bug 1: Tier "premium" — impossible latency + consistency
- **Symptom**: Premium tier promises latency=20ms with consistency="strong" — impossible per constraint #1
- **Expected**: Either relax latency to >=50ms or change consistency to "eventual"
- **Guidance**: This is a premium tier, so keep consistency="strong" and relax latency to 50ms

### Bug 2: Tier "enterprise" — impossible availability + consistency
- **Symptom**: Enterprise tier promises availability=99.999% with consistency="strong" — impossible per constraint #2
- **Expected**: Either reduce availability to <=99.9% or change consistency to "eventual"
- **Guidance**: Enterprise needs strong consistency, so set availability to 99.9%

### Bug 3: Tier "realtime" — impossible latency + availability
- **Symptom**: Realtime tier promises latency=10ms with availability=99.99% — impossible per constraint #3
- **Expected**: Either increase latency to >=100ms or reduce availability below 99.99%
- **Guidance**: Realtime prioritizes low latency, so reduce availability to 99.9%

---

## Expected Outcome

After fixing all 3 tiers: `python3 test_tiers.py` — all tests pass.

---

## Constraints

- Do not modify `test_tiers.py` or `constraints.py`
- Only fix `tiers.py`
- Each fix has a recommended direction — follow the guidance
