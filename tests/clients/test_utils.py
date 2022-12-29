"""Utils tests."""
import pytest
import json
from pirpos2siigo.models import Pirpos2SiigoMap, DefaultClient, TaxesMap
from pirpos2siigo.clients import load_pirpos2siigo_config, ErrorConfigPirposSiigo


@pytest.fixture
def input_config():
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
                "document": 222222222222,
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


def test_build_configuration(input_config):
    """Check pytantic works properly with config objects."""

    # object must be created
    with open("tests/clients/test_config.json", "w", encoding="utf-8") as file:
        json.dump(input_config[0], file)

    assert load_pirpos2siigo_config("tests/clients/test_config.json")

    with open("tests/clients/test_config.json", "w", encoding="utf-8") as file:
        json.dump(input_config[1], file)

    with pytest.raises(ErrorConfigPirposSiigo):
        load_pirpos2siigo_config("tests/clients/test_config.json")
