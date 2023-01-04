"""Pirpos2Siggo configuration map."""
from typing import Dict, List, Tuple
from pydantic import BaseModel
from pirpos2siigo.models.clients import Client


class TaxesMap(BaseModel):
    """Map for taxes."""

    pirpos_name: str
    siigo_name: str
    value: float
    tax_id: int


class Pirpos2SiigoMap(BaseModel):
    """Validator for configuration.json file."""

    payment_map: Dict[str, int]
    taxes_map: List[TaxesMap]
    invoice_map: Dict[str, int]
    default_client: Client
