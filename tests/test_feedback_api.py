import os
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


def sample_rag_result(question: str = "What is type 2 diabetes?") -> dict:
    return {
        "question": question,
        "answer": "Type 2 diabetes is a condition that affects blood glucose.",
        "evidence_label": "Strong evidence",
        "evidence_reason": "Relevant guidance was found.",
        "unsafe_question": False,
        "scope_check": {
            "in_scope": True,
            "reason": "Type 2 diabetes question.",
            "matched_scope_terms": ["type 2 diabetes"],
            "matched_out_of_scope_terms": [],
        },
        "citations": ["NHS"],
        "retrieved_sources": ["NHS"],
        "retrieved_chunks": [
            {
                "source": "NHS",
                "source_file": "nhs_type2_diabetes_overview.txt",
                "chunk_index": 0,
                "text": "Type 2 diabetes is a common condition.",
                "relevance_score": 2.0,
                "score_breakdown": None,
            }
        ],
        "provider": "openai",
        "model": "test-model",
        "api_called": False,
        "fallback_used": False,
        "usage_estimate": {"input_tokens": 10, "max_output_tokens": 800},
    }


class FeedbackApiTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("DIASIFT_FEEDBACK_DB")
        os.environ["DIASIFT_FEEDBACK_DB"] = str(
            Path(self.temp_dir.name) / "feedback.sqlite3"
        )
        self.client = TestClient(app)

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("DIASIFT_FEEDBACK_DB", None)
        else:
            os.environ["DIASIFT_FEEDBACK_DB"] = self.previous_db_path
        self.temp_dir.cleanup()

    @patch("rag_pipeline.run_rag_pipeline")
    @patch("llm_providers.get_default_model")
    def test_answer_creates_response_id_and_feedback_can_be_saved(
        self,
        get_default_model,
        run_rag_pipeline,
    ):
        get_default_model.return_value = "test-model"
        run_rag_pipeline.return_value = sample_rag_result()

        answer_response = self.client.post(
            "/answer",
            json={"question": "What is type 2 diabetes?", "call_api": False},
        )

        self.assertEqual(answer_response.status_code, 200)
        answer_data = answer_response.json()
        self.assertIn("response_id", answer_data)
        self.assertIn("created_at", answer_data)

        feedback_response = self.client.post(
            "/feedback",
            json={
                "response_id": answer_data["response_id"],
                "rating": "not_helpful",
                "reason": "sources_not_helpful",
            },
        )

        self.assertEqual(feedback_response.status_code, 200)
        feedback_data = feedback_response.json()
        self.assertEqual(feedback_data["response_id"], answer_data["response_id"])
        self.assertEqual(feedback_data["rating"], "not_helpful")
        self.assertEqual(feedback_data["reason"], "sources_not_helpful")
        self.assertIn("created_at", feedback_data)
        self.assertIn("updated_at", feedback_data)
        self.assertEqual(run_rag_pipeline.call_count, 1)

    @patch("rag_pipeline.run_rag_pipeline")
    @patch("llm_providers.get_default_model")
    def test_repeated_feedback_updates_same_response(
        self,
        get_default_model,
        run_rag_pipeline,
    ):
        get_default_model.return_value = "test-model"
        run_rag_pipeline.return_value = sample_rag_result()

        answer_data = self.client.post(
            "/answer",
            json={"question": "What is type 2 diabetes?", "call_api": False},
        ).json()

        self.client.post(
            "/feedback",
            json={
                "response_id": answer_data["response_id"],
                "rating": "not_helpful",
                "reason": "did_not_answer",
            },
        )
        update_response = self.client.post(
            "/feedback",
            json={"response_id": answer_data["response_id"], "rating": "helpful"},
        )

        self.assertEqual(update_response.status_code, 200)
        updated_feedback = update_response.json()
        self.assertEqual(updated_feedback["rating"], "helpful")
        self.assertIsNone(updated_feedback["reason"])

        review_response = self.client.get("/feedback")
        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(len(review_response.json()), 1)

    def test_feedback_for_unknown_response_is_rejected(self):
        response = self.client.post(
            "/feedback",
            json={"response_id": "missing-response", "rating": "helpful"},
        )

        self.assertEqual(response.status_code, 404)

    @patch("rag_pipeline.run_rag_pipeline")
    @patch("llm_providers.get_default_model")
    def test_helpful_feedback_rejects_negative_reason(
        self,
        get_default_model,
        run_rag_pipeline,
    ):
        get_default_model.return_value = "test-model"
        run_rag_pipeline.return_value = sample_rag_result()

        answer_data = self.client.post(
            "/answer",
            json={"question": "What is type 2 diabetes?", "call_api": False},
        ).json()

        response = self.client.post(
            "/feedback",
            json={
                "response_id": answer_data["response_id"],
                "rating": "helpful",
                "reason": "did_not_answer",
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    import unittest

    unittest.main()
