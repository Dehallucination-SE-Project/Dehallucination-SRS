# Dehallucination-SRS
Software Requirements Specification for Project ID 39 - Dehallucination Add-On Module for Enhancing Reliability of AI Applications

API operator setup and the approved role-permission policy are documented in
[AUTHENTICATION.md](AUTHENTICATION.md).

## Configuration and secrets

Set sensitive values through the operating-system or deployment environment, or
through the deployment platform's secret manager. Do not place credentials,
API tokens, private keys, or other secret values in source files or commit them
to this repository.

Local `.env` files and common private-key files are ignored by Git. The
application does not load `.env` files automatically; use them only with local
tooling that is explicitly configured to load them. A tracked `.env.example`
may document variable names, but must contain placeholders rather than real
values.

ARCHITECTURE:
<img width="411" height="931" alt="image" src="https://github.com/user-attachments/assets/e2606331-2b20-43b0-9feb-80d8e5d91b4e" />
