"""Synchronization domain models."""
from enum import Enum
from typing import Union
from datetime import datetime
from pydantic import BaseModel
from invoice_synchronizer.domain import User, Invoice, Product


class SynchronizationType(str, Enum):
    """Synchronization type."""
    CLIENTS = "clients"
    PRODUCTS = "products"
    INVOICES = "invoices"


class OperationType(str, Enum):
    """Operation type for synchronization."""
    CREATING = "creating"
    UPDATING = "updating"


SynchronizationModels = Union[User, Product, Invoice]


class DetectedError(BaseModel):
    """Detected error model."""

    type_op: OperationType
    error: str
    error_date: datetime
    failed_model: SynchronizationModels
