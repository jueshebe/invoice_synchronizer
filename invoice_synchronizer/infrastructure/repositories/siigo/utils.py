from typing import Dict, Any, Optional
from invoice_synchronizer.domain import User
from invoice_synchronizer.domain.models.user import User, DocumentType


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
