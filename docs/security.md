# CodeMentor AI Security Notes

## Authentication

- Uses JWT access tokens
- Stores only hashed passwords
- Requires bearer tokens for protected routes
- Applies token expiration

## Authorization

- Every history record is owned by a single authenticated user
- History endpoints only return rows where `user_id` matches the current user
- Unauthorized access does not reveal another user's records

## AI Safety

- API keys stay in backend environment variables
- Frontend never receives the AI secret key
- AI responses are validated as JSON before use
- Provider failures return a safe fallback object

## SQL Safety

- SQL is analysis-only
- No database connections are created for user SQL input
- No query execution is performed
- Potentially destructive SQL is flagged with warnings

## Input Validation

- Prompt and code lengths are limited
- Unsupported languages are rejected
- Empty prompt or code is rejected for the appropriate action
- Static analysis is conservative and pattern-based

## Frontend Storage

- JWT token storage uses `localStorage` for the academic demo
- The app clears local token state on logout or auth failure

## Residual Risks

- AI output can still be imperfect
- Static analysis is not a replacement for real code review
- `localStorage` is acceptable for a class project, but a production app would need stronger token handling

