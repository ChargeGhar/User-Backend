# Logout Reliability Plan (`docs/Plans/Logout/00_MASTER_Logout.md`)

## Summary
- First action: create a single master planning doc at `docs/Plans/Logout/00_MASTER_Logout.md` with this exact implementation/test spec before code changes.
- Goal: fix user-facing logout failures on shared devices by making logout idempotent for authenticated requests and removing the current 500 error path.
- Confirmed baseline issues:
  - `/api/auth/logout` can fail on token mismatch (`token_user_mismatch`) for cross-user stale-token scenarios.
  - Invalid refresh token paths currently can produce `500` because `AuthService` passes unsupported kwargs to `BaseService.handle_service_error`.

## Implementation Changes
- `POST /api/auth/logout` contract (public behavior):
  - Keep `IsAuthenticated` (invalid/missing access token still returns `401`).
  - Accept either `refresh_token` or `refresh` in request body.
  - Treat refresh token as optional for logout success path.
  - Return success `200` for authenticated logout requests even when refresh token is missing, malformed, already blacklisted, expired, or from another user.
  - Add response metadata fields:
    - `token_revoked: bool`
    - `revocation_reason: one_of(valid_blacklisted, already_invalid, token_mismatch, token_missing)`
- Auth service behavior:
  - Refactor `AuthService.logout_user` to best-effort revoke token without raising on token errors/mismatch.
  - Remove hard failure on cross-user token mismatch; log warning and return success metadata.
  - Keep audit logging as best-effort (do not fail logout if audit write fails).
- Error-handling regression fix:
  - In `AuthService.logout_user` and `AuthService.refresh_token`, replace invalid `handle_service_error(..., code=...)` usage with explicit `ServiceException(detail=..., code=...)` so invalid refresh token paths return `400` instead of `500`.

## API/Type Updates
- `LogoutSerializer` input:
  - Add optional alias support for `refresh` in addition to `refresh_token`.
  - Normalize into a single internal `refresh_token` value or `None`.
- Logout response payload:
  - Keep existing envelope and message.
  - Add non-breaking fields `token_revoked` and `revocation_reason` in `data`.
- `POST /api/auth/refresh`:
  - No shape change; behavior change only: invalid token consistently returns `400` with `invalid_refresh_token` code.

## Test Plan
- Add focused auth tests (new `tests/user/auth/test_logout.py`):
  - Valid access + valid refresh for same user -> `200`, `token_revoked=true`.
  - Valid access + malformed refresh -> `200`, `token_revoked=false`, reason `already_invalid`.
  - Valid access + already-blacklisted refresh -> `200`, `token_revoked=false` (or true if implementation can detect blacklist state), non-error reason.
  - Valid access (User B) + refresh from User A -> `200`, `token_revoked=false`, reason `token_mismatch`.
  - Valid access + missing refresh field -> `200`, `token_revoked=false`, reason `token_missing`.
- Add refresh regression test:
  - `POST /api/auth/refresh` with invalid token returns `400` (not `500`) and `invalid_refresh_token`.
- Manual verification on running Docker stack:
  - Two-user shared-device sequence with mixed tokens confirms no logout failure response and no server `500`.

## Assumptions and Defaults
- Chosen behavior: idempotent logout (`Always 200`) for authenticated callers.
- Chosen plan format: single master plan file under `docs/Plans/Logout`.
- Scope is limited to user auth logout/refresh reliability; no partner/admin auth redesign.
