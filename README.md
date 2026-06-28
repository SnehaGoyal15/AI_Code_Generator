# CodeMentor AI

CodeMentor AI is a full-stack academic project that acts as an AI-assisted coding mentor. It helps users generate code, explain code, debug code, optimize solutions, review code quality, generate documentation, and maintain personal coding history through a secure web workspace.

## 1. Project Objective

The objective of CodeMentor AI is to provide a beginner-friendly coding assistant that can support software development learning and practice. It is designed for college submission, demonstrating full-stack development, authentication, database integration, AI prompt handling, static analysis, and responsive UI design.

## 2. Key Features

- Generate code from natural language prompts
- Explain code in beginner-friendly language
- Debug existing source code
- Suggest optimized solutions
- Review code quality using a rubric
- Generate documentation and README content
- Save and restore coding history
- Download generated code and full reports
- Secure login and registration with JWT authentication
- SQL Safety Mode with text-only analysis
- Static checks for selected languages

## 3. Supported Programming Languages

- Python
- Java
- C
- C++
- JavaScript
- SQL

## 4. Technology Stack

- Frontend: React, Vite, plain CSS, Monaco Editor
- Backend: FastAPI
- Database: SQLite
- ORM: SQLAlchemy
- Authentication: JWT, Passlib with bcrypt
- Testing: pytest, FastAPI TestClient

## 5. System Architecture Overview

CodeMentor AI uses a clean client-server architecture:

- The React frontend collects prompts, language selection, optional input code, and action selection.
- The frontend sends authenticated requests to the FastAPI backend.
- The backend validates requests, builds structured prompts, and calls the configured AI provider.
- AI responses are validated as JSON before being returned.
- The backend stores each action in SQLite under the authenticated user account.
- The frontend retrieves the current user history and restores saved sessions from the backend.

High-level flow:

```text
User -> React UI -> FastAPI API -> AI Provider
                     |               |
                     v               v
                 SQLite history   JSON validation
```

## 6. Folder Structure

```text
code-mentor-ai/
  backend/
    app/
      main.py
      database.py
      models.py
      schemas.py
      config.py
      ai_service.py
      prompt_templates.py
      services/
      routers/
      utils/
    requirements.txt
    .env.example
    tests/
  frontend/
    src/
      components/
      pages/
      services/
      styles/
    package.json
  docs/
    architecture.md
    api-documentation.md
    security.md
    demo-script.md
  README.md
  .gitignore
```

## 7. Setup Instructions

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm

### Backend setup

```bash
cd code-mentor-ai/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and add the required environment variables described below.

### Frontend setup

```bash
cd code-mentor-ai/frontend
npm install
cp .env.example .env
```

## 8. Environment Variables

### Backend

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLite connection string |
| `FRONTEND_ORIGINS` | Allowed CORS origins |
| `GEMINI_MODEL` | Gemini model name, defaults to `gemini-2.5-flash` |
| `GEMINI_API_KEY` | Gemini API key |
| `BREVO_API_KEY` | Brevo API key for login email notifications |
| `BREVO_FROM` | Verified Brevo sender address |
| `EMAIL_SEND_TIMEOUT_SECONDS` | Timeout for outgoing email requests |
| `LOGIN_OTP_EXPIRES_IN_MINUTES` | OTP lifetime for login verification |
| `JWT_SECRET` | JWT signing secret |
| `JWT_ALGORITHM` | JWT algorithm, usually `HS256` |
| `JWT_EXPIRES_IN_MINUTES` | Access token lifetime |

### Frontend

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Backend URL for API requests |
| `VITE_USE_MOCK_AI` | Enables mock responses when the AI key is unavailable |

The backend uses Gemini only for AI features. Login email notifications use Brevo when configured. Keep all API keys in the backend environment and never expose them in frontend code.

## 9. How to Run the Backend

```bash
cd code-mentor-ai/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend health check:

```text
http://127.0.0.1:8000/api/health
```

## 10. How to Run the Frontend

```bash
cd code-mentor-ai/frontend
npm run dev
```

Open the Vite URL shown in the terminal, usually:

```text
http://127.0.0.1:5173
```

