# TEST5: Mutation-Resistant Test Suite

## Goal
Write comprehensive tests for a math/validation library (`mathlib.py`) that detect subtle bugs through mutation testing. Your tests must kill at least 16 out of 20 seeded mutants.

## Library Specification — 25 Behaviors

### Basic Arithmetic
1. `add(a, b)` returns `a + b` as a float
2. `subtract(a, b)` returns `a - b` as a float
3. `multiply(a, b)` returns `a * b` as a float
4. `divide(a, b)` returns `a / b` as a float; raises `MathLibError("division_by_zero")` when `b == 0`
5. `modulo(a, b)` returns `a % b`; raises `MathLibError("division_by_zero")` when `b == 0`

### Advanced Math
6. `power(base, exp)` returns `base ** exp`; raises `MathLibError("overflow")` if result exceeds 1e15
7. `sqrt(x)` returns the square root of `x`; raises `MathLibError("domain_error")` for negative `x`
8. `absolute(x)` returns the absolute value of `x`
9. `minimum(a, b)` returns the smaller of `a` and `b`
10. `maximum(a, b)` returns the larger of `a` and `b`
11. `clamp(x, lo, hi)` returns `x` clamped to `[lo, hi]`; raises `MathLibError("invalid_range")` if `lo > hi`

### Number Properties
12. `is_even(n)` returns `True` if `n` is divisible by 2, else `False`
13. `is_odd(n)` returns `True` if `n` is not divisible by 2, else `False`
14. `is_prime(n)` returns `True` if `n` is a prime number (n >= 2), else `False`

### Combinatorics
15. `factorial(n)` returns `n!`; raises `MathLibError("domain_error")` for negative `n`
16. `fibonacci(n)` returns the `n`-th Fibonacci number (0-indexed: fib(0)=0, fib(1)=1, fib(2)=1, fib(3)=2); raises `MathLibError("domain_error")` for negative `n`
17. `gcd(a, b)` returns the greatest common divisor of `a` and `b`
18. `lcm(a, b)` returns the least common multiple of `a` and `b`

### Statistics
19. `mean(values)` returns the arithmetic mean; raises `MathLibError("empty_input")` for empty list
20. `median(values)` returns the median value; raises `MathLibError("empty_input")` for empty list
21. `mode(values)` returns the most frequent value (first if tied); raises `MathLibError("empty_input")` for empty list
22. `std_dev(values)` returns the population standard deviation; raises `MathLibError("empty_input")` for empty or single-element list
23. `percentile(values, p)` returns the p-th percentile (0-100); raises `MathLibError("invalid_range")` if p not in [0, 100]

### Utilities
24. `normalize(values, lo, hi)` scales values to `[lo, hi]` range; raises `MathLibError("empty_input")` for empty list; raises `MathLibError("constant_input")` when all values are equal
25. `validate_range(value, lo, hi)` returns `True` if `lo <= value <= hi`; raises `MathLibError("invalid_range")` if `lo > hi`

## Edge Cases to Cover
- Zero division in divide, modulo
- Negative input in sqrt, factorial, fibonacci
- Empty lists in all statistics functions
- Overflow in power
- Boundary values: clamp at exact boundaries, percentile at 0 and 100
- Prime checks: 0, 1, 2, 3, large primes, even numbers
- Fibonacci: 0, 1, large indices
- Normalize: constant input, single element after filtering
- GCD/LCM with zero arguments

## Grading
- Phase 1: All tests must pass on the correct `mathlib.py` (pytest passes)
- Phase 2: Tests are run against 20 mutant versions; must kill >= 16/20 (80%)
- A mutant is "killed" when at least one test fails on it

## Deliverables
- `tests/test_mathlib.py` with at least 25 test functions covering all behaviors
- Tests must be deterministic and fast (no random, no sleep)
- Verifier must run tests and confirm mutation kill rate >= 80%
