"""Model for invoices."""
from typing import List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from pirpos2siigo.models.person import Person
from pirpos2siigo.models.products import Product
from pirpos2siigo.models.taxes import Retention


class InvoiceProduct(BaseModel):
    """Invoice product model.

    Product object contains current information of a product
    some invoice can have another state of a product.
    """

    product: Product
    price: float
    quantity: int


class PaymentType(Enum):
    """Type of payments."""

    CASH = "CASH"
    DEBIT_CARD = "DEBIT_CARD"
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    RAPPI = "RAPPI"


class Payment(BaseModel):
    """Payment model."""

    payment_type: PaymentType
    value: float


class InvoiceId(BaseModel):
    """Invoice identifier."""

    prefix: str
    number: int


class Invoice(BaseModel):
    """Invoice model."""

    invoice_id: InvoiceId
    cachier: Person
    seller: Person
    client: Person
    created_on: datetime
    products: List[InvoiceProduct]
    retention: List[Retention]
    total: float
    payments: Payment
