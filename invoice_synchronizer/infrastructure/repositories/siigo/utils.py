from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import re
from invoice_synchronizer.domain import (
    User,
    DocumentType,
    TaxType,
    Product,
    Invoice,
    InvoiceId,
    InvoiceStatus,
    Payment,
    OrderItems,
    ParseDataError,
)
from invoice_synchronizer.infrastructure.config import SystemParameters
from invoice_synchronizer.infrastructure.repositories.utils import (
    find_mapping,
    filter_client_by_document,
)


def user_to_siigo_payload(client: User, contacts: Optional[Any] = None) -> Dict[str, Any]:
    """Convert User model to Siigo payload."""
    full_name = client.name.split(" ") + (client.last_name.split(" ") if client.last_name else [""])

    name, last_name = [full_name[0].strip(), " ".join(full_name[1:])]
    last_name = last_name if len(last_name) > 0 else "."
    last_name = last_name[0:50].strip()

    if client.document_type == DocumentType.NIT:
        person_type = "Company"
        if last_name:
            client_name = [name + " " + last_name]
        else:
            client_name = [client.name]
    else:
        person_type = "Person"
        if last_name:
            client_name = [name, last_name]
        else:
            client_name = [name]
    state_code = str(client.city_detail.state_code)
    state_code = state_code if len(state_code) > 1 else f"0{state_code}"

    contacts_info = (
        contacts
        if contacts
        else [
            {
                "first_name": name,
                "last_name": last_name,
                "email": client.email,
                "phone": {
                    "indicative": "",
                    "number": client.phone[0:10],
                    "extension": "",
                },
            }
        ]
    )
    address = re.sub(r"[^a-zA-Z0-9 ]", "", client.address)
    payload = {
        "type": "Customer",
        "person_type": person_type,
        "id_type": str(client.document_type.value),
        "identification": str(client.document_number),
        "check_digit": str(client.check_digit),
        "name": client_name,
        "commercial_name": "",
        "branch_office": 0,
        "active": "true",
        "vat_responsible": "false",
        "fiscal_responsibilities": [{"code": client.responsibilities.value}],
        "address": {
            "address": address,
            "city": {
                "country_code": str(client.city_detail.country_code),
                "state_code": state_code,
                "city_code": str(client.city_detail.city_code),
            },
            "postal_code": "",
        },
        "phones": [
            {
                "indicative": "",
                "number": client.phone[0:10],
                "extension": "",
            }
        ],
        "contacts": contacts_info,
        "comments": "Created from Pirpos2Siigo software",
        # "related_users": {"seller_id": 629, "collector_id": 629},
    }
    return payload


def define_siigo_product(
    system_parameters: SystemParameters,
    code: str,
    name: str,
    final_price: float,
    raw_taxes: List[Dict[str, Any]],
) -> Product:
    """From siigo data create Product."""

    taxes: List[TaxType] = []
    taxes_values: Dict[TaxType, float] = {}
    percentages_taxes: List[float] = []
    for raw_tax in raw_taxes:
        mapping = find_mapping(system_parameters.taxes, "siigo_id", raw_tax["id"])
        tax_name = mapping["system_id"]
        tax_percentage = raw_tax["percentage"]
        tax_type = TaxType(tax_name=tax_name, tax_percentage=tax_percentage)
        taxes.append(tax_type)
        percentages_taxes.append(tax_percentage)

    base_price = final_price / (1 + sum(percentages_taxes) / 100)

    for parsed_tax in taxes:
        tax_value = base_price * (parsed_tax.tax_percentage / 100)
        taxes_values[parsed_tax] = tax_value

    product = Product(
        product_id=code,
        name=name,
        base=base_price,
        final_price=final_price,
        taxes=taxes,
        taxes_values=taxes_values,
    )
    return product


