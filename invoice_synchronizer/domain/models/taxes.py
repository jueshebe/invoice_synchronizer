"""Model for products."""

from pydantic import BaseModel


class TaxType(BaseModel):
    """Tax information."""

    model_config = {"frozen": True}

    tax_name: str
    tax_percentage: float


class Retention(BaseModel):
    """Retention Information."""

    retention_name: str
    retention_percentage: float
