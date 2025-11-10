"""PirPos client."""
from typing import List, Tuple
import os
from abc import ABC, abstractmethod
import json
from logging import Logger
import logging
from datetime import datetime
import time
from invoice_synchronizer.domain.models import User, Product, Invoice


class PlatformConnector(ABC):
    """Interface to define a connector to a platform."""

    @abstractmethod
    def get_clients(self) -> List[User]:
        """Get clients."""

    @abstractmethod
    def get_products(self) -> List[Product]:
        """Get current products."""

    @abstractmethod
    def get_invoices(
        self, init_day: datetime, end_day: datetime
    ) -> List[Invoice]:
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

    @property
    @abstractmethod
    def clients(self) -> List[User]:
        """Getter for clients."""

    @property
    @abstractmethod
    def products(self) -> List[Product]:
        """Getter for products."""