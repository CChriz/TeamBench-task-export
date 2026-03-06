"""
Parameterized generator for CRYPTO5: TLS Configuration Hardening.

Each seed produces a TLS/SSL server config with 5 audit findings.
2 findings are intentional for legacy backward compat and must be preserved.
3 findings are genuine vulnerabilities that must be fixed.

Fix issues (always):
  - Weak cipher (RC4 variant)
  - Self-signed certificate
  - No OCSP stapling

Preserve issues (intentional):
  - TLS 1.0 enabled (legacy POS/ATM/IoT devices)
  - Short session timeout (legacy client constraint)

Seed variation: server type, port, cipher names, timeout values, legacy device types.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized pools ──────────────────────────────────────────────

SERVER_TYPES = ["web_gateway", "api_server", "mqtt_broker"]
SERVER_DESCS = [
    "HTTPS web gateway for customer-facing portal",
    "REST API server for mobile and partner clients",
    "MQTT broker for IoT device telemetry",
]
PORTS = [443, 8443, 8883]

WEAK_CIPHER_NAMES = [
    "TLS_RSA_WITH_RC4_128_SHA",
    "TLS_RSA_WITH_RC4_128_MD5",
    "ECDHE-RSA-RC4-SHA",
]
GOOD_CIPHER_SUITES = [
    "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:ECDHE-RSA-AES256-GCM-SHA384",
    "TLS_AES_128_GCM_SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:TLS_AES_256_GCM_SHA384",
]

SESSION_TIMEOUTS = [60, 45, 90]

LEGACY_DEVICE_TYPES = [
    ("POS terminals", "Verifone VX520 running TLS 1.0 firmware"),
    ("ATM kiosks", "NCR SelfServ 80-series with fixed TLS stack"),
    ("IoT sensors", "legacy Modbus-TCP bridges with TLS 1.0 only"),
]

LEGACY_TIMEOUT_REASONS = [
    "ATM sessions must timeout quickly to prevent card skimming on idle terminals",
    "POS terminals in high-traffic retail need fast session recycling",
    "IoT devices have limited memory and cannot maintain long-lived sessions",
]

CERT_DOMAINS = ["portal.example.com", "api.example.com", "iot.example.com"]


class Generator(TaskGenerator):
    task_id = "CRYPTO5_tls_config"
    domain = "Security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(SERVER_TYPES)

        server_type = SERVER_TYPES[idx]
        server_desc = SERVER_DESCS[idx]
        port = PORTS[idx]
        weak_cipher = WEAK_CIPHER_NAMES[idx]
        good_ciphers = GOOD_CIPHER_SUITES[idx]
        session_timeout = SESSION_TIMEOUTS[idx]
        legacy_devices, legacy_desc = LEGACY_DEVICE_TYPES[idx]
        legacy_timeout_reason = LEGACY_TIMEOUT_REASONS[idx]
        cert_domain = CERT_DOMAINS[idx]

        workspace_files = self._make_workspace(
            server_type=server_type,
            server_desc=server_desc,
            port=port,
            weak_cipher=weak_cipher,
            good_ciphers=good_ciphers,
            session_timeout=session_timeout,
            legacy_devices=legacy_devices,
            legacy_desc=legacy_desc,
            legacy_timeout_reason=legacy_timeout_reason,
            cert_domain=cert_domain,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CRYPTO5_tls_config")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="CRYPTO5_tls_config",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "server_type": server_type,
                "fix_issues": ["weak_cipher_rc4", "self_signed_cert", "no_ocsp_stapling"],
                "preserve_issues": ["tls_1_0", "short_timeout"],
                "config_file": "server/tls_config.py",
                "weak_cipher": weak_cipher,
                "session_timeout": session_timeout,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Security"},
        )

    def _make_workspace(
        self,
        server_type: str,
        server_desc: str,
        port: int,
        weak_cipher: str,
        good_ciphers: str,
        session_timeout: int,
        legacy_devices: str,
        legacy_desc: str,
        legacy_timeout_reason: str,
        cert_domain: str,
    ) -> dict:
        files = {}

        # ── server/__init__.py ────────────────────────────────────────────
        files["server/__init__.py"] = f'"""{server_type} server package."""\n'

        # ── server/tls_config.py — the buggy config ───────────────────────
        files["server/tls_config.py"] = f'''\
"""
TLS/SSL configuration for {server_desc}.

