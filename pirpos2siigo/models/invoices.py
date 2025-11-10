"""Model for invoices."""
from typing import List, Dict
from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from pirpos2siigo.models.user import User
from pirpos2siigo.models.products import Product
from pirpos2siigo.models.taxes import Retention, TaxType
from typing import Optional


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

class InvoiceStatus(Enum):
    """Invoice status."""

    PAID = "PAID"
    PENDING = "PENDING"
    ANULATED = "ANULATED"


class Invoice(BaseModel):
    """Invoice model."""

    business: User
    cachier: User
    sell_point: str
    seller: User
    client: User
    created_on: datetime
    anulated_on: Optional[datetime] = None
    invoice_id: InvoiceId
    payments: List[Payment]
    products: List[Product]
    total: float
    taxes_values: List[Dict[TaxType, float]]
    retention_values: List[Dict[Retention, float]]
    status: InvoiceStatus = InvoiceStatus.PAID
