# CodeMentor AI Architecture

## Overview

CodeMentor AI follows a simple three-layer architecture:

1. Presentation layer: React + Vite frontend
2. API layer: FastAPI backend
3. Data layer: SQLite with SQLAlchemy

## Frontend Responsibilities

- Collect prompt, language, and action type
- Show Monaco Editor input and output panels
- Handle login, registration, and logout
- Attach JWT tokens to protected requests
- Display history, downloads, and result summaries

## Backend Responsibilities

- Validate request data
- Enforce authentication and ownership checks
- Generate structured prompts
- Call the AI provider through a single isolated service
- Validate AI JSON before using it
- Run conservative static analysis
- Save history records to SQLite

## Data Flow

```text
User action
  -> React page
  -> API service
  -> FastAPI endpoint
  -> Prompt template
  -> AI service
  -> JSON validation
  -> SQLite save
  -> Response to UI
```

## Key Design Choices

- JWT tokens are used for user sessions
- Passwords are hashed with bcrypt
- SQL output is analysis-only
- History is scoped per authenticated user
- AI output is normalized to a strict schema

## Why This Architecture Works Well for a College Project

- It is easy to explain in a viva or presentation
- It demonstrates both frontend and backend skills
- It includes authentication, persistence, and validation
- It is modular enough to extend later

