# INC8: Cascading Timeout

## Goal

A 3-service request chain has timeout misconfigurations that cause cascading
failures, plus retry policies that amplify the problem. Fix the timeout cascade
and the 2 harmful retry configurations while preserving the 2 correct retries.

## Requirements

1. Fix the timeout cascade: upstream timeouts must be >= downstream timeouts
2. Fix the 2 harmful retry configurations
3. Preserve the 2 correct retry configurations (documented in `RETRY_POLICY.md`)
4. All tests must pass after changes: `pytest tests/`

## Architecture

Three services form a synchronous request chain:

```
gateway.py  -->  order_service.py  -->  inventory_service.py
```

Each service has configurable timeout and retry settings.

## Timeout Cascade Bug

The gateway timeout (5s) is SHORTER than the order_service timeout (10s). When
the order_service takes 6-10 seconds to respond, the gateway times out first,
returning an error to the client. Meanwhile, the order_service continues
processing (zombie request), potentially completing a state-changing operation
that the client thinks failed.

Fix: gateway timeout must be >= order_service timeout + buffer. Similarly,
order_service timeout must be >= inventory_service timeout + buffer.

## Retry Configurations (4 total)

### Correct Retries (preserve these)

1. **Idempotent GET retry**: `GET /inventory/check` retries on timeout are safe
   because the operation is read-only. Documented in `RETRY_POLICY.md`.

2. **Health check retry**: `/health` endpoint retries are safe because health
   checks are idempotent and stateless. Documented in `RETRY_POLICY.md`.

### Harmful Retries (fix these)

3. **Non-idempotent POST retry**: `POST /orders/create` retries on timeout.
   If the first request succeeded but the response was lost (timeout), the
   retry creates a duplicate order and double-charges the customer.
   Fix: disable retry for non-idempotent operations, or require idempotency keys.

4. **Retry storm amplification**: When inventory_service is slow, order_service
   retries 3 times. Each retry causes gateway to also retry, creating 3x3=9
   total requests to inventory_service from a single client request.
   Fix: add retry budget or circuit breaker to prevent amplification.

## Supporting Files

- `gateway.py` — API gateway with timeout and retry config
- `order_service.py` — order processing service
- `inventory_service.py` — inventory checking service
- `INCIDENT_REPORT.md` — documents a past cascading timeout incident
- `RETRY_POLICY.md` — documents which operations are idempotent
- `config.py` — service configuration (timeouts, retry counts)
- `tests/test_services.py` — service tests (must all pass)
