"""Model for products."""
from typing import List
from pydantic import BaseModel, validator
from pirpos2siigo.models.utils import normalize
from pirpos2siigo.models.taxes import TaxType


class Product(BaseModel):
    """Product info."""

    product_id: str
    name: str
    base: float
    final_price: float
    taxes: List[TaxType]

    @validator("name")
    @classmethod
    def clean_name(cls, name: str) -> str:
        """Remove upercase and accents."""
        return normalize(name)
