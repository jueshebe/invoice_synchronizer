"""Utils used by clients."""
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import json
from pirpos2siigo.models import (
    Pirpos2SiigoMap,
    Client,
    CityDetail,
    Product,
    TaxInfo,
    Invoice,
    Employee,
    InvoiceProduct,
)


def load_pirpos2siigo_config(file_path: str) -> Pirpos2SiigoMap:
    """Read JSON configuration file.

    It contains information of how map Pirpos to Siigo

    Parameters
    ----------
    file_path : str
        file direction

    Returns
    -------
        Pirpos2SiigoMap object
    """
    try:
        with open(file_path, "rt", encoding="utf-8") as file:
            data = json.load(file)
            config_obj = Pirpos2SiigoMap(**data)
            return config_obj
    except Exception as error:
        raise ErrorConfigPirposSiigo(
            f"""error loading file {file_path}. Error msg: {error}"""
        ) from error


def create_client(
    configuration_file: Pirpos2SiigoMap,
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    document: Optional[str] = None,
    check_digit: Optional[str] = None,
    document_type: Optional[str] = None,
    responsibilities: Optional[str] = None,
    city_name: Optional[str] = None,
    city_state: Optional[str] = None,
    city_code: Optional[str] = None,
    country_code: Optional[str] = None,
) -> Client:
    """Create client object."""
    default_client = configuration_file.default_client
    return Client(
        name=name,
        email=email if email else default_client.email,
        phone=phone if phone else default_client.phone,
        address=address if address else default_client.address,
        document=document if document else default_client.document,
        check_digit=check_digit if check_digit else default_client.check_digit,
        document_type=document_type
        if document_type
        else default_client.document_type,
        responsibilities=responsibilities
        if responsibilities
        else default_client.responsibilities,
        city_detail=CityDetail(
            city_name=city_name
            if city_name
            else default_client.city_detail.city_name,
            city_state=city_state
            if city_state
            else default_client.city_detail.city_state,
            city_code=city_code
            if city_code
            else default_client.city_detail.city_code,
            country_code=country_code
            if country_code
            else default_client.city_detail.country_code,
        ),
    )


def create_pirpos_product(
    product_id: str,
    name: str,
    location_stock: Dict[str, Any],
    sub_products: List[Dict[str, Any]],
) -> List[Product]:
    """From pirpos data create product."""
    products: List[Product] = []

    if len(sub_products) == 0:
        products.append(
            create_product(
                product_id,
                name,
                location_stock["price"],
                [(float(location_stock["tax"]["percentage"])) / 100],
            )
        )
    else:
        for sub_product in sub_products:
            product_id = sub_product["_id"]
            products.append(
                create_product(
                    product_id,
                    sub_product["name"],
                    sub_product["locationsStock"][0]["price"],
                    [(float(location_stock["tax"]["percentage"])) / 100],
                )
            )
    return products


def create_product(
    product_id: str, name: str, price: float, taxes: List[float]
) -> Product:
    """Create product object."""
    return Product(product_id=product_id, name=name, price=price, taxes=taxes)


def create_invoice(
    cachier_name: str,
    cachier_id: str,
    seller_name: str,
    seller_id: str,
    client: Client,
    created_on: datetime,
    invoice_prefix: str,
    invoice_number: int,
    payment_method: List[Tuple[str, float]],
    invoice_products: List[Tuple[Product, float, int, float]],
    total: float,
) -> Invoice:
    """Create invoice."""
    return Invoice(
        cachier=Employee(name=cachier_name, employee_id=cachier_id),
        seller=Employee(name=seller_name, employee_id=seller_id),
        client=client,
        created_on=created_on,
        invoice_prefix=invoice_prefix,
        invoice_number=invoice_number,
        payment_method=payment_method,
        products=[
            InvoiceProduct(
                product=invoice_product[0],
                price=invoice_product[1],
                quantity=invoice_product[2],
                tax=invoice_product[3],
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
