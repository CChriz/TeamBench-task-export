"""
Input validation helpers for marketplace_api.

These validators enforce strict rules. They should only be applied to
endpoints where strict validation is appropriate.
"""
import re
from typing import Optional


def validate_email(value: str) -> bool:
    """Return True if value looks like a valid email address."""
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value))


def validate_user(data: dict) -> Optional[str]:
    """Validate user payload. Returns error string or None."""
    if not data.get("name"):
        return "'name' is required and must be non-empty"
    if not data.get("email"):
        return "'email' is required"
    if not validate_email(data["email"]):
        return "'email' must be a valid email address"
    return None


def validate_item(data: dict) -> Optional[str]:
    """Validate item payload. Returns error string or None."""
    if not data.get("name"):
        return "'name' is required and must be non-empty"
    price = data.get("price")
    if price is None:
        return "'price' is required"
    try:
        price = float(price)
    except (TypeError, ValueError):
        return "'price' must be a number"
    if price <= 0:
        return "'price' must be a positive number"
    return None


def validate_order(data: dict) -> Optional[str]:
    """Validate order payload. Returns error string or None."""
    uid = data.get("user_id")
    if uid is None:
        return "'user_id' is required"
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        return "'user_id' must be an integer"
    if uid <= 0:
        return "'user_id' must be a positive integer"

    iid = data.get("item_id")
    if iid is None:
        return "'item_id' is required"
    try:
        iid = int(iid)
    except (TypeError, ValueError):
        return "'item_id' must be an integer"
    if iid <= 0:
        return "'item_id' must be a positive integer"

    qty = data.get("quantity")
    if qty is None:
        return "'quantity' is required"
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        return "'quantity' must be an integer"
    if qty < 1:
        return "'quantity' must be >= 1"
    return None


def validate_report(data: dict, allowed_types: list) -> Optional[str]:
    """Validate report payload. Returns error string or None."""
    rt = data.get("report_type")
    if not rt:
        return "'report_type' is required"
    if rt not in allowed_types:
        return f"'report_type' must be one of: {', '.join(allowed_types)}"
    return None
