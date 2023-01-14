"""Updater Class."""
from logging import Logger
from datetime import datetime
import json
import logging
from pirpos2siigo.clients import PirposConnector, SiigoConnector
from pirpos2siigo.service.utils import get_missing_outdated_clients, save_error


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
        """Update and create client on siigo from pirpos data.

        Parameters
        ----------
        clients : List[Client]
            List of outdated clients
        must_download: bool
            download siigo clients
        """
        self.logger.info("Updating clients")
        self.pirpos_client.get_pirpos_clients()
        self.siigo_client.get_siigo_clients()

        # get missing and ourdated clients
        missing_clients, outdated_clients = get_missing_outdated_clients(
            self.pirpos_client.clients, self.siigo_client.clients, self.siigo_client.configuration.default_client
        )

        if len(missing_clients) + len(outdated_clients) == 0:
            self.logger.info("All Clients already updated.")
            return

        for counter, client in enumerate(missing_clients):
            try:
                self.siigo_client.create_client(client)
                self.logger.info(f"{counter + 1}/{len(missing_clients)} created")
            except Exception as error:
                self.logger.error(f"Error with client {client.document} check clients_errors.json")
                error_data = {
                    "type_op": "Creating",
                    "client": json.loads(client.json()),
                    "error": str(error),
                    "error_date": str(datetime.now())
                }
                save_error(error_data, "clients_errors.json")

        for counter, difference_data in enumerate(outdated_clients):
            try:
                self.siigo_client.update_client(difference_data[0])
                self.logger.info(f"{counter + 1}/{len(outdated_clients)} updated")
            except Exception as error:
                self.logger.error(f"Error with client {client.document} check clients_errors.json")
                error_data = {
                    "type_op": "Updating",
                    "client": json.loads(client.json()),
                    "error": str(error)
                }
                save_error(error_data, "clients_error.json")