## 11. API Endpoint Table

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/health` | No | Health check |
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Request a login OTP by email |
| POST | `/api/auth/verify-login-otp` | No | Verify OTP and receive JWT |
| GET | `/api/auth/me` | Yes | Get current user profile |
| POST | `/api/generate` | Yes | Generate code |
| POST | `/api/explain` | Yes | Explain code |
| POST | `/api/debug` | Yes | Debug code |
| POST | `/api/optimize` | Yes | Optimize code |
| POST | `/api/review` | Yes | Review code quality |
| POST | `/api/documentation` | Yes | Generate documentation |
| POST | `/api/history` | Yes | Save a history record |
| GET | `/api/history` | Yes | List user history |
| GET | `/api/history/{history_id}` | Yes | Fetch one history item |
| DELETE | `/api/history/{history_id}` | Yes | Delete one history item |

## 12. Authentication Flow

1. A user registers or logs in from the frontend.
2. The backend hashes passwords with `passlib[bcrypt]`.
3. Registration still returns a JWT access token right away.
4. Login now happens in two steps: the user enters email and password, then the backend sends a one-time code to the registered email address.
5. The frontend submits the OTP to `/api/auth/verify-login-otp`.
6. The backend validates the OTP and issues a JWT access token with an expiry time.
7. The frontend stores the token locally for this academic project.
8. The frontend sends `Authorization: Bearer <token>` on protected requests.
9. The backend validates the token and scopes history to the authenticated user.
10. Logging out clears the token and returns the user to the login screen.

## 13. Security Measures

- Passwords are never stored in plain text.
- JWT secrets and AI keys stay only in backend environment variables.
- Login uses a one-time password flow and OTPs are hashed before storage.
- Brevo sends login OTP emails when configured, and login still works in development if email is unavailable.
- Protected endpoints reject unauthenticated requests with `401`.
- History data is filtered by `user_id` so one user cannot read another user’s records.
- SQL mode is analysis-only and never executes database queries.
- Static checks are conservative and never execute user code.
- The frontend does not expose the AI API key.
- AI responses are validated before use to reduce malformed output risks.

## 14. SQL Safety Mode

When SQL is selected, CodeMentor AI switches into a text-only safety mode.

### What it does

- Never connects to a real database
- Never executes SQL
- Flags destructive or data-changing statements
- Labels queries as read-only or write/destructive when possible
- Warns about `SELECT *`, missing `WHERE`, and unclear joins
- Suggests safer read-only preview queries when relevant

### Why it matters

This keeps the project safe for academic use and makes it clear that SQL output is for analysis and learning only.

## 15. Limitations

CodeMentor AI provides AI-assisted suggestions and static analysis. It does not guarantee that generated or corrected code is fully error-free. User review and testing are required.

Additional limitations:

- AI output quality depends on the configured model and prompt quality
- Static checks are pattern-based and may miss complex bugs
- The project currently supports a limited set of languages
- Token storage in `localStorage` is acceptable for an academic demo, but stronger browser security would be needed for production

## 16. Future Enhancements

- Add refresh token support
- Add user profile settings
- Add feedback/rating submission for each history item
- Add syntax highlighting themes and editor preferences
- Add more language support
- Add export to PDF for reports
- Add stronger role-based access control
- Add richer code smell analysis
- Add deployment configuration for Render, Vercel, or Railway

## 17. Screenshots

Add project screenshots using these placeholder filenames:

- `docs/screenshots/login-page.png`
- `docs/screenshots/workspace-home.png`
- `docs/screenshots/sql-safety-mode.png`
- `docs/screenshots/review-rubric.png`
- `docs/screenshots/history-sidebar.png`
- `docs/screenshots/download-report.png`

## 18. Testing Instructions

The backend includes deterministic automated tests with a separate SQLite test database and mocked AI calls.

```bash
cd code-mentor-ai/backend
pytest -q
```

What the tests cover:

- Health check
- Validation errors
- Authentication
- Protected route authorization
- History access control
- Static SQL safety checks
- Static brace detection

## 19. Sample Prompts for Users

- `Write a Python function to reverse a string.`
- `Explain this Java code in simple words.`
- `Debug this C++ function and fix the issues.`
- `Optimize this JavaScript loop for better performance.`
- `Review this Python script and give a quality score.`
- `Generate documentation for this SQL project helper.`

## 20. Demo Notes

For a 5-minute presentation, use the step-by-step demo in `docs/demo-script.md`.
