"""Updater Class."""
from logging import Logger
from copy import copy
from datetime import datetime
import json
import logging
from pirpos2siigo.clients import PirposConnector, SiigoConnector
from pirpos2siigo.service.utils import (
    get_missing_outdated_clients,
    save_error,
    get_missing_outdated_products,
    get_missing_outdated_invoices,
    filter_only_deleted_invoices,
)
from pirpos2siigo.models import InvoiceStatus


class Updater:
    """Class to update data from pirpos to siigo."""

    def __init__(
        self,
        pirpos_client: PirposConnector,
        siigo_client: SiigoConnector,
        logger: Logger = logging.getLogger(),
    ):
        """Load Pirpos and Siigo clients."""
        self.pirpos_client: PirposConnector = pirpos_client
        self.siigo_client: SiigoConnector = siigo_client
        self.logger = logger
        logger.info("Updated ready.")

    def update_clients(self) -> None:
        """Update and create client on siigo from pirpos data."""
        self.logger.info("Updating clients")
        self.pirpos_client.get_pirpos_clients()
        self.siigo_client.get_siigo_clients()

        # get missing and ourdated clients
        missing_clients, outdated_clients = get_missing_outdated_clients(
            self.pirpos_client.clients,
            self.siigo_client.clients,
            self.siigo_client.configuration.default_client,
        )

        if len(missing_clients) + len(outdated_clients) == 0:
            self.logger.info("All Clients already updated.")
            return

        for counter, client in enumerate(missing_clients):
            try:
                self.siigo_client.create_client(client)
                self.logger.info(
                    f"{counter + 1}/{len(missing_clients)} clients created"
                )
            except Exception as error:
                self.logger.error(
                    f"Error with client {client.document} check clients_errors.json"
                )
                error_data = {
                    "type_op": "Creating",
                    "client": json.loads(client.json()),
                    "error": str(error),
                    "error_date": str(datetime.now()),
                }
                save_error(error_data, "../clients_errors.json")

        for counter, difference_data in enumerate(outdated_clients):
            try:
                self.siigo_client.update_client(difference_data[0])
                self.logger.info(
                    f"{counter + 1}/{len(outdated_clients)} clients updated"
                )
            except Exception as error:
                self.logger.error(
                    f"Error with client {difference_data[0].document} check clients_errors.json"
                )
                error_data = {
                    "type_op": "Updating",
                    "client": json.loads(difference_data[0].json()),
                    "error": str(error),
                }
                save_error(error_data, "../clients_error.json")

    def update_products(self) -> None:
        """Update and create products on siigo from pirpos data."""
        self.logger.info("Updating products")
        self.pirpos_client.get_pirpos_products()
        self.siigo_client.get_siigo_products()

        # get missing and ourdated clients
        missing_products, outdated_products = get_missing_outdated_products(
            self.pirpos_client.products,
            self.siigo_client.products,
        )

        if len(missing_products) + len(outdated_products) == 0:
            self.logger.info("All Products already updated.")
            return

        for counter, product in enumerate(missing_products):
            try:
                self.siigo_client.create_product(product)
                self.logger.info(
                    f"{counter + 1}/{len(missing_products)} products created"
                )
            except Exception as error:
                self.logger.error(
                    f"Error with product {product.name} check products_error.json"
                )
                error_data = {
                    "type_op": "Creating",
                    "product": json.loads(product.json()),
                    "error": str(error),
                    "error_date": str(datetime.now()),
                }
                save_error(error_data, "../products_error.json")

        for counter, difference_data in enumerate(outdated_products):
            try:
                self.siigo_client.update_product(difference_data[0])
                self.logger.info(
                    f"{counter + 1}/{len(outdated_products)} products updated"
                )

            except Exception as error:
                self.logger.error(
                    f"Error with product {difference_data[0].name} check products_errors.json"
                )
                error_data = {
                    "type_op": "Updating",
                    "client": json.loads(difference_data[0].json()),
                    "error": str(error),
                }
                save_error(error_data, "../products_error.json")

    def update_invoices(self, init_date: datetime, end_day: datetime) -> None:
        """Update and create invoices on siigo from pirpos data."""
        self.logger.info("Updating invoices")
        ref_invoices = self.pirpos_client.get_pirpos_invoices_per_client(
            init_date, end_day
        )
        unchecked_invoices = self.siigo_client.get_siigo_invoices(
            init_date, end_day
        )

        # get missing and ourdated clients
        (
            missing_invoices,
            outdated_invoices,
            must_be_deleted,
        ) = get_missing_outdated_invoices(ref_invoices, unchecked_invoices)

        total = 0
        for ref_invoice in ref_invoices:
            total += ref_invoice.total

        for counter, difference_data in enumerate(outdated_invoices):
            invoice = difference_data[0]
            try:
                self.siigo_client.update_invoice(invoice)
                self.logger.info(
                    f"{counter + 1}/{len(outdated_invoices)} invoice updated"
                )
            except Exception as error:
                self.logger.error(
                    f"Error with invoice {invoice.invoice_prefix}{invoice.invoice_number} check invoices_error.json"
                )
                error_data = {
                    "type_op": "Updating",
                    "invoice": json.loads(difference_data[0].json()),
                    "error": str(error),
                }
                save_error(error_data, "../invoices_error.json")

        if len(missing_invoices) + len(outdated_invoices) == 0:
            self.logger.info("All invoices already updated.")
            return

        for _ in range(100):
            failed_invoices = []
            for counter, invoice in enumerate(missing_invoices):
                try:
                    self.siigo_client.create_invoice(invoice)
                    self.logger.info(
                        f"{invoice.invoice_number} | {counter + 1}/{len(missing_invoices)} invoices created"
                    )
                except Exception as error:
                    failed_invoices.append(invoice)
                    self.logger.warning(
                        f"Error with invoice {invoice.invoice_prefix}{invoice.invoice_number}\nerror: {error}"
                    )
                    # self.logger.error(
                    #     f"Error with invoice {invoice.invoice_prefix}{invoice.invoice_number} check invoices_error.json"
                    # )
                    # error_data = {
                    #     "type_op": "Creating",
                    #     "invoice": json.loads(invoice.json()),
                    #     "error": str(error),
                    #     "error_date": str(datetime.now()),
                    # }
                    # save_error(error_data, "invoices_error.json")
            missing_invoices = copy(failed_invoices)
            failed_invoices = []

            if len(missing_invoices) == 0:
                break

    def update_canceled_invoices(
        self, init_date: datetime, end_day: datetime
    ) -> None:
        self.logger.info("Checking canceled invoices")
        ref_invoices = self.pirpos_client.get_pirpos_invoices_per_client(
            init_date, end_day, status=InvoiceStatus.CANCELED
        )
        unchecked_invoices = self.siigo_client.get_siigo_invoices(
            init_date, end_day
        )

        (
            missing_invoices,
            outdated_invoices,
            _,
        ) = get_missing_outdated_invoices(ref_invoices, unchecked_invoices)

        for _ in range(100):
            failed_invoices = []
            for counter, invoice in enumerate(missing_invoices):
                try:
                    if not invoice.payment_method:
                        self.logger.info(
                            f"Invoice without payment method {invoice.invoice_prefix}{invoice.invoice_number}"
                        )
                        continue
                    self.siigo_client.create_invoice(invoice)
                    self.logger.info(
                        f"{invoice.invoice_number} | {counter + 1}/{len(missing_invoices)} invoices created"
                    )
                except Exception as error:
                    failed_invoices.append(invoice)
                    self.logger.warning(
                        f"Error with invoice {invoice.invoice_prefix}{invoice.invoice_number}\nerror: {error}"
                    )
                    # self.logger.error(
                    #     f"Error with invoice {invoice.invoice_prefix}{invoice.invoice_number} check invoices_error.json"
                    # )
                    # error_data = {
                    #     "type_op": "Creating",
                    #     "invoice": json.loads(invoice.json()),
                    #     "error": str(error),
                    #     "error_date": str(datetime.now()),
                    # }
                    # save_error(error_data, "invoices_error.json")
            missing_invoices = copy(failed_invoices)
            failed_invoices = []

            if len(missing_invoices) == 0:
                break

        self.logger.info("Anulating invoices")

        unchecked_invoices = self.siigo_client.get_siigo_invoices(
            init_date, end_day
        )


        invoices_to_delete = filter_only_deleted_invoices(
            ref_invoices, unchecked_invoices
        )

        for _ in range(4):
            failed_invoices = []
            for counter, invoice in enumerate(invoices_to_delete):
                try:
                    # self.siigo_client.remove_invoice(invoice)
                    self.siigo_client.credit_note(invoice)
                    self.logger.info(
                        f"{invoice.invoice_number} | {counter + 1}/{len(ref_invoices)} invoices with credit note"
                    )
                except Exception as error:
                    failed_invoices.append(invoice)
                    self.logger.warning(
                        f"Error with invoice {invoice.invoice_prefix}{invoice.invoice_number}\nerror: {error}"
                    )
            if len(failed_invoices) == 0:
                break
            else:
                invoices_to_delete = copy(failed_invoices)
