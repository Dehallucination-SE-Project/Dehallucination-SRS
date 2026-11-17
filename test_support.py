"""Shared test credentials for exercising real API authentication."""

TEST_CREDENTIALS = [
    {
        "token": "test-end-user-token",
        "subject": "end-user-1",
        "role": "end_user",
    },
    {
        "token": "test-developer-token",
        "subject": "application-1",
        "role": "application_developer",
    },
    {
        "token": "test-reviewer-token",
        "subject": "qa-reviewer",
        "role": "reviewer",
    },
    {
        "token": "test-admin-token",
        "subject": "administrator-1",
        "role": "administrator",
    },
]

TEST_TOKENS = {
    entry["role"]: entry["token"]
    for entry in TEST_CREDENTIALS
}


def auth_headers(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_TOKENS[role]}"}
