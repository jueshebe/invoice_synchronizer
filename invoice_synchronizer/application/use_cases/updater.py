"""Updater Class."""

from copy import copy
from logging import Logger
from datetime import datetime
import json
from invoice_synchronizer.domain import PlatformConnector, User
from invoice_synchronizer.application.use_cases.utils import (
    get_missing_outdated_clients,
    save_error,
    get_missing_outdated_products,
    get_missing_outdated_invoices,
)


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

        for counter, client in enumerate(missing_clients):
            try:
                self.target_client.create_client(client)
                self.logger.info("%s/%s clients created", counter + 1, len(missing_clients))
            except Exception as error:
                self.logger.error(
                    "Error with client %s check clients_errors.json", client.document_number
                )
                error_data = {
                    "type_op": "Creating",
                    "client": json.loads(client.json()),
                    "error": str(error),
                    "error_date": str(datetime.now()),
                }
                save_error(error_data, "clients_errors.json")

        for counter, outdated_client in enumerate(outdated_clients):
            try:
                self.target_client.update_client(outdated_client)
                self.logger.info("%s/%s clients updated", counter + 1, len(outdated_clients))
            except Exception as error:
                self.logger.error(
                    "Error with client %s check clients_errors.json",
                    outdated_client.document_number,
                )
                error_data = {
                    "type_op": "Updating",
                    "client": json.loads(outdated_client.json()),
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

        for counter, product in enumerate(missing_products):
            try:
                self.target_client.create_product(product)
                self.logger.info("%s/%s products created", counter + 1, len(missing_products))
            except Exception as error:
                self.logger.error("Error with product %s check products_error.json", product.name)
                error_data = {
                    "type_op": "Creating",
                    "product": json.loads(product.json()),
                    "error": str(error),
                    "error_date": str(datetime.now()),
                }
                save_error(error_data, "products_error.json")

        for counter, outdated_product in enumerate(outdated_products):
            try:
                self.target_client.update_product(outdated_product)
                self.logger.info("%s/%s products updated", counter + 1, len(outdated_products))

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

    def update_invoices(self, init_date: datetime, end_day: datetime) -> None:
        """Update and create invoices on target from source data."""
        self.logger.info("Updating invoices")
        ref_invoices = self.source_client.get_invoices(init_date, end_day)
        unchecked_invoices = self.target_client.get_invoices(init_date, end_day)

        # get missing and ourdated clients
        (
            missing_invoices,
            outdated_invoices,
            _,
        ) = get_missing_outdated_invoices(ref_invoices, unchecked_invoices)
        self.logger.info(
            "Found %s missing and %s outdated invoices",
            len(missing_invoices),
            len(outdated_invoices),
        )

        for counter, invoice in enumerate(outdated_invoices):
            try:
                self.target_client.update_invoice(invoice)
                self.logger.info("%s/%s invoice updated", counter + 1, len(outdated_invoices))
            except Exception as error:
                self.logger.error(
                    "Error with invoice %s%s check invoices_error.json",
                    invoice.invoice_id.prefix,
                    invoice.invoice_id.number,
                )
                error_data = {
                    "type_op": "Updating",
                    "invoice": json.loads(invoice.json()),
                    "error": str(error),
                }
                save_error(error_data, "invoices_error.json")

        for _ in range(100):
            failed_invoices = []
            for counter, invoice in enumerate(missing_invoices):
                try:
                    self.target_client.create_invoice(invoice)
                    self.logger.info(
                        "%s | %s/%s invoices created",
                        invoice.invoice_id.number,
                        counter + 1,
                        len(missing_invoices),
                    )
                except Exception as error:
                    failed_invoices.append(invoice)
                    self.logger.warning(
                        "Error with invoice %s%s\nerror: %s",
                        invoice.invoice_id.prefix,
                        invoice.invoice_id.number,
                        error,
                    )
                    error_data = {
                        "type_op": "Creating",
                        "invoice": json.loads(invoice.json()),
                        "error": str(error),
                    }
                    save_error(error_data, "invoices_error.json")

            missing_invoices = copy(failed_invoices)
            failed_invoices = []

            if len(missing_invoices) == 0:
                break
