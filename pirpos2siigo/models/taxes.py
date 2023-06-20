"""Model for products."""
from enum import Enum


class TaxType(Enum):
    """Stock information."""

    IVA19 = 0.19
    IMPO_CONSUMO = 0.08


class Retention(Enum):
    """Retention Information."""

    AUTORRENTA_08 = "AUTORRENTA_08"
