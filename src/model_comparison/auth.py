"""HTTP Basic Authentication."""

import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .config import config

security = HTTPBasic()


def verify_credentials(
    credentials: HTTPBasicCredentials = Depends(security)
) -> str:
    """Verify HTTP Basic Auth credentials.

    Returns username if valid, raises HTTP 401 if invalid.
    """
    # Use secrets.compare_digest to prevent timing attacks
    is_correct_username = secrets.compare_digest(
        credentials.username, config.AUTH_USERNAME
    )
    is_correct_password = secrets.compare_digest(
        credentials.password, config.AUTH_PASSWORD
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
