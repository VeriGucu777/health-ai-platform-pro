# Refresh token sessions (pilot)

## Model

Health AI Platform Pro uses **multi-session refresh rotation**:

- Each successful **login** creates a row in `user_refresh_sessions` with an HMAC digest of the refresh JWT `jti` (never the raw token).
- Each successful **refresh** rotates the digest on that session row (replay of the previous refresh JWT is denied).
- **Multiple devices** may hold independent refresh sessions for the same user (separate login flows).
- **Access tokens** remain valid until expiry unless `token_version` changes.

## Global revocation

These operations revoke **all** refresh sessions and bump `token_version` (invalidates all access tokens):

- `POST /api/v1/auth/logout`
- Authenticated password change

## Security notes

- Refresh replay is audited with `reason_code: refresh_token_reuse`.
- Raw refresh tokens must not appear in logs or database columns.
