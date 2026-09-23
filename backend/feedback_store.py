from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Literal
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_FEEDBACK_DB_PATH = BASE_DIR / "data" / "feedback.sqlite3"

FeedbackRating = Literal["helpful", "not_helpful"]

NEGATIVE_FEEDBACK_REASONS = {
    "did_not_answer",
    "difficult_to_understand",
    "information_incorrect",
    "sources_not_helpful",
    "other",
}


def get_feedback_db_path() -> Path:
    configured_path = os.getenv("DIASIFT_FEEDBACK_DB")

    if configured_path:
        return Path(configured_path).expanduser()

    return DEFAULT_FEEDBACK_DB_PATH


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_feedback_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    initialize(connection)
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS responses (
            response_id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT,
            evidence_label TEXT NOT NULL,
            evidence_reason TEXT NOT NULL,
            unsafe_question INTEGER NOT NULL,
            scope_in_scope INTEGER NOT NULL,
            scope_reason TEXT NOT NULL,
            api_called INTEGER NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS feedback (
            response_id TEXT PRIMARY KEY,
            rating TEXT NOT NULL CHECK (rating IN ('helpful', 'not_helpful')),
            reason TEXT CHECK (
                reason IS NULL OR reason IN (
                    'did_not_answer',
                    'difficult_to_understand',
                    'information_incorrect',
                    'sources_not_helpful',
                    'other'
                )
            ),
            reason_text TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (response_id) REFERENCES responses(response_id) ON DELETE CASCADE
        );
        """
    )
    connection.commit()


def create_response_record(result: dict[str, Any]) -> dict[str, Any]:
    response_id = result.get("response_id") or str(uuid4())
    created_at = result.get("created_at") or utc_now_iso()

    record = dict(result)
    record["response_id"] = response_id
    record["created_at"] = created_at

    return record


def save_response(result: dict[str, Any]) -> dict[str, Any]:
    record = create_response_record(result)
    scope_check = record.get("scope_check") or {}

    with closing(connect()) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO responses (
                    response_id,
                    question,
                    answer,
                    evidence_label,
                    evidence_reason,
                    unsafe_question,
                    scope_in_scope,
                    scope_reason,
                    api_called,
                    provider,
                    model,
                    created_at,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(response_id) DO UPDATE SET
                    question = excluded.question,
                    answer = excluded.answer,
                    evidence_label = excluded.evidence_label,
                    evidence_reason = excluded.evidence_reason,
                    unsafe_question = excluded.unsafe_question,
                    scope_in_scope = excluded.scope_in_scope,
                    scope_reason = excluded.scope_reason,
                    api_called = excluded.api_called,
                    provider = excluded.provider,
                    model = excluded.model,
                    created_at = excluded.created_at,
                    payload_json = excluded.payload_json
                """,
                (
                    record["response_id"],
                    record["question"],
                    record.get("answer"),
                    record["evidence_label"],
                    record["evidence_reason"],
                    int(bool(record["unsafe_question"])),
                    int(bool(scope_check.get("in_scope", False))),
                    scope_check.get("reason", ""),
                    int(bool(record["api_called"])),
                    record["provider"],
                    record["model"],
                    record["created_at"],
                    json.dumps(record, ensure_ascii=False),
                ),
            )

    return record


def response_exists(response_id: str) -> bool:
    with closing(connect()) as connection:
        row = connection.execute(
            "SELECT 1 FROM responses WHERE response_id = ?",
            (response_id,),
        ).fetchone()

    return row is not None


def save_feedback(
    response_id: str,
    rating: FeedbackRating,
    reason: str | None = None,
    reason_text: str | None = None,
) -> dict[str, Any]:
    if rating == "helpful":
        reason = None
        reason_text = None

    timestamp = utc_now_iso()

    with closing(connect()) as connection:
        response_row = connection.execute(
            "SELECT 1 FROM responses WHERE response_id = ?",
            (response_id,),
        ).fetchone()

        if response_row is None:
            raise KeyError(response_id)

        with connection:
            connection.execute(
                """
                INSERT INTO feedback (
                    response_id,
                    rating,
                    reason,
                    reason_text,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(response_id) DO UPDATE SET
                    rating = excluded.rating,
                    reason = excluded.reason,
                    reason_text = excluded.reason_text,
                    updated_at = excluded.updated_at
                """,
                (response_id, rating, reason, reason_text, timestamp, timestamp),
            )

        row = connection.execute(
            """
            SELECT response_id, rating, reason, reason_text, created_at, updated_at
            FROM feedback
            WHERE response_id = ?
            """,
            (response_id,),
        ).fetchone()

    return dict(row)


def list_feedback(limit: int = 100) -> list[dict[str, Any]]:
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT
                feedback.response_id,
                feedback.rating,
                feedback.reason,
                feedback.reason_text,
                feedback.created_at,
                feedback.updated_at,
                responses.question,
                responses.answer,
                responses.evidence_label,
                responses.unsafe_question,
                responses.scope_in_scope,
                responses.created_at AS response_created_at
            FROM feedback
            JOIN responses ON responses.response_id = feedback.response_id
            ORDER BY feedback.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]
