"""Model for invoices."""
from typing import Tuple, List
from datetime import datetime
from pydantic import BaseModel
from pirpos2siigo.models.clients import Client
from pirpos2siigo.models.products import Product, TaxInfo


class Employee(BaseModel):
    """Cachier model."""

    name: str
    employee_id: str  # TODO: add employee mapping


class InvoiceProduct(BaseModel):
    """Invoice product model.

    Product object contains current information of a product
    some invoice can have another state of a product.
    """

    product: Product
    price: float
    quantity: int
    tax: TaxInfo


class Payment(BaseModel):
    """Payment model."""

    pirpos_name: str
    siigo_id: int


class Prefix(BaseModel):
    """Prefix model."""

    prefix: str
    siigo_id: int
    siigo_code: int


class Invoice(BaseModel):
    """Invoice model."""

    cachier: Employee
    seller: Employee
    client: Client
    created_on: datetime
    invoice_prefix: Prefix
    invoice_number: int
    payment_method: List[Tuple[Payment, float]]
    products: List[InvoiceProduct]
    total: float
