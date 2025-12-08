"""Model for products."""

from typing import List, Dict
from pydantic import BaseModel, validator
from invoice_synchronizer.domain.models.utils import normalize
from invoice_synchronizer.domain.models.taxes import TaxType


class Product(BaseModel):
    """Product info."""

    product_id: str
    name: str
    base: float
    final_price: float
    taxes: List[TaxType]
    taxes_values: List[Dict[TaxType, float]]

    @validator("name")
    @classmethod
    def clean_name(cls, name: str) -> str:
        """Remove upercase and accents."""
        return normalize(name)
