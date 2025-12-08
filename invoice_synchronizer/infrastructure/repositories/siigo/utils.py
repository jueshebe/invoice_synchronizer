import json
from typing import Dict, List, Union, Tuple
from pydantic import BaseModel


class PaymentMap(BaseModel):
    """Payment mapping between pirpos and siigo."""

    name: str
    siigo_id: int


class TaxMap(BaseModel):
    """Tax mapping between pirpos and siigo."""

    name: str
    siigo_name: str
    siigo_id: int
    value: float


class InvoiceMap(BaseModel):
    """Invoice prefix mapping between pirpos and siigo."""

    prefix: str
    siigo_id: int
    siigo_code: int


class SiigoMap(BaseModel):
    """Validator for configuration.json file."""

    payment_map: List[PaymentMap]
    taxes_map: List[TaxMap]
    prefix_map: List[InvoiceMap]
    retentions: List[TaxMap]


def load_siigo_config(file_path: str) -> SiigoMap:
    """Read JSON configuration file.

    It contains information of how map Pirpos to Siigo

    Parameters
    ----------
    file_path : str
        file direction

    Returns
    -------
        SiigoMap object
    """
    try:
        with open(file_path, "rt", encoding="utf-8") as file:
            data = json.load(file)
            return SiigoMap(**data)
    except Exception as error:
        raise ValueError(f"""error loading file {file_path}. Error msg: {error}""") from error


def get_tax_map(configuration: SiigoMap, name_key: str) -> TaxInfo:
    """Find tax mapping."""
    for tax_map in configuration.taxes_map:
        if name_key in [tax_map.siigo_name, tax_map.pirpos_name]:
            return TaxInfo(
                pirpos_name=tax_map.pirpos_name,
                siigo_name=tax_map.siigo_name,
                siigo_id=tax_map.siigo_id,
                value=tax_map.value,
            )
    raise ValueError(f"name_key {name_key} not recognized, check configuration file.")
