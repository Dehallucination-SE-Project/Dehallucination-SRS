# API authentication and role permissions

The API uses Bearer tokens configured by the operator. It does not create
credentials automatically and has no default token. Configure
`DEHALLUCINATION_API_CREDENTIALS` before starting the application. If it is
missing or invalid, protected routes return HTTP 503. Requests without a valid
token return HTTP 401 with a Bearer challenge; an authenticated caller without
the required role receives HTTP 403.

## Configure credentials in PowerShell

Create a different long, random token for each subject. Keep this JSON in a
secret manager for deployed environments. For local development, set it only
in the current PowerShell session (replace the example tokens before use):

```powershell
$env:DEHALLUCINATION_API_CREDENTIALS = '[{"token":"REPLACE_WITH_RANDOM_TOKEN_1","subject":"app-1","role":"application_developer"},{"token":"REPLACE_WITH_RANDOM_TOKEN_2","subject":"reviewer-1","role":"reviewer"},{"token":"REPLACE_WITH_RANDOM_TOKEN_3","subject":"admin-1","role":"administrator"}]'
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Run the server command in the same PowerShell window where you set the
environment variable. Do not commit tokens, paste them into issue comments, or
use the test-only tokens from `test_support.py` outside automated tests. Restart
the API after changing the credentials. Tokens are currently held in process
environment configuration; rotation takes effect after restart.

## Approved role matrix

| Role | Permissions |
| --- | --- |
| `end_user` | Submit a verification request; read own reports |
| `application_developer` | Submit verification; retrieve evidence; create reports for own accepted requests; read own reports |
| `reviewer` | Read any report; list and read reviews; approve or reject pending reviews |
| `administrator` | View detailed service status; reserved permissions for configuration management and security-audit reads |

Each configured credential has one `subject` and one `role`. Subjects identify
ownership and audit actors; the reviewer field in a decision must match the
authenticated reviewer subject. A developer cannot create a report for another
subject's verification request. End users and developers cannot read reports
belonging to other subjects. Reviewers can read any report for review work.

## Route access

`/` and `/api/v1/health` are public liveness endpoints; health exposes no
dependency details. Detailed `/api/v1/status` requires the administrator role.
Verification requires `end_user` or `application_developer`. Evidence retrieval
and report creation require `application_developer`. Report retrieval requires
an end-user, developer, or reviewer credential, with owner checks for the first
two roles. Review routes require `reviewer`.

The approved administrator permissions for configuration and audit access are
reserved in the policy, but the corresponding management/read API routes do not
exist yet. This implementation does not invent those endpoints. Source-policy
and threshold configuration remain outside this change.

Report ownership is stored on the report row in SQLite. Existing report
databases are migrated by adding a nullable `owner_subject` column; reports
created before this change have no known owner, so end users and developers
cannot read those legacy rows. Reviewers retain their authorized read access.
