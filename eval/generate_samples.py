"""Generate synthetic invoice images + ground truth JSON for evaluation."""

import json
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GROUND_TRUTH_DIR = Path(__file__).parent / "ground_truth" / "invoices"


def _get_font(size: int):
    """Get a font, falling back to default if needed."""
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except (OSError, IOError):
            return ImageFont.load_default(size=size)


def _get_bold_font(size: int):
    """Get a bold font, falling back to regular."""
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size, index=1)
    except (OSError, IOError):
        return _get_font(size)


def draw_invoice(
    draw: ImageDraw.ImageDraw,
    data: dict,
    width: int,
):
    """Draw an invoice layout on the image."""
    font = _get_font(16)
    font_sm = _get_font(14)
    font_lg = _get_bold_font(24)
    font_bold = _get_bold_font(16)
    black = (0, 0, 0)
    gray = (100, 100, 100)
    light_gray = (200, 200, 200)

    y = 40

    # Header
    draw.text((40, y), data["vendor_name"], fill=black, font=font_lg)
    y += 35

    if data.get("vendor_address"):
        addr = data["vendor_address"]
        for line in [addr.get("street"), f"{addr.get('city', '')}, {addr.get('state', '')} {addr.get('postal_code', '')}", addr.get("country")]:
            if line and line.strip(", "):
                draw.text((40, y), line, fill=gray, font=font_sm)
                y += 20

    # Invoice title
    y += 20
    draw.text((width - 250, 40), "INVOICE", fill=black, font=font_lg)
    draw.text((width - 250, 75), f"Invoice #: {data['invoice_number']}", fill=black, font=font)
    draw.text((width - 250, 95), f"Date: {data['invoice_date']}", fill=black, font=font)
    if data.get("due_date"):
        draw.text((width - 250, 115), f"Due Date: {data['due_date']}", fill=black, font=font)
    if data.get("purchase_order_number"):
        draw.text((width - 250, 135), f"PO #: {data['purchase_order_number']}", fill=black, font=font)

    # Divider
    y += 10
    draw.line([(40, y), (width - 40, y)], fill=light_gray, width=2)
    y += 20

    # Bill To
    draw.text((40, y), "Bill To:", fill=gray, font=font_bold)
    y += 22
    if data.get("customer_name"):
        draw.text((40, y), data["customer_name"], fill=black, font=font)
        y += 20
    if data.get("customer_address"):
        addr = data["customer_address"]
        for line in [addr.get("street"), f"{addr.get('city', '')}, {addr.get('state', '')} {addr.get('postal_code', '')}", addr.get("country")]:
            if line and line.strip(", "):
                draw.text((40, y), line, fill=gray, font=font_sm)
                y += 20

    y += 20

    # Table header
    draw.rectangle([(40, y), (width - 40, y + 28)], fill=(240, 240, 240))
    cols = [40, 320, 420, 520, 620]
    headers = ["Description", "Qty", "Unit Price", "Amount"]
    for i, h in enumerate(headers):
        draw.text((cols[i] + 5, y + 5), h, fill=black, font=font_bold)
    y += 30

    # Line items
    for item in data.get("line_items", []):
        draw.text((cols[0] + 5, y + 3), item["description"], fill=black, font=font)
        if item.get("quantity"):
            draw.text((cols[1] + 5, y + 3), str(item["quantity"]), fill=black, font=font)
        if item.get("unit_price"):
            draw.text((cols[2] + 5, y + 3), f"${item['unit_price']}", fill=black, font=font)
        draw.text((cols[3] + 5, y + 3), f"${item['amount']}", fill=black, font=font)
        y += 25
        draw.line([(40, y), (width - 40, y)], fill=light_gray, width=1)

    y += 20

    # Totals
    totals_x = width - 250
    if data.get("subtotal"):
        draw.text((totals_x, y), f"Subtotal:", fill=gray, font=font)
        draw.text((totals_x + 120, y), f"${data['subtotal']}", fill=black, font=font)
        y += 22
    if data.get("tax_rate") and data.get("tax_amount"):
        draw.text((totals_x, y), f"Tax ({data['tax_rate']}%):", fill=gray, font=font)
        draw.text((totals_x + 120, y), f"${data['tax_amount']}", fill=black, font=font)
        y += 22
    if data.get("discount_amount"):
        draw.text((totals_x, y), f"Discount:", fill=gray, font=font)
        draw.text((totals_x + 120, y), f"-${data['discount_amount']}", fill=black, font=font)
        y += 22
    if data.get("shipping_amount"):
        draw.text((totals_x, y), f"Shipping:", fill=gray, font=font)
        draw.text((totals_x + 120, y), f"${data['shipping_amount']}", fill=black, font=font)
        y += 22

    draw.line([(totals_x, y), (width - 40, y)], fill=black, width=2)
    y += 8
    draw.text((totals_x, y), f"Total ({data.get('currency', 'USD')}):", fill=black, font=font_bold)
    draw.text((totals_x + 120, y), f"${data['total_amount']}", fill=black, font=font_bold)
    y += 30

    # Payment terms / notes
    if data.get("payment_terms"):
        draw.text((40, y), f"Payment Terms: {data['payment_terms']}", fill=gray, font=font_sm)
        y += 20
    if data.get("notes"):
        draw.text((40, y), f"Notes: {data['notes']}", fill=gray, font=font_sm)


