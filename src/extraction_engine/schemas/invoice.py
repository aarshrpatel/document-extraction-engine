from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from extraction_engine.schemas.base import BaseExtractionResult


class Address(BaseModel):
    """Structured address."""

    model_config = ConfigDict(strict=True)

    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class LineItem(BaseModel):
    """Single line item on an invoice."""

    model_config = ConfigDict(strict=True)

    description: str
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal
    item_code: str | None = None


class InvoiceSchema(BaseExtractionResult):
    """Extracted invoice data."""

    doc_type: str = Field(default="invoice", frozen=True)

    # Core fields
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    purchase_order_number: str | None = None

    # Parties
    vendor_name: str | None = None
    vendor_address: Address | None = None
    vendor_tax_id: str | None = None
    customer_name: str | None = None
    customer_address: Address | None = None
    customer_tax_id: str | None = None

    # Financial
    currency: str | None = Field(default=None, max_length=3)
    subtotal: Decimal | None = None
    tax_amount: Decimal | None = None
    tax_rate: Decimal | None = None
    discount_amount: Decimal | None = None
    shipping_amount: Decimal | None = None
    total_amount: Decimal | None = None

    # Line items
    line_items: list[LineItem] = Field(default_factory=list)

    # Payment
    payment_terms: str | None = None
    bank_account: str | None = None
    notes: str | None = None
