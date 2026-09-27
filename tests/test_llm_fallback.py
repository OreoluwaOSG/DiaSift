import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import llm_providers
import rag_pipeline


RETRIEVED_CHUNK = {
    "document": "Type 2 diabetes symptoms can develop gradually.",
    "metadata": {
        "source": "NHS Type 2 Diabetes Symptoms",
        "source_file": "nhs.txt",
        "chunk_index": 0,
    },
    "relevance_score": 2.0,
    "score_breakdown": {},
}


class LlmFallbackTests(TestCase):
    @patch.object(rag_pipeline, "check_question_scope")
    @patch.object(rag_pipeline, "label_evidence_strength")
    @patch.object(rag_pipeline, "search_documents")
    @patch.object(rag_pipeline, "call_llm")
    def test_openai_failure_uses_gemini_backup(
        self,
        call_llm,
        search_documents,
        label_evidence_strength,
        check_question_scope,
    ):
        call_llm.side_effect = [RuntimeError("OpenAI unavailable"), "Backup answer."]
        search_documents.return_value = [RETRIEVED_CHUNK]
        label_evidence_strength.return_value = {
            "label": "Strong evidence",
            "reason": "Relevant guidance was found.",
        }
        check_question_scope.return_value = {
            "in_scope": True,
            "reason": "Type 2 diabetes question.",
            "matched_scope_terms": ["type 2 diabetes"],
            "matched_out_of_scope_terms": [],
        }

        result = rag_pipeline.run_rag_pipeline(
            question="What are the symptoms of type 2 diabetes?",
            call_api=True,
        )

        self.assertEqual(result["answer"], "Backup answer.")
        self.assertEqual(result["provider"], "gemini")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(call_llm.call_count, 2)

    def test_gemini_max_tokens_is_not_treated_as_complete(self):
        response_data = {
            "candidates": [
                {
                    "finishReason": "MAX_TOKENS",
                    "content": {"parts": [{"text": "An unfinished answer"}]},
                }
            ]
        }

        with self.assertRaisesRegex(RuntimeError, "output-token limit"):
            llm_providers.extract_text_from_gemini_response(response_data)


if __name__ == "__main__":
    import unittest

    unittest.main()
