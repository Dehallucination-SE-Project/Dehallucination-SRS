"""Regression tests for Git's local-secret ignore rules."""

import subprocess
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parent


@pytest.mark.parametrize(
    "secret_path",
    [
        ".env",
        ".env.local",
        ".env.production",
        "secrets/credentials.json",
        "private/server.key",
        "private/server.pem",
        "private/server.p12",
        "private/server.pfx",
    ],
)
def test_local_secret_files_are_ignored_by_git(secret_path):
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", secret_path],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == secret_path


def test_env_example_can_be_tracked():
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", ".env.example"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert not result.stdout