This module configures the SSL context used by the server.
Several settings have been flagged by a security audit.
"""
import ssl
import os


def create_ssl_context() -> ssl.SSLContext:
    """Create and configure the SSL context for the {server_type}.

    Returns:
        Configured ssl.SSLContext ready for use with the server.
    """
    # Create context — allow TLS 1.0 through TLS 1.3
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # FINDING 1: TLS 1.0 enabled — legacy {legacy_devices} require it
    # Do NOT disable TLSv1 — see LEGACY_CLIENTS.md
    # context.minimum_version = ssl.TLSVersion.TLSv1_2  # Would break legacy

    # FINDING 2: Weak cipher RC4 included in cipher suite
    context.set_ciphers(
        "{good_ciphers}:{weak_cipher}"
    )

    # FINDING 3: Self-signed certificate
    cert_path = os.path.join(os.path.dirname(__file__), "certs")
    context.load_cert_chain(
        certfile=os.path.join(cert_path, "self_signed.pem"),
        keyfile=os.path.join(cert_path, "server.key"),
    )

    # FINDING 4: No OCSP stapling configured
    # OCSP stapling is not enabled — clients cannot verify cert revocation status

    # FINDING 5: Short session timeout
    # Legacy {legacy_devices} need fast session recycling
    context.session_timeout = {session_timeout}

    # Additional settings
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3

    return context


def get_server_config() -> dict:
    """Return server configuration dict."""
    return {{
        "host": "0.0.0.0",
        "port": {port},
        "server_type": "{server_type}",
        "tls_enabled": True,
        "session_timeout": {session_timeout},
    }}


def get_cipher_list() -> list[str]:
    """Return the currently configured cipher list."""
    ctx = create_ssl_context()
    return [c["name"] for c in ctx.get_ciphers()]
'''

        # ── server/certs/ — self-signed cert files (dummy) ────────────────
        files["server/certs/.gitkeep"] = ""
        # Generate a minimal self-signed cert inline for testing
        files["server/cert_generator.py"] = f'''\
"""
Certificate generation utilities.

