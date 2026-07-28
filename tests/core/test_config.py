"""Test production config validation."""
from unittest.mock import patch

import pytest
from app.core.config import settings, validate_production_config


def test_production_env_requires_admin_token() -> None:
    """APP_ENV=production without ADMIN_TOKEN should raise RuntimeError."""
    with (
        patch.object(settings, "app_env", "production"),
        patch.object(settings, "admin_token", ""),
    ):
        with pytest.raises(RuntimeError, match="ADMIN_TOKEN is required"):
            validate_production_config()


def test_production_env_with_token_passes() -> None:
    """APP_ENV=production with valid ADMIN_TOKEN should pass."""
    with (
        patch.object(settings, "app_env", "production"),
        patch.object(settings, "admin_token", "my-secret-token"),
    ):
        validate_production_config()  # should not raise
