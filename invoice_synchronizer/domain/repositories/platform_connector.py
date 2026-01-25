"""PirPos client."""

from typing import List
from abc import ABC, abstractmethod
from datetime import datetime
from invoice_synchronizer.domain.models import User, Product, Invoice


class PlatformConnector(ABC):
    """Interface to define a connector to a platform."""

    @abstractmethod
    def get_clients(self) -> List[User]:
        """Get clients."""

    @abstractmethod
    def create_client(self, client: User) -> None:
        """Create client."""

    @abstractmethod
    def update_client(self, client: User) -> None:
        """Update client."""

    @abstractmethod
    def get_products(self) -> List[Product]:
        """Get current products."""

    @abstractmethod
    def create_product(self, product: Product) -> None:
        """Create product."""

    @abstractmethod
    def update_product(self, product: Product) -> None:
        """Update product."""

    @abstractmethod
    def get_invoices(self, init_day: datetime, end_day: datetime) -> List[Invoice]:
        """Get invoices.

        Parameters
        ----------
        init_day : datetime
            initial time to download invoices. year-month-day
        end_day : datetime
            end time to download invoices year-month-day

        Returns
        -------
        List[Invoice]
            Invoices per client in a range of time
        """

    @abstractmethod
    def create_invoice(self, invoice: Invoice) -> None:
        """Create invoice."""

    @abstractmethod
    def update_invoice(self, invoice: Invoice) -> None:
        """Update invoice."""
