"""Siigo client."""
from typing import List
import os
import json
import requests
from pirpos2siigo.models import Client, Product, Invoice
from pirpos2siigo.clients.utils import (
    load_pirpos2siigo_config,
    create_client,
    create_invoice,
    ErrorSiigoToken,
    ErrorLoadingSiigoClients,
    ErrorLoadingSiigoProducts,
    ErrorLoadingSiigoInvoices,
)


class SiigoConnector:
    """Class to manage siigo invoices, clients and products."""

    def __init__(
        self,
        siigo_username: str = os.environ["SIIGO_USER_NAME"],
        siigo_access_key: str = os.environ["SIIGO_ACCESS_KEY"],
        configuration_path: str = "configuration.JSON",
    ):
        """Parameters used to make a connection."""
        # Siigo API info
        self.__siigo_username = siigo_username
        self.__siigo_access_key = siigo_access_key
        self.__configuration = load_pirpos2siigo_config(configuration_path)
        self.__siigo_access_token = self.__get_siigo_access_token()
        self.__products: List[Product]
        self.__clients: List[Client]
        # self.load_pirpos_clients()
        # self.load_pirpos_products()

    def __get_siigo_access_token(self) -> str:
        """Obtiene el token de acceso para usar la API de SIIGO.

        Raises
        ------
        ErrorSiigoToken
            Error solicitando token, datos incorrectos.

        Returns
        -------
        str
            access_token

        """
        url = "https://api.siigo.com/auth"
        values = {
            "username": self.__siigo_username,
            "access_key": self.__siigo_access_key,
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, data=json.dumps(values), headers=headers)

        if not response.ok:
            raise ErrorSiigoToken(
                "Error solicitando token, revisar userName y access_key"
            )
        data = response.json()

        if "access_token" in data.keys():
            access_token = data["access_token"]
            assert isinstance(access_token, str)
        else:
            raise ErrorSiigoToken(
                "access_token key is not present in the respose"
            )

        return access_token


if __name__ == "__main__":

    user_name = os.getenv("SIIGO_USER_NAME")
    user_password = os.getenv("SIIGO_ACCESS_KEY")
    PATH = (
        "/Users/julianestehe/Programs/asadero/pirpos2siigo/configuration.JSON"
    )
    assert isinstance(user_name, str)
    assert isinstance(user_password, str)
    connector = SiigoConnector(user_name, user_password, PATH)
