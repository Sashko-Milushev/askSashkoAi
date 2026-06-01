# GitHub Copilot Custom Instructions

## Project Overview
This is a FastAPI project called **askSashkoAi** — an AI-powered assistant.

## Response Style
- Be concise and to the point
- No filler phrases — skip "Certainly!", "Great question!", "Of course!", "Sure!", or any similar openers
- No closing remarks like "Let me know if you need anything else" or "Hope that helps!"
- Use bullet points and structured formatting — avoid long prose paragraphs
- Keep answers short and direct; if more detail is needed, use headers to organize it
- Use Python best practices and follow PEP 8
- Prefer FastAPI idiomatic patterns (dependency injection, Pydantic models, async/await)
- Always add type hints to functions and variables

## Questions to the User
- When a question requires user input, format it like this:
  ```
  ❓ QUESTION: <your question here>
  ```
- Always put questions in a clearly visible block — uppercase label, impossible to miss
- Never bury a question inside a paragraph

## Tech Stack
- **Framework:** FastAPI
- **Language:** Python 3.10+
- **AI/ML:** (define your AI libraries here, e.g. OpenAI, LangChain, etc.)
- **Knowledge base:** PDF documents in `knowledge_resources/`

## Code Conventions
- Use `snake_case` for variables and functions
- Use `PascalCase` for classes and Pydantic models
- Group imports: standard library → third-party → local
- Prefer async functions for route handlers

## Preferred Libraries
- `fastapi` for API routing
- `pydantic` for data validation
- `uvicorn` for serving
- `python-dotenv` for environment variables

## What to Avoid
- Do not use `print()` for logging — use Python's `logging` module instead
- Do not hardcode secrets or API keys — use environment variables

## Additional Instructions
<!-- Add any other custom instructions below -->

