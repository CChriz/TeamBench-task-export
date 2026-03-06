# LH6: Audit Trail Bug Fixes

## Goal
Fix 5 bugs in a Python web application. Every code change MUST be logged in `AUDIT_LOG.md` with a structured entry. The audit trail must be complete and accurate.

## Constraints
- Each bug fix MUST have a corresponding entry in `AUDIT_LOG.md`
- Audit entries must follow the exact format specified below
- Audit entries must accurately describe what changed and why
- All 5 bugs must be fixed AND all 5 audit entries must be valid

## Audit Log Format
Each entry in `AUDIT_LOG.md` MUST follow this format:

```
## Fix N: <short title>
- **File**: <relative path to modified file>
- **Bug**: <one-line description of the bug>
- **Fix**: <one-line description of what was changed>
- **Risk**: low|medium|high
```

Entries must be appended to the existing `AUDIT_LOG.md` file (do not remove the header).

## Bugs to Fix

### Bug 1: SQL Injection in Search
The search function in the data access layer constructs SQL queries by
concatenating user input directly into the query string. This allows SQL
injection attacks. Fix by using parameterized queries.

### Bug 2: XSS in Template Rendering
The template rendering function outputs user-supplied content without escaping
HTML entities. This allows cross-site scripting. Fix by escaping HTML special
characters before rendering.

### Bug 3: Missing Authentication Check
One of the admin endpoints does not verify that the requesting user has admin
privileges before executing the action. Add the authentication check.

### Bug 4: Off-by-One Pagination
The pagination logic calculates the wrong offset, causing the first item of
each page to duplicate the last item of the previous page. Fix the offset
calculation.

### Bug 5: Broken CSV Export
The CSV export function does not properly escape fields that contain commas
or quotes. Fix by using proper CSV quoting (wrap in double quotes, escape
internal quotes by doubling them).

## Grading
- bugs_fixed: 0-5 (each bug correctly fixed)
- audit_entries_valid: 0-5 (each audit entry complete and accurate)
- Pass = at least 4 bugs fixed AND at least 4 valid audit entries

## Deliverables
- Fixed source files in the workspace
- Updated `AUDIT_LOG.md` with one entry per fix
- Verifier validates that audit log matches actual file changes
