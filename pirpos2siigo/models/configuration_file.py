"""Pirpos2Siggo configuration map."""
from typing import Dict, List, Tuple
from pydantic import BaseModel


class TaxesMap(BaseModel):
    """Map for taxes."""

    pirpos_name: str
    siigo_name: str
    value: float
    tax_id: int


class DefaultClient(BaseModel):
    """Default client used to send invoices."""

    name: str
    document: int


class Pirpos2SiigoMap(BaseModel):
    """Validator for configuration.json file."""

    payment_map: Dict[str, int]
    taxes_map: List[TaxesMap]
    invoice_map: Dict[str, int]
    default_client: DefaultClient
