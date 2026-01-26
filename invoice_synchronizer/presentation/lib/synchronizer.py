"""Exposed library"""

import os
import sys
import logging
from datetime import datetime
from invoice_synchronizer.infrastructure import SystemConfig, PirposConnector, SiigoConnector
from invoice_synchronizer.application import Updater


class InvoiceSynchronizer:
    """Invoice Synchronizer class."""

    def __init__(self):
        """Initialize the Invoice Synchronizer."""
        system_config = SystemConfig()
        pirpos_config = system_config.define_pirpos_config()
        siigo_config = system_config.define_siigo_config()
        logger = logging.getLogger("invoice_synchronizer_logger")
        logger.setLevel(level=logging.INFO)
        logs_stream_formatter = logging.Formatter(
            fmt=(
                "%(levelname)-8s %(asctime)s \t %(filename)s @function"
                "%(funcName)s line %(lineno)s \n%(message)s\n"
            ),
            datefmt="%H:%M:%S",
        )
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(logs_stream_formatter)
        console_handler.setLevel(level=logging.DEBUG)

        path_folder = os.path.join(os.path.expanduser("~"), ".config/pirpos2siigo")
        os.makedirs(path_folder, exist_ok=True)
        file_handler = logging.FileHandler(filename=os.path.join(path_folder, "logs.txt"))
        file_handler.setFormatter(logs_stream_formatter)
        file_handler.setLevel(level=logging.DEBUG)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        self.pirpos_connector = PirposConnector(pirpos_config, logger=logger)
        self.siigo_connector = SiigoConnector(siigo_config, logger=logger)

        self.updater = Updater(
            source_client=self.pirpos_connector,
            target_client=self.siigo_connector,
            default_client=system_config.default_user,
            logger=logger,
        )


if __name__ == "__main__":
    synchronizer = InvoiceSynchronizer()

    synchronizer.updater.update_products()
    synchronizer.updater.update_clients()
    init_date = datetime(2026, 1, 4)
    end_date = datetime(2026, 1, 4)
    # synchronizer.updater.update_invoices(init_date, end_date)
    # invoices = synchronizer.updater.target_client.get_invoices(init_date, end_date)
    # invoices_source = synchronizer.updater.source_client.get_invoices(init_date, end_date)
    print("Finished")
