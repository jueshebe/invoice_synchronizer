"""End modules."""

from importlib.metadata import version
from invoice_synchronizer.presentation.lib.synchronizer import InvoiceSynchronizer

__version__ = version("invoice_synchronizer")
__all__ = ["InvoiceSynchronizer"]
