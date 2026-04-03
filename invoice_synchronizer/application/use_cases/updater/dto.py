"""DTO for the updater use case."""
from datetime import datetime
from typing import List
from pydantic import BaseModel
from invoice_synchronizer.domain.synchronization.synchronization import (
    DetectedError,
    SynchronizationType,
    SynchronizationModels,
)


class ProcessReport(BaseModel):
    """Process specific invoices model."""

    synchronization_type: SynchronizationType
    start_date: datetime
    end_date: datetime
    iterations: int
    errors: List[DetectedError] = []
    finished: List[SynchronizationModels] = []
    ref: List[SynchronizationModels] = []

