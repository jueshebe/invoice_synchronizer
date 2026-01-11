from typing import Dict, Any, Optional, List
from invoice_synchronizer.domain.models import User, DocumentType, TaxType, Product
from invoice_synchronizer.infrastructure.config import SystemParameters
from invoice_synchronizer.infrastructure.repositories.utils import find_mapping


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
            "address": client.address,
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
