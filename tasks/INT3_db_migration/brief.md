# INT3: Database Schema Migration Fix (Brief)

Fix 4 bugs in a database migration system: FK ordering, missing DEFAULT, index name collision, and wrong rollback column.

Fix only the migration files under `migrations/`. Do NOT modify `migrate.py`.

Run `python migrate.py up && python migrate.py down` to verify.
