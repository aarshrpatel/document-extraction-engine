from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from extraction_engine.schemas.base import BaseExtractionResult, ExtractionMetadata, FieldConfidence
from extraction_engine.schemas.invoice import Address, InvoiceSchema, LineItem
from extraction_engine.schemas.registry import get_schema, list_doc_types


class TestBaseSchema:
    def test_base_extraction_result(self):
        result = BaseExtractionResult(
            doc_type="test",
            source_filename="test.pdf",
        )
        assert result.doc_type == "test"
        assert result.source_filename == "test.pdf"
        assert isinstance(result.extracted_at, datetime)

    def test_extraction_metadata(self):
        meta = ExtractionMetadata(
            model_version="claude-sonnet-4-6",
            processing_time_ms=1500,
            page_count=2,
        )
        assert meta.model_version == "claude-sonnet-4-6"
        assert meta.processing_time_ms == 1500

    def test_field_confidence_bounds(self):
        # Valid
        fc = FieldConfidence(
            field_name="test",
            value="val",
            confidence=Decimal("0.95"),
        )
        assert fc.confidence == Decimal("0.95")

        # Out of bounds
        with pytest.raises(ValidationError):
            FieldConfidence(
                field_name="test",
                value="val",
                confidence=Decimal("1.5"),
            )


class TestInvoiceSchema:
    def test_minimal_invoice(self):
        invoice = InvoiceSchema(
            source_filename="test.pdf",
        )
        assert invoice.doc_type == "invoice"
        assert invoice.invoice_number is None
        assert invoice.line_items == []

    def test_full_invoice(self):
        invoice = InvoiceSchema(
            source_filename="inv-001.pdf",
            invoice_number="INV-001",
            invoice_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            vendor_name="Acme Corp",
            vendor_address=Address(
                street="123 Main St",
                city="Springfield",
                state="IL",
                postal_code="62701",
                country="US",
            ),
            customer_name="Widget Inc",
            currency="USD",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("8.00"),
            total_amount=Decimal("108.00"),
            line_items=[
                LineItem(
                    description="Widget A",
                    quantity=Decimal("2"),
                    unit_price=Decimal("50.00"),
                    amount=Decimal("100.00"),
                ),
            ],
        )
        assert invoice.invoice_number == "INV-001"
        assert invoice.total_amount == Decimal("108.00")
        assert len(invoice.line_items) == 1
        assert invoice.line_items[0].description == "Widget A"

    def test_invoice_uses_decimal_not_float(self):
        invoice = InvoiceSchema(
            source_filename="test.pdf",
            total_amount=Decimal("99.99"),
        )
        assert isinstance(invoice.total_amount, Decimal)

    def test_invoice_json_schema_output(self):
        schema = InvoiceSchema.model_json_schema()
        assert "properties" in schema
        assert "invoice_number" in schema["properties"]
        assert "line_items" in schema["properties"]

    def test_invoice_frozen_doc_type(self):
        invoice = InvoiceSchema(source_filename="test.pdf")
        with pytest.raises(ValidationError):
            invoice.doc_type = "not_invoice"

    def test_currency_max_length(self):
        with pytest.raises(ValidationError):
            InvoiceSchema(
                source_filename="test.pdf",
                currency="USDX",
            )


class TestLineItem:
    def test_minimal_line_item(self):
        item = LineItem(description="Service", amount=Decimal("50.00"))
        assert item.quantity is None
        assert item.unit_price is None

    def test_full_line_item(self):
        item = LineItem(
            description="Consulting",
            quantity=Decimal("10"),
            unit_price=Decimal("150.00"),
            amount=Decimal("1500.00"),
            item_code="SVC-001",
        )
        assert item.quantity * item.unit_price == item.amount


class TestRegistry:
    def test_get_invoice_schema(self):
        schema = get_schema("invoice")
        assert schema is InvoiceSchema

    def test_unknown_doc_type_raises(self):
        with pytest.raises(ValueError, match="Unknown document type"):
            get_schema("unknown_type")

    def test_list_doc_types(self):
        types = list_doc_types()
        assert "invoice" in types
