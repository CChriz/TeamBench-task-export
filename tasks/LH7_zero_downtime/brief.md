# LH7: Zero-Downtime Database Migration (Brief)

Migrate a database column to two new columns with zero downtime.

The `migrations/` directory has 4 migration scripts that are in the WRONG ORDER.
Reorder them and fix any issues so `run_migrations.py` succeeds.

See `RUNBOOK.md` for the correct migration pattern.

Run: `python app.py` to seed data, then `python run_migrations.py` to apply migrations.
