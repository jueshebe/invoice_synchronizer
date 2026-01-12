"""Model for invoices."""

from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from invoice_synchronizer.domain.models.user import User
from invoice_synchronizer.domain.models.products import Product
from invoice_synchronizer.domain.models.taxes import Retention, TaxType


class Payment(BaseModel):
    """Payment model."""

    payment_type: str
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


class OrderItems(BaseModel):
    """Order items model."""

    product: Product
    quantity: int


class Invoice(BaseModel):
    """Invoice model."""

    # business: User
    # cachier: User
    # sell_point: str
    # seller: User
    client: User
    created_on: datetime
    anulated_on: Optional[datetime] = None
    invoice_id: InvoiceId
    payments: List[Payment]
    order_items: List[OrderItems]
    total: float
    taxes_values: Dict[TaxType, float]
    # retention_values: List[Dict[Retention, float]]
    status: InvoiceStatus = InvoiceStatus.PAID
