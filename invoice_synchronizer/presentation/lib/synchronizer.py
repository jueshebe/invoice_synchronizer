"""Invoice Synchronizer library"""

import os
import sys
import logging
from datetime import datetime
from invoice_synchronizer.infrastructure import SystemConfig, PirposConnector, SiigoConnector
from invoice_synchronizer.application import Updater, ProcessReport


class InvoiceSynchronizer:
    """Invoice synchronization service between Loggro and Siigo platforms.

    This class provides a high-level interface for synchronizing business data
    (clients, products, and invoices) between Loggro point-of-sale system and
    Siigo accounting platform.

    The synchronization process maintains data integrity by:
    - Creating missing records in the target system (Siigo)
    - Updating existing records that have changed
    - Handling errors gracefully and providing detailed logging

    Attributes:
        pirpos_connector: Interface to Loggro system
        siigo_connector: Interface to Siigo system
        updater: Core synchronization logic handler

    Example:
        >>> from datetime import datetime
        >>> sync = InvoiceSynchronizer()
        >>>
        >>> # Synchronize reference data first
        >>> clients_report = sync.update_clients()
        >>> products_report = sync.update_products()
        >>>
        >>> # Then synchronize invoices
        >>> invoices_report = sync.update_invoices(
        ...     init_date=datetime(2026, 1, 1),
        ...     end_date=datetime(2026, 1, 31),
        ...     iterations=5
        ... )
        >>> print(f"Errors: {len(invoices_report.errors)}")
    """

    def __init__(self):
        """Initialize the Invoice Synchronizer with required configurations.

        Sets up connections to both Loggro and Siigo systems, configures logging,
        and prepares the synchronization components.

        Requires environment variables for authentication:
        - Loggro credentials and configuration
        - Siigo API credentials and configuration

        The logger is configured to output to both console and a log file
        located at ~/.config/pirpos2siigo/logs.txt

        Raises:
            KeyError: If required environment variables are missing
            Exception: If system configuration or connection setup fails
        """
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

    def update_products(self) -> ProcessReport:
        """Synchronize products from Loggro to Siigo.

        Fetches all products from Loggro and synchronizes them with Siigo.
        Creates missing products and updates existing ones that have changed.

        This method should typically be run before synchronizing invoices to ensure
        all product references are available in Siigo.

        Returns:
            ProcessReport: Report with synchronization results including errors and finished products.

        Raises:
            Exception: If connection to either Loggro or Siigo fails, or if
                      critical product synchronization errors occur.
        """
        return self.updater.update_products()

    def update_clients(self) -> ProcessReport:
        """Synchronize clients from Loggro to Siigo.

        Fetches all clients/customers from Loggro and synchronizes them with Siigo.
        Creates missing clients and updates existing ones that have changed.

        This method should typically be run before synchronizing invoices to ensure
        all client references are available in Siigo.

        Returns:
            ProcessReport: Report with synchronization results including errors and finished clients.

        Raises:
            Exception: If connection to either PirPOS or Siigo fails, or if
                      critical client synchronization errors occur.
        """
        return self.updater.update_clients()

    def update_invoices(
        self, init_date: datetime, end_date: datetime, iterations: int
    ) -> ProcessReport:
        """Update invoices from Loggro to Siigo within a date range.

        Synchronizes invoices between Loggro and Siigo platforms for the specified date range.
        The process runs in iterations to handle large volumes of data efficiently.

        Args:
            init_date (datetime): Start date for invoice synchronization (inclusive).
            end_date (datetime): End date for invoice synchronization (inclusive).
            iterations (int): Number of iterations to process the date range. Higher values
                            process smaller batches, useful for large date ranges or rate limiting.

        Returns:
            ProcessReport: Report with synchronization results including:
                - errors: List of DetectedError objects for failed operations
                - finished: Invoices successfully synchronized
                - ref: Reference invoices from source system

        Example:
            >>> from datetime import datetime
            >>> sync = InvoiceSynchronizer()
            >>> result = sync.update_invoices(
            ...     init_date=datetime(2026, 1, 1),
            ...     end_date=datetime(2026, 1, 31),
            ...     iterations=5
            ... )
            >>> print(f"Errors: {len(result.errors)}")
            >>> print(f"Finished: {len(result.finished)}")
        """
        return self.updater.update_invoices(
            init_date=init_date, end_date=end_date, iterations=iterations
        )

    def update_specific_invoices(
        self, process_specific_invoices: ProcessReport
    ) -> ProcessReport:
        """Process specific invoices that previously failed synchronization.

        Takes a ProcessReport object containing missing or outdated invoices
        and attempts to synchronize them again. This is typically used to retry
        invoices that failed in a previous synchronization run.

        Args:
            process_specific_invoices (ProcessReport): Report with errors from previous run.

        Returns:
            ProcessReport: Updated report with synchronization results.

        Example:
            >>> # Load previously failed invoices from JSON
            >>> with open("error_invoices.json", "r") as f:
            ...     data = json.load(f)
            >>> failed_report = ProcessReport(**data)
            >>>
            >>> # Retry synchronization
            >>> sync = InvoiceSynchronizer()
            >>> result = sync.update_specific_invoices(failed_report)
            >>>
            >>> # Check if any invoices still failed
            >>> if len(result.errors) == 0:
            ...     print("All invoices synchronized successfully!")
        """
        return self.updater.update_invoices(
            process_report=process_specific_invoices, iterations=0
        )


if __name__ == "__main__":
    synchronizer = InvoiceSynchronizer()

    # result_products = synchronizer.updater.update_products()
    # result_clients = synchronizer.updater.update_clients()
    init_date_test = datetime(2026, 4, 1)
    end_date_test = datetime(2026, 4, 1)
    result_invoices = synchronizer.update_invoices(init_date_test, end_date_test, 1)
    print("Finished")
