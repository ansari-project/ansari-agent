"""Tests for HTTP Basic Auth."""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from model_comparison.auth import verify_credentials
from model_comparison.config import config


def test_verify_credentials_valid():
    """Test valid credentials."""
    creds = HTTPBasicCredentials(
        username=config.AUTH_USERNAME,
        password=config.AUTH_PASSWORD
    )
    username = verify_credentials(creds)
    assert username == config.AUTH_USERNAME


def test_verify_credentials_invalid_username():
    """Test invalid username."""
    creds = HTTPBasicCredentials(
        username="wrong",
        password=config.AUTH_PASSWORD
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_credentials(creds)

    assert exc_info.value.status_code == 401


def test_verify_credentials_invalid_password():
    """Test invalid password."""
    creds = HTTPBasicCredentials(
        username=config.AUTH_USERNAME,
        password="wrong"
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_credentials(creds)

    assert exc_info.value.status_code == 401


def test_verify_credentials_both_invalid():
    """Test both username and password invalid."""
    creds = HTTPBasicCredentials(
        username="wrong",
        password="wrong"
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_credentials(creds)

    assert exc_info.value.status_code == 401
