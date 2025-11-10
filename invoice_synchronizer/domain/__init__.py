from invoice_synchronizer.domain.models import (
    Invoice,
    InvoiceId,
    InvoiceStatus,
    User,
    CityDetail,
    Responsibilities,
    DocumentType,
    Product,
    Payment,
    PaymentType,
    TaxType,
    Retention
)

from invoice_synchronizer.domain.repositories.platform_connector import PlatformConnector