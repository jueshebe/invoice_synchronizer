"""Model for products."""
from enum import Enum
from typing import List
from pydantic import BaseModel


class TaxInfo(BaseModel):
    """Stock information."""

    pirpos_name: str
    siigo_name: str
    siigo_id: int
    value: float


class Product(BaseModel):
    """Product info."""

    product_id: str
    name: str
    price: float
    taxes: List[TaxInfo]
