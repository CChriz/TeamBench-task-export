"""Internal utilities — warehouse inventory tracking service."""


def old_format(data: dict) -> str:
    """Deprecated: use format_data() instead. Will be removed Q3."""
    import json
    return json.dumps(data, sort_keys=True)


def format_data(data: dict, *, indent: int = 2) -> str:
    """Format data for output. Preferred API."""
    import json
    return json.dumps(data, indent=indent, sort_keys=True)


def parse_id(raw: str) -> int:
    """Parse a string ID to integer."""
    return int(raw.strip())