def product_to_siigo_payload(
    system_parameters: SystemParameters,
    product: Product,
) -> Dict[str, Any]:
    """Convert Product model to Siigo payload."""
    tax_ids = []
    for tax in product.taxes:
        mapping = find_mapping(system_parameters.taxes, "system_id", tax.tax_name)
        tax_ids.append({"id": int(mapping["siigo_id"])})

    if product.final_price > 0:
        prices = [
            {
                "currency_code": "COP",
                "price_list": [
                    {
                        "position": 1,
                        "value": product.final_price if product.final_price > 0 else 1,
                    }
                ],
            }
        ]
    else:
        prices = []

    payload = {
        "code": product.product_id,
        "name": product.name,
        "account_group": 673,
        "type": "Product",
        "stock_control": "false",
        "active": "true",
        "tax_classification": "Taxed",
        "tax_included": "true",
        "tax_consumption_value": 0,
        "taxes": tax_ids,
        "prices": prices,
        "unit": "94",
        "unit_label": "unidad",
        "reference": "REF1",
        "description": ".",
    }
    return payload


def define_siigo_invoice(
    system_parameters: SystemParameters,
    data: List[Dict[str, Any]],
    clients: List[User],
) -> Dict[str, Invoice]:

    invoices: Dict[str, Invoice] = {}
    for invoice_info in data:
        try:
            # select client
            client_document = int(invoice_info["customer"]["identification"])
            client = filter_client_by_document(clients, client_document)

            # Parse created time with optional milliseconds
            date_str = invoice_info["date"]
            try:
                # Try with milliseconds first
                created_time = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
            except ValueError:
                # Fall back to format without milliseconds
                created_time = datetime.strptime(date_str, "%Y-%m-%d")
            # anulated_time = datetime.strptime(invoice_info["modifiedOn"], "%Y-%m-%dT%H:%M:%S.%f%z")
            # anulated_time = None
            siigo_id = invoice_info["id"]
            invoice_number = invoice_info["number"]
            invoice_prefix = invoice_info["prefix"]
            invoice_id = InvoiceId(prefix=invoice_prefix, number=invoice_number)

            payments: List[Payment] = []
            for payment_data in invoice_info["payments"]:
                mapping = find_mapping(
                    system_parameters.payments, "siigo_id", str(payment_data["id"])
                )
                payment_type = mapping["system_id"]
                value = payment_data["value"]
                payment = Payment(payment_type=payment_type, value=value)
                payments.append(payment)

            # select products
            order_items: List[OrderItems] = []
            taxes_values: Dict[TaxType, float] = {}
            for product_info in invoice_info["items"]:
                product_id = product_info["code"]
                quantity = product_info["quantity"]
                product = define_siigo_product(
                    system_parameters,
                    code=product_id,
                    name=product_info["description"],
                    final_price=float(product_info["total"]) / quantity,
                    raw_taxes=product_info.get("taxes", []),
                )
                order_items.append(OrderItems(product=product, quantity=quantity))
                for tax, value in product.taxes_values.items():
                    if tax in taxes_values:
                        taxes_values[tax] += value * quantity
                    else:
                        taxes_values[tax] = value * quantity

            total = invoice_info["total"]

            # mapping = find_mapping(
            #     system_parameters.invoice_status, "siigo_id", invoice_info["status"]
            # )
            # status_type = mapping["system_id"]
            # status = InvoiceStatus(status_type)
            status = InvoiceStatus.PAID

            invoice_obj = Invoice(
                client=client,
                created_on=created_time,
                # anulated_on=anulated_time if status == InvoiceStatus.ANULATED else None,
                anulated_on=None,
                invoice_id=invoice_id,
                payments=payments,
                order_items=order_items,
                total=total,
                taxes_values=taxes_values,
                status=status,
            )
            invoices[siigo_id] = invoice_obj

        except Exception as error:
            print(
                f"Factura {invoice_info['prefix']}{invoice_info['number']}",
                f"raise error: {error}",
            )
            raise ParseDataError(
                (
                    f"Factura {invoice_info['prefix']}{invoice_info['number']}"
                    f"raise error: {error}"
                )
            ) from error
    return invoices


def get_invoice_number_2_siigo_id_mapping(invoice_by_id: Dict[str, Invoice]) -> Dict[str, str]:
    """Get mapping from invoice number to siigo id."""
    mapping: Dict[str, str] = {}
    for siigo_id, invoice in invoice_by_id.items():
        invoice_number_str = f"{invoice.invoice_id.prefix}{invoice.invoice_id.number}"
        mapping[invoice_number_str] = siigo_id
    return mapping


