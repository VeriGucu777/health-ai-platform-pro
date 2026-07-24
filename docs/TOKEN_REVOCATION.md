# Token Revocation — Deferred Implementation

This document describes the recommended approach for server-side token revocation in Health AI Platform Pro. **WS1 intentionally does not implement revocation** because a reliable solution requires either a database migration or shared external storage.

## Current Behavior (After WS1)

- Access and refresh tokens remain cryptographically signed JWTs with separate `type` claims.
- `POST /api/v1/auth/logout` validates the refresh token but does **not** invalidate outstanding tokens server-side.
- Clients must discard tokens locally after logout.
- Access tokens remain valid until they expire (default: 30 minutes).
- Refresh tokens remain valid until they expire (default: 7 days).

This is acceptable for the current single-stage deployment but should be upgraded before high-sensitivity production use.

## Why In-Memory Revocation Was Not Implemented

An in-process denylist (set/dict of revoked JTIs) would:

- Break across multiple Uvicorn/Gunicorn workers
- Reset on every deploy or process restart
- Give a false sense of security in horizontally scaled environments such as Render

WS1 avoids this anti-pattern.

## Recommended Future Approach (Minimal Database Option)

**Option A — `token_version` on `users` (preferred minimal migration):**

1. Add `token_version INTEGER NOT NULL DEFAULT 0` to `users`.
2. Include `tv` claim in access and refresh JWTs.
3. On login/refresh, embed the user's current `token_version`.
4. On logout or password change, increment `token_version`.
5. Reject tokens whose `tv` claim does not match the stored value.

Pros: one integer comparison per request; no Redis; works across workers.
Cons: invalidates **all** active sessions for the user on logout (usually desirable).

## Recommended Future Approach (Refresh Rotation)

After Option A, add refresh-token rotation:

1. Add `jti` claim to refresh tokens.
2. Store revoked refresh JTIs in PostgreSQL with `expires_at` for TTL cleanup, **or** store `last_valid_refresh_jti` on the user row.
3. On refresh, issue a new pair and invalidate the presented refresh token.
4. Detect refresh-token reuse as a potential compromise signal.

## Recommended Future Approach (High Scale)

- Redis-backed JTI blocklist with TTL matching token expiry
- Or OAuth2-style opaque refresh tokens stored server-side

## Implementation Trigger

Implement revocation when any of the following become requirements:

- Server-side logout must immediately invalidate access tokens
- Multi-worker production enforces stricter session control
- Compliance review requires demonstrable token invalidation

Until then, keep access tokens short-lived and document client-side token discard on logout.
