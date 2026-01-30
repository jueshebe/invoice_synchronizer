"""Updater Class."""

from typing import List, Optional, Any
from logging import Logger
from datetime import datetime
import json
from pydantic import BaseModel, model_validator
from tqdm import tqdm
from invoice_synchronizer.domain import PlatformConnector, User, Invoice, TaxType
from invoice_synchronizer.application.use_cases.utils import (
    get_missing_outdated_clients,
    save_error,
    get_missing_outdated_products,
    get_missing_outdated_invoices,
)


class ProcessSpecificInvoices(BaseModel):
    """Process specific invoices model."""

    missing_invoices: List[Invoice] = []
    outdated_invoices: List[Invoice] = []

    @model_validator(mode='before')
    @classmethod
    def fix_taxes_values(cls, data: Any) -> Any:
        """Fix taxes_values dict keys from string representation to TaxType objects."""
        if isinstance(data, dict):
            for invoice_list_name in ['missing_invoices', 'outdated_invoices']:
                if invoice_list_name in data:
                    for invoice in data[invoice_list_name]:
                        # Fix taxes_values in invoice
                        if 'taxes_values' in invoice and isinstance(invoice['taxes_values'], dict):
                            new_taxes_values = {}
                            for tax_str, value in invoice['taxes_values'].items():
                                # Parse the string representation: "tax_name='I CONSUMO' tax_percentage=8.0"
                                if isinstance(tax_str, str) and "tax_name=" in tax_str:
                                    try:
                                        # Extract tax_name and tax_percentage
                                        name_part = tax_str.split("tax_name=")[1].split(" tax_percentage=")[0].strip("'")
                                        percentage_part = float(tax_str.split("tax_percentage=")[1])
                                        tax_obj = TaxType(tax_name=name_part, tax_percentage=percentage_part)
                                        new_taxes_values[tax_obj] = value
                                    except (ValueError, IndexError):
                                        # If parsing fails, skip this entry
                                        continue
                                else:
                                    # If it's already a proper key, keep it
                                    new_taxes_values[tax_str] = value
                            invoice['taxes_values'] = new_taxes_values

                        # Fix taxes_values in order_items products
                        if 'order_items' in invoice:
                            for order_item in invoice['order_items']:
                                if 'product' in order_item and 'taxes_values' in order_item['product']:
                                    product = order_item['product']
                                    if isinstance(product['taxes_values'], dict):
                                        new_taxes_values = {}
                                        for tax_str, value in product['taxes_values'].items():
                                            if isinstance(tax_str, str) and "tax_name=" in tax_str:
                                                try:
                                                    name_part = tax_str.split("tax_name=")[1].split(" tax_percentage=")[0].strip("'")
                                                    percentage_part = float(tax_str.split("tax_percentage=")[1])
                                                    tax_obj = TaxType(tax_name=name_part, tax_percentage=percentage_part)
                                                    new_taxes_values[tax_obj] = value
                                                except (ValueError, IndexError):
                                                    continue
                                            else:
                                                new_taxes_values[tax_str] = value
                                        product['taxes_values'] = new_taxes_values
        return data


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

        for counter, client in enumerate(tqdm(missing_clients, desc="Creating clients")):
            try:
                self.target_client.create_client(client)
                self.logger.info("%s/%s clients created", counter + 1, len(missing_clients))
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

        for counter, outdated_client in enumerate(tqdm(outdated_clients, desc="Updating clients")):
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

        for counter, product in enumerate(missing_products):
            try:
                self.target_client.create_product(product)
                self.logger.info("%s/%s products created", counter + 1, len(missing_products))
            except Exception as error:
                self.logger.error("Error with product %s check products_error.json", product.name)
                error_data = {
                    "type_op": "Creating",
                    "product": json.loads(product.model_dump_json()),
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

    def update_invoices(
        self,
        init_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        process_specific_invoices: Optional[ProcessSpecificInvoices] = None,
    ) -> ProcessSpecificInvoices:
        """Update and create invoices on target from source data."""
        self.logger.info("Updating invoices")

        if process_specific_invoices:
            missing_invoices = process_specific_invoices.missing_invoices
            outdated_invoices = process_specific_invoices.outdated_invoices
        elif init_date and end_date:
            self.logger.info("Fetching invoices from %s to %s", init_date, end_date)
            self.logger.info("Getting invoices from source platform")
            ref_invoices = self.source_client.get_invoices(init_date, end_date)
            self.logger.info("Getting invoices from target platform")
            unchecked_invoices = self.target_client.get_invoices(init_date, end_date)

            # get missing and ourdated clients
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

        error_outdated_invoices: List[Invoice] = []
        for counter, invoice in enumerate(outdated_invoices):
            try:
                self.target_client.update_invoice(invoice)
                self.logger.info(
                    "%s | %s/%s invoices updated",
                    invoice.invoice_id.number,
                    counter + 1,
                    len(outdated_invoices),
                )
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

        return ProcessSpecificInvoices(
            missing_invoices=error_missing_invoices,
            outdated_invoices=error_outdated_invoices,
        )

    def update_invoices_iterations(
        self, init_date: datetime, end_date: datetime, iterations: int = 0
    ) -> ProcessSpecificInvoices:
        """Update invoices making iterations."""
        error_invoices = None
        for _ in range(iterations + 1):
            error_invoices = self.update_invoices(init_date, end_date, error_invoices)

            if not error_invoices.missing_invoices and not error_invoices.outdated_invoices:
                break

        if error_invoices is None:
            error_invoices = ProcessSpecificInvoices()
        return error_invoices

