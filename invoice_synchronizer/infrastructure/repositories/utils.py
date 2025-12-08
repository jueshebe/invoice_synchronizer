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


def clean_document(document: Union[str, int]) -> int:
    """Read client document and validate it.

    Parameters
    ----------
    document : str
        ex: 9 0 1 5 4 7 7 5 7 - 3

    Returns
    -------
    str
        return -> '901547757'.
    """
    if isinstance(document, int):
        return document

    document_str = document.replace(" ", "")
    if "-" in document_str:
        document_str = document_str[: document_str.find("-")]
    return int(document_str)


def create_client(
    default_client: User,
    name: str,
    last_name: Optional[str] = None,
    document_type: Optional[int] = None,
    document: Optional[str] = None,
    check_digit: Optional[int] = None,
    city_name: Optional[str] = None,
    city_state: Optional[str] = None,
    city_code: Optional[str] = None,
    country_code: Optional[str] = None,
    state_code: Optional[str] = None,
    responsibilities: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
) -> User:
    """Create client object."""
    # Map document_type integer to DocumentType enum if provided
    if document_type is not None:
        mapped_document_type = DocumentType(document_type)
    else:
        mapped_document_type = default_client.document_type

    if responsibilities is not None:
        responsibilities_map = Responsibilities(responsibilities)
    else:
        responsibilities_map = default_client.responsibilities

    return User(
        name=name,
        last_name=last_name,
        document_type=mapped_document_type,
        document_number=clean_document(document) if document else default_client.document_number,
        check_digit=check_digit if check_digit else default_client.check_digit,
        city_detail=CityDetail(
            city_name=city_name if city_name else default_client.city_detail.city_name,
            city_state=city_state if city_state else default_client.city_detail.city_state,
            city_code=city_code if city_code else default_client.city_detail.city_code,
            country_code=country_code if country_code else default_client.city_detail.country_code,
            state_code=state_code if state_code else default_client.city_detail.state_code,
        ),
        responsibilities=responsibilities_map,
        email=email if email else default_client.email,
        phone=phone if phone else default_client.phone,
        address=address if address else default_client.address,
    )


def create_product(
    product_id: str,
    name: str,
    base: float,
    final_price: float,
    taxes: List[TaxType],
    taxes_values: List[Dict[TaxType, float]],
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


def get_prefix_map(configuration: Pirpos2SiigoMap, key_value: Union[str, int]) -> InvoiceMap:
    """Find prefix mapping."""
    for prefix_map in configuration.prefix_map:
        if key_value in [prefix_map.prefix, prefix_map.siigo_id]:
            return prefix_map
    raise ValueError(
        f"key_value {key_value} not recognized for prefix map, check configuration file."
    )


def get_payment_map(configuration: Pirpos2SiigoMap, key_value: Union[str, int]) -> Payment:
    """Find prefix mapping."""
    payments_map = configuration.payment_map
    for payment_map in payments_map:
        if key_value in [payment_map.pirpos_name, payment_map.siigo_id]:
            return payment_map
    raise ValueError(
        f"key_value {key_value} not recognized for payments map, check configuration file."
    )


def create_invoice(
    configuration: Pirpos2SiigoMap,
    cachier_name: str,
    cachier_id: str,
    seller_name: str,
    seller_id: str,
    client: User,
    created_on: datetime,
    invoice_prefix: str,
    invoice_number: int,
    payments: List[Tuple[Union[str, int], float]],
    invoice_products: List[Tuple[Product, float, int, str]],
    total: float,
    siigo_id: Optional[str] = None,
) -> Invoice:
    """Create invoice."""
    return Invoice(
        siigo_id=siigo_id,
        cachier=User(name=cachier_name, employee_id=cachier_id),
        seller=User(name=seller_name, employee_id=seller_id),
        client=client,
        created_on=datetime(created_on.year, created_on.month, created_on.day),
        invoice_prefix=get_prefix_map(configuration, invoice_prefix),
        invoice_number=invoice_number,
        payment_method=[
            (
                get_payment_map(configuration, payment[0]),
                payment[1],
            )
            for payment in payments
            if payment[1]
        ],
        products=[
            Product(
                product=invoice_product[0],
                price=invoice_product[1],
                quantity=invoice_product[2],
                tax=get_tax_map(configuration, invoice_product[3]),
            )
            for invoice_product in invoice_products
        ],
        total=total,
    )


class ErrorConfigPirposSiigo(Exception):
    """File provided doesn't have correct information."""


class ErrorPirposToken(Exception):
    """Can't obtain pirpos token."""


class ErrorLoadingPirposClients(Exception):
    """Can't download Pirpos clients."""


class ErrorLoadingPirposProducts(Exception):
    """Can't download Pirpos clients."""


class ErrorLoadingPirposInvoices(Exception):
    """Can't download Pirpos Invoices."""


class ErrorSiigoToken(Exception):
    """Can't obtain siigo token."""


class ErrorLoadingSiigoClients(Exception):
    """Can't download Siigo clients."""


class ErrorLoadingSiigoProducts(Exception):
    """Can't download Siigo clients."""


class ErrorLoadingSiigoInvoices(Exception):
    """Can't download Siigo Invoices."""


class ErrorCreatingSiigoClient(Exception):
    """Can't create client."""


class ErrorUpdatingSiigoClient(Exception):
    """Can't update client."""


class ErrorCreatingSiigoProduct(Exception):
    """Can't create product."""


class ErrorUpdatingSiigoProduct(Exception):
    """Can't update product."""


class ErrorCreatingSiigoInvoice(Exception):
    """Can't create invoice."""


class ErrorUpdatingSiigoInvoice(Exception):
    """Can't update invoice."""
