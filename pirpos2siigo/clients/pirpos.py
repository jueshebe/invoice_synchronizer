"""PirPos client."""
from typing import Tuple, List, Dict, Union, Optional
import os
import json
import requests
import pandas as pd
from pirpos2siigo.clients.utils import (
    load_pirpos2siigo_config,
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

    def load_pirpos_clients(self, batch_clients: int = 200) -> pd.DataFrame:
        """Load pirpos clients.

        Parameters
        ----------
        batch_clients : int, optional
            batch used to download clients, by default 200

        Returns
        -------
        pd.Dataframe
          Dataframe with pirpos clients
        """
        page = 0
        clients = []
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
            data = response.json()["data"]
            if len(data) == 0:
                break
            clients.extend(data)
            page += 1
        clients_db = pd.json_normalize(clients)
        default_client = {
            "name": self._configuration.default_client.name,
            "document": self._configuration.default_client.document,
        }

        # adding default client
        clients_db.loc[len(clients_db.index)] = default_client
        clients_db = clients_db.fillna("")
        clients_db = clients_db.astype(str)
        clients_db["document"] = clients_db["document"].apply(clean_document)

        return clients_db

if __name__ == "__main__":
    user_name = os.getenv("PIRPOS_USER_NAME")
    user_password = os.getenv("PIRPOS_PASSWORD")
    path = "/Users/julianestehe/Programs/asadero/pirpos2siigo/configuration.JSON"
    connector = PirposConnector(user_name, user_password, path)
    loaded_clients = connector.load_pirpos_clients()
    pass