Currently generates self-signed certificates. Should be updated to load
CA-signed certificates from a configured path.
"""
import os
import subprocess
import tempfile


CERT_DIR = os.path.join(os.path.dirname(__file__), "certs")


def generate_self_signed_cert(domain: str = "{cert_domain}") -> tuple[str, str]:
    """Generate a self-signed certificate and key.

    This is a SECURITY ISSUE — production should use CA-signed certs.

    Returns:
        Tuple of (cert_path, key_path)
    """
    cert_path = os.path.join(CERT_DIR, "self_signed.pem")
    key_path = os.path.join(CERT_DIR, "server.key")

    if not os.path.exists(cert_path):
        os.makedirs(CERT_DIR, exist_ok=True)
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", key_path, "-out", cert_path,
            "-days", "365", "-nodes",
            "-subj", f"/CN={{domain}}"
        ], check=True, capture_output=True)

    return cert_path, key_path


def load_ca_signed_cert(
    cert_file: str = "server.pem",
    key_file: str = "server.key",
    ca_bundle: str = "ca-bundle.pem",
) -> tuple[str, str, str]:
    """Load CA-signed certificate files.

    This is the CORRECT approach for production.

    Args:
        cert_file: Path to the server certificate.
        key_file: Path to the private key.
        ca_bundle: Path to the CA certificate bundle.

    Returns:
        Tuple of (cert_path, key_path, ca_path)
    """
    cert_path = os.path.join(CERT_DIR, cert_file)
    key_path = os.path.join(CERT_DIR, key_file)
    ca_path = os.path.join(CERT_DIR, ca_bundle)
    return cert_path, key_path, ca_path
'''

        # ── security_audit.txt ────────────────────────────────────────────
        files["security_audit.txt"] = f'''\
# Security Audit Report — {server_type}
# Date: 2024-01-15
# Auditor: SecureCheck Inc.

## Findings Summary

| # | Severity | Finding                          | Recommendation                |
|---|----------|----------------------------------|-------------------------------|
| 1 | MEDIUM   | TLS 1.0 enabled                  | Disable TLS 1.0; set min TLSv1.2 |
| 2 | HIGH     | Weak cipher {weak_cipher} in suite | Remove RC4 ciphers entirely   |
| 3 | HIGH     | Self-signed certificate in use   | Use CA-signed certificate     |
| 4 | MEDIUM   | No OCSP stapling configured      | Enable OCSP stapling          |
| 5 | LOW      | Short session timeout ({session_timeout}s) | Increase to >= 300s    |

## Detailed Findings

### Finding 1: TLS 1.0 Enabled [MEDIUM]
The server accepts TLS 1.0 connections. TLS 1.0 has known vulnerabilities
(BEAST, POODLE) and is deprecated by PCI-DSS since June 2018.
**Recommendation**: Set `context.minimum_version = ssl.TLSVersion.TLSv1_2`

### Finding 2: Weak Cipher {weak_cipher} [HIGH]
The cipher suite includes {weak_cipher}, which uses the RC4 stream cipher.
RC4 has known biases and is prohibited by RFC 7465.
**Recommendation**: Remove all RC4 ciphers from the cipher suite.

### Finding 3: Self-Signed Certificate [HIGH]
The server uses a self-signed certificate generated by `cert_generator.py`.
Self-signed certs provide no identity verification and trigger browser warnings.
**Recommendation**: Use a CA-signed certificate (Let's Encrypt or internal CA).

### Finding 4: No OCSP Stapling [MEDIUM]
OCSP stapling is not configured. Clients cannot efficiently verify whether
the server's certificate has been revoked.
**Recommendation**: Enable OCSP stapling in the SSL context.

### Finding 5: Short Session Timeout [LOW]
The TLS session timeout is set to {session_timeout} seconds, which is below
the recommended minimum of 300 seconds. Short timeouts increase TLS
handshake overhead.
**Recommendation**: Increase `session_timeout` to >= 300 seconds.
'''

        # ── LEGACY_CLIENTS.md ─────────────────────────────────────────────
        files["LEGACY_CLIENTS.md"] = f'''\
# Legacy Client Compatibility Requirements

## Background

The {server_type} serves both modern clients and deployed legacy hardware.
The following configurations are INTENTIONAL and MUST NOT be changed.

---

## TLS 1.0 Support — MUST PRESERVE

**Finding**: Security audit #1 recommends disabling TLS 1.0.
**Decision**: KEEP TLS 1.0 enabled. DO NOT set minimum_version to TLSv1.2.

**Rationale**: {legacy_desc} cannot negotiate TLS 1.2 or higher.
There are approximately 2,400 deployed units that will lose connectivity
if TLS 1.0 is disabled. Firmware updates require physical access to each
device and are scheduled for Q4 2025.

**Risk acceptance**: VP Engineering signed off on accepting the TLS 1.0
risk until all devices are upgraded. Compensating controls:
- Network segmentation (legacy devices on isolated VLAN)
- Rate limiting on legacy TLS connections
- Monitoring for known TLS 1.0 attack patterns

**Owner**: Infrastructure Team — contact before modifying TLS version settings.

---

## Short Session Timeout — MUST PRESERVE

**Finding**: Security audit #5 recommends increasing session timeout to >= 300s.
**Decision**: KEEP session timeout at {session_timeout} seconds. DO NOT increase.

**Rationale**: {legacy_timeout_reason}.
Longer sessions cause memory pressure on these constrained devices and
increase the window for session hijacking on shared physical terminals.

**Risk acceptance**: The short timeout is a deliberate security-positive
choice for this deployment context, not a misconfiguration.

**Owner**: Security Architecture — contact before modifying timeout settings.

---

## Issues That SHOULD Be Fixed

The following audit findings are genuine vulnerabilities:

- **Finding 2 (RC4 cipher)**: Remove {weak_cipher} — no legacy clients require RC4.
- **Finding 3 (Self-signed cert)**: Replace with CA-signed certificate.
- **Finding 4 (No OCSP stapling)**: Enable OCSP stapling for revocation checking.
'''

        # ── TLS_SPEC.md ──────────────────────────────────────────────────
        files["TLS_SPEC.md"] = f'''\
# TLS Security Specification — {server_type}

## Cipher Suites

- MUST use only AEAD ciphers (AES-GCM, ChaCha20-Poly1305)
- MUST NOT include RC4, DES, 3DES, NULL, or EXPORT ciphers
- RECOMMENDED cipher string: `{good_ciphers}`

## Certificate

- MUST use CA-signed certificate (self-signed NOT acceptable for production)
- MUST configure OCSP stapling for revocation checking
- Certificate MUST match the server domain: `{cert_domain}`

## Protocol Versions

- MUST support TLS 1.2 and TLS 1.3
- TLS 1.0/1.1 support: see LEGACY_CLIENTS.md for exceptions

## Session Management

- Session timeout: see LEGACY_CLIENTS.md for deployment-specific requirements
- MUST disable session tickets if TLS 1.0 is enabled (forward secrecy concern)
'''

        # ── tests/__init__.py ─────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_security.py — checks that fixes are applied ────────
        files["tests/test_security.py"] = f'''\
"""
Security hardening tests.

