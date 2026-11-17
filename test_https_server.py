"""Tests for the HTTPS deployment launcher."""

from unittest.mock import Mock

import pytest

import serve_https


@pytest.mark.parametrize(
    "configured_values",
    [
        {},
        {"TLS_CERT_FILE": "server.crt"},
        {"TLS_KEY_FILE": "server.key"},
    ],
)
def test_https_launcher_fails_closed_without_both_tls_files(
    monkeypatch,
    configured_values,
):
    monkeypatch.delenv("TLS_CERT_FILE", raising=False)
    monkeypatch.delenv("TLS_KEY_FILE", raising=False)
    for name, value in configured_values.items():
        monkeypatch.setenv(name, value)

    run = Mock()
    monkeypatch.setattr(serve_https.uvicorn, "run", run)

    with pytest.raises(RuntimeError, match="TLS_CERT_FILE and TLS_KEY_FILE"):
        serve_https.start()

    run.assert_not_called()


def test_https_launcher_passes_tls_configuration_to_uvicorn(monkeypatch):
    monkeypatch.setenv("TLS_CERT_FILE", "C:/run/certs/server.crt")
    monkeypatch.setenv("TLS_KEY_FILE", "C:/run/secrets/server.key")
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    run = Mock()
    monkeypatch.setattr(serve_https.uvicorn, "run", run)

    serve_https.start()

    run.assert_called_once_with(
        "main:app",
        host="0.0.0.0",
        port=8443,
        ssl_certfile="C:/run/certs/server.crt",
        ssl_keyfile="C:/run/secrets/server.key",
    )
