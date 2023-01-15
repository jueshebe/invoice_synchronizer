"""Model for products."""
from typing import List, Optional
from pydantic import BaseModel, validator
from pirpos2siigo.models.utils import normalize

class TaxInfo(BaseModel):
    """Stock information."""

    pirpos_name: str
    siigo_name: str
    siigo_id: int
    value: float


class Product(BaseModel):
    """Product info."""

    siigo_id: Optional[str]
    product_id: str
    name: str
    price: float
    taxes: List[TaxInfo]

    @validator("name")
    @classmethod
    def clean_name(cls, name: str) -> str:
        """Remove upercase and accents."""
        return normalize(name)
