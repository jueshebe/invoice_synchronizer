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


def create_product(
    system_parameters: SystemParameters,
    product_id: str,
    name: str,
    base: float,
    final_price: float,
) -> List[Product]:
    """From pirpos data create product."""
    products: List[Product] = []

    Product(
        product_id=product_id,
        name=name,
        base=base,
        final_price=final_price,
        taxes=taxes,
        taxes_values=taxes_values,
    )
    return products


def create_invoice():
    pass


def find_mapping(
    mappings: List[Dict[str, Any]], client_key: str, client_value: str
) -> Dict[str, Any]:
    """Find mapping value in system configuration."""
    for mapping in mappings:
        if str(mapping[client_key]) == str(client_value):
            return mapping
    raise ValueError(f"Mapping for {client_key}: {client_value} not found. Check system mappings.")


# def create_invoice(
#     configuration: Pirpos2SiigoMap,
#     cachier_name: str,
#     cachier_id: str,
#     seller_name: str,
#     seller_id: str,
#     client: User,
#     created_on: datetime,
#     invoice_prefix: str,
#     invoice_number: int,
#     payments: List[Tuple[Union[str, int], float]],
#     invoice_products: List[Tuple[Product, float, int, str]],
#     total: float,
#     siigo_id: Optional[str] = None,
# ) -> Invoice:
#     """Create invoice."""
#     return Invoice(
#         siigo_id=siigo_id,
#         cachier=User(name=cachier_name, employee_id=cachier_id),
#         seller=User(name=seller_name, employee_id=seller_id),
#         client=client,
#         created_on=datetime(created_on.year, created_on.month, created_on.day),
#         invoice_prefix=get_prefix_map(configuration, invoice_prefix),
#         invoice_number=invoice_number,
#         payment_method=[
#             (
#                 get_payment_map(configuration, payment[0]),
#                 payment[1],
#             )
#             for payment in payments
#             if payment[1]
#         ],
#         products=[
#             Product(
#                 product=invoice_product[0],
#                 price=invoice_product[1],
#                 quantity=invoice_product[2],
#                 tax=get_tax_map(configuration, invoice_product[3]),
#             )
#             for invoice_product in invoice_products
#         ],
#         total=total,
#     )
