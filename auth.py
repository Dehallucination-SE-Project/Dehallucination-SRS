"""Environment-configured Bearer authentication and role authorization."""

from dataclasses import dataclass
from enum import Enum
import json
import os
import secrets
from typing import Any, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


class Role(str, Enum):
    END_USER = "end_user"
    APPLICATION_DEVELOPER = "application_developer"
    REVIEWER = "reviewer"
    ADMINISTRATOR = "administrator"


class Permission(str, Enum):
    SUBMIT_VERIFICATION = "submit_verification"
    RETRIEVE_EVIDENCE = "retrieve_evidence"
    CREATE_REPORT = "create_report"
    READ_OWN_REPORT = "read_own_report"
    READ_ANY_REPORT = "read_any_report"
    REVIEW_REPORTS = "review_reports"
    VIEW_SERVICE_STATUS = "view_service_status"
    MANAGE_CONFIGURATION = "manage_configuration"
    READ_SECURITY_AUDIT = "read_security_audit"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.END_USER: frozenset({
        Permission.SUBMIT_VERIFICATION,
        Permission.READ_OWN_REPORT,
    }),
    Role.APPLICATION_DEVELOPER: frozenset({
        Permission.SUBMIT_VERIFICATION,
        Permission.RETRIEVE_EVIDENCE,
        Permission.CREATE_REPORT,
        Permission.READ_OWN_REPORT,
    }),
    Role.REVIEWER: frozenset({
        Permission.READ_ANY_REPORT,
        Permission.REVIEW_REPORTS,
    }),
    Role.ADMINISTRATOR: frozenset({
        Permission.VIEW_SERVICE_STATUS,
        Permission.MANAGE_CONFIGURATION,
        Permission.READ_SECURITY_AUDIT,
    }),
}

AUTH_CREDENTIALS_ENV = "DEHALLUCINATION_API_CREDENTIALS"
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    """Verified subject and role associated with an API credential."""

    subject: str
    role: Role


@dataclass(frozen=True)
class _Credential:
    token: str
    principal: Principal


def _authentication_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication is not configured correctly",
    )


def _load_credentials() -> list[_Credential]:
    raw_configuration = os.environ.get(AUTH_CREDENTIALS_ENV)
    if not raw_configuration:
        raise _authentication_unavailable()

    try:
        entries: Any = json.loads(raw_configuration)
    except (TypeError, ValueError) as exc:
        raise _authentication_unavailable() from exc

    if not isinstance(entries, list) or not entries:
        raise _authentication_unavailable()

    credentials = []
    seen_tokens = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise _authentication_unavailable()

        token = entry.get("token")
        subject = entry.get("subject")
        role_value = entry.get("role")
        if (
            not isinstance(token, str)
            or not token
            or token != token.strip()
            or not token.isascii()
            or not isinstance(subject, str)
            or not subject.strip()
            or not isinstance(role_value, str)
        ):
            raise _authentication_unavailable()

        if token in seen_tokens:
            raise _authentication_unavailable()
        seen_tokens.add(token)

        try:
            role = Role(role_value)
        except ValueError as exc:
            raise _authentication_unavailable() from exc

        credentials.append(
            _Credential(
                token=token,
                principal=Principal(subject=subject.strip(), role=role),
            )
        )

    return credentials


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    """Authenticate a Bearer token and return its configured subject and role."""
    configured_credentials = _load_credentials()
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise _invalid_credentials()

    provided_token = credentials.credentials
    if not provided_token.isascii():
        raise _invalid_credentials()
    for configured in configured_credentials:
        if secrets.compare_digest(provided_token, configured.token):
            return configured.principal

    raise _invalid_credentials()


def has_permission(principal: Principal, permission: Permission) -> bool:
    """Return whether a principal's configured role grants a permission."""
    return permission in ROLE_PERMISSIONS[principal.role]


def require_permission(permission: Permission) -> Callable[..., Principal]:
    """Build a dependency that authenticates and checks one permission."""

    def dependency(principal: Principal = Depends(require_principal)) -> Principal:
        if not has_permission(principal, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return principal

    return dependency


def require_any_permission(
    *permissions: Permission,
) -> Callable[..., Principal]:
    """Build a dependency that accepts any listed permission."""
    if not permissions:
        raise ValueError("at least one permission is required")

    def dependency(principal: Principal = Depends(require_principal)) -> Principal:
        if not any(has_permission(principal, item) for item in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return principal

    return dependency
