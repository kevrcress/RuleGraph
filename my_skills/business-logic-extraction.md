# Business Logic Extraction Skill

## Purpose
Extract genuine business rules from source code and documents using LLM analysis with prompt injection defenses.

## Key behaviors
- Always use the system prompt from `app/ingest/extractor.py` verbatim — it contains critical prompt injection framing
- Route to `claude-haiku-4-5` for complexity < 0.5, `claude-sonnet-4-5` for >= 0.5
- Return structured JSON with title, definition, and confidence per rule
- Parse JSON that may be wrapped in markdown code fences

## What counts as a business rule
- Status transition rules and restrictions
- Validation rules and invariants
- Payment and financial rules
- Eligibility and authorization rules
- Cancellation and refund policies
- Domain event triggers

## What to ignore
- Infrastructure code
- Dependency injection setup
- Logging and monitoring code
- Database migrations
- Test utilities
