"""Run the API over HTTPS using certificate paths supplied by deployment."""

import os

import uvicorn


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8443


def start() -> None:
    """Start Uvicorn with TLS, failing closed when TLS files are not configured."""
    certificate_file = os.environ.get("TLS_CERT_FILE", "").strip()
    key_file = os.environ.get("TLS_KEY_FILE", "").strip()
    if not certificate_file or not key_file:
        raise RuntimeError(
            "Set TLS_CERT_FILE and TLS_KEY_FILE before starting the HTTPS server."
        )

    host = os.environ.get("HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        ssl_certfile=certificate_file,
        ssl_keyfile=key_file,
    )


if __name__ == "__main__":
    start()
