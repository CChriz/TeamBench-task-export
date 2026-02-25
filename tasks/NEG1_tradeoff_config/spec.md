# NEG1: Conflicting Constraints Negotiation

## Goal
Configure and fix the HTTP service so it simultaneously satisfies performance, security, and reliability requirements.

## Three Constraint Categories (ALL must pass)

### Performance
- p95 latency must be < 100ms per request
- The current implementation is significantly slower than this threshold due to the input validation step
- **Constraint**: Validation must not be disabled — the solution must make validation fast enough to meet the latency target, not skip it

### Security
- All inputs must be validated before processing (validation cannot be disabled or bypassed)
- TLS must be enabled for all connections
- No plaintext credentials may appear in config files or source code
- Session tokens must be generated using a cryptographically secure method

### Reliability
- External service calls must be wrapped with a circuit breaker
- Failed requests must be retried with exponential backoff: base delay of 100ms, maximum of 3 retry attempts
- The circuit breaker must open after 3 consecutive failures and remain open for 10 seconds before attempting recovery

## Common Traps
- Disabling validation satisfies the performance requirement but violates security
- Enabling all features without optimizing validation satisfies security but fails the performance benchmark
- Implementing only the circuit breaker satisfies reliability but leaves performance and security unaddressed

## Deliverables
- Fixed service code meeting all 3 constraint categories
- All 3 benchmarks pass simultaneously
