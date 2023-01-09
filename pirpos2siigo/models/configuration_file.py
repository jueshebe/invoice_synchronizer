"""Pirpos2Siggo configuration map."""
from typing import Dict, List
from pydantic import BaseModel
from pirpos2siigo.models.clients import Client
from pirpos2siigo.models.products import TaxInfo
from pirpos2siigo.models.invoices import Payment


class InvoiceMap(BaseModel):
    """Map for invoices."""

    prefix: str
    siigo_id: int
    siigo_code: int


class Pirpos2SiigoMap(BaseModel):
    """Validator for configuration.json file."""

    payment_map: List[Payment]
    taxes_map: List[TaxInfo]
    prefix_map: List[InvoiceMap]
    default_client: Client
    retentions: List[TaxInfo]
