from extraction_engine.schemas.base import BaseExtractionResult
from extraction_engine.schemas.invoice import InvoiceSchema

SCHEMA_REGISTRY: dict[str, type[BaseExtractionResult]] = {
    "invoice": InvoiceSchema,
}


def get_schema(doc_type: str) -> type[BaseExtractionResult]:
    """Get the schema class for a document type."""
    schema = SCHEMA_REGISTRY.get(doc_type)
    if schema is None:
        raise ValueError(f"Unknown document type: {doc_type}. Available: {list(SCHEMA_REGISTRY)}")
    return schema


def list_doc_types() -> list[str]:
    """List all registered document types."""
    return list(SCHEMA_REGISTRY.keys())
