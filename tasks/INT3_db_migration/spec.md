# INT3: Database Schema Migration Fix

## Goal
Fix a database migration system that has 4 bugs preventing successful up/down migration.

## Requirements
1. Fix FK constraint ordering: migration creates a foreign key before the referenced table exists
2. Fix NOT NULL column: a NOT NULL column is added without a DEFAULT value, breaking existing rows
3. Fix index naming: an index name collides with an existing index in a prior migration
4. Fix rollback: the down migration drops the wrong column, corrupting the schema
5. Running all migrations up then down must succeed without errors
6. The final schema after up must match `schema_design.md`

## Supporting Documents
- `migrations/001_initial.py` — First migration (creates base tables)
- `migrations/002_add_features.py` — Second migration (the buggy one)
- `migrations/003_indexes.py` — Third migration (index collision)
- `schema_design.md` — Target schema specification
- `migrate.py` — Migration runner (do not modify)
- `tests/test_migrations.py` — Tests that run migrations up and down

## The 4 Bugs
Each migration file has at least one bug. The bugs are ordering-dependent — fixing
them requires understanding the migration sequence.

## Important
Do NOT modify `migrate.py` (the migration runner). Only fix the migration files.
