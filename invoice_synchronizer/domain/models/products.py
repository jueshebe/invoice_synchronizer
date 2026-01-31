"""Model for products."""

from typing import List, Dict, Any
from pydantic import BaseModel, field_validator, model_validator
from invoice_synchronizer.domain.models.utils import normalize
from invoice_synchronizer.domain.models.taxes import TaxType


class Product(BaseModel):
    """Product info."""

    product_id: str
    name: str
    base: float
    final_price: float
    taxes: List[TaxType]
    taxes_values: Dict[TaxType, float]

    @model_validator(mode='before')
    @classmethod
    def decode_tax_type_keys(cls, data: Any) -> Any:
        """Decode TaxType keys from string format: tax_name='I CONSUMO' tax_percentage=8.0."""
        if isinstance(data, dict) and 'taxes_values' in data:
            taxes_values = data['taxes_values']
            if isinstance(taxes_values, dict):
                new_taxes_values = {}
                for key, value in taxes_values.items():
                    if isinstance(key, str) and "tax_name=" in key and "tax_percentage=" in key:
                        # Parse: tax_name='I CONSUMO' tax_percentage=8.0
                        name_start = key.find("tax_name='") + len("tax_name='")
                        name_end = key.find("'", name_start)
                        tax_name = key[name_start:name_end]
                        
                        percentage_start = key.find("tax_percentage=") + len("tax_percentage=")
                        tax_percentage = float(key[percentage_start:])
                        
                        # Create TaxType object
                        tax_type = TaxType(tax_name=tax_name, tax_percentage=tax_percentage)
                        new_taxes_values[tax_type] = value
                    else:
                        # Keep non-string keys or keys that don't match pattern
                        new_taxes_values[key] = value
                
                data['taxes_values'] = new_taxes_values
        return data

    @field_validator("name")
    @classmethod
    def clean_name(cls, name: str) -> str:
        """Remove upercase and accents."""
        return normalize(name)
