"""Updater Use Case."""

from typing import List, Optional, cast
from logging import Logger
from datetime import datetime
from tqdm import tqdm
from invoice_synchronizer.domain import (
    PlatformConnector,
    User,
    Product,
    Invoice,
    DetectedError,
    SynchronizationType,
    SynchronizationModels,
    OperationType,
)
from invoice_synchronizer.application.use_cases.updater.dto import ProcessReport
from invoice_synchronizer.application.use_cases.updater.utils import (
    get_missing_outdated_clients,
    get_missing_outdated_products,
    get_missing_outdated_invoices,
    get_failed_invoices,
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
        logger.info("Updater ready.")

    def update_clients(self) -> ProcessReport:
        """Update and create clients."""
        self.logger.info("Updating clients")

        # variables for process report
        sinchronization_type = SynchronizationType.CLIENTS
        start_date = datetime.now()
        iterations = 1
        errors: List[DetectedError] = []
        finished_clients: List[User] = []

        source_clients = self.source_client.get_clients()
        target_clients = self.target_client.get_clients()

        # get missing and outdated clients
        missing_clients, outdated_clients = get_missing_outdated_clients(
            source_clients,
            target_clients,
            self.default_client,
        )

        if len(missing_clients) + len(outdated_clients) == 0:
            self.logger.info("All Clients already updated.")
            process_report = ProcessReport(
                synchronization_type=sinchronization_type,
                start_date=start_date,
                end_date=datetime.now(),
                iterations=iterations,
                errors=errors,
                finished=[],
                ref=cast(List[SynchronizationModels], source_clients),
            )
            return process_report

        for client in tqdm(missing_clients, desc="Creating clients"):
            try:
                self.target_client.create_client(client)
                finished_clients.append(client)
            except Exception as error:
                errors.append(
                    DetectedError(
                        type_op=OperationType.CREATING,
                        error=str(error),
                        error_date=datetime.now(),
                        failed_model=client,
                    )
                )

        for outdated_client in tqdm(outdated_clients, desc="Updating clients"):
            try:
                self.target_client.update_client(outdated_client)
                finished_clients.append(outdated_client)
            except Exception as error:
                errors.append(
                    DetectedError(
                        type_op=OperationType.UPDATING,
                        error=str(error),
                        error_date=datetime.now(),
                        failed_model=outdated_client,
                    )
                )

        process_report = ProcessReport(
            synchronization_type=sinchronization_type,
            start_date=start_date,
            end_date=datetime.now(),
            iterations=iterations,
            errors=errors,
            finished=cast(List[SynchronizationModels], finished_clients),
            ref=cast(List[SynchronizationModels], source_clients),
        )
        return process_report

    def update_products(self) -> ProcessReport:
        """Update and create products."""
        self.logger.info("Updating products")

        # variables for process report
        sinchronization_type = SynchronizationType.PRODUCTS
        start_date = datetime.now()
        iterations = 1
        errors: List[DetectedError] = []
        finished_products: List[Product] = []

        source_products = self.source_client.get_products()
        target_products = self.target_client.get_products()

        # get missing and ourdated clients
        missing_products, outdated_products = get_missing_outdated_products(
            source_products,
            target_products,
        )

        if len(missing_products) + len(outdated_products) == 0:
            self.logger.info("All Products already updated.")
            process_report = ProcessReport(
                synchronization_type=sinchronization_type,
                start_date=start_date,
                end_date=datetime.now(),
                iterations=iterations,
                errors=errors,
                finished=[],
                ref=cast(List[SynchronizationModels], source_products),
            )
            return process_report

        for product in tqdm(missing_products, desc="Creating products"):
            try:
                self.target_client.create_product(product)
                finished_products.append(product)
            except Exception as error:
                errors.append(
                    DetectedError(
                        type_op=OperationType.CREATING,
                        error=str(error),
                        error_date=datetime.now(),
                        failed_model=product,
                    )
                )

        for outdated_product in tqdm(outdated_products, desc="Updating products"):
            try:
                self.target_client.update_product(outdated_product)
                finished_products.append(outdated_product)
            except Exception as error:
                errors.append(
                    DetectedError(
                        type_op=OperationType.UPDATING,
                        error=str(error),
                        error_date=datetime.now(),
                        failed_model=outdated_product,
                    )
                )

        process_report = ProcessReport(
            synchronization_type=sinchronization_type,
            start_date=start_date,
            end_date=datetime.now(),
            iterations=iterations,
            errors=errors,
            finished=cast(List[SynchronizationModels], finished_products),
            ref=cast(List[SynchronizationModels], source_products),
        )
        return process_report

    def _update_invoices(
        self,
        init_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        process_specific_invoices: Optional[ProcessReport] = None,
    ) -> ProcessReport:
        """Update and create invoices on target from source data."""

        # variables for process report
        synchronization_type = SynchronizationType.INVOICES
        start_date = (
            process_specific_invoices.start_date if process_specific_invoices else datetime.now()
        )
        iterations = process_specific_invoices.iterations + 1 if process_specific_invoices else 1
        errors: List[DetectedError] = []
        finished_invoices: List[Invoice] = []

        if process_specific_invoices:
            missing_invoices, outdated_invoices, ref_invoices = get_failed_invoices(
                process_specific_invoices
            )
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

        if len(missing_invoices) + len(outdated_invoices) == 0:
            self.logger.info("All Invoices already updated.")
            process_report = ProcessReport(
                synchronization_type=synchronization_type,
                start_date=start_date,
                end_date=datetime.now(),
                iterations=iterations,
                errors=errors,
                finished=[],
                ref=cast(List[SynchronizationModels], ref_invoices),
            )
            return process_report

        self.logger.info(
            "Processing %s missing and %s outdated invoices",
            len(missing_invoices),
            len(outdated_invoices),
        )

        for invoice in tqdm(outdated_invoices, desc="Updating invoices"):
            try:
                self.target_client.update_invoice(invoice)
                finished_invoices.append(invoice)
            except Exception as error:
                errors.append(
                    DetectedError(
                        type_op=OperationType.UPDATING,
                        error=str(error),
                        error_date=datetime.now(),
                        failed_model=invoice,
                    )
                )

        for invoice in tqdm(missing_invoices, desc="Creating invoices"):
            try:
                self.target_client.create_invoice(invoice)
                finished_invoices.append(invoice)
            except Exception as error:
                errors.append(
                    DetectedError(
                        type_op=OperationType.CREATING,
                        error=str(error),
                        error_date=datetime.now(),
                        failed_model=invoice,
                    )
                )

        process_report = ProcessReport(
            synchronization_type=synchronization_type,
            start_date=start_date,
            end_date=datetime.now(),
            iterations=iterations,
            errors=errors,
            finished=cast(List[SynchronizationModels], finished_invoices),
            ref=cast(List[SynchronizationModels], ref_invoices),
        )
        return process_report

    def update_invoices(
        self,
        init_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        process_report: Optional[ProcessReport] = None,
        iterations: int = 0,
    ) -> ProcessReport:
        """Update invoices making iterations."""
        self.logger.info("Updating invoices")
        if iterations < 0:
            raise ValueError("Iterations must be greater than or equal to 0")

        for _ in range(iterations + 1):
            process_report = self._update_invoices(init_date, end_date, process_report)

            if len(process_report.errors) == 0:
                break

        if process_report is None:
            raise ValueError("Error invoices must be defined")
        return process_report
