
import pytest

from auth import require_auth
from main import app


@pytest.fixture(autouse=True)
def configure_authentication_for_tests(request):
    """
    Bypass authentication only for legacy tests.

    Authentication-specific tests continue using the
    real authentication dependency.
    """

    if request.module.__name__ == "test_auth":
        yield
        return

    original_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[require_auth] = (
        lambda: "authenticated-test-user"
    )

    yield

    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)
