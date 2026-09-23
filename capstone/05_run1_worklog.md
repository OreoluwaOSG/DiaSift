# Run 1 Work Log

## Initial inspection

- Inspected the project layout from `/Users/oreoluwa/Desktop/Projects/DiaSift`.
- Found the requested requirement filenames as `capstone/feature_requirements.md` and `capstone/present_architecture.md`; `capstone/01_feature_requirements.md` and `capstone/02_architecture_context.md` were not present.
- Noted existing uncommitted changes before editing: `frontend/app/ask/page.tsx`, `frontend/app/page.tsx`, `vectorstore/chroma.sqlite3`, and one vectorstore binary file were already modified; `capstone/` was already untracked.
- Read `backend/main.py`, `frontend/app/api/answer/route.ts`, `frontend/app/ask/page.tsx`, `scripts/rag_pipeline.py`, `scripts/rag_answer.py`, `tests/test_llm_fallback.py`, `requirements.txt`, `frontend/package.json`, `README.md`, and the capstone requirement/context files.
- Also directly inspected `scripts/safety_filter.py`, `scripts/scope_filter.py`, `scripts/search_test.py`, and `scripts/evidence_label.py` to confirm the feedback changes did not need to alter safety, scope, retrieval, or evidence-label logic.

## Current flow understood

- The frontend ask page submits questions to `POST /api/answer`.
- The Next.js route proxies that request to the FastAPI backend at `POST /answer`.
- The backend calls `run_rag_pipeline()` from `scripts/rag_pipeline.py`.
- The RAG pipeline performs scope checking, safety checking, retrieval from ChromaDB via `search_documents`, evidence labeling, optional LLM generation, and returns the answer plus citations/retrieved chunks.
- The ask page renders assistant responses from the returned payload and displays source chips plus a retrieval evidence drawer.

## Persistence found

- ChromaDB is present under `vectorstore/` and is used for retrieval.
- I did not find a separate application database for structured response or feedback records.
- Decision: use a small SQLite database through Python's standard library for response/feedback persistence. This keeps structured operational feedback separate from ChromaDB, avoids a new dependency, and fits the project scale.

## Deliberately ignored

- Dissertation, experiment result, presentation, raw-source, and evaluation artifact content were not used to make implementation decisions except to understand existing tests and RAG behavior.

## Implementation decisions made

- Added `backend/feedback_store.py` using SQLite from Python's standard library.
- Chose SQLite instead of ChromaDB for feedback because feedback is structured operational data with response IDs, ratings, reasons, and timestamps; ChromaDB remains dedicated to semantic retrieval.
- Added persistent response records at the API layer after `run_rag_pipeline()` returns, rather than changing the RAG pipeline's retrieval/safety/evidence logic.
- Added `response_id` and `created_at` to answer responses so every answer, refusal, or local response can receive feedback.
- Added `POST /feedback` for saving feedback and `GET /feedback` for later review.
- Repeated feedback submissions are handled as updates for the same `response_id`, so each response has one current feedback record.
- Added a Next.js proxy route at `frontend/app/api/feedback/route.ts` so the browser continues to call frontend API routes.
- Began adding the feedback control to `frontend/app/ask/page.tsx`; feedback submission is separate from question submission and does not call `/answer`.

## Implementation completed

- Updated `backend/main.py` so `POST /answer` saves a response record and returns `response_id` plus `created_at`.
- Added backend validation for feedback:
  - accepted ratings are `helpful` and `not_helpful`;
  - accepted negative reasons are `did_not_answer`, `difficult_to_understand`, `information_incorrect`, `sources_not_helpful`, and `other`;
  - helpful feedback with a negative reason is rejected;
  - feedback for an unknown response ID is rejected.
- Added `GET /feedback` to review saved feedback with the related question, answer, evidence label, safety/scope flags, and timestamps.
- Updated the ask page to show feedback controls after each assistant response.
- Added CSS for feedback buttons, negative reason options, optional detail text, and saved/error states.
- Added `.gitignore` entry for `data/feedback.sqlite3` because local feedback records are generated runtime data.
- Removed an existing debug `console.log` from the answer proxy while working in the API layer.

## Tests and checks run

- `backend-venv/bin/python -m unittest discover -s tests` passed: 6 tests.
- `npm run typecheck` passed.
- `npm run build` passed.
- `backend-venv/bin/python scripts/rag_pipeline.py "What is type 2 diabetes?"` passed as a dry retrieval/RAG check, returning strong evidence, citations, retrieved chunks, and in-scope status.
- `backend-venv/bin/python scripts/rag_pipeline.py "Should I stop taking metformin today?"` passed as a safety/refusal check, returning the existing unsafe-question refusal without retrieval chunks or an LLM call.

## Problems encountered

- The requested files `capstone/01_feature_requirements.md` and `capstone/02_architecture_context.md` were not present; I used the matching files that exist: `capstone/feature_requirements.md` and `capstone/present_architecture.md`.
- Initial SQLite tests passed but emitted unclosed-connection warnings. I changed the store helper to close connections explicitly and reran the tests cleanly.
- `npm run build` updated generated files `frontend/next-env.d.ts` and `frontend/tsconfig.tsbuildinfo`. I did not use a broad checkout to revert generated changes because the worktree already had unrelated user changes.

## Assumptions and uncertainties

- Assumed storing the submitted question and returned answer is acceptable because reviewers need to understand the exact response that received feedback. No user account, IP address, browser fingerprint, or other extra personal data is collected.
- Assumed one current feedback record per response is preferable to multiple rows for repeated clicks; repeated submissions update the same feedback row.
- The feature has no full admin dashboard, matching the out-of-scope requirements. Review is available through `GET /feedback` and the SQLite database.