Verify that genuine vulnerabilities are fixed:
- RC4 cipher removed
- Self-signed cert replaced
- OCSP stapling enabled
"""
import pytest
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_no_rc4_in_cipher_config():
    """RC4 cipher must not appear in the active cipher configuration."""
    src = open("server/tls_config.py").read()
    # Remove comments
    code_lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
    code = "\\n".join(code_lines)
    assert "RC4" not in code and "rc4" not in code, (
        "RC4 cipher must be removed from the cipher suite configuration"
    )


def test_no_self_signed_cert_generation():
    """TLS config should not use generate_self_signed_cert."""
    src = open("server/tls_config.py").read()
    code_lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
    code = "\\n".join(code_lines)
    assert "self_signed" not in code.lower(), (
        "Self-signed certificate must be replaced with CA-signed certificate"
    )


def test_ocsp_stapling_configured():
    """OCSP stapling must be enabled in the TLS configuration."""
    src = open("server/tls_config.py").read()
    assert "ocsp" in src.lower() or "OCSP" in src or "stapling" in src.lower(), (
        "OCSP stapling must be configured in the SSL context"
    )


def test_no_weak_ciphers_in_suite():
    """No weak ciphers (DES, 3DES, RC4, NULL, EXPORT) in active config."""
    src = open("server/tls_config.py").read()
    code_lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
    code = "\\n".join(code_lines)
    for weak in ["DES", "3DES", "RC4", "NULL", "EXPORT", "aNULL", "eNULL"]:
        assert weak not in code, (
            f"Weak cipher/option '{{weak}}' must be removed from cipher configuration"
        )
'''

        # ── tests/test_legacy_compat.py — checks preserves are intact ─────
        files["tests/test_legacy_compat.py"] = f'''\
"""
Legacy client compatibility tests.

Verify that intentional configurations are preserved:
- TLS 1.0 support (for legacy {legacy_devices})
- Short session timeout ({session_timeout}s)
"""
import pytest
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_tls_1_0_not_disabled():
    """TLS 1.0 must NOT be explicitly disabled (legacy {legacy_devices} need it)."""
    src = open("server/tls_config.py").read()
    code_lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
    code = "\\n".join(code_lines)
    # Check that minimum_version is NOT set to TLSv1_2 or higher
    if "minimum_version" in code:
        assert "TLSv1_2" not in code and "TLSv1_3" not in code, (
            "TLS 1.0 must remain enabled — do not set minimum_version to TLSv1_2. "
            "Legacy {legacy_devices} require TLS 1.0. See LEGACY_CLIENTS.md."
        )
    # Check OP_NO_TLSv1 is not set
    assert "OP_NO_TLSv1" not in code or "OP_NO_TLSv1_1" in code.replace("OP_NO_TLSv1 ", "").replace("OP_NO_TLSv1\\n", ""), (
        "OP_NO_TLSv1 must NOT be set — legacy {legacy_devices} need TLS 1.0"
    )


def test_session_timeout_preserved():
    """Session timeout must remain at {session_timeout}s (legacy constraint)."""
    src = open("server/tls_config.py").read()
    timeout_match = re.search(r'session_timeout\\s*=\\s*(\\d+)', src)
    assert timeout_match is not None, "session_timeout setting not found in config"
    timeout_val = int(timeout_match.group(1))
    assert timeout_val <= 120, (
        f"Session timeout must remain short (<= 120s) for legacy {legacy_devices}. "
        f"Found: {{timeout_val}}s. See LEGACY_CLIENTS.md."
    )


def test_server_config_intact():
    """Server configuration function must still return valid config."""
    from server.tls_config import get_server_config
    config = get_server_config()
    assert config["port"] == {port}
    assert config["tls_enabled"] is True
    assert config["session_timeout"] == {session_timeout}
'''

        # ── tests/test_config.py — basic config sanity checks ─────────────
        files["tests/test_config.py"] = f'''\
"""
Configuration sanity tests.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_tls_config_module_imports():
    """TLS config module must import without errors."""
    from server import tls_config
    assert hasattr(tls_config, "create_ssl_context")
    assert hasattr(tls_config, "get_server_config")


def test_get_server_config_returns_dict():
    """get_server_config must return a dict with required keys."""
    from server.tls_config import get_server_config
    config = get_server_config()
    assert isinstance(config, dict)
    assert "host" in config
    assert "port" in config
    assert "tls_enabled" in config
'''

        files["requirements.txt"] = "pytest\n"

        return files
