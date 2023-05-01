"""utils for services."""
from typing import List, Tuple, Dict, Any
from os import path
import json
from pirpos2siigo.models import Client, Product, Invoice


def get_missing_outdated_clients(
    ref_clients: List[Client],
    unchecked_clients: List[Client],
    default_client: Client,
) -> Tuple[List[Client], List[Tuple[Client, Dict[str, Any]]]]:
    """Divide unchecked_clients in missing_clients and outdated_clients.

    Parameters
    ----------
    ref_clients : List[Client]
        Reference used as updated clients
    unchecked_clients : List[Client]
        Unchecked clients

    Returns
    -------
    Tuple[List[Client], List[Client]]
    """
    unchecked_documents = [client.document for client in unchecked_clients]

    missing_clients = [
        client
        for client in ref_clients
        if client.document not in unchecked_documents
    ]

    present_ref_clients: List[Client] = [
        client
        for client in ref_clients
        if client.document in unchecked_documents
        and client.document != default_client.document
    ]

    outdated_clients: List[Tuple[Client, Dict[str, Any]]] = []
    for ref_client in present_ref_clients:

        def filter_outdated_clients(client: Client) -> bool:
            """Get outdated_clients."""
            return client.document == ref_client.document

        unchecked_client: Client = list(
            filter(filter_outdated_clients, unchecked_clients)
        )[
            0
        ]  # TODO: is supposed Siigo does not repear docuemnt clients

        unchecked_dict = unchecked_client.dict()
        ref_dict = ref_client.dict()
        for key in ref_dict:
            if (
                key not in ["siigo_id", "pirpos_id", "check_digit"]
                and unchecked_dict[key] != ref_dict[key]
            ):
                if key == "name":
                    name1 = unchecked_client.name.replace(" ", "")
                    name2 = ref_client.name.replace(" ", "")
                    if name1 == name2:
                        continue

                ref_client.siigo_id = unchecked_client.siigo_id
                difference = {key: unchecked_dict[key]}
                outdated_clients.append((ref_client, difference))
                break

    return (missing_clients, outdated_clients)


def get_missing_outdated_products(
    ref_products: List[Product],
    unchecked_products: List[Product],
) -> Tuple[List[Product], List[Tuple[Product, Dict[str, Any]]]]:
    """Divide unchecked_clients in missing_clients and outdated_clients."""
    unchecked_id = [product.product_id for product in unchecked_products]

    missing_products = [
        product
        for product in ref_products
        if product.product_id not in unchecked_id
    ]

    present_ref_products: List[Product] = [
        product
        for product in ref_products
        if product.product_id in unchecked_id
    ]

    outdated_products: List[Tuple[Product, Dict[str, Any]]] = []
    for ref_product in present_ref_products:

        def filter_outdated_product(product: Product) -> bool:
            """Get outdated_products."""
            return product.product_id == ref_product.product_id

        unchecked_product: Product = list(
            filter(filter_outdated_product, unchecked_products)
        )[
            0
        ]  # TODO: is supposed Siigo does not repear docuemnt clients

        unchecked_dict = unchecked_product.dict()
        ref_dict = ref_product.dict()
        for key in ref_dict:
            if (
                key not in ["siigo_id", "product_id"]
                and unchecked_dict[key] != ref_dict[key]
            ):

                ref_product.siigo_id = unchecked_product.siigo_id
                difference = {key: unchecked_dict[key]}
                outdated_products.append((ref_product, difference))
                break

    return (missing_products, outdated_products)


def get_missing_outdated_invoices(
    ref_invoices: List[Invoice],
    unchecked_invoices: List[Invoice],
) -> Tuple[List[Invoice], List[Tuple[Invoice, Dict[str, Any]]]]:
    """Divide unchecked_invoices in missing_invoices and outdated_invoices."""
    unchecked_numbers: List[str] = [
        f"{invoice.invoice_prefix.siigo_id}{invoice.invoice_number}"
        for invoice in unchecked_invoices
    ]

    missing_invoices = [
        invoice
        for invoice in ref_invoices
        if f"{invoice.invoice_prefix.siigo_id}{invoice.invoice_number}"
        not in unchecked_numbers
    ]

    present_ref_invoices: List[Invoice] = [
        invoice
        for invoice in ref_invoices
        if f"{invoice.invoice_prefix.siigo_id}{invoice.invoice_number}"
        in unchecked_numbers
    ]

    outdated_invoices: List[Tuple[Invoice, Dict[str, Any]]] = []
    for ref_invoice in present_ref_invoices:

        def filter_outdated_invoice(invoice: Invoice) -> bool:
            """Get outdated_invoices."""
            return (
                invoice.invoice_prefix.siigo_id == ref_invoice.invoice_prefix.siigo_id
                and invoice.invoice_number == ref_invoice.invoice_number
            )

        unchecked_invoice: Invoice = list(
            filter(filter_outdated_invoice, unchecked_invoices)
        )[
            0
        ]  # TODO: is supposed Siigo does not repear docuemnt clients

        unchecked_dict = unchecked_invoice.dict()
        ref_dict = ref_invoice.dict()
        for key in ref_dict:
            if (
                key not in ["siigo_id", "invoice_prefix", "cachier", "seller", "products", "payment_method"]  # TODO: Make better this check
                and unchecked_dict[key] != ref_dict[key]
            ):
                if key == "client":
                    if unchecked_invoice.client.document == ref_invoice.client.document:
                        continue
                if key == "created_on":
                    if unchecked_invoice.created_on.date() == ref_invoice.created_on.date():
                        continue

                ref_invoice.siigo_id = unchecked_invoice.siigo_id
                difference = {key: unchecked_dict[key]}
                outdated_invoices.append((ref_invoice, difference))
                break

    return (missing_invoices, outdated_invoices)


def save_error(error_data: Dict[str, str], file_name: str) -> None:
    """Save error on json file."""
    if path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as json_file:
            clients_errors: List[Dict[str, str]] = json.load(json_file)
    else:
        clients_errors = []

    # save error
    clients_errors.append(error_data)

    with open(file_name, "w", encoding="utf-8") as json_file:
        json_file.write(json.dumps(clients_errors, indent=4))


if __name__ == "__main__":
    error_data_test = {"ke4": "1", "prueba": "error"}
    exception_test = KeyError("some error")
    FILE_NAME = "test_error.json"

    save_error(error_data_test, FILE_NAME)
