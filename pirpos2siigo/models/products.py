"""Model for products."""
from typing import List, Dict
from pydantic import BaseModel, validator
from pirpos2siigo.models.utils import normalize
from pirpos2siigo.models.taxes import TaxType


class Product(BaseModel):
    """Product info."""

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