def create_sample(data: dict, filename: str):
    """Create an invoice image and ground truth JSON."""
    width, height = 750, 900
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    draw_invoice(draw, data, width)

    img_path = GROUND_TRUTH_DIR / f"{filename}.png"
    img.save(str(img_path), "PNG")
    print(f"  Created {img_path}")

    # Ground truth JSON (matches InvoiceSchema fields)
    gt = {k: v for k, v in data.items()}
    gt_path = GROUND_TRUTH_DIR / f"{filename}.json"
    gt_path.write_text(json.dumps(gt, indent=2, default=str))
    print(f"  Created {gt_path}")


# ── Sample invoices ──────────────────────────────────────────────

SAMPLES = [
    {
        "name": "invoice_001",
        "data": {
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-03-15",
            "due_date": "2024-04-14",
            "vendor_name": "Acme Technologies Inc.",
            "vendor_address": {
                "street": "100 Innovation Drive",
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94105",
                "country": "US",
            },
            "customer_name": "GlobalTech Solutions LLC",
            "customer_address": {
                "street": "500 Commerce Blvd",
                "city": "Austin",
                "state": "TX",
                "postal_code": "73301",
                "country": "US",
            },
            "currency": "USD",
            "subtotal": "2500.00",
            "tax_rate": "8.25",
            "tax_amount": "206.25",
            "total_amount": "2706.25",
            "line_items": [
                {"description": "Cloud Hosting (Monthly)", "quantity": "1", "unit_price": "1500.00", "amount": "1500.00"},
                {"description": "API Integration Service", "quantity": "5", "unit_price": "200.00", "amount": "1000.00"},
            ],
            "payment_terms": "Net 30",
            "notes": "Thank you for your business!",
        },
    },
    {
        "name": "invoice_002",
        "data": {
            "invoice_number": "2024-0042",
            "invoice_date": "2024-06-01",
            "due_date": "2024-06-30",
            "purchase_order_number": "PO-8834",
            "vendor_name": "Summit Office Supplies",
            "vendor_address": {
                "street": "222 Market Street",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country": "US",
            },
            "customer_name": "Riverdale Accounting Group",
            "customer_address": {
                "street": "88 Financial Plaza, Suite 400",
                "city": "New York",
                "state": "NY",
                "postal_code": "10005",
                "country": "US",
            },
            "currency": "USD",
            "subtotal": "847.50",
            "tax_rate": "7",
            "tax_amount": "59.33",
            "total_amount": "906.83",
            "line_items": [
                {"description": "Ergonomic Desk Chair", "quantity": "3", "unit_price": "189.00", "amount": "567.00"},
                {"description": "Monitor Stand", "quantity": "3", "unit_price": "45.00", "amount": "135.00"},
                {"description": "Wireless Keyboard", "quantity": "5", "unit_price": "29.10", "amount": "145.50"},
            ],
            "payment_terms": "Net 30",
        },
    },
    {
        "name": "invoice_003",
        "data": {
            "invoice_number": "FRL-10293",
            "invoice_date": "2024-01-10",
            "due_date": "2024-02-09",
            "vendor_name": "Freelance Design Co.",
            "vendor_address": {
                "street": "45 Artist Row",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "US",
            },
            "customer_name": "BrightStar Marketing",
            "customer_address": {
                "street": "1200 Ad Avenue",
                "city": "Los Angeles",
                "state": "CA",
                "postal_code": "90001",
                "country": "US",
            },
            "currency": "USD",
            "subtotal": "4200.00",
            "tax_amount": "0.00",
            "total_amount": "4200.00",
            "line_items": [
                {"description": "Brand Identity Package", "quantity": "1", "unit_price": "2500.00", "amount": "2500.00"},
                {"description": "Social Media Templates (10 designs)", "quantity": "1", "unit_price": "1200.00", "amount": "1200.00"},
                {"description": "Business Card Design", "quantity": "1", "unit_price": "500.00", "amount": "500.00"},
            ],
            "payment_terms": "Due on receipt",
            "notes": "All designs delivered via shared drive.",
        },
    },
    {
        "name": "invoice_004",
        "data": {
            "invoice_number": "MFG-2024-0871",
            "invoice_date": "2024-09-20",
            "due_date": "2024-10-20",
            "vendor_name": "Pacific Manufacturing Ltd.",
            "vendor_address": {
                "street": "8800 Industrial Parkway",
                "city": "Seattle",
                "state": "WA",
                "postal_code": "98101",
                "country": "US",
            },
            "customer_name": "Apex Electronics Inc.",
            "customer_address": {
                "street": "300 Circuit Lane",
                "city": "San Jose",
                "state": "CA",
                "postal_code": "95110",
                "country": "US",
            },
            "currency": "USD",
            "subtotal": "15750.00",
            "tax_rate": "9.5",
            "tax_amount": "1496.25",
            "shipping_amount": "350.00",
            "total_amount": "17596.25",
            "line_items": [
                {"description": "PCB Assembly Board v3.2", "quantity": "500", "unit_price": "12.50", "amount": "6250.00"},
                {"description": "LED Display Module 5-inch", "quantity": "200", "unit_price": "22.50", "amount": "4500.00"},
                {"description": "Custom Enclosure (ABS)", "quantity": "500", "unit_price": "10.00", "amount": "5000.00"},
            ],
            "payment_terms": "Net 30",
        },
    },
    {
        "name": "invoice_005",
        "data": {
            "invoice_number": "CS-5590",
            "invoice_date": "2024-11-05",
            "due_date": "2024-12-05",
            "vendor_name": "ClearView Consulting",
            "vendor_address": {
                "street": "77 Strategy Tower, Floor 12",
                "city": "Boston",
                "state": "MA",
                "postal_code": "02101",
                "country": "US",
            },
            "customer_name": "MedFirst Health Systems",
            "customer_address": {
                "street": "400 Wellness Drive",
                "city": "Philadelphia",
                "state": "PA",
                "postal_code": "19101",
                "country": "US",
            },
            "currency": "USD",
            "subtotal": "32000.00",
            "tax_amount": "0.00",
            "discount_amount": "3200.00",
            "total_amount": "28800.00",
            "line_items": [
                {"description": "IT Strategy Assessment", "quantity": "80", "unit_price": "200.00", "amount": "16000.00"},
                {"description": "System Architecture Review", "quantity": "40", "unit_price": "250.00", "amount": "10000.00"},
                {"description": "Compliance Gap Analysis", "quantity": "24", "unit_price": "250.00", "amount": "6000.00"},
            ],
            "payment_terms": "Net 30",
            "notes": "10% volume discount applied.",
        },
    },
    {
        "name": "invoice_006",
        "data": {
            "invoice_number": "INV-EU-2024-112",
            "invoice_date": "2024-04-22",
            "due_date": "2024-05-22",
            "vendor_name": "Nordic Data Services AB",
            "vendor_address": {
                "street": "Drottninggatan 55",
                "city": "Stockholm",
                "state": None,
                "postal_code": "111 21",
                "country": "SE",
            },
            "vendor_tax_id": "SE556677889901",
            "customer_name": "FinanceHub GmbH",
            "customer_address": {
                "street": "Friedrichstrasse 100",
                "city": "Berlin",
                "state": None,
                "postal_code": "10117",
                "country": "DE",
            },
            "customer_tax_id": "DE123456789",
            "currency": "EUR",
            "subtotal": "9600.00",
            "tax_rate": "25",
            "tax_amount": "2400.00",
            "total_amount": "12000.00",
            "line_items": [
                {"description": "Data Pipeline Setup", "quantity": "1", "unit_price": "5000.00", "amount": "5000.00"},
                {"description": "Monthly Maintenance (3 months)", "quantity": "3", "unit_price": "1200.00", "amount": "3600.00"},
                {"description": "Training Workshop (on-site)", "quantity": "2", "unit_price": "500.00", "amount": "1000.00"},
            ],
            "payment_terms": "Net 30",
            "bank_account": "IBAN: SE45 5000 0000 0583 9825 7466",
        },
    },
    {
        "name": "invoice_007",
        "data": {
            "invoice_number": "LS-2024-3301",
            "invoice_date": "2024-07-15",
            "due_date": "2024-08-14",
            "vendor_name": "Landscaping Pros LLC",
            "vendor_address": {
                "street": "950 Greenway Road",
                "city": "Denver",
                "state": "CO",
                "postal_code": "80201",
                "country": "US",
            },
            "customer_name": "Sunrise Commercial Properties",
            "customer_address": {
                "street": "2100 Business Park Drive",
                "city": "Denver",
                "state": "CO",
                "postal_code": "80205",
                "country": "US",
            },
            "currency": "USD",
            "subtotal": "3825.00",
            "tax_rate": "4.55",
            "tax_amount": "174.04",
            "total_amount": "3999.04",
            "line_items": [
                {"description": "Lawn Maintenance (July)", "quantity": "4", "unit_price": "275.00", "amount": "1100.00"},
                {"description": "Tree Trimming Service", "quantity": "1", "unit_price": "950.00", "amount": "950.00"},
                {"description": "Irrigation System Repair", "quantity": "1", "unit_price": "1275.00", "amount": "1275.00"},
                {"description": "Mulch Delivery & Install", "quantity": "10", "unit_price": "50.00", "amount": "500.00"},
            ],
            "payment_terms": "Net 30",
        },
    },
    {
        "name": "invoice_008",
        "data": {
            "invoice_number": "WD-0088",
            "invoice_date": "2024-02-28",
            "due_date": "2024-03-14",
            "vendor_name": "WebDev Studio",
            "vendor_address": {
                "street": "12 Digital Lane",
                "city": "Miami",
                "state": "FL",
                "postal_code": "33101",
                "country": "US",
            },
            "customer_name": "Coastal Realty Group",
            "customer_address": {
                "street": "700 Beachside Blvd",
                "city": "Fort Lauderdale",
                "state": "FL",
                "postal_code": "33301",
                "country": "US",
            },
            "currency": "USD",
            "subtotal": "7500.00",
            "tax_rate": "6",
            "tax_amount": "450.00",
            "total_amount": "7950.00",
            "line_items": [
                {"description": "Website Redesign", "quantity": "1", "unit_price": "5000.00", "amount": "5000.00"},
                {"description": "SEO Optimization Package", "quantity": "1", "unit_price": "1500.00", "amount": "1500.00"},
                {"description": "SSL Certificate (1 year)", "quantity": "1", "unit_price": "200.00", "amount": "200.00"},
                {"description": "Domain Registration (2 years)", "quantity": "1", "unit_price": "30.00", "amount": "30.00"},
                {"description": "Hosting Setup", "quantity": "1", "unit_price": "770.00", "amount": "770.00"},
            ],
            "payment_terms": "50% upfront, 50% on completion",
        },
    },
    {
        "name": "invoice_009",
        "data": {
            "invoice_number": "CATR-2024-0199",
            "invoice_date": "2024-12-01",
            "due_date": "2024-12-15",
            "vendor_name": "Gourmet Catering Co.",
            "vendor_address": {
                "street": "330 Culinary Way",
                "city": "Nashville",
                "state": "TN",
                "postal_code": "37201",
                "country": "US",
            },
            "customer_name": "TechCon Events Inc.",
            "customer_address": {
                "street": "1 Convention Center Drive",
                "city": "Nashville",
                "state": "TN",
                "postal_code": "37213",
                "country": "US",
            },
            "currency": "USD",
            "subtotal": "8550.00",
            "tax_rate": "9.25",
            "tax_amount": "790.88",
            "total_amount": "9340.88",
            "line_items": [
                {"description": "Lunch Buffet (150 guests)", "quantity": "150", "unit_price": "35.00", "amount": "5250.00"},
                {"description": "Coffee & Beverage Station", "quantity": "2", "unit_price": "400.00", "amount": "800.00"},
                {"description": "Dessert Bar", "quantity": "1", "unit_price": "1500.00", "amount": "1500.00"},
                {"description": "Staff (8 hours)", "quantity": "8", "unit_price": "125.00", "amount": "1000.00"},
            ],
            "payment_terms": "Due on receipt",
            "notes": "Event date: December 10, 2024",
        },
    },
    {
        "name": "invoice_010",
        "data": {
            "invoice_number": "LGL-4455",
            "invoice_date": "2024-08-30",
            "due_date": "2024-09-29",
            "vendor_name": "Harrison & Associates Law Firm",
            "vendor_address": {
                "street": "1500 Justice Boulevard, Suite 800",
                "city": "Washington",
                "state": "DC",
                "postal_code": "20001",
                "country": "US",
            },
            "customer_name": "Pinnacle Ventures Corp.",
            "customer_address": {
                "street": "600 Investment Row",
                "city": "Charlotte",
                "state": "NC",
                "postal_code": "28201",
                "country": "US",
            },
            "currency": "USD",
            "subtotal": "18500.00",
            "tax_amount": "0.00",
            "total_amount": "18500.00",
            "line_items": [
                {"description": "Contract Review & Negotiation", "quantity": "25", "unit_price": "350.00", "amount": "8750.00"},
                {"description": "Regulatory Compliance Filing", "quantity": "1", "unit_price": "4500.00", "amount": "4500.00"},
                {"description": "Legal Consultation", "quantity": "15", "unit_price": "350.00", "amount": "5250.00"},
            ],
            "payment_terms": "Net 30",
            "notes": "Matter ref: PVC-2024-M-0102",
        },
    },
]


def main():
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating {len(SAMPLES)} sample invoices...\n")

    for sample in SAMPLES:
        print(f"[{sample['name']}]")
        create_sample(sample["data"], sample["name"])
        print()

    print(f"Done! {len(SAMPLES)} samples in {GROUND_TRUTH_DIR}")


if __name__ == "__main__":
    main()
