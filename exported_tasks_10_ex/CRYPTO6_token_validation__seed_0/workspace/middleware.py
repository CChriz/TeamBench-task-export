"""
Request authentication middleware for auth_service.
"""
from auth import validate_token
from refresh import is_blacklisted


def authenticate_request(auth_header: str) -> dict | None:
    """
    Authenticate an incoming request using the Authorization header.

    Returns the token payload if valid, None otherwise.
    """
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Strip "Bearer " prefix

    # Check blacklist
    if is_blacklisted(token):
        return None

    return validate_token(token)
