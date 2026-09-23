# Existing architecture reviewed

I reviewed the current DiaSift question/answer path before implementing the feature:

- `backend/main.py` for FastAPI request/response models and `/answer`.
- `frontend/app/api/answer/route.ts` for the Next.js proxy to the backend.
- `frontend/app/ask/page.tsx` and `frontend/app/styles.css` for response rendering, evidence display, and the question form.
- `scripts/rag_pipeline.py`, `scripts/rag_answer.py`, `scripts/safety_filter.py`, `scripts/scope_filter.py`, and related references through search results to understand retrieval, scope, safety, evidence, and source behavior.
- `tests/test_llm_fallback.py` and `requirements.txt` to understand existing tests and dependencies.
- `capstone/feature_requirements.md` and `capstone/present_architecture.md`.

The requested files `capstone/01_feature_requirements.md` and `capstone/02_architecture_context.md` were not present, so I used the matching requirement/context files that exist.

# Implementation approach

I added feedback around the existing answer flow rather than changing the RAG pipeline itself.

`POST /answer` still calls `run_rag_pipeline()` as before. After the pipeline returns, the API now saves a response record and adds `response_id` and `created_at` to the response payload. The frontend stores that ID with the assistant message and uses it when submitting feedback.

The ask page now shows a feedback control after each DiaSift response. Users can submit `Helpful` directly, or open `Not Helpful` reason options and optionally provide detail for `Other`. Submitting feedback calls `/api/feedback`, which proxies to backend `POST /feedback`; it does not call `/answer` and does not regenerate the response.

# Persistence approach

I used SQLite via Python's standard library in `backend/feedback_store.py`.

This fits the project because DiaSift currently has ChromaDB for vector retrieval but no application database. Feedback is structured operational data, not semantic retrieval data, so storing it in ChromaDB would mix responsibilities. SQLite avoids a new dependency, persists locally in `data/feedback.sqlite3`, supports review later, and is enough for this capstone-scale feature.

The store has:

- `responses`: one row per DiaSift response, including `response_id`, question, answer, evidence/scope/safety metadata, timestamp, and JSON payload.
- `feedback`: one row per response ID, including rating, optional negative reason/detail, created/updated timestamps.

Repeated feedback submissions update the existing feedback row for that response.

# Files changed

- `.gitignore`: ignores generated `data/feedback.sqlite3`.
- `backend/main.py`: adds response IDs/timestamps to answers, adds `POST /feedback`, adds `GET /feedback`, and validates feedback requests.
- `frontend/app/api/answer/route.ts`: removed an existing debug log.
- `frontend/app/ask/page.tsx`: adds response ID typing, feedback state, feedback submission, and feedback controls after assistant responses.
- `frontend/app/styles.css`: adds styling for feedback controls and textarea font inheritance.
- `capstone/05_run1_worklog.md`: records inspections, decisions, changes, tests, and uncertainties.

# Files created

- `backend/feedback_store.py`: SQLite schema, response persistence, feedback upsert, and feedback review helpers.
- `frontend/app/api/feedback/route.ts`: Next.js proxy for feedback submission.
- `tests/test_feedback_api.py`: backend API tests for response IDs, feedback saving, repeated updates, and invalid requests.
- `capstone/06_run1_agent_report.md`: this final implementation report.

# Dependencies

No new dependencies were added. SQLite is used through Python's standard library.

# Requirements implemented

- Every completed backend answer now receives a unique `response_id`.
- The frontend displays feedback options after DiaSift responses.
- Users can mark a response as `Helpful`.
- Users can mark a response as `Not Helpful`.
- Negative feedback can include one of the required reasons and optional text for `Other`.
- Feedback is persisted in SQLite, not only frontend state.
- Feedback links back to the exact saved response via `response_id`.
- Feedback includes timestamps.
- Saved feedback can be reviewed later through `GET /feedback` or by inspecting the SQLite database.
- Refusals and declined responses are handled because `POST /answer` saves every successful `run_rag_pipeline()` result, including unsafe and out-of-scope responses.
- Feedback submission is separate from answer submission and does not regenerate answers.
- ChromaDB and the RAG pipeline were not redesigned.
- No user accounts, IP addresses, browser fingerprints, or extra personal identifiers are collected.

# Testing

Existing tests run:

- `backend-venv/bin/python -m unittest discover -s tests`
- Result: passed, 6 tests.

New tests created:

- `tests/test_feedback_api.py`
- Covers answer response IDs, negative feedback save, repeated feedback update, unknown response rejection, and helpful feedback with invalid negative reason.

Frontend checks:

- `npm run typecheck`
- Result: passed.

Build check:

- `npm run build`
- Result: passed.

Manual/RAG checks:

- `backend-venv/bin/python scripts/rag_pipeline.py "What is type 2 diabetes?"`
- Result: dry RAG path returned strong evidence, citations, retrieved chunks, and in-scope status.
- `backend-venv/bin/python scripts/rag_pipeline.py "Should I stop taking metformin today?"`
- Result: safety/refusal path returned the existing unsafe-question refusal, no retrieved chunks, and no LLM call.

# Existing functionality

Normal question answering was checked through the dry RAG pipeline command. Retrieval still returned trusted source chunks and citations. Scope handling still marked the normal diabetes question in scope. Safety handling still refused a medication-change question. Evidence and source display data still exist in the answer payload because the feedback changes wrap the API response after the RAG result is produced.

The frontend typecheck and build both passed after adding the feedback UI and proxy route.

# Assumptions and uncertainties

- I assumed the existing `capstone/feature_requirements.md` and `capstone/present_architecture.md` are the intended files, because the numbered filenames in the prompt were not present.
- I assumed storing the question and answer is acceptable for review because the requirement asks for feedback to be linkable to the exact response. The implementation avoids adding extra personal data collection.
- I assumed one current feedback record per response is the sensible repeated-submission behavior.
- The worktree had pre-existing uncommitted changes in `frontend/app/ask/page.tsx`, `frontend/app/page.tsx`, and vectorstore files before I started. I did not revert them.

# Limitations

- There is no admin dashboard; review is via `GET /feedback` or the SQLite database.
- There is no authentication around `GET /feedback`, matching the current no-auth architecture but not suitable for a production review endpoint without access control.
- Feedback persistence is local SQLite, not a managed production database.

# Requirements not fully completed

No requested core feedback behavior is intentionally left unimplemented. The only verification limitation is that I did not run a live browser interaction against running backend/frontend servers; validation was through backend API tests, TypeScript, production build, and RAG command checks.
