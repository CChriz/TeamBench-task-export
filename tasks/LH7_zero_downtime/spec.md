# LH7: Zero-Downtime Database Migration

## Goal
Execute a database schema migration with **zero downtime**. The application must remain
functional throughout the migration process.

## Current State
- `app.py` has a SQLAlchemy model with an old column that needs to be split into two new columns
- 4 migration scripts in `migrations/` directory
- `run_migrations.py` executes migrations in filename sort order

## Problems to Fix

### 1. Migration Order is WRONG
The migration files are numbered incorrectly. The current filename ordering executes:
1. Backfill (Step 2) — runs before columns exist
2. Drop old column (Step 4) — runs before backfill/switch
3. Add new columns (Step 1) — runs too late
4. Switch reads (Step 3) — runs after drop

**Correct order must be**: Add columns -> Backfill -> Switch reads -> Drop old column

### 2. Missing Backfill Completeness Check
The drop-old-column migration does NOT verify that all rows have been backfilled.
It must check for NULL values in new columns before proceeding.

### 3. Update app.py
After migrations complete, `app.py` should include the new columns in the model.

## RUNBOOK.md
Contains the correct migration sequence documentation. Follow it.

## Deliverables
1. Migration files renamed/reordered to execute in correct sequence
2. Backfill completeness check added to the drop-old-column migration
3. `app.py` updated with new columns in model
4. `run_migrations.py` must succeed end-to-end
5. Verifier writes `attestation.json`
