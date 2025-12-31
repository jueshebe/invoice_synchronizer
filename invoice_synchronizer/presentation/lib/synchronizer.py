"""Exposed library"""

import logging
from invoice_synchronizer.infrastructure import SystemConfig, PirposConnector, SiigoConnector
from invoice_synchronizer.application import Updater


class InvoiceSynchronizer:
    """Invoice Synchronizer class."""

    def __init__(self):
        """Initialize the Invoice Synchronizer."""
        system_config = SystemConfig()
        pirpos_config = system_config.define_pirpos_config()
        siigo_config = system_config.define_siigo_config()
        logger = logging.getLogger()
        self.pirpos_connector = PirposConnector(pirpos_config, logger=logger)
        self.siigo_connector = SiigoConnector(siigo_config, logger=logger)

        self.updater = Updater(
            source_client=self.pirpos_connector,
            target_client=self.siigo_connector,
            default_client=system_config.default_user,
        )


if __name__ == "__main__":
    synchronizer = InvoiceSynchronizer()

    synchronizer.updater.update_clients()
