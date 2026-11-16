# Security Audit Events

`AuditTrail` stores an event ID, request ID, actor, action, UTC timestamp, and
JSON details for each recorded event.

Successful human-review decisions are recorded as `review_decision` events.
Their details include `outcome: success` and the approved or rejected decision.
Failed review requests do not change review state and do not create a
`review_decision` event.

The current API has no source-configuration administration endpoints, so this
change does not add or audit configuration operations. The reviewer value is
currently supplied in the request body. Until authentication is restored, that
value is not a verified identity and must not be treated as proof of who made
the decision.
