import json

import pytest

from extraction_engine.extraction.prompts import build_correction_prompt, build_extraction_prompt


class TestPrompts:
    def test_build_extraction_prompt_includes_schema(self):
        prompt = build_extraction_prompt("invoice", "Sample OCR text")
        assert "invoice" in prompt
        assert "Sample OCR text" in prompt
        assert "invoice_number" in prompt  # From schema

    def test_build_extraction_prompt_no_ocr(self):
        prompt = build_extraction_prompt("invoice", "")
        assert "No OCR text available" in prompt

    def test_build_correction_prompt(self):
        prompt = build_correction_prompt(
            errors="field required: invoice_number",
            previous_output='{"total": 100}',
        )
        assert "field required" in prompt
        assert '{"total": 100}' in prompt

    def test_unknown_doc_type_raises(self):
        with pytest.raises(ValueError, match="Unknown document type"):
            build_extraction_prompt("unknown_type", "text")
