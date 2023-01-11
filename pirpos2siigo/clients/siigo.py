"""Siigo client."""
from typing import List, Tuple
import os
import json
from datetime import datetime, timedelta
import requests
from pirpos2siigo.models import Client, DocumentType, Product, Invoice, TaxInfo
from pirpos2siigo.clients.utils import (
    load_pirpos2siigo_config,
    create_client,
    create_invoice,
    get_missing_outdated_clients,
    ErrorSiigoToken,
    ErrorLoadingSiigoClients,
    ErrorLoadingSiigoProducts,
    ErrorLoadingSiigoInvoices,
    ErrorCreatingSiigoClient,
    ErrorUpdatingSiigoClient

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
        self.get_siigo_clients()
        self.get_siigo_products()

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

    def get_siigo_clients(self, page_size: int = 100) -> None:
        """Load Siigo clients.

        Parameters
        ----------
        batch_clients : int, optional
            batch used to download clients, by default 200

        Returns
        -------
          List[Client]
          List with Siigo clients
        """
        url = (
            "https://api.siigo.com/v1/customers?page={page}"
            f"&page_size={page_size}"
        )
        payload = ""
        headers = {
            "authority": "services.siigo.com",
            "accept": "application/json, text/plain, */*",
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }
        page = 1
        clients: List[Client] = []

        while True:
            response = requests.request(
                "GET",
                url.format(page=page),
                headers=headers,
                data=payload,
            )
            if not response.ok:
                raise ErrorLoadingSiigoClients(
                    f"Can't download Siigo clients\n {response.text}"
                )

            data = response.json()["results"]
            if len(data) == 0:
                break

            for client_data in data:
                if not client_data.get("name"):
                    continue

                if len(client_data.get("contacts", [])) > 0:
                    contacts = client_data.get("contacts")[0]
                else:
                    contacts = {}

                client = create_client(
                    configuration_file=self.__configuration,
                    siigo_id=client_data["id"],
                    pirpos_id=None,
                    name=" ".join(client_data["name"]),
                    email=contacts.get("email"),
                    phone=contacts.get("phone", {}).get("number"),
                    address=client_data.get("address", {}).get("address"),
                    document=client_data.get("identification"),
                    check_digit=client_data.get("check_digit"),
                    document_type=int(client_data.get("id_type", {})["code"]),
                    responsibilities=client_data.get(
                        "fiscal_responsibilities", [{}]
                    )[0].get("code"),
                    city_name=client_data.get("address", {})
                    .get("city", {})
                    .get("city_name"),
                    city_state=client_data.get("address", {})
                    .get("city", {})
                    .get("state_name"),
                    city_code=client_data.get("address", {})
                    .get("city", {})
                    .get("city_code"),  # TODO: check this with pirpos. use Enum
                    country_code=client_data.get("address", {})
                    .get("city", {})
                    .get("country_code"),
                    state_code=client_data.get("address", {})
                    .get("city", {})
                    .get("state_code"),
                )
                clients.append(client)
            page += 1
        self.__clients = clients

    def get_siigo_products(self, batch_products: int = 100) -> None:
        """Get created products on Siigo.

        Parameters
        ----------
        batch_products : int, optional
            batch used to download products, by default 200

        Returns
        -------
        List[Product]
            Siigo products
        """
        url = "https://services.siigo.com/ACReportApi/api/v1/Report/post"
        headers = {
            "authority": "services.siigo.com",
            "accept": "application/json, text/plain, */*",
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }

        page = 0
        products: List[Product] = []

        while True:
            payload = json.dumps(
                {
                    "Id": 5054,
                    "Skip": batch_products * page,
                    "Take": batch_products,
                    "Sort": " ",
                    "FilterCriterias": (
                        '[{"Field":"_vGroup","FilterType":2,"OperatorType":0,"Value":[-1]'
                        ',"ValueUI":"","Source":"[{\\"id\\":1590,\\"name\\":\\"Domicilios\\"}'
                        ',{\\"id\\":1487,\\"name\\":\\"Insumos\\"},{\\"id\\":673,\\"name\\":'
                        '\\"Productos\\"},{\\"id\\":674,\\"name\\":\\"Servicios\\"}]"},'
                        '{"Field":"_vType","FilterType":7,"OperatorType":0,"Value":[-1],'
                        '"ValueUI":"","Source":"TypeProductEnum"},{"Field":"_vProduct",'
                        '"FilterType":6,"OperatorType":0,"Value":[],"ValueUI":"","Source":"40"}'
                        ',{"Field":"_vBalance","FilterType":7,"OperatorType":0,"Value":["3"],'
                        '"ValueUI":"Todos","Source":"ProductBalancesEnum"},{"Field":"_vState",'
                        '"FilterType":7,"OperatorType":0,"Value":["1"],"ValueUI":"Activo",'
                        '"Source":"ProductStateEnum"},{"Field":"Currency","FilterType":65,'
                        '"OperatorType":0,"Value":["ALL"],"ValueUI":"Moneda Local","Source":null}]'
                    ),
                    "Params": '{"TabID":"912","pTabID":"912"}',
                    "GetTotalCount": False,
                    "GridOrderCriteria": None,
                }
            )
            response = requests.request(
                "POST", url, headers=headers, data=payload
            )
            if not response.ok:
                raise ErrorLoadingSiigoProducts("Can't download Siigo Products")
            data = response.json()["data"]["Value"]["Table"]
            if len(data) == 0:
                break

            for product_info in data:
                taxes: List[TaxInfo] = []
                for tax_info in self.__configuration.taxes_map:
                    if tax_info.siigo_name in [
                        product_info["tax1name"],
                        product_info["tax2name"],
                        product_info["tax3name"],
                    ]:
                        taxes.append(tax_info)

                products.append(
                    Product(
                        product_id=product_info["Code"],
                        name=product_info["Description"],
                        price=product_info["Precio de venta 1"]
                        if product_info["Precio de venta 1"]
                        else 0,
                        taxes=taxes,
                    )
                )
            page += 1

        self.__products = products

    def get_siigo_invoices(
        self,
        init_day: datetime,
        end_day: datetime,
        page_size: int = 100,
    ) -> List[Invoice]:
        """Load Siigo invoices.

        Returns
        -------
          List[Invoice]
          List with Siigo invoices
        """
        day1 = init_day.strftime("%Y-%m-%d")
        day2 = (end_day + timedelta(days=1)).strftime("%Y-%m-%d")
        url = (
            f"https://api.siigo.com/v1/invoices?date_end={day2}"
            f"&date_start={day1}"
            "&page={page}&"
            f"page_size={page_size}"
        )
        payload = ""
        headers = {
            "Authorization": self.__siigo_access_token,
            "Content-Type": "application/json",
        }

        page = 1
        invoices: List[Invoice] = []
        while True:
            response = requests.request(
                "GET",
                url.format(page=page),
                headers=headers,
                data=payload,
            )
            if not response.ok:
                raise ErrorLoadingSiigoInvoices(
                    f"Can't download Siigo clients\n {response.text}"
                )

            data = response.json()["results"]
            if len(data) == 0:
                break

            for invoice_info in data:

                # select client
                client_document = invoice_info.get("customer", {}).get(
                    "identification"
                )

                def filter_client(
                    client: Client, document: str = client_document
                ) -> bool:
                    return client.document == document

                filtered_clients: List[Client] = list(
                    filter(filter_client, self.__clients)
                )

                if len(filtered_clients) > 0:
                    client = filtered_clients[0]
                else:
                    client = self.__configuration.default_client

                # select products
                invoice_products: List[Tuple[Product, float, int, str]] = []
                for product_info in invoice_info["items"]:
                    product_id = product_info["code"]

                    def filter_product(
                        product: Product, product_id: str = product_id
                    ) -> bool:
                        return product.product_id == product_id

                    filtered_products: List[Product] = list(
                        filter(filter_product, self.__products)
                    )
                    if len(filtered_products) > 0:
                        product = filtered_products[0]
                    else:
                        product = self.__products[0]
                    price = product_info["total"]
                    quantity = product_info["quantity"]
                    tax_name = product_info["taxes"][0]["name"]
                    invoice_products.append(
                        (product, price, quantity, tax_name)
                    )

                invoice_obj = create_invoice(
                    self.__configuration,
                    cachier_name="",
                    cachier_id="",
                    seller_name="",
                    seller_id="",
                    client=client,
                    created_on=datetime.strptime(
                        invoice_info["date"], "%Y-%m-%d"
                    ),
                    invoice_prefix=invoice_info["document"]["id"],
                    invoice_number=invoice_info["number"],
                    payments=[
                        (payment["id"], payment["value"])
                        for payment in invoice_info["payments"]
                        if payment["value"] is not None
                    ],
                    invoice_products=invoice_products,
                    total=invoice_info["total"],
                )
                invoices.append(invoice_obj)
            page += 1

        return invoices

    def create_clients(self, clients: List[Client]) -> None:
        """Create list of clients.

        Parameters
        ----------
        clients : List[Client]
            list of clients to be created
        """
        url = "https://api.siigo.com/v1/customers"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }

        for client in clients:
            full_name = client.name.split(" ")
            name, last_name = [full_name[0], " ".join(full_name[1:])]
            if client.document_type == DocumentType.NIT:
                person_type = "Company"
                client_name = [client.name]
            else:
                person_type = "Person"
                client_name = [name, last_name]

            payload = {
                "type": "Customer",
                "person_type": person_type,
                "id_type": str(client.document_type.value),
                "identification": str(client.document),
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
                        "state_code": str(client.city_detail.state_code),
                        "city_code": str(client.city_detail.city_code),
                    },
                    "postal_code": "",
                },
                "phones": [
                    {
                        "indicative": "",
                        "number": client.phone,
                        "extension": "",
                    }
                ],
                "contacts": [
                    {
                        "first_name": name,
                        "last_name": last_name,
                        "email": client.email,
                        "phone": {
                            "indicative": "",
                            "number": client.phone,
                            "extension": "",
                        },
                    }
                ],
                "comments": "Created from Pirpos2Siigo software",
                # "related_users": {"seller_id": 629, "collector_id": 629},
            }

            response = requests.request(
                "POST",
                url,
                headers=headers,
                data=str(payload),
            )
            if not response.ok:
                raise ErrorCreatingSiigoClient(
                    f"Can't download Siigo clients\n {response.text}"
                )

    def _update_clients(self, clients: List[Client]) -> None:
        """Update list of clients.

        Parameters
        ----------
        clients : List[Client]
            list of clients to be updated
        """
        url = "https://api.siigo.com/v1/customers/{siigo_id}"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }

        for client in clients:
            full_name = client.name.split(" ")
            name, last_name = [full_name[0], " ".join(full_name[1:])]
            if client.document_type == DocumentType.NIT:
                person_type = "Company"
                client_name = [client.name]
            else:
                person_type = "Person"
                client_name = [name, last_name]

            client_url = url.format(siigo_id=client.siigo_id)
            payload = {
                "type": "Customer",
                "person_type": person_type,
                "id_type": str(client.document_type.value),
                "identification": str(client.document),
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
                        "state_code": str(client.city_detail.state_code),
                        "city_code": str(client.city_detail.city_code),
                    },
                    "postal_code": "",
                },
                "phones": [
                    {
                        "indicative": "",
                        "number": client.phone,
                        "extension": "",
                    }
                ],
                "contacts": [
                    {
                        "first_name": name,
                        "last_name": last_name,
                        "email": client.email,
                        "phone": {
                            "indicative": "",
                            "number": client.phone,
                            "extension": "",
                        },
                    }
                ],
                "comments": "Created from Pirpos2Siigo software",
                # "related_users": {"seller_id": 629, "collector_id": 629},
            }

            response = requests.request(
                "PUT",
                client_url,
                headers=headers,
                data=str(payload),
            )
            if not response.ok:
                raise ErrorUpdatingSiigoClient(
                    f"Can't download Siigo clients\n {response.text}"
                )
    def update_clients(
        self, clients: List[Client], must_download: bool = False
    ) -> None:
        """Update and create client on siigo.

        Errors will be saved on ./errors/errors_clients.json

        Parameters
        ----------
        clients : List[Client]
            List of outdated clients
        must_download: bool
            download siigo clients
        """
        errors_backup = {}
        errors = False
        error_count = 0

        # get actual siigo clients
        if must_download:
            self.get_siigo_clients()

        # get missing and ourdated clients
        missing_clients, outdated_clients = get_missing_outdated_clients(
            clients, self.clients
        )

        if len(missing_clients) > 0:
            self.create_clients(missing_clients)

        if len(outdated_clients) > 0:
            self._update_clients(outdated_clients)


    @property
    def clients(self) -> List[Client]:
        """Clients property."""
        return self.__clients

    @property
    def products(self) -> List[Product]:
        """Products property."""
        return self.__products


if __name__ == "__main__":

    user_name = os.getenv("SIIGO_USER_NAME")
    user_password = os.getenv("SIIGO_ACCESS_KEY")
    PATH = (
        "/Users/julianestehe/Programs/asadero/pirpos2siigo/configuration.JSON"
    )
    assert isinstance(user_name, str)
    assert isinstance(user_password, str)
    connector = SiigoConnector(user_name, user_password, PATH)

    # test download invoices
    # date_1 = datetime(2022, 9, 2)
    # date_2 = datetime(2022, 9, 2)
    # list_invoices = connector.get_siigo_invoices(date_1, date_2, 100)

    test_client_json = connector.clients[0].json()
    test_client = Client(**json.loads(test_client_json))
    test_client.name = "Julian test2"
    test_client.document = 1121923076
    # connector.create_clients([test_client])
    # connector._update_clients([test_client])
    connector.update_clients([test_client])
    pass
