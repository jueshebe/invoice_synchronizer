"""Model for invoices."""

from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from invoice_synchronizer.domain.models.user import User
from invoice_synchronizer.domain.models.products import Product
from invoice_synchronizer.domain.models.taxes import TaxType


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

    def __eq__(self, other) -> bool:
        """Compare two Invoice objects using date-only comparison for datetime fields."""
        if not isinstance(other, Invoice):
            return False

        # Compare all fields except the datetime fields normally
        if (
            self.client.document_number != other.client.document_number
            or self.invoice_id != other.invoice_id
            or self.payments != other.payments
            # or self.order_items != other.order_items
            or self.total != other.total
            or self.taxes_values != other.taxes_values
            or self.status != other.status
        ):
            return False

        # Compare created_on using only date part
        if self.created_on.date() != other.created_on.date():
            return False

        # Compare anulated_on using only date part (handle None case)
        if self.anulated_on is None and other.anulated_on is not None:
            return False
        if self.anulated_on is not None and other.anulated_on is None:
            return False
        if (
            self.anulated_on is not None
            and other.anulated_on is not None
            and self.anulated_on.date() != other.anulated_on.date()
        ):
            return False

        return True

    def __hash__(self) -> int:
        """Generate hash using date-only for datetime fields."""
        anulated_date = self.anulated_on.date() if self.anulated_on else None

        # Create a tuple of hashable elements
        hash_tuple = (
            hash(self.client),
            self.created_on.date(),
            anulated_date,
            hash(self.invoice_id),
            hash(tuple(self.payments)),
            hash(tuple(self.order_items)),
            self.total,
            hash(tuple(sorted(self.taxes_values.items()))),
            self.status,
        )

        return hash(hash_tuple)
