"""Model for products."""
from pydantic import BaseModel


class TaxType(BaseModel):
    """Stock information."""
    
    tax_name: str
    tax_percentage: float


class Retention(BaseModel):
    """Retention Information."""

    retention_name: str
    retention_percentage: float