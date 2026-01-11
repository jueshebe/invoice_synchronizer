"""Utils used by clients."""

from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime
import json
from invoice_synchronizer.domain.models import (
    User,
    CityDetail,
    Product,
    TaxType,
    Invoice,
    Payment,
    Product,
    Responsibilities,
    DocumentType,
)
from invoice_synchronizer.infrastructure.config import SystemParameters
from invoice_synchronizer.infrastructure.repositories.utils import find_mapping


def define_pitpos_product(
    system_parameters: SystemParameters,
    product_id: str,
    name: str,
    final_price: float,
    raw_taxes: Optional[List[Dict[str, Any]]] = None,
) -> Product:
    """Define pirpos product from pirpos data."""
    raw_taxes = raw_taxes or []
    taxes: List[TaxType] = []
    taxes_values: Dict[TaxType, float] = {}
    percentages_taxes: List[float] = []

    for tax in raw_taxes:
        mapping = find_mapping(system_parameters.taxes, "pirpos_id", tax["tax"]["name"])
        tax_name = mapping["system_id"]
        tax_percentage = tax["tax"]["percentage"]
        tax_type = TaxType(tax_name=tax_name, tax_percentage=tax_percentage)
        taxes.append(tax_type)
        percentages_taxes.append(tax_percentage)

    base_price = final_price / (1 + sum(percentages_taxes) / 100)

    for parsed_tax in taxes:
        tax_value = base_price * (parsed_tax.tax_percentage / 100)
        taxes_values[parsed_tax] = tax_value

    product = Product(
        product_id=product_id,
        name=name,
        base=base_price,
        final_price=final_price,
        taxes=taxes,
        taxes_values=taxes_values,
    )
    return product


def define_pirpos_product_subproducts(
    system_parameters: SystemParameters,
    product_id: str,
    name: str,
    location_stock: Dict[str, Any],
    sub_products: List[Dict[str, Any]],
) -> List[Product]:
    """From pirpos data create products."""
    products: List[Product] = []

    if len(sub_products) == 0:
        products.append(
            define_pitpos_product(
                system_parameters,
                product_id=product_id,
                name=name,
                final_price=location_stock["price"],
                raw_taxes=location_stock["taxes"],
            )
        )
    else:
        for sub_product in sub_products:
            product_id = sub_product["_id"]
            name = sub_product["name"]
            location_stock = sub_product["locationsStock"][0]
            products.append(
                define_pitpos_product(
                    system_parameters,
                    product_id=product_id,
                    name=name,
                    final_price=location_stock["price"],
                    raw_taxes=location_stock["taxes"],
                )
            )
    return products


def create_invoice():
    pass
