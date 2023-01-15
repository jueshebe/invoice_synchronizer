"""Updater Class."""
from logging import Logger
from datetime import datetime
import json
import logging
from pirpos2siigo.clients import PirposConnector, SiigoConnector
from pirpos2siigo.service.utils import (
    get_missing_outdated_clients,
    save_error,
    get_missing_outdated_products,
)


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
                save_error(error_data, "clients_errors.json")

        for counter, difference_data in enumerate(outdated_clients):
            try:
                self.siigo_client.update_client(difference_data[0])
                self.logger.info(
                    f"{counter + 1}/{len(outdated_clients)} clients updated"
                )
            except Exception as error:
                self.logger.error(
                    f"Error with client {client.document} check clients_errors.json"
                )
                error_data = {
                    "type_op": "Updating",
                    "client": json.loads(client.json()),
                    "error": str(error),
                }
                save_error(error_data, "clients_error.json")

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
                save_error(error_data, "products_error.json")

        for counter, difference_data in enumerate(outdated_products):
            try:
                self.siigo_client.update_product(difference_data[0])
                self.logger.info(
                    f"{counter + 1}/{len(outdated_products)} products updated"
                )
            except Exception as error:
                self.logger.error(
                    f"Error with client {difference_data[0].name} check clients_errors.json"
                )
                error_data = {
                    "type_op": "Updating",
                    "client": json.loads(difference_data[0].json()),
                    "error": str(error),
                }
                save_error(error_data, "products_error.json")
