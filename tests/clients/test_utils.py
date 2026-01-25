"""Utils tests."""
import json
from typing import List, Dict, Union
import pytest
from invoice_synchronizer.clients import (
    load_pirpos2siigo_config,
    ErrorConfigPirposSiigo,
    create_client,
)


@pytest.fixture
def input_config() -> List[Dict]:
    """Inputs for test load_pirpos2siigo_config."""
    return [
        {
            "payment_map": {
                "Efectivo": 3025,
                "Tarjeta débito": 3027,
                "Tarjeta crédito": 3027,
                "Transferencia bancaria": 7300,
                "Domicilio": 3025,
                "Rappi": 7325,
            },
            "taxes_map": [
                {
                    "pirpos_name": "I CONSUMO",
                    "siigo_name": "",
                    "value": 0.08,
                    "tax_id": 7081,
                },
                {
                    "pirpos_name": "None",
                    "siigo_name": "",
                    "value": 0.08,
                    "tax_id": 7081,
                },
            ],
            "invoice_map": {"LL": 13136, "": 27233},
            "default_client": {
                "name": "Consumidor Final",
                "email": "no-reply@pirpos.com",
                "phone": "3102830171",
                "address": "calle 35#27-16",
                "document": "222222222222",
                "check_digit": "0",
                "document_type": 13,
                "responsibilities": "R-99-PN",
                "city_detail": {
                    "city_name": "Villavicencio",
                    "city_state": "Meta",
                    "city_code": "50001",
                    "country_code": "Co",
                },
            },
        },
        {
            "payment_map": {
                "Efectivo": 3025,
                "Tarjeta débito": 3027,
                "Tarjeta crédito": 3027,
                "Transferencia bancaria": 7300,
                "Domicilio": 3025,
                "Rappi": 7325,
            },
            "taxes_map": [
                {
                    "prpos_name": "I CONSUMO",
                    "siigo_name": "",
                    "value": 0.08,
                    "tax_id": 7081,
                },
                {
                    "pirpos_name": "None",
                    "sigo_name": "",
                    "value": 0.08,
                    "tax_id": 7081,
                },
            ],
            "invoice_mp": {"LL": 13136, "": 27233},
            "default_client": {
                "nam": "Consumidor Final",
                "document": 222222222222,
            },
        },
    ]


def test_build_configuration(input_config: List[Dict]) -> None:
    """Check pytantic works properly with config objects."""

    # object must be created
    with open("tests/clients/test_config.json", "w", encoding="utf-8") as file:
        json.dump(input_config[0], file)

    assert load_pirpos2siigo_config("tests/clients/test_config.json")

    with open("tests/clients/test_config2.json", "w", encoding="utf-8") as file:
        json.dump(input_config[1], file)

    with pytest.raises(ErrorConfigPirposSiigo):
        load_pirpos2siigo_config("tests/clients/test_config2.json")


@pytest.fixture
def input_create_client() -> List[Dict[str, Union[str, int]]]:
    """Inputs for test create_client."""
    return [
        {
            "name": "test_client1"
        },
        {
            "name": "test_client2",
            "email": "test_email@gmail.com",
            "phone": "3102830171",
            "address": "calle 35#27-16",
            "document": "222222222222",
            "check_digit": "0",
            "document_type": 13,
            "responsibilities": "R-99-PN",
            "city_name": "Villavicencio",
            "city_state": "Meta",
            "city_code": "50001",
            "country_code": "Co"
        },
        {
            "name": "test_client2",
            "email2": "test_email@gmail.com",
            "phone": "3102830171",
            "address": "calle 35#27-16",
            "document": "222222222222",
            "check_digit": "0",
            "document_type": 13,
            "responsibilities": "R-99-PN",
            "city_name": "Villavicencio",
            "city_state": "Meta",
            "city_code": "50001",
            "country_code": "Co"
        } 
    ]


def test_create_client(input_create_client: List[Dict[str, Union[str, int]]]) -> None:
    """Check client creation with default parameters."""

    config = load_pirpos2siigo_config("tests/clients/test_config.json")
    assert create_client(configuration_file=config, **input_create_client[0])
    assert create_client(configuration_file=config, **input_create_client[1])

    with pytest.raises(TypeError):
        create_client(configuration_file=config, **input_create_client[2])
