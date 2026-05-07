#!/usr/bin/env python3
"""Count unique valid participants per (task, mode) from Firebase RTDB.

Filters out test/development identities (test*, admin*, team_test_*,
probe*, single-char names, missing emails, malformed emails). Only
counts sessions that actually completed (phase == 'completed') AND
have a survey response — that ensures we count people who genuinely
went through the full flow, not someone who joined and walked away.

Usage:
  python3 count_participants.py                     # default summary
  python3 count_participants.py --include-cancelled # also count phase!=completed
  python3 count_participants.py --no-survey-required
  python3 count_participants.py --csv > counts.csv
  python3 count_participants.py --details           # also list participant emails

Output:
  Per-(task, mode) row: task_id | mode | n_participants | n_sessions
  Plus per-mode totals and a grand total of unique humans across all tasks.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from typing import Iterable

DB_URL = os.environ.get("TEAMBENCH_FIREBASE_URL", "")

# Pattern matches we treat as INVALID (development/test identities).
# Match against both NAME and EMAIL — anything that looks like a tester
# is dropped from the count regardless of which field carries the giveaway.
#
# The 1-3 char all-lowercase rule catches the common "type two letters
# to skip the form" pattern (a, ai, ab, abc, daf, etc.). Real
# first/last names are almost never <=3 lowercase letters.
_INVALID_PATTERNS = [
    re.compile(r"^test\d*$", re.IGNORECASE),
    re.compile(r"^admin\d*$", re.IGNORECASE),
    re.compile(r"^team[_\-]?test[_\-]?\d*$", re.IGNORECASE),
    re.compile(r"^probe.*$", re.IGNORECASE),
    re.compile(r"^[a-z]$", re.IGNORECASE),         # single-char names like "a", "b", "c"
    re.compile(r"^[a-z]{1,3}$"),                    # 1-3 char all-LOWERCASE names: a, ai, ab, abc, daf
    re.compile(r"^test\d+@google\.com$", re.IGNORECASE),
    re.compile(r"^admin\d+@google\.com$", re.IGNORECASE),
    re.compile(r"^test\d+@admin\d+\.edu$", re.IGNORECASE),
    re.compile(r"^admin\d+@admin\d+\.edu$", re.IGNORECASE),
    re.compile(r"^team[_\-]?test[_\-]?\d+@google\.com$", re.IGNORECASE),
    re.compile(r"^probe\d*@.*$", re.IGNORECASE),
]
# Real-email shape: must contain @ and a TLD-like fragment, length >= 5.
_EMAIL_SHAPE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _fetch(path: str) -> dict:
    """One REST GET against the database root. Returns {} on failure."""
    url = f"{DB_URL}/{path.lstrip('/')}.json"
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            return json.load(resp) or {}
    except Exception as e:
        print(f"[fetch] {path} failed: {e}", file=sys.stderr)
        return {}


def _is_valid_participant(name: str, email: str) -> bool:
    """True if this looks like a real research participant.

    Empty / unparseable emails fail. Names or emails matching any
    development pattern fail. The check is intentionally strict; we
    err on the side of FALSE so dev pollution doesn't inflate counts.
    """
    name = (name or "").strip().lower()
    email = (email or "").strip().lower()
    if not email:
        return False
    if not _EMAIL_SHAPE.match(email):
        return False
    if len(name) < 2:
        return False
    for pat in _INVALID_PATTERNS:
        if pat.match(name) or pat.match(email):
            return False
    # Also reject name == email (often a placeholder).
    if name == email:
        return False
    return True


def _session_completed(sess: dict) -> bool:
    """True if the session reached its end-of-flow.

    Required: phase == 'completed' OR status == 'completed'. We accept
    either because team/oracle/hybrid set them slightly differently.
    """
    if not isinstance(sess, dict):
        return False
    return (sess.get("phase") == "completed") or (sess.get("status") == "completed")


def _session_has_survey(sess: dict, role: str) -> bool:
    """True if THIS role submitted a survey for this session."""
    surv = sess.get("survey") or {}
    return isinstance(surv, dict) and role in surv


# Module-level: every (email -> set of names ever observed). Populated by
# both collectors so render_table can show real names alongside emails.
NAMES_BY_EMAIL: dict[str, set[str]] = defaultdict(set)


def collect_counts_legacy(
    require_completed: bool = True,
    require_survey: bool = True,
) -> tuple[dict[tuple[str, str], set[str]], dict[tuple[str, str], int], dict, list]:
    """Walk every session in legacy teambench/sessions and bucket by (task, mode).

    Returns:
        participants_by_task_mode: { (task_id, mode) -> set[email] }
        sessions_by_task_mode:     { (task_id, mode) -> int (unique sessions) }
        rejection_reasons:         { reason -> count }  (debug)
        skipped_session_ids:       [(sid, reason)]      (debug, capped at 50)
    """
    sessions = _fetch("teambench/sessions") or {}
    participants_by_task_mode: dict[tuple[str, str], set[str]] = defaultdict(set)
    sessions_by_task_mode: dict[tuple[str, str], int] = defaultdict(int)
    rejection_reasons: dict[str, int] = defaultdict(int)
    skipped: list[tuple[str, str]] = []

    for sid, sess in sessions.items():
        if not isinstance(sess, dict):
            rejection_reasons["malformed_session"] += 1
            continue
        task_id = sess.get("taskId")
        mode = sess.get("mode")
        if not task_id or not mode:
            rejection_reasons["missing_task_or_mode"] += 1
            if len(skipped) < 50:
                skipped.append((sid, "missing_task_or_mode"))
            continue
        if require_completed and not _session_completed(sess):
            rejection_reasons["not_completed"] += 1
            if len(skipped) < 50:
                skipped.append((sid, f"not_completed (phase={sess.get('phase')})"))
            continue
        parts = sess.get("participants") or {}
        if not isinstance(parts, dict):
            rejection_reasons["no_participants_dict"] += 1
            continue
        counted_any_for_session = False
        for role, p in parts.items():
            if not isinstance(p, dict):
                continue
            name = p.get("name", "")
            email = p.get("email", "")
            if not _is_valid_participant(name, email):
                rejection_reasons["invalid_identity"] += 1
                continue
            if require_survey and not _session_has_survey(sess, role):
                rejection_reasons["no_survey"] += 1
                continue
            em = email.strip().lower()
            participants_by_task_mode[(task_id, mode)].add(em)
            if name and name.strip():
                NAMES_BY_EMAIL[em].add(name.strip())
            counted_any_for_session = True
        if counted_any_for_session:
            sessions_by_task_mode[(task_id, mode)] += 1

    return participants_by_task_mode, sessions_by_task_mode, dict(rejection_reasons), skipped


def collect_counts_new(
    require_completed: bool = True,
    require_survey: bool = True,
) -> tuple[dict[tuple[str, str], set[str]], dict[tuple[str, str], int], dict, list]:
    """Walk teambench_new/tasks/{taskId}/{mode}/sessions and bucket by (task, mode).

    teambench_new is the authoritative analysis tree (rolled out 2026-04-25).
    Sessions older than that exist only in legacy. Use this source when the
    question is "what shows up in the new structured analysis tree?".

    Per-participant survey check uses the role-suffixed path
    participants/{pid}/survey/{role} (matches the role-suffix change
    shipped in commit b307815).
    """
    root = _fetch("teambench_new") or {}
    tasks = (root.get("tasks") or {}) if isinstance(root, dict) else {}
    participants_by_task_mode: dict[tuple[str, str], set[str]] = defaultdict(set)
    sessions_by_task_mode: dict[tuple[str, str], int] = defaultdict(int)
    rejection_reasons: dict[str, int] = defaultdict(int)
    skipped: list[tuple[str, str]] = []

    for task_id, by_mode in (tasks or {}).items():
        if not isinstance(by_mode, dict):
            continue
        for mode, mode_blob in by_mode.items():
            sessions = (mode_blob or {}).get("sessions") or {}
            if not isinstance(sessions, dict):
                continue
            for sid, sess in sessions.items():
                if not isinstance(sess, dict):
                    rejection_reasons["malformed_session"] += 1
                    continue
                meta = sess.get("meta") or {}
                if require_completed and not _session_completed(meta):
                    rejection_reasons["not_completed"] += 1
                    if len(skipped) < 50:
                        skipped.append((sid, f"not_completed (phase={meta.get('phase')})"))
                    continue
                parts = sess.get("participants") or {}
                if not isinstance(parts, dict):
                    rejection_reasons["no_participants_dict"] += 1
                    continue
                counted_any_for_session = False
                for pid, blob in parts.items():
                    if not isinstance(blob, dict):
                        continue
                    profile = blob.get("profile") or {}
                    name = profile.get("name", "")
                    email = profile.get("email", "")
                    role = profile.get("role", "")
                    if not _is_valid_participant(name, email):
                        rejection_reasons["invalid_identity"] += 1
                        continue
                    if require_survey:
                        # Survey is keyed by role suffix in v2:
                        # participants/{pid}/survey/{role}
                        surv = blob.get("survey") or {}
                        if not (isinstance(surv, dict) and role and role in surv):
                            rejection_reasons["no_survey"] += 1
                            continue
                    em = email.strip().lower()
                    participants_by_task_mode[(task_id, mode)].add(em)
                    if name and name.strip():
                        NAMES_BY_EMAIL[em].add(name.strip())
                    counted_any_for_session = True
                if counted_any_for_session:
                    sessions_by_task_mode[(task_id, mode)] += 1

    return participants_by_task_mode, sessions_by_task_mode, dict(rejection_reasons), skipped


def collect_counts(
    source: str,
    require_completed: bool,
    require_survey: bool,
):
    """Dispatch to the right collector based on --source flag."""
    if source == "legacy":
        return collect_counts_legacy(require_completed, require_survey)
    if source == "new":
        return collect_counts_new(require_completed, require_survey)
    raise ValueError(f"unknown source: {source!r} (expected 'new' or 'legacy')")


def render_table(
    parts: dict[tuple[str, str], set[str]],
    sessions: dict[tuple[str, str], int],
    *, csv: bool = False, details: bool = False,
) -> None:
    rows = sorted(parts.keys(), key=lambda x: (x[0], x[1]))
    def _label(em: str) -> str:
        names = NAMES_BY_EMAIL.get(em) or set()
        if not names:
            return em
        # Sort for stable output; '|' joins multiple distinct names per email.
        return f"{em}  ({' | '.join(sorted(names))})"

    if csv:
        print("task_id,mode,n_participants,n_sessions,participants")
        for (tid, mode) in rows:
            emails = sorted(parts[(tid, mode)])
            labels = [_label(em).replace(',', ' ') for em in emails]
            print(f"{tid},{mode},{len(emails)},{sessions[(tid, mode)]},{';'.join(labels)}")
        return

    # Pretty table.
    if not rows:
        print("(no rows match the current filters — try --include-cancelled or --no-survey-required)")
        return
    col_task_w = max(len(t) for t,_ in rows + [("task_id","")])
    col_mode_w = max(len(m) for _,m in rows + [("","mode")])
    col_task_w = max(col_task_w, len("task_id"))
    col_mode_w = max(col_mode_w, len("mode"))
    print(f"{'task_id'.ljust(col_task_w)}  {'mode'.ljust(col_mode_w)}  n_participants  n_sessions")
    print(f"{'-'*col_task_w}  {'-'*col_mode_w}  --------------  ----------")
    for (tid, mode) in rows:
        n_p = len(parts[(tid, mode)])
        n_s = sessions[(tid, mode)]
        print(f"{tid.ljust(col_task_w)}  {mode.ljust(col_mode_w)}  {str(n_p).rjust(14)}  {str(n_s).rjust(10)}")
        if details:
            for em in sorted(parts[(tid, mode)]):
                print(f"  └─ {_label(em)}")

    # Per-mode totals.
    by_mode_unique: dict[str, set[str]] = defaultdict(set)
    by_mode_sessions: dict[str, int] = defaultdict(int)
    for (tid, mode), emails in parts.items():
        by_mode_unique[mode] |= emails
        by_mode_sessions[mode] += sessions[(tid, mode)]
    print()
    print("PER-MODE TOTALS (unique humans across all tasks)")
    print(f"{'mode'.ljust(col_mode_w)}  unique_humans  total_sessions")
    print(f"{'-'*col_mode_w}  -------------  --------------")
    for mode in sorted(by_mode_unique):
        print(f"{mode.ljust(col_mode_w)}  {str(len(by_mode_unique[mode])).rjust(13)}  {str(by_mode_sessions[mode]).rjust(14)}")

    # Grand total: unique humans across ALL modes.
    everyone: set[str] = set()
    for emails in parts.values():
        everyone |= emails
    print()
    print(f"GRAND TOTAL unique participants across ALL tasks/modes: {len(everyone)}")


def main(argv: Iterable[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", choices=("new", "legacy"), default="new",
                   help="Which Firebase tree to count from. 'new' = teambench_new "
                        "(authoritative analysis tree, only contains sessions from "
                        "the v2 cutover onward); 'legacy' = teambench/sessions "
                        "(includes older test data + sessions written by stale "
                        "browser tabs that bypassed v2). Default: new.")
    p.add_argument("--include-cancelled", action="store_true",
                   help="Also count sessions whose phase != 'completed'.")
    p.add_argument("--no-survey-required", action="store_true",
                   help="Don't require the participant to have submitted a survey.")
    p.add_argument("--csv", action="store_true", help="Emit CSV instead of table.")
    p.add_argument("--details", action="store_true",
                   help="Also list each participant's email under their (task, mode) row.")
    p.add_argument("--debug", action="store_true",
                   help="Print rejection reason histogram + sample skipped session ids.")
    args = p.parse_args(list(argv))

    parts, sessions, reasons, skipped = collect_counts(
        source=args.source,
        require_completed=not args.include_cancelled,
        require_survey=not args.no_survey_required,
    )

    print(f"# source: {args.source}  | completed_only={not args.include_cancelled}  | survey_required={not args.no_survey_required}")
    render_table(parts, sessions, csv=args.csv, details=args.details)

    if args.debug:
        print()
        print("REJECTION REASONS (sessions/participants filtered out)")
        for reason, n in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {n}")
        if skipped:
            print()
            print(f"FIRST {len(skipped)} SKIPPED SESSION IDS")
            for sid, reason in skipped[:20]:
                print(f"  {sid} ({reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
