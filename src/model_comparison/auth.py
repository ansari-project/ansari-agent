"""HTTP Basic Authentication (optional)."""

import secrets
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .config import config

security = HTTPBasic(auto_error=False)


def verify_credentials(
    credentials: Optional[HTTPBasicCredentials] = Depends(security)
) -> Optional[str]:
    """Verify HTTP Basic Auth credentials if auth is enabled.

    Returns username if valid, None if auth disabled, raises HTTP 401 if invalid.
    """
    # If auth is not enabled, allow access
    if not config.auth_enabled:
        return None

    # Auth is enabled, credentials are required
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Use secrets.compare_digest to prevent timing attacks
    is_correct_username = secrets.compare_digest(
        credentials.username, config.auth_username
    )
    is_correct_password = secrets.compare_digest(
        credentials.password, config.auth_password or ""
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
