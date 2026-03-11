from datetime import date
from decimal import Decimal

from extraction_engine.schemas.invoice import InvoiceSchema


class ValidationResult:
    """Result of custom validation checks."""

    def __init__(self):
        self.warnings: list[str] = []
        self.errors: list[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_invoice(invoice: InvoiceSchema) -> ValidationResult:
    """Run custom business logic validations on an extracted invoice."""
    result = ValidationResult()

    # Check line items sum to subtotal
    if invoice.line_items and invoice.subtotal is not None:
        line_total = sum(item.amount for item in invoice.line_items)
        if abs(line_total - invoice.subtotal) > Decimal("0.02"):
            result.warnings.append(
                f"Line items total ({line_total}) does not match "
                f"subtotal ({invoice.subtotal})"
            )

    # Check subtotal + tax = total
    if (
        invoice.subtotal is not None
        and invoice.tax_amount is not None
        and invoice.total_amount is not None
    ):
        expected_total = invoice.subtotal + invoice.tax_amount
        if invoice.discount_amount:
            expected_total -= invoice.discount_amount
        if invoice.shipping_amount:
            expected_total += invoice.shipping_amount
        if abs(expected_total - invoice.total_amount) > Decimal("0.02"):
            result.warnings.append(
                f"Computed total ({expected_total}) does not match "
                f"total_amount ({invoice.total_amount})"
            )

    # Check date reasonableness
    if invoice.invoice_date is not None:
        if invoice.invoice_date > date.today():
            result.warnings.append("Invoice date is in the future")
        if invoice.invoice_date.year < 2000:
            result.warnings.append("Invoice date year is before 2000")

    if invoice.due_date is not None and invoice.invoice_date is not None:
        if invoice.due_date < invoice.invoice_date:
            result.warnings.append("Due date is before invoice date")

    # Check currency code format
    if invoice.currency is not None:
        if len(invoice.currency) != 3 or not invoice.currency.isalpha():
            result.errors.append(f"Invalid currency code: {invoice.currency}")

    # Check for negative totals
    if invoice.total_amount is not None and invoice.total_amount < 0:
        result.warnings.append("Total amount is negative")

    # Check line item unit_price * quantity = amount
    for i, item in enumerate(invoice.line_items):
        if item.quantity is not None and item.unit_price is not None:
            expected = item.quantity * item.unit_price
            if abs(expected - item.amount) > Decimal("0.02"):
                result.warnings.append(
                    f"Line item {i + 1}: quantity * unit_price ({expected}) "
                    f"does not match amount ({item.amount})"
                )

    return result
