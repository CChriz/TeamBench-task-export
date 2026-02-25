"""
Parameterized generator for P1: Policy-Driven Config Change.

Each seed produces:
  - Different policy values (rate limits, timeouts, password requirements,
    allowed/blocked features, retention periods)
  - A seed-specific policy.txt with those values
  - A starting config.json with intentional violations
  - expected.json with the correct compliant config
  - seed-specific spec.md and brief.md
"""
from __future__ import annotations

import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# Log level options
LOG_LEVELS_ALLOWED = [["warn", "error"], ["error"], ["info", "warn", "error"]]
LOG_LEVELS_ALL = ["debug", "info", "warn", "error"]

# Auth method options
AUTH_METHODS = ["jwt", "oauth2", "saml"]
AUTH_METHODS_DEPRECATED = ["basic", "none", "token"]

# CORS options
CORS_OPTIONS = [[], ["https://internal.example.com"], ["https://app.corp.net"]]


class Generator(TaskGenerator):
    task_id = "P1_policy_config"
    domain = "policy"
    difficulty = "easy"
    languages = ["json"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # ── Pick seed-specific policy values ──

        # Rule 1: max_connections range
        conn_min = rng.choice([50, 100, 150, 200])
        conn_max = rng.choice([300, 400, 500, 600, 800])
        correct_conn = rng.randint(conn_min, conn_max)

        # Rule 2: timeout_sec (exact)
        correct_timeout = rng.choice([15, 30, 45, 60])

        # Rule 3: ssl_enabled (always must be true)
        correct_ssl = True

        # Rule 4: log_level (enum from allowed set)
        allowed_log_levels_idx = rng.randint(0, len(LOG_LEVELS_ALLOWED) - 1)
        allowed_log_levels = LOG_LEVELS_ALLOWED[allowed_log_levels_idx]
        correct_log_level = rng.choice(allowed_log_levels)

        # Rule 5: retry_count (exact)
        correct_retry = rng.choice([2, 3, 5])

        # Rule 6: cors_origins
        cors_idx = rng.randint(0, len(CORS_OPTIONS) - 1)
        correct_cors = CORS_OPTIONS[cors_idx]

        # Rule 7: rate_limit_rpm range
        rpm_min = rng.choice([30, 60, 100])
        rpm_max = rpm_min + rng.choice([60, 120, 180])
        correct_rpm = rng.randint(rpm_min, rpm_max)

        # Rule 8: auth_method (enum)
        correct_auth = rng.choice(AUTH_METHODS)

        # Rule 9: session_timeout_min (exact)
        correct_session_timeout = rng.choice([15, 30, 60, 120])

        # Rule 10: min_password_length (exact)
        correct_min_pw = rng.choice([8, 10, 12, 16])

        # ── Build correct config ──
        correct_config = {
            "max_connections": correct_conn,
            "timeout_sec": correct_timeout,
            "ssl_enabled": correct_ssl,
            "log_level": correct_log_level,
            "retry_count": correct_retry,
            "cors_origins": correct_cors,
            "rate_limit_rpm": correct_rpm,
            "auth_method": correct_auth,
            "session_timeout_min": correct_session_timeout,
            "min_password_length": correct_min_pw,
        }

        # ── Build violated config (intentional violations) ──
        # Violate at least 4-6 keys
        violated_config = dict(correct_config)

        # Violation 1: max_connections out of range
        violated_config["max_connections"] = rng.choice([
            conn_max + rng.randint(10, 200),
            max(0, conn_min - rng.randint(1, 40)),
        ])

        # Violation 2: wrong timeout
        wrong_timeout = correct_timeout + rng.choice([15, 30, 60])
        violated_config["timeout_sec"] = wrong_timeout

        # Violation 3: ssl disabled
        violated_config["ssl_enabled"] = False

        # Violation 4: forbidden log level
        forbidden_levels = [l for l in LOG_LEVELS_ALL if l not in allowed_log_levels]
        if forbidden_levels:
            violated_config["log_level"] = rng.choice(forbidden_levels)

        # Violation 5: wrong retry count
        violated_config["retry_count"] = correct_retry + rng.choice([2, 5, 7])

        # Violation 6: bad cors origins
        violated_config["cors_origins"] = ["*"]

        # Violation 7: rpm out of range
        violated_config["rate_limit_rpm"] = rng.choice([
            max(0, rpm_min - rng.randint(10, 50)),
            rpm_max + rng.randint(50, 200),
        ])

        # Violation 8: deprecated auth
        violated_config["auth_method"] = rng.choice(AUTH_METHODS_DEPRECATED)

        # Violation 9: wrong session timeout
        violated_config["session_timeout_min"] = correct_session_timeout + rng.choice([15, 45, 90])

        # Violation 10: add an extra key (policy violation: no extra keys)
        violated_config["extra_flag"] = True

        # ── Generate policy.txt ──
        cors_policy_text = (
            "an empty list []"
            if not correct_cors
            else f"exactly {json.dumps(correct_cors)}"
        )
        allowed_log_str = " or ".join(f'"{l}"' for l in allowed_log_levels)
        forbidden_log_str = ", ".join(
            f'"{l}"' for l in LOG_LEVELS_ALL if l not in allowed_log_levels
        )
        auth_deprecated_str = " and ".join(f'"{m}"' for m in AUTH_METHODS_DEPRECATED)
        fy_year = 2025 + (seed % 3)

        policy_txt = f"""CONFIGURATION POLICY DOCUMENT
Version: {2 + seed % 3}.{seed % 5}
Effective Date: {fy_year}-01-01
Classification: INTERNAL

=== MANDATORY CONFIGURATION RULES ===

Rule 1: Connection Limits
  max_connections must be set between {conn_min} and {conn_max} (inclusive).
  Values outside this range are a compliance violation.

Rule 2: Timeout
  timeout_sec must be exactly {correct_timeout} seconds.
  No other value is acceptable.

Rule 3: SSL/TLS
  ssl_enabled must be true.
  Plaintext connections are prohibited by security policy.

Rule 4: Logging
  log_level must be set to {allowed_log_str}.
  {forbidden_log_str} levels are prohibited in production.

Rule 5: Retry Policy
  retry_count must be exactly {correct_retry}.
  Higher values cause cascading failures. Lower values reduce resilience.

Rule 6: CORS
  cors_origins must be {cors_policy_text}.
  Wildcard origins ("*") are prohibited. Specific origins must be
  configured through the gateway, not the application.

Rule 7: Rate Limiting
  rate_limit_rpm must be between {rpm_min} and {rpm_max} (inclusive).
  This ensures fair usage without blocking legitimate traffic.

Rule 8: Authentication
  auth_method must be "{correct_auth}".
  {auth_deprecated_str} are deprecated and prohibited.

Rule 9: Session Timeout
  session_timeout_min must be exactly {correct_session_timeout} minutes.
  Sessions must not exceed this duration for security compliance.

Rule 10: Password Policy
  min_password_length must be exactly {correct_min_pw}.
  Shorter passwords do not meet the minimum security standard.

=== END OF POLICY ===

No additional configuration keys are permitted beyond the 10 listed above.
Any extra keys constitute a policy violation.
"""

        # ── expected.json ──
        expected = {
            "correct_config": correct_config,
            "policy_rules": {
                "max_connections": {"type": "int_range", "min": conn_min, "max": conn_max},
                "timeout_sec": {"type": "exact_int", "value": correct_timeout},
                "ssl_enabled": {"type": "exact_bool", "value": True},
                "log_level": {"type": "enum", "allowed": allowed_log_levels},
                "retry_count": {"type": "exact_int", "value": correct_retry},
                "cors_origins": {"type": "exact_list", "value": correct_cors},
                "rate_limit_rpm": {"type": "int_range", "min": rpm_min, "max": rpm_max},
                "auth_method": {"type": "enum", "allowed": AUTH_METHODS},
                "session_timeout_min": {"type": "exact_int", "value": correct_session_timeout},
                "min_password_length": {"type": "exact_int", "value": correct_min_pw},
            },
            "required_keys": list(correct_config.keys()),
        }

        corpus_files = {
            "policy.txt": policy_txt,
        }

        workspace_files = {
            "config.json": json.dumps(violated_config, indent=2) + "\n",
        }

        spec_md = self._generate_spec(
            cors_origins=correct_cors,
            rule_count=10,
            correct_timeout=correct_timeout,
            correct_retry=correct_retry,
            correct_min_pw=correct_min_pw,
            correct_auth=correct_auth,
        )
        brief_md = self._generate_brief()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            corpus_files=corpus_files,
        )

    def _generate_spec(self, cors_origins: list, rule_count: int = 10,
                       correct_timeout: int = 30, correct_retry: int = 3,
                       correct_min_pw: int = 12, correct_auth: str = "jwt") -> str:
        cors_str = json.dumps(cors_origins)
        return f"""# P1: Policy-Driven Config Change

## Goal
Generate a configuration file (`output/config.json`) that complies with ALL {rule_count} rules
defined in the policy document.

## Context
This deployment uses {correct_auth} authentication with a {correct_timeout}s timeout policy,
{correct_retry} retries, and a minimum password length of {correct_min_pw} characters.
The CORS origins are restricted to: {cors_str}.

## Hard Requirements

1. Produce `output/config.json` that satisfies every rule in `corpus/policy.txt`.
2. The config must be valid JSON with exact key names as specified in the policy.
3. The config must contain exactly the keys enumerated in the policy document -- no more, no less.
4. Each key's value must satisfy the constraint specified for that key in the policy
   (exact values, permitted ranges, or allowed enumerations as appropriate).
5. The initial `config.json` template in the workspace has intentional policy violations
   that must be identified and corrected.

## Policy Source

Read `corpus/policy.txt` to obtain the authoritative rules. The Planner must derive
the required values for each configuration key directly from that document.

## Deliverables
- Corrected `output/config.json` in workspace.
- Verifier must check each policy rule and produce attestation.
"""

    def _generate_brief(self) -> str:
        return """# P1: Policy-Driven Config (Brief)

Fix the config file to comply with the compliance policy.
The Planner has the full policy rules -- ask the Planner for specific requirements.
Output goes to `output/config.json`.
"""
