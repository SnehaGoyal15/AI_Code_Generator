# CodeMentor AI API Documentation

## Base URL

```text
http://127.0.0.1:8000/api
```

## Health

### `GET /health`

Returns backend status.

Example response:

```json
{
  "success": true,
  "message": "CodeMentor AI backend is running.",
  "environment": "development"
}
```

## Authentication

### `POST /auth/register`

Creates a new account and returns a JWT access token.

### `POST /auth/login`

Starts the OTP login flow by verifying credentials and sending a one-time code to the user's email.

### `POST /auth/verify-login-otp`

Verifies the OTP and returns a JWT access token.

### `GET /auth/me`

Returns the authenticated user's profile.

## AI Actions

All AI action endpoints accept:

```json
{
  "prompt": "string",
  "language": "Python",
  "code": "string or null"
}
```

### `POST /generate`
### `POST /explain`
### `POST /debug`
### `POST /optimize`
### `POST /review`
### `POST /documentation`

These endpoints:

- validate the request
- call the configured AI provider
- validate JSON output
- save history to MongoDB
- return the `history_id`

## History

### `POST /history`

Saves a history record for the current user.

### `GET /history`

Returns the authenticated user's history items, newest first.

### `GET /history/{history_id}`

Returns one history record if it belongs to the authenticated user.

### `DELETE /history/{history_id}`

Deletes one history record if it belongs to the authenticated user.

## Response Notes

- Protected endpoints require `Authorization: Bearer <token>`
- Unauthorized requests return `401`
- Accessing another user's history returns `404`
- SQL requests are treated as text-only analysis
