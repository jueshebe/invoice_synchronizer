"""Exposed library"""

from invoice_synchronizer.infrastructure import SystemConfig, PirposConnector, SiigoConnector
from invoice_synchronizer.application import Updater


class InvoiceSynchronizer:
    """Invoice Synchronizer class."""

    def __init__(self):
        """Initialize the Invoice Synchronizer."""
        system_config = SystemConfig()
        pirpos_config = system_config.define_pirpos_config()
        siigo_config = system_config.define_siigo_config()
        self.pirpos_connector = PirposConnector(
            pirpos_username=pirpos_config.pirpos_username,
            pirpos_password=pirpos_config.pirpos_password,
            configuration_path=pirpos_config.configuration_path,
            batch_size=pirpos_config.batch_size,
        )
        self.siigo_connector = SiigoConnector(
            siigo_username=siigo_config.siigo_username,
            siigo_access_key=siigo_config.siigo_access_key,
            configuration_path=siigo_config.configuration_path,
        )

        self.updated = Updater(
            source_client=self.pirpos_connector,
            target_client=self.siigo_connector,
            default_client=system_config.default_user,
        )
