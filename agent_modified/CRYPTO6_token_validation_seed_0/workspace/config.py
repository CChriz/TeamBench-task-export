"""Configuration for auth_service."""
import os
import secrets

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
TOKEN_LIFETIME = 300  # seconds
GRACE_WINDOW = 0  # seconds — zero grace for production
ALLOWED_ISSUERS = ['auth.myapp.com', 'sso.myapp.com']
REFRESH_TOKEN_LIFETIME = 1200  # seconds
