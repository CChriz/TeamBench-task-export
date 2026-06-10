"""Configuration for auth_service."""

SECRET_KEY = "super-secret-key-2024-prod"
ALGORITHM = "HS256"
TOKEN_LIFETIME = 300  # seconds
GRACE_WINDOW = 60  # seconds — BUG: should be 0 for production
ALLOWED_ISSUERS = ['auth.myapp.com', 'sso.myapp.com']
REFRESH_TOKEN_LIFETIME = 1200  # seconds