def update_invoices_with_credit_notes(
    invoices: Dict[str, Invoice],
    credit_note_data: List[Dict[str, Any]],
    credit_note_doc_name_acentry: Dict[str, str],
) -> Tuple[List[Invoice], Dict[str, str]]:
    """Update invoices with credit note information."""
    invoice_id_to_credit_acentry_id: Dict[str, str] = {}
    for credit_note in credit_note_data:
        invoice_id = credit_note["invoice"]["id"]
        credit_note_date = datetime.strptime(credit_note["date"], "%Y-%m-%d")
        invoice = invoices.get(invoice_id)
        if not invoice:
            continue
        invoice.anulated_on = credit_note_date
        invoice.status = InvoiceStatus.ANULATED
        invoice_id_to_credit_acentry_id[invoice_id] = credit_note_doc_name_acentry[
            credit_note["name"]
        ]
    return list(invoices.values()), invoice_id_to_credit_acentry_id


def invoice_to_siigo_payload(
    system_parameters: SystemParameters,
    invoice: Invoice,
    retentions: List[int],
    seller_id: int,
) -> Dict[str, Any]:
    """Convert Invoice model to Siigo payload."""
    mapping = find_mapping(system_parameters.prefixes, "system_id", invoice.invoice_id.prefix)
    document_id = mapping["siigo_id"]
    items = []

    for order in invoice.order_items:
        if order.product.base <= 0:
            continue
        item = {
            "code": order.product.product_id,
            "description": order.product.name,
            "quantity": order.quantity,
            "price": round(order.product.base, 6),
            "discount": 0,
            "taxes": [
                {
                    "id": find_mapping(system_parameters.taxes, "system_id", tax.tax_name)[
                        "siigo_id"
                    ]
                }
                for tax in order.product.taxes
            ],
        }
        items.append(item)

    payments = [] 
    for payment in invoice.payments:
        product_payment = {
            "id": find_mapping(system_parameters.payments, "system_id", payment.payment_type)[
                "siigo_id"
            ],
            "value": round(payment.value, 2),
            "due_date": invoice.created_on.strftime("%Y-%m-%d"),
        }
        payments.append(product_payment)

    payload = {
        "document": {"id": document_id},
        "number": invoice.invoice_id.number,
        "date": invoice.created_on.strftime("%Y-%m-%d"),
        "customer": {
            "identification": str(invoice.client.document_number),
            "branch_office": 0,
        },
        "seller": seller_id,
        "observations": "invoice created from pirpos2siigo software",
        "items": items,
        "payments": payments,
        "retentions": [{"id": retention} for retention in retentions],
    }
    return payload


def get_payload_credit_note(
    invoice_id: str,
    invoice: Invoice,
    system_parameters: SystemParameters,
    credit_note_docuement_id: int,
) -> Dict[str, Any]:
    items = []
    for order in invoice.order_items:
        item = {
            "code": order.product.product_id,
            "quantity": order.quantity,
            "description": order.product.name,
            "price": round(order.product.base, 6),
            "taxes": [
                {"id": find_mapping(system_parameters.taxes, "system_id", tax.tax_name)["siigo_id"]}
                for tax in order.product.taxes
            ],
        }
        items.append(item)

    payments = []
    for payment in invoice.payments:
        product_payment = {
            "id": find_mapping(system_parameters.payments, "system_id", payment.payment_type)[
                "siigo_id"
            ],
            "value": round(payment.value, 2),
            "due_date": invoice.created_on.strftime("%Y-%m-%d"),
        }
        payments.append(product_payment)

    if invoice.anulated_on is None:
        raise ValueError("Invoice anulated_on date is required for credit note payload.")

    payload = {
        "document": {"id": credit_note_docuement_id},
        "date": invoice.anulated_on.strftime("%Y-%m-%d"),
        "invoice": invoice_id,
        "reason": "2",
        "items": items,
        "payments": payments,
    }
    return payload
