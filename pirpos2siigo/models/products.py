"""Model for products."""
from enum import Enum
from typing import List
from pydantic import BaseModel


class TaxInfo(Enum):
    """Stock information."""

    IVA = 0.19
    I_CONSUMO = 0.08


class Product(BaseModel):
    """Product info."""

    product_id: str
    name: str
    price: float
    taxes: List[TaxInfo]
