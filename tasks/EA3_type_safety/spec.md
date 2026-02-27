# EA3: Type Safety — Fix mypy Errors

## Goal

The codebase has type annotation errors and omissions that cause `mypy --strict` to report
errors. Fix them so that mypy reports zero errors.

## Type Check Command

```
mypy app/ --ignore-missing-imports --strict 2>&1
```

## Application Modules

- `app/models.py` — data model classes with typed fields and methods
- `app/service.py` — service layer: processing functions, lookups, transformations
- `app/utils.py` — utility functions including date parsing and dict merging; a `Registry` class
- `app/dynamic.py` — dynamic dispatch and plugin registry (see below)

## Intentional Dynamic Patterns (require `type: ignore`, not code changes)

`app/dynamic.py` contains three patterns that use deliberate Python dynamism. Mypy cannot
statically verify these patterns, but they are correct by design. The right fix for each is
to add a `# type: ignore[<code>]` comment on the flagged line — **not** to remove the dynamic
behavior or restructure the code.

The three patterns and their appropriate ignore codes:

1. **Dynamic method dispatch via `getattr`**: Calling a method looked up by string name at
   runtime. Mypy cannot verify the call is valid. Use `# type: ignore[no-untyped-call]`.

2. **Return value from `Any`-typed registry**: When a function returns a value fetched from a
   dict typed as `dict` (with implicit `Any` values), mypy raises a return type error.
   Use `# type: ignore[no-any-return]`.

3. **Calling an `Any`-typed callable**: A cast function received from configuration as `Any`
   and then invoked as a callable. Mypy cannot verify the call signature.
   Use `# type: ignore[operator]`.

All other type errors in `app/models.py`, `app/service.py`, and `app/utils.py` are real
annotation gaps or type mismatches that should be fixed with proper type annotations.

## Deliverables

- All mypy errors resolved with correct type annotations or code fixes
- Exactly 3 `# type: ignore` comments — one per dynamic pattern in `app/dynamic.py`
- `mypy app/ --ignore-missing-imports --strict` reports 0 errors
