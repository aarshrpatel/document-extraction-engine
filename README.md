# Document Extraction Engine

An eval-first document extraction system that converts messy scans and PDFs into verified structured data using a two-pass OCR + Vision Language Model pipeline. Built to solve the "data entry bottleneck" in industries like banking, logistics, and insurance where manual document processing costs billions and carries a 1-4% error rate.

## How It Works

```
PDF/JPG Input
    |
    v
[ Preprocessing ] -- page split, contrast normalization, sharpen
    |
    +---> [ Tesseract / Azure OCR ] ---> OCR text + confidence scores
    |
    +---> [ Image bytes ]
              |
              v
[ Claude VLM ] -- receives: system prompt + OCR context + image + JSON schema
    |
    v
[ Pydantic Validation ] -- strict types, custom business-rule validators
    |
    v
[ Confidence Scoring ] -- cross-references extracted values against OCR text
    |
    v
Structured JSON Output ---> PostgreSQL
```

**Why two-pass?** OCR handles degraded scans and handwriting better than VLMs alone. The OCR text acts as a "hint layer" — Claude cross-references what it sees in the image with the OCR output, reducing hallucination.

## Key Features

- **Two-pass OCR + VLM extraction** using Tesseract (free, local) or Azure Document Intelligence with Claude Sonnet 4.6
- **Strict Pydantic schemas** with `Decimal` for money (no floating-point artifacts), `date` for dates, and strict mode validation
- **4-layer hallucination prevention:**
  1. Prompt-level constraints ("if not visible, set to null — never guess")
  2. OCR cross-reference flagging
  3. Pydantic type enforcement + custom validators (line items must sum to subtotal, dates must be reasonable)
  4. Per-field confidence scoring
- **Eval-first framework** — automated accuracy measurement with Levenshtein similarity, field-level accuracy, and numeric tolerance scoring against ground-truth datasets
- **Validation retry** — if Pydantic rejects Claude's output, the validation errors are sent back for a correction attempt (max 2 retries)
- **Async processing** via Celery + Redis with a sync endpoint for testing
- **REST API** with FastAPI for document upload, job tracking, and eval runs

## Tech Stack

| Layer | Technology |
|-------|-----------|
| VLM | Anthropic Claude Sonnet 4.6 |
| OCR | Tesseract (default) / Azure Document Intelligence (optional) |
| Validation | Pydantic v2 (strict mode) |
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy + Alembic |
| Task Queue | Celery + Redis |
| Eval | Custom scorer + DeepEval integration |
| Document Processing | PyMuPDF + Pillow |

## Quick Start

### Prerequisites

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (`brew install tesseract` on macOS)
- Docker (for PostgreSQL + Redis)
- An Anthropic API key

### Setup

```bash
# Clone and enter the repo
git clone https://github.com/aarshpatel/document-extraction-engine.git
cd document-extraction-engine

# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra dev

# Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Start PostgreSQL + Redis
docker compose up -d

# Run database migrations
PYTHONPATH=src uv run alembic upgrade head

# Start the API server
PYTHONPATH=src uv run uvicorn extraction_engine.main:app --port 8000
```

### Extract a Document

```bash
# Synchronous extraction (returns result immediately)
curl -X POST "http://localhost:8000/api/v1/extract/sync?doc_type=invoice" \
  -F "file=@path/to/invoice.pdf"

# Async extraction (returns job_id, processes via Celery)
curl -X POST "http://localhost:8000/api/v1/extract?doc_type=invoice" \
  -F "file=@path/to/invoice.pdf"

# Check job status
curl http://localhost:8000/api/v1/jobs/{job_id}
```

### Example Output

```json
{
  "invoice_number": "INV-2024-001",
  "invoice_date": "2024-03-15",
  "due_date": "2024-04-14",
  "vendor_name": "Acme Technologies Inc.",
  "vendor_address": {
    "street": "100 Innovation Drive",
    "city": "San Francisco",
    "state": "CA",
    "postal_code": "94105",
    "country": "US"
  },
  "customer_name": "GlobalTech Solutions LLC",
  "currency": "USD",
  "subtotal": "2500.00",
  "tax_amount": "206.25",
  "tax_rate": "8.25",
  "total_amount": "2706.25",
  "line_items": [
    {
      "description": "Cloud Hosting (Monthly)",
      "quantity": "1",
      "unit_price": "1500.00",
      "amount": "1500.00"
    },
    {
      "description": "API Integration Service",
      "quantity": "5",
      "unit_price": "200.00",
      "amount": "1000.00"
    }
  ],
  "payment_terms": "Net 30"
}
```

## Evaluation Framework

The eval suite measures extraction accuracy against hand-verified ground truth data.

```bash
# Run eval against the 10 included sample invoices
PYTHONPATH=src uv run python -m eval.runner --doc-type invoice

# Output:
#   invoice_001: accuracy=100.0% similarity=1.000 (30/30 fields)
#   invoice_002: accuracy=100.0% similarity=1.000 (34/34 fields)
#   ...
#   EVALUATION SUMMARY (10 documents)
#   Field accuracy:  100.0% (350/350)
#   Avg similarity:  1.000
```

**Metrics tracked:**
- **Field-level accuracy** — exact match per field (with numeric tolerance for money)
- **Levenshtein similarity** — fuzzy text comparison (catches partial extractions)
- **Per-field confidence** — OCR cross-reference score (1.0 = found in OCR, 0.3 = not found)

Ground truth samples include 10 synthetic invoices covering edge cases: zero-tax invoices, volume discounts, international addresses (EUR/IBAN), high-volume manufacturing orders, and multi-line service invoices.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/extract` | Upload document, returns job_id (async via Celery) |
| `POST` | `/api/v1/extract/sync` | Upload document, returns extracted data immediately |
| `GET` | `/api/v1/jobs/{job_id}` | Poll job status + extraction result |
| `GET` | `/api/v1/jobs` | List recent jobs with filters |
| `POST` | `/api/v1/eval/run` | Trigger eval run against ground truth |
| `GET` | `/api/v1/eval/runs/{id}` | Get eval run results + metrics |
| `GET` | `/api/v1/health` | Health check |

Interactive API docs available at `http://localhost:8000/docs` when the server is running.

## Running Tests

```bash
# All tests (44 tests)
PYTHONPATH=src uv run pytest tests/ -v

# Unit tests only
PYTHONPATH=src uv run pytest tests/unit/ -v

# Integration tests (uses mocked API calls)
PYTHONPATH=src uv run pytest tests/integration/ -v
```

## Project Structure

```
src/extraction_engine/
  config.py              # pydantic-settings (env-based config)
  main.py                # FastAPI application
  schemas/               # Pydantic models (invoice, base, registry)
  preprocessing/         # Document loading, image processing, OCR
  extraction/            # Claude API calls, prompt templates, retry logic
  validation/            # Business-rule validators, confidence scoring
  pipeline/              # Orchestrator (load -> OCR -> extract -> validate)
  worker/                # Celery tasks for async processing
  api/                   # REST endpoints, response models
  db/                    # SQLAlchemy models, repositories

eval/
  ground_truth/invoices/ # 10 sample invoices (PNG + JSON pairs)
  metrics.py             # Levenshtein, field accuracy, numeric tolerance
  scorer.py              # Per-field + aggregate scoring
  runner.py              # Batch eval CLI runner
  deepeval_suite.py      # DeepEval integration

tests/
  unit/                  # Schema, validator, metrics, prompt tests
  integration/           # API + pipeline tests with mocked externals
```

## License

MIT
