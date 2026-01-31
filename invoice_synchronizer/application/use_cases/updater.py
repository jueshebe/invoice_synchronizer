"""Updater Class."""

from typing import List, Optional
from logging import Logger
from datetime import datetime
import json
from pydantic import BaseModel
from tqdm import tqdm
from invoice_synchronizer.domain import PlatformConnector, User, Invoice
from invoice_synchronizer.application.use_cases.utils import (
    get_missing_outdated_clients,
    save_error,
    get_missing_outdated_products,
    get_missing_outdated_invoices,
)


class InvoicesProcessReport(BaseModel):
    """Process specific invoices model."""

    error_missing_invoices: List[Invoice] = []
    error_outdated_invoices: List[Invoice] = []
    finished_invoices: List[Invoice] = []


class Updater:
    """Class to update data from pirpos to siigo."""

    def __init__(
        self,
        source_client: PlatformConnector,
        target_client: PlatformConnector,
        default_client: User,
        logger: Logger,
    ):
        """Load data fomr source and update on target."""
        self.source_client: PlatformConnector = source_client
        self.target_client: PlatformConnector = target_client
        self.default_client: User = default_client
        self.logger = logger
        logger.info("Updated ready.")

    def update_clients(self) -> None:
        """Update and create clients."""
        self.logger.info("Updating clients")
        source_clients = self.source_client.get_clients()
        target_clients = self.target_client.get_clients()

        # get missing and ourdated clients
        missing_clients, outdated_clients = get_missing_outdated_clients(
            source_clients,
            target_clients,
            self.default_client,
        )

        if len(missing_clients) + len(outdated_clients) == 0:
            self.logger.info("All Clients already updated.")
            return

        for client in tqdm(missing_clients, desc="Creating clients"):
            try:
                self.target_client.create_client(client)
            except Exception as error:
                self.logger.error(
                    "Error with client %s check clients_errors.json", client.document_number
                )
                error_data = {
                    "type_op": "Creating",
                    "client": json.loads(client.model_dump_json()),
                    "error": str(error),
                    "error_date": str(datetime.now()),
                }
                save_error(error_data, "clients_errors.json")

        for outdated_client in tqdm(outdated_clients, desc="Updating clients"):
            try:
                self.target_client.update_client(outdated_client)
            except Exception as error:
                self.logger.error(
                    "Error with client %s check clients_errors.json",
                    outdated_client.document_number,
                )
                error_data = {
                    "type_op": "Updating",
                    "client": json.loads(outdated_client.model_dump_json()),
                    "error": str(error),
                }
                save_error(error_data, "clients_error.json")

    def update_products(self) -> None:
        """Update and create products."""
        self.logger.info("Updating products")
        source_products = self.source_client.get_products()
        target_products = self.target_client.get_products()

        # get missing and ourdated clients
        missing_products, outdated_products = get_missing_outdated_products(
            source_products,
            target_products,
        )

        if len(missing_products) + len(outdated_products) == 0:
            self.logger.info("All Products already updated.")
            return

        for product in tqdm(missing_products, desc="Creating products"):
            try:
                self.target_client.create_product(product)
            except Exception as error:
                self.logger.error("Error with product %s check products_error.json", product.name)
                error_data = {
                    "type_op": "Creating",
                    "product": json.loads(product.model_dump_json()),
                    "error": str(error),
                    "error_date": str(datetime.now()),
                }
                save_error(error_data, "products_error.json")

        for outdated_product in tqdm(outdated_products, desc="Updating products"):
            try:
                self.target_client.update_product(outdated_product)

            except Exception as error:
                self.logger.error(
                    "Error with product %s check products_errors.json", outdated_product.name
                )
                error_data = {
                    "type_op": "Updating",
                    "client": json.loads(outdated_product.json()),
                    "error": str(error),
                }
                save_error(error_data, "products_error.json")

    def update_invoices(
        self,
        init_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        process_specific_invoices: Optional[InvoicesProcessReport] = None,
    ) -> InvoicesProcessReport:
        """Update and create invoices on target from source data."""
        self.logger.info("Updating invoices")

        if process_specific_invoices:
            missing_invoices = process_specific_invoices.error_missing_invoices
            outdated_invoices = process_specific_invoices.error_outdated_invoices
        elif init_date and end_date:
            self.logger.info("Fetching invoices from %s to %s", init_date, end_date)
            self.logger.info("Getting invoices from source platform")
            ref_invoices = self.source_client.get_invoices(init_date, end_date)
            self.logger.info("Getting invoices from target platform")
            unchecked_invoices = self.target_client.get_invoices(init_date, end_date)

            # get missing and outdated clients
            (
                missing_invoices,
                outdated_invoices,
                _,
            ) = get_missing_outdated_invoices(ref_invoices, unchecked_invoices)
        else:
            raise ValueError("Must provide init_date and end_date or specific invoices to process")

        self.logger.info(
            "Processing %s missing and %s outdated invoices",
            len(missing_invoices),
            len(outdated_invoices),
        )

        finished_invoices : List[Invoice] = []
        error_outdated_invoices: List[Invoice] = []
        for invoice in tqdm(outdated_invoices, desc="Updating invoices"):
            try:
                self.target_client.update_invoice(invoice)
                finished_invoices.append(invoice)
            except Exception as error:
                self.logger.error(
                    "Error with invoice %s%s check invoices_error.json",
                    invoice.invoice_id.prefix,
                    invoice.invoice_id.number,
                )
                error_data = {
                    "type_op": "Updating",
                    "invoice": json.loads(invoice.model_dump_json()),
                    "error": str(error),
                }
                save_error(error_data, "invoices_error.json")
                error_outdated_invoices.append(invoice)

        error_missing_invoices: List[Invoice] = []
        for invoice in tqdm(missing_invoices, desc="Creating invoices"):
            try:
                self.target_client.create_invoice(invoice)
                finished_invoices.append(invoice)
            except Exception as error:
                self.logger.warning(
                    "Error with invoice %s%s\nerror: %s",
                    invoice.invoice_id.prefix,
                    invoice.invoice_id.number,
                    error,
                )
                error_data = {
                    "type_op": "Creating",
                    "invoice": json.loads(invoice.model_dump_json()),
                    "error": str(error),
                }
                save_error(error_data, "invoices_error.json")
                error_missing_invoices.append(invoice)

        all_finished_invoices = finished_invoices
        if process_specific_invoices:
            all_finished_invoices = process_specific_invoices.finished_invoices

        return InvoicesProcessReport(
            error_missing_invoices=error_missing_invoices,
            error_outdated_invoices=error_outdated_invoices,
            finished_invoices=all_finished_invoices,
        )

    def update_invoices_iterations(
        self, init_date: datetime, end_date: datetime, iterations: int = 0
    ) -> InvoicesProcessReport:
        """Update invoices making iterations."""
        error_invoices = None
        for _ in range(iterations + 1):
            error_invoices = self.update_invoices(init_date, end_date, error_invoices)

            if not error_invoices.error_missing_invoices and not error_invoices.error_outdated_invoices:
                break

        if error_invoices is None:
            error_invoices = InvoicesProcessReport()
        return error_invoices

