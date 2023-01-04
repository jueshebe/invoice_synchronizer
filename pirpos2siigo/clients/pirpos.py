"""PirPos client."""
from typing import List
import os
import json
import requests
from pirpos2siigo.models import Client
from pirpos2siigo.clients.utils import (
    load_pirpos2siigo_config,
    create_client,
    ErrorPirposToken,
    ErrorLoadingPirposClients
)


class PirposConnector:
    """Class to manage pirpos invoices and clients."""

    def __init__(
        self,
        pirpos_username: str,
        pirpos_password: str,
        configuration_path: str,
    ):
        """Parameters used to make a connection."""
        self.__pirpos_username = pirpos_username
        self.__pirpos_password = pirpos_password
        self._configuration = load_pirpos2siigo_config(configuration_path)
        self.__pirpos_access_token = self.__get_siigo_access_token()

    def __get_siigo_access_token(self) -> str:
        """Get pirpos access token to comunicate with the server.

        Raises
        ------
        ErrorPirposToken

        Returns
        -------
        str
            token
        """
        url = "https://api.pirpos.com/login"
        values = {
            "name": "",
            "email": self.__pirpos_username,
            "password": self.__pirpos_password,
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, data=json.dumps(values), headers=headers)

        if not response.ok:
            raise ErrorPirposToken(
                "Error getting Pirpos token, check email and password"
            )

        data = response.json()
        if "tokenCurrent" in data.keys():
            access_token = data["tokenCurrent"]
            assert isinstance(access_token, str)
        else:
            raise ErrorPirposToken(
                "tokenCurrent key is not present in the respose"
            )
        return access_token

    def load_pirpos_clients(self, batch_clients: int = 200) -> List[Client]:
        """Load pirpos clients.

        Parameters
        ----------
        batch_clients : int, optional
            batch used to download clients, by default 200

        Returns
        -------
        List[Client]
          list of Client object.
        """
        page = 0
        clients: List[Client] = []
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }
        while True:
            url = "https://api.pirpos.com/clients?pagination=true"\
                f"&limit={batch_clients}&page={page}&clientData=&"

            response = requests.request("GET", url, headers=headers)
            if not response.ok:
                raise ErrorLoadingPirposClients(
                    f"Can't download PirPos clients\n {response.text}"
                )

            data = response.json()["data"]  # TODO: check incoming data with BaseModel class
            if len(data) == 0:
                break

            for client_data in data:
                clients.append(create_client(
                    configuration_file=self._configuration,
                    name=client_data["name"],
                    email=client_data.get("email"),
                    phone=client_data.get("phone"),
                    address=client_data.get("address"),
                    document=client_data.get("document"),
                    check_digit=client_data.get("checkDigit"),
                    document_type=client_data.get("idDocumentType"),
                    responsibilities=client_data.get("responsibilities"),
                    city_name=client_data.get("cityDetail", {}).get("cityName"),
                    city_state=client_data.get("cityDetail", {}).get("stateName"),
                    city_code=client_data.get("cityDetail", {}).get("cityCode"),
                    country_code=client_data.get("cityDetail", {}).get("countryCode")
                )
                )
            page += 1

        return clients

    def _load_pirpos_products(self, batch_products: int = 200):
        """get created products on pirpos

        Parameters
        ----------
        batch_products : int, optional
            batch used to download products, by default 200

        Returns
        -------
        pd.DataFrame
            Pirpos products
        """

        page = 0
        products = []
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://app.pirpos.com/",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }

        while True:
            url = f"https://api.pirpos.com/products?pagination=true&limit={batch_products}&page={page}&name=&categoryId=undefined&useInRappi=undefined&"
            response = requests.request("GET", url, headers=headers)
            if not response.ok:
                raise ErrorLoadingPirposProducts(
                    "Can't download Pirpos Products"
                )
            data = response.json()["data"]
            if len(data) == 0:
                break
            for product_info in data:
                products.extend(read_pirpos_product(product_info))

            page += 1

        products_db = pd.json_normalize(products)
        products_db = products_db.fillna("")
        products_db = products_db.astype(str)
        products_db["name"] = products_db["name"].apply(Utils.normalize)
        return products_db


if __name__ == "__main__":
    user_name = os.getenv("PIRPOS_USER_NAME")
    user_password = os.getenv("PIRPOS_PASSWORD")
    PATH = "/Users/julianestehe/Programs/asadero/pirpos2siigo/configuration.JSON"
    assert isinstance(user_name, str)
    assert isinstance(user_password, str)
    connector = PirposConnector(user_name, user_password, PATH)
    # loaded_clients = connector.load_pirpos_clients()
    loaded_products = connector._load_pirpos_products()
