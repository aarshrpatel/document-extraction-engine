from datetime import date
from decimal import Decimal

from extraction_engine.schemas.invoice import InvoiceSchema, LineItem
from extraction_engine.validation.validators import validate_invoice


class TestInvoiceValidation:
    def test_valid_invoice_no_warnings(self):
        invoice = InvoiceSchema(
            source_filename="test.pdf",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            total_amount=Decimal("110.00"),
            invoice_date=date(2024, 6, 15),
            due_date=date(2024, 7, 15),
            line_items=[
                LineItem(description="Item A", amount=Decimal("100.00")),
            ],
        )
        result = validate_invoice(invoice)
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_line_items_sum_mismatch(self):
        invoice = InvoiceSchema(
            source_filename="test.pdf",
            subtotal=Decimal("200.00"),
            line_items=[
                LineItem(description="Item A", amount=Decimal("50.00")),
                LineItem(description="Item B", amount=Decimal("60.00")),
            ],
        )
        result = validate_invoice(invoice)
        assert any("Line items total" in w for w in result.warnings)

    def test_total_mismatch(self):
        invoice = InvoiceSchema(
            source_filename="test.pdf",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            total_amount=Decimal("200.00"),
        )
        result = validate_invoice(invoice)
        assert any("Computed total" in w for w in result.warnings)

    def test_future_invoice_date(self):
        invoice = InvoiceSchema(
            source_filename="test.pdf",
            invoice_date=date(2099, 1, 1),
        )
        result = validate_invoice(invoice)
        assert any("future" in w for w in result.warnings)

    def test_due_before_invoice(self):
        invoice = InvoiceSchema(
            source_filename="test.pdf",
            invoice_date=date(2024, 6, 15),
            due_date=date(2024, 5, 1),
        )
        result = validate_invoice(invoice)
        assert any("Due date is before" in w for w in result.warnings)

    def test_invalid_currency(self):
        invoice = InvoiceSchema(
            source_filename="test.pdf",
            currency="US",
        )
        result = validate_invoice(invoice)
        assert not result.is_valid

    def test_line_item_math_mismatch(self):
        invoice = InvoiceSchema(
            source_filename="test.pdf",
            line_items=[
                LineItem(
                    description="Widget",
                    quantity=Decimal("3"),
                    unit_price=Decimal("10.00"),
                    amount=Decimal("50.00"),  # Should be 30.00
                ),
            ],
        )
        result = validate_invoice(invoice)
        assert any("quantity * unit_price" in w for w in result.warnings)

    def test_negative_total(self):
        invoice = InvoiceSchema(
            source_filename="test.pdf",
            total_amount=Decimal("-50.00"),
        )
        result = validate_invoice(invoice)
        assert any("negative" in w for w in result.warnings)
