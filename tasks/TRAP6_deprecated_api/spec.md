# TRAP6: Deprecated API Migration

## Goal

The codebase uses `old_api` calls across 8 callsites. A migration guide instructs you to migrate
ALL callsites to the new `new_api` interface. However, some callsites are invoked from a vendored
third-party library that only understands the old API.

## Requirements

1. Migrate callsites to `new_api` where safe — follow the migration guide
2. Preserve callsites that are called from vendored dependencies — see `VENDORED_DEPS.md`
3. All tests must pass after changes: `pytest tests/`
4. The vendored library integration tests must still pass

## Supporting Documents

- `migration_guide.md` — Says to migrate ALL callsites to `new_api` (overly broad)
- `VENDORED_DEPS.md` — Documents which modules are consumed by vendored third-party code
  that only understands the old API interface

## Contradiction to Resolve

The migration guide was written before the vendored dependency constraint was discovered.
`VENDORED_DEPS.md` is authoritative. When the migration guide and `VENDORED_DEPS.md` conflict,
trust `VENDORED_DEPS.md`. Migrating a vendored-dependency callsite will break the vendored
library at runtime.
