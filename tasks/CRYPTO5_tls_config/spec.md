# CRYPTO5: TLS Configuration Hardening

## Goal

A security audit identified 5 issues in the TLS/SSL server configuration. Fix the genuine
security vulnerabilities while preserving intentional configurations required for backward
compatibility with legacy clients.

## Requirements

1. Fix genuine security issues identified in `security_audit.txt`
2. Preserve intentional configurations documented in `LEGACY_CLIENTS.md`
3. All tests must pass: `pytest tests/`
4. TLS handshake must still work after changes
5. Legacy client compatibility tests must pass

## Supporting Documents

- `security_audit.txt` — Lists all 5 audit findings with severity ratings
- `LEGACY_CLIENTS.md` — Documents which configurations are intentional for legacy support
- `TLS_SPEC.md` — Target TLS security requirements

## Contradiction to Resolve

The security audit recommends fixing ALL 5 issues. However, `LEGACY_CLIENTS.md` documents
that 2 of the findings are intentional configurations required for backward compatibility
with deployed legacy hardware. These 2 must be preserved.

`LEGACY_CLIENTS.md` is authoritative. When the audit findings and legacy requirements
conflict, trust `LEGACY_CLIENTS.md`.
