"""Utils used by clients."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from invoice_synchronizer.domain import (
    User,
    Product,
    TaxType,
    OrderItems,
    Invoice,
    Payment,
    InvoiceId,
    InvoiceStatus,
    ParseDataError,
)
from invoice_synchronizer.infrastructure.config import SystemParameters
from invoice_synchronizer.infrastructure.repositories.utils import (
    find_mapping,
    filter_client_by_document,
)


def define_pirpos_product(
    system_parameters: SystemParameters,
    product_id: str,
    name: str,
    final_price: float,
    raw_taxes: Optional[List[Dict[str, Any]]] = None,
) -> Product:
    """Define pirpos product from pirpos data."""
    raw_taxes = raw_taxes or []
    taxes: List[TaxType] = []
    taxes_values: Dict[TaxType, float] = {}
    percentages_taxes: List[float] = []

    for tax in raw_taxes:
        if tax.get("taxName"):
            tax_name = tax["taxName"]
            tax_percentage = tax["taxValue"]
        else:
            try:
                tax_name = tax["tax"]["name"]
                tax_percentage = tax["tax"]["percentage"]
            except Exception:
                continue

        mapping = find_mapping(system_parameters.taxes, "pirpos_id", tax_name)
        tax_name = mapping["system_id"]
        tax_type = TaxType(tax_name=tax_name, tax_percentage=tax_percentage)
        taxes.append(tax_type)
        percentages_taxes.append(tax_percentage)

    base_price = final_price / (1 + sum(percentages_taxes) / 100)

    for parsed_tax in taxes:
        tax_value = base_price * (parsed_tax.tax_percentage / 100)
        taxes_values[parsed_tax] = tax_value

    product = Product(
        product_id=product_id,
        name=name,
        base=base_price,
        final_price=final_price,
        taxes=taxes,
        taxes_values=taxes_values,
    )
    return product


def define_pirpos_product_subproducts(
    system_parameters: SystemParameters,
    product_id: str,
    name: str,
    location_stock: Dict[str, Any],
    sub_products: List[Dict[str, Any]],
) -> List[Product]:
    """From pirpos data create products."""
    products: List[Product] = []

    if len(sub_products) == 0:
        products.append(
            define_pirpos_product(
                system_parameters,
                product_id=product_id,
                name=name,
                final_price=location_stock["price"],
                raw_taxes=location_stock["taxes"],
            )
        )
    else:
        for sub_product in sub_products:
            product_id = sub_product["_id"]
            name = sub_product["name"]
            location_stock = sub_product["locationsStock"][0]
            products.append(
                define_pirpos_product(
                    system_parameters,
                    product_id=product_id,
                    name=name,
                    final_price=location_stock["price"],
                    raw_taxes=location_stock["taxes"],
                )
            )
    return products


def filter_product_by_id(products: List[Product], product_id: str) -> Product:
    """Filter product by product id."""

    def filter_product(product: Product, product_id: str = product_id) -> bool:
        return product.product_id == product_id

    filtered_products: List[Product] = list(filter(filter_product, products))
    if len(filtered_products) == 0:
        raise ValueError(f"Product with id {product_id} not found.")
    return filtered_products[0]


def define_pirpos_invoices(
    data: List[Dict[str, Any]],
    system_parameters: SystemParameters,
    clients: List[User],
) -> List[Invoice]:

    invoices: List[Invoice] = []
    for invoice_info in data:
        try:
            # select client
            client_document = int(invoice_info["client"]["document"])
            client = filter_client_by_document(clients, client_document)

            created_time = datetime.strptime(invoice_info["createdOn"], "%Y-%m-%dT%H:%M:%S.%f%z")
            anulated_time = datetime.strptime(invoice_info["modifiedOn"], "%Y-%m-%dT%H:%M:%S.%f%z")
            invoice_prefix = invoice_info["invoicePrefix"]
            invoice_number = invoice_info["seq"]
            invoice_id = InvoiceId(prefix=invoice_prefix, number=invoice_number)

            payments: List[Payment] = []
            for payment_data in invoice_info["paid"]["paymentMethodValue"]:
                mapping = find_mapping(
                    system_parameters.payments, "pirpos_id", payment_data["paymentMethod"]
                )
                payment_type = mapping["system_id"]
                value = payment_data["value"]
                payment = Payment(payment_type=payment_type, value=value)
                payments.append(payment)

            # select products
            order_items: List[OrderItems] = []
            taxes_values: Dict[TaxType, float] = {}
            for product_info in invoice_info["products"]:
                product_id = product_info["idInternal"]
                quantity = product_info["quantity"]
                product = define_pirpos_product(
                    system_parameters,
                    product_id=product_id,
                    name=product_info["name"],
                    final_price=float(product_info["price"]),
                    raw_taxes=product_info.get("taxes", []),
                )
                order_items.append(OrderItems(product=product, quantity=quantity))
                for tax, value in product.taxes_values.items():
                    if tax in taxes_values:
                        taxes_values[tax] += value * quantity
                    else:
                        taxes_values[tax] = value * quantity

            total = invoice_info["total"]

            mapping = find_mapping(
                system_parameters.invoice_status, "pirpos_id", invoice_info["status"]
            )
            status_type = mapping["system_id"]
            status = InvoiceStatus(status_type)

            invoice_obj = Invoice(
                client=client,
                created_on=created_time,
                anulated_on=anulated_time if status == InvoiceStatus.ANULATED else None,
                invoice_id=invoice_id,
                payments=payments,
                order_items=order_items,
                total=total,
                taxes_values=taxes_values,
                status=status,
            )
            invoices.append(invoice_obj)

        except Exception as error:
            print(
                f"Factura {invoice_info['invoicePrefix']}{invoice_info['seq']}",
                f"raise error: {error}",
            )
            raise ParseDataError(
                (
                    f"Factura {invoice_info['invoicePrefix']}{invoice_info['seq']}"
                    f"raise error: {error}"
                )
            ) from error
    return invoices
