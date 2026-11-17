"""Test-only environment configuration for real Bearer-auth requests."""

import json

import pytest

from test_support import TEST_CREDENTIALS


@pytest.fixture(autouse=True)
def configure_test_api_credentials(monkeypatch):
    monkeypatch.setenv(
        "DEHALLUCINATION_API_CREDENTIALS",
        json.dumps(TEST_CREDENTIALS),
    )
