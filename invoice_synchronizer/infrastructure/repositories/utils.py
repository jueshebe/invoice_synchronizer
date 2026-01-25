"""Utils used by clients."""

from typing import Dict, Any, List
from invoice_synchronizer.domain.models import (
    User,
)


def find_mapping(
    mappings: List[Dict[str, Any]], client_key: str, client_value: str
) -> Dict[str, Any]:
    """Find mapping value in system configuration."""
    for mapping in mappings:
        if str(mapping[client_key]) == str(client_value):
            return mapping
    raise ValueError(f"Mapping for {client_key}: {client_value} not found. Check system mappings.")


def filter_client_by_document(clients: List[User], document: int) -> User:
    """Filter client by document number."""

    def filter_client(client: User, document: int = document) -> bool:
        return client.document_number == document

    filtered_clients: List[User] = list(filter(filter_client, clients))
    if len(filtered_clients) == 0:
        raise ValueError(f"Client with document {document} not found.")
    return filtered_clients[0]
