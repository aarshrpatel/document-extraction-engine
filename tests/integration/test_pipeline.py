"""Integration tests for the extraction pipeline.

These tests use mocked external API calls (Anthropic, Azure).
"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from extraction_engine.config import Settings


MOCK_INVOICE_RESPONSE = json.dumps({
    "doc_type": "invoice",
    "source_filename": "test.pdf",
    "invoice_number": "INV-001",
    "invoice_date": "2024-01-15",
    "vendor_name": "Acme Corp",
    "customer_name": "Widget Inc",
    "currency": "USD",
    "subtotal": "100.00",
    "tax_amount": "10.00",
    "total_amount": "110.00",
    "line_items": [
        {
            "description": "Consulting Service",
            "quantity": "10",
            "unit_price": "10.00",
            "amount": "100.00",
        }
    ],
})


class TestExtractionPipelineMocked:
    """Test pipeline with mocked external services."""

    @patch("extraction_engine.extraction.extractor.anthropic.Anthropic")
    def test_extractor_parses_response(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=MOCK_INVOICE_RESPONSE)]
        mock_client.messages.create.return_value = mock_message

        settings = Settings(
            anthropic_api_key="test-key",
            azure_doc_intel_endpoint="https://test.cognitiveservices.azure.com/",
            azure_doc_intel_key="test-key",
        )

        from extraction_engine.extraction.extractor import Extractor
        from extraction_engine.preprocessing.image import image_to_base64

        extractor = Extractor(settings)

        # Create a small test image
        img = Image.new("RGB", (100, 100), "white")
        img_b64 = image_to_base64(img)

        result = extractor.extract(
            doc_type="invoice",
            image_b64=img_b64,
            ocr_text="INV-001 Acme Corp",
            source_filename="test.pdf",
        )

        assert result.doc_type == "invoice"
        assert result.invoice_number == "INV-001"
        assert result.total_amount == Decimal("110.00")
        assert len(result.line_items) == 1
