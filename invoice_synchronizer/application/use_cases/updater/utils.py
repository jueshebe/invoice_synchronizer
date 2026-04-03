"""utils for services."""

from typing import List, Tuple
from invoice_synchronizer.domain import User, Product, Invoice
from invoice_synchronizer.domain.synchronization.synchronization import (
    SynchronizationType,
    OperationType,
)
from invoice_synchronizer.application.use_cases.updater.dto import ProcessReport


def get_missing_outdated_clients(
    ref_clients: List[User],
    unchecked_clients: List[User],
    default_client: User,
) -> Tuple[List[User], List[User]]:
    """Divide unchecked_clients in missing_clients and outdated_clients.

    Parameters
    ----------
    ref_clients : List[User]
        Reference clients. This is the source of truth.
    unchecked_clients : List[User]
        Clients to check against the reference clients.

    Returns
    -------
    Tuple[List[User], List[User]]
    """
    unchecked_documents = [client.document_number for client in unchecked_clients]

    missing_clients = [
        client for client in ref_clients if client.document_number not in unchecked_documents
    ]

    present_ref_clients: List[User] = [
        client
        for client in ref_clients
        if client.document_number in unchecked_documents
        and client.document_number != default_client.document_number
    ]

    outdated_clients: List[User] = []
    for ref_client in present_ref_clients:

        def filter_outdated_clients(client: User) -> bool:
            """Get outdated_clients."""
            return client.document_number == ref_client.document_number

        unchecked_client: User = list(filter(filter_outdated_clients, unchecked_clients))[0]

        if ref_client != unchecked_client:
            outdated_clients.append(ref_client)

    return (missing_clients, outdated_clients)


def get_missing_outdated_products(
    ref_products: List[Product],
    unchecked_products: List[Product],
) -> Tuple[List[Product], List[Product]]:
    """Divide unchecked_clients in missing_clients and outdated_clients."""
    unchecked_id = [product.product_id for product in unchecked_products]

    missing_products = [
        product for product in ref_products if product.product_id not in unchecked_id
    ]

    present_ref_products: List[Product] = [
        product for product in ref_products if product.product_id in unchecked_id
    ]

    outdated_products: List[Product] = []
    for ref_product in present_ref_products:

        def filter_outdated_product(product: Product) -> bool:
            """Get outdated_products."""
            return product.product_id == ref_product.product_id

        unchecked_product: Product = list(filter(filter_outdated_product, unchecked_products))[0]

        if ref_product != unchecked_product:
            outdated_products.append(ref_product)

    return (missing_products, outdated_products)


def get_missing_outdated_invoices(
    ref_invoices: List[Invoice],
    unchecked_invoices: List[Invoice],
) -> Tuple[List[Invoice], List[Invoice], List[Invoice]]:
    """Divide unchecked_invoices in missing_invoices and outdated_invoices."""
    unchecked_numbers: List[str] = [
        f"{invoice.invoice_id.prefix}{invoice.invoice_id.number}" for invoice in unchecked_invoices
    ]

    ref_invoices_numbers: List[str] = [
        f"{invoice.invoice_id.prefix}{invoice.invoice_id.number}" for invoice in ref_invoices
    ]

    missing_invoices = [
        invoice
        for invoice in ref_invoices
        if f"{invoice.invoice_id.prefix}{invoice.invoice_id.number}" not in unchecked_numbers
    ]

    must_be_deleted_invoices: List[Invoice] = [
        invoice
        for invoice in unchecked_invoices
        if f"{invoice.invoice_id.prefix}{invoice.invoice_id.number}" not in ref_invoices_numbers
    ]

    present_ref_invoices: List[Invoice] = [
        invoice
        for invoice in ref_invoices
        if f"{invoice.invoice_id.prefix}{invoice.invoice_id.number}" in unchecked_numbers
    ]

    outdated_invoices: List[Invoice] = []
    for ref_invoice in present_ref_invoices:

        def filter_outdated_invoice(invoice: Invoice) -> bool:
            """Get outdated_invoices."""
            return (
                invoice.invoice_id.prefix == ref_invoice.invoice_id.prefix
                and invoice.invoice_id.number == ref_invoice.invoice_id.number
            )

        unchecked_invoice: Invoice = list(filter(filter_outdated_invoice, unchecked_invoices))[0]

        if ref_invoice != unchecked_invoice:
            outdated_invoices.append((ref_invoice))

    return (missing_invoices, outdated_invoices, must_be_deleted_invoices)


def get_failed_invoices(process_report: ProcessReport) -> Tuple[List[Invoice], List[Invoice], List[Invoice]]:
    """Get failed invoices.

    Parameters
    ----------
    process_report : ProcessReport
        Process report with errors.

    Returns
    -------
    Tuple[List[Invoice], List[Invoice], List[Invoice]]
        Failed invoices by creation, updating, and reference invoices.
    """
    # Confirm it's an invoice synchronization
    if process_report.synchronization_type != SynchronizationType.INVOICES:
        raise ValueError(
            f"Expected INVOICES synchronization type, got {process_report.synchronization_type}"
        )

    failed_creating: List[Invoice] = []
    failed_updating: List[Invoice] = []

    for error in process_report.errors:
        # Check if failed_model is an Invoice
        if isinstance(error.failed_model, Invoice):
            if error.type_op == OperationType.CREATING:
                failed_creating.append(error.failed_model)
            elif error.type_op == OperationType.UPDATING:
                failed_updating.append(error.failed_model)

    # Filter ref to get only invoices
    ref_invoices = [item for item in process_report.ref if isinstance(item, Invoice)]

    return (failed_creating, failed_updating, ref_invoices)