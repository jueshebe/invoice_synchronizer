"""Siigo client."""

from typing import List, Tuple, Dict, Optional
import os
import re
import time
import json
from datetime import datetime, timedelta
import logging
from logging import Logger
import requests
from invoice_synchronizer.domain import (
    User,
    DocumentType,
    Product,
    Invoice,
    TaxType,
    InvoiceStatus,
    AuthenticationError,
    FetchDataError,
    UploadError,
    UpdateError,
    PlatformConnector,
)
from invoice_synchronizer.infrastructure.repositories.utils import (
    create_invoice,
)
from invoice_synchronizer.infrastructure.config import SiigoConfig
from invoice_synchronizer.infrastructure.repositories.siigo.utils import user_to_siigo_payload
from invoice_synchronizer.infrastructure.repositories.rate_limiter.rate_limiter import RateLimiter


class SiigoConnector(PlatformConnector):
    """Class to manage siigo invoices, clients and products."""

    def __init__(self, siigo_config: SiigoConfig, logger: Logger):
        """Parameters used to make a connection."""
        # Siigo API info
        self.__logger = logger
        self.__siigo_username = siigo_config.siigo_username
        self.__siigo_access_key = siigo_config.siigo_access_key
        self.__configuration = siigo_config.system_mapping
        self.__products: List[Product]
        self.__documents_to_id: Dict[int, str] = {}
        self.__documents_to_raw_user: Dict[int, Any] = {}
        self.__page_size = 500
        self.__batch_products: int = 100
        self.__timeout = siigo_config.timeout
        self.default_client = siigo_config.default_user
        self._rate_limiter = RateLimiter(max_requests_per_minute=90, logger=logger)
        self.__siigo_access_token = self.__get_siigo_access_token()
        logger.info("Siigo connector initialized.")

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
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        response = requests.post(
            url, data=json.dumps(values), headers=headers, timeout=self.__timeout
        )

        if not response.ok:
            raise AuthenticationError("Error solicitando token, revisar userName y access_key")
        data = response.json()

        if "access_token" in data.keys():
            access_token = data["access_token"]
            assert isinstance(access_token, str)
        else:
            raise AuthenticationError("access_token key is not present in the respose")

        return access_token

    def get_clients(self) -> List[User]:
        """Load Siigo clients.

        Returns
        -------
          List[Client]
          List with Siigo clients
        """
        url = "https://api.siigo.com/v1/customers?page={page}" f"&page_size={self.__page_size}"
        payload = ""
        headers = {
            "authority": "services.siigo.com",
            "accept": "application/json, text/plain, */*",
            "authorization": self.__siigo_access_token,
            "content-type": "application/json; charset=UTF-8",
            "Partner-Id": "DesarrolloPropio",
        }
        page = 1
        clients: List[User] = []

        while True:
            self._rate_limiter.wait_if_needed()
            response = requests.request(
                "GET",
                url.format(page=page),
                headers=headers,
                data=payload,
                timeout=self.__timeout,
            )
            if not response.ok:
                raise FetchDataError(f"Can't download Siigo clients\n {response.text}")

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

                try:
                    name = client_data["name"][0]
                    last_name: Optional[str] = " ".join(client_data["name"][1:])
                    if last_name == ".":
                        last_name = None
                except TypeError:
                    continue

                client = User.create_user_with_defaults(
                    default_user=self.default_client,
                    name=name,
                    last_name=last_name,
                    document_type=int(client_data.get("id_type", {})["code"]),
                    document=client_data.get("identification"),
                    check_digit=client_data.get("check_digit"),
                    city_name=client_data.get("address", {}).get("city", {}).get("city_name"),
                    city_state=client_data.get("address", {}).get("city", {}).get("state_name"),
                    city_code=client_data.get("address", {})
                    .get("city", {})
                    .get("city_code"),  # TODO: check this with pirpos. use Enum
                    country_code=client_data.get("address", {}).get("city", {}).get("country_code"),
                    state_code=client_data.get("address", {}).get("city", {}).get("state_code"),
                    responsibilities=client_data.get("fiscal_responsibilities", [{}])[0].get(
                        "code"
                    ),
                    email=contacts.get("email"),
                    phone=contacts.get("phone", {}).get("number"),
                    address=client_data.get("address", {}).get("address"),
                )
                clients.append(client)
                self.__documents_to_id[client.document_number] = client_data["id"]
                self.__documents_to_raw_user[client.document_number] = client_data
            page += 1
        return clients

    def create_client(self, client: User) -> None:
        """Create client.

        Parameters
        ----------
        client : Client
           client to be created
        """
        url = "https://api.siigo.com/v1/customers"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json; charset=UTF-8",
            "Partner-Id": "DesarrolloPropio",
        }
        payload = user_to_siigo_payload(client)
        self._rate_limiter.wait_if_needed()
        response = requests.request(
            "POST",
            url,
            headers=headers,
            data=str(payload),
            timeout=self.__timeout,
        )
        if not response.ok:
            raise UploadError(f"Can't create clients\n {response.text}")

    def update_client(self, client: User) -> None:
        """Update client.

        Parameters
        ----------
        client : Client
            client to be updated
        """
        url = "https://api.siigo.com/v1/customers/{siigo_id}"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json; charset=UTF-8",
            "Partner-Id": "DesarrolloPropio",
        }
        user_siigo_id = self.__documents_to_id.get(client.document_number)
        if user_siigo_id is None:
            self.get_clients()
            user_siigo_id = self.__documents_to_id.get(client.document_number)
            if user_siigo_id is None:
                raise UpdateError(f"Siigo ID for client {client.document_number} not found.")

        client_url = url.format(siigo_id=user_siigo_id)
        payload = user_to_siigo_payload(
            client, self.__documents_to_raw_user[client.document_number].get("contacts")
        )

        # Debug info
        self.__logger.debug(
            f"Updating client {client.document_number} with Siigo ID: {user_siigo_id}"
        )
        self.__logger.debug(f"URL: {client_url}")
        self._rate_limiter.wait_if_needed()
        response = requests.request(
            "PUT",
            client_url,
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False),
            timeout=self.__timeout,
        )
        if not response.ok:
            raise UpdateError(f"Can't update Siigo client\n {response.text}")

    def get_products(self) -> None:
        """Get created products on Siigo.

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
            "content-type": "application/json; charset=UTF-8",
        }

        page = 0
        products: List[Product] = []

        while True:
            payload = json.dumps(
                {
                    "Id": 5054,
                    "Skip": self.__batch_products * page,
                    "Take": self.__batch_products,
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
            response = requests.request("POST", url, headers=headers, data=payload)
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
                        siigo_id=product_info["ProductGUID"],
                        product_id=product_info["Code"],
                        name=product_info["Description"],
                        price=(
                            product_info["Precio de venta 1"]
                            if product_info["Precio de venta 1"]
                            else 0
                        ),
                        taxes=taxes,
                    )
                )
            page += 1

        self.__products = products

    def create_product(self, product: Product) -> None:
        """Create product.

        Parameters
        ----------
        products : Product
            product to be created
        """
        url = "https://api.siigo.com/v1/products"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }
        if len(product.taxes) > 0:
            tax = [{"id": product.taxes[0].siigo_id}]
        else:
            tax = []

        if product.price > 0:
            prices = [
                {
                    "currency_code": "COP",
                    "price_list": [
                        {
                            "position": 1,
                            "value": product.price if product.price > 0 else 1,
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
            "taxes": tax,
            "prices": prices,
            "unit": "94",
            "unit_label": "unidad",
            "reference": "REF1",
            "description": ".",
        }
        response = requests.request(
            "POST",
            url,
            headers=headers,
            data=str(payload),
        )
        if not response.ok:
            raise ErrorCreatingSiigoProduct(f"Can't create product\n {response.text}")

    def update_product(self, product: Product) -> None:
        """Update product.

        Parameters
        ----------
        products : Product
            product to be updated
        """
        url = f"https://api.siigo.com/v1/products/{product.siigo_id}"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }
        if len(product.taxes) > 0:
            tax = [{"id": product.taxes[0].siigo_id}]
        else:
            tax = []

        if product.price > 0:
            prices = [
                {
                    "currency_code": "COP",
                    "price_list": [
                        {
                            "position": 1,
                            "value": product.price if product.price > 0 else 1,
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
            "taxes": tax,
            "prices": prices,
            "unit": "94",
            "unit_label": "unidad",
            "reference": "REF1",
            "description": ".",
        }
        response = requests.request(
            "PUT",
            url,
            headers=headers,
            data=str(payload),
        )
        if not response.ok:
            raise ErrorUpdatingSiigoProduct(f"Can't update product\n {response.text}")

    def get_invoices(
        self, init_day: datetime, end_day: datetime, invoice_status: List[InvoiceStatus]
    ) -> List[Invoice]:
        """Load Siigo invoices.

        Returns
        -------
          List[Invoice]
          List with Siigo invoices
        """
        if update_data:
            self.get_siigo_products()
            self.get_siigo_clients()

        day1 = init_day.strftime("%Y-%m-%d")
        day2 = (end_day + timedelta(days=1)).strftime("%Y-%m-%d")
        url = (
            f"https://api.siigo.com/v1/invoices?date_end={day2}"
            f"&date_start={day1}"
            # "&page={page}&"
            f"&page_size={page_size}"
        )
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
            )
            if not response.ok:
                if response.json()["Errors"][0]["Code"] == "document_query_service":
                    continue
                raise ErrorLoadingSiigoInvoices(f"Can't download Siigo invoices\n {response.text}")

            response_ob = response.json()
            data = response_ob["results"]
            next_link = response_ob["_links"].get("next", {"href": None})["href"]
            if len(data) == 0 or next_link is None:
                break
            else:
                url = next_link

            for invoice_info in data:

                # select client
                client_document_str = str(
                    invoice_info.get("customer", {}).get("identification", "0")
                )

                client_document = int(client_document_str) if client_document_str.isnumeric() else 0

                def filter_client(client: Client, document: int = client_document) -> bool:
                    return client.document == document

                filtered_clients: List[Client] = list(filter(filter_client, self.__clients))

                if len(filtered_clients) > 0:
                    client = filtered_clients[0]
                else:
                    client = self.__configuration.default_client

                # select products
                invoice_products: List[Tuple[Product, float, int, str]] = []
                for product_info in invoice_info["items"]:
                    product_id = product_info["code"]

                    def filter_product(product: Product, product_id: str = product_id) -> bool:
                        return product.product_id == product_id

                    filtered_products: List[Product] = list(filter(filter_product, self.__products))
                    if len(filtered_products) > 0:
                        product = filtered_products[0]
                    else:
                        product = self.__products[0]
                    quantity = product_info["quantity"]
                    price = int(product_info["total"] / quantity)
                    tax_name = product_info["taxes"][0]["name"]
                    invoice_products.append((product, price, quantity, tax_name))

                invoice_obj = create_invoice(
                    self.__configuration,
                    cachier_name="",
                    cachier_id="",
                    seller_name="",
                    seller_id="",
                    client=client,
                    created_on=datetime.strptime(invoice_info["date"], "%Y-%m-%d"),
                    invoice_prefix=invoice_info["document"]["id"],
                    invoice_number=invoice_info["number"],
                    payments=[
                        (payment["id"], payment["value"])
                        for payment in invoice_info["payments"]
                        if payment["value"] is not None
                    ],
                    invoice_products=invoice_products,
                    total=invoice_info["total"],
                    siigo_id=invoice_info["id"],
                )
                invoices.append(invoice_obj)

        return invoices

    def create_invoice(self, invoice: Invoice) -> None:
        """Create invoice."""
        url = "https://api.siigo.com/v1/invoices"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }

        payload = {
            "document": {"id": invoice.invoice_prefix.siigo_id},
            "number": invoice.invoice_number,
            "date": invoice.created_on.strftime("%Y-%m-%d"),
            "customer": {
                "identification": str(invoice.client.document),
                "branch_office": 0,
            },
            "seller": 709,  # TODO: Employee mapping
            "observations": "invoice created from pirpos2siigo software",
            "items": [
                {
                    "code": invoice_product.product.product_id,
                    "description": invoice_product.product.name,
                    "quantity": invoice_product.quantity,
                    "price": round(
                        invoice_product.price / (1 + invoice_product.tax.value),
                        2,
                    ),
                    "discount": 0,
                    "taxes": [{"id": invoice_product.tax.siigo_id}],
                }
                for invoice_product in invoice.products
            ],
            "payments": [
                {
                    "id": pay_method[0].siigo_id,
                    "value": pay_method[1],
                    "due_date": invoice.created_on.strftime("%Y-%m-%d"),
                }
                for pay_method in invoice.payment_method
            ],
            "retentions": [
                {"id": retention.siigo_id} for retention in self.__configuration.retentions
            ],
        }

        for retries in range(30):
            response = requests.request(
                "POST",
                url,
                headers=headers,
                data=str(payload),
            )
            if not response.ok:
                if response.json()["Errors"][0]["Code"] == "already_exists":
                    self.__logger.warning(
                        f"Document {invoice.invoice_prefix}{invoice.invoice_number} already exists"
                    )
                    return

                if response.json()["Errors"][0]["Code"] == "duplicated_document":
                    self.__logger.info("duplicated_document error. try to send it again")
                    time.sleep(2)

                elif response.json()["Errors"][0]["Code"] == "invalid_total_payments":
                    message = response.json()["Errors"][0]["Message"]
                    self.__logger.warning(message)
                    pyment = [int(s) for s in re.findall(r"\b\d+\b", message)][0]
                    self.__logger.info(
                        "payment modified from {0} to {1}".format(
                            payload["payments"][0]["value"], pyment
                        )
                    )
                    payload["payments"] = (
                        [  # este ajuste elimina otros metedos de pago asociados !!cuidado!!
                            {
                                "id": payload["payments"][0]["id"],
                                "value": pyment,
                            }
                        ]
                    )
            else:
                return

        raise ErrorCreatingSiigoInvoice(f"Can't create invoice\n {response.text}")

    def update_invoice(self, invoice: Invoice) -> None:
        """Create invoice."""
        url = "https://api.siigo.com/v1/invoices/{invoice_id}"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }

        payload = {
            "document": {"id": invoice.invoice_prefix.siigo_id},
            "number": invoice.invoice_number,
            "date": invoice.created_on.strftime("%Y-%m-%d"),
            "customer": {
                "identification": str(invoice.client.document),
                "branch_office": 0,
            },
            "seller": 709,  # TODO: Employee mapping
            "observations": "invoice created from pirpos2siigo software",
            "items": [
                {
                    "code": invoice_product.product.product_id,
                    "description": invoice_product.product.name,
                    "quantity": invoice_product.quantity,
                    "price": round(
                        invoice_product.price / (1 + invoice_product.tax.value),
                        2,
                    ),
                    "discount": 0,
                    "taxes": [{"id": invoice_product.tax.siigo_id}],
                }
                for invoice_product in invoice.products
            ],
            "payments": [
                {
                    "id": pay_method[0].siigo_id,
                    "value": pay_method[1],
                    "due_date": invoice.created_on.strftime("%Y-%m-%d"),
                }
                for pay_method in invoice.payment_method
            ],
            "retentions": [
                {"id": retention.siigo_id} for retention in self.__configuration.retentions
            ],
        }

        for retries in range(30):
            response = requests.request(
                "PUT",
                url.format(invoice_id=invoice.siigo_id),
                headers=headers,
                data=str(payload),
            )
            if not response.ok:
                # if response.json()["Errors"][0]["Code"] == "already_exists":
                #     self.__logger.warning(
                #         f"Document {invoice.invoice_prefix}{invoice.invoice_number} already exists"
                #     )
                #     return

                if response.json()["Errors"][0]["Code"] == "duplicated_document":
                    self.__logger.info("duplicated_document error. try to send it again")
                    time.sleep(2)

                elif response.json()["Errors"][0]["Code"] == "invalid_total_payments":
                    message = response.json()["Errors"][0]["Message"]
                    self.__logger.warning(message)
                    pyment = [int(s) for s in re.findall(r"\b\d+\b", message)][0]
                    self.__logger.info(
                        "payment modified from {0} to {1}".format(
                            payload["payments"][0]["value"], pyment
                        )
                    )
                    payload["payments"] = (
                        [  # este ajuste elimina otros metedos de pago asociados !!cuidado!!
                            {
                                "id": payload["payments"][0]["id"],
                                "value": pyment,
                            }
                        ]
                    )
            else:
                return

        raise ErrorUpdatingSiigoInvoice(f"Can't update invoice\n {response.text}")

    def credit_note(self, invoice: Invoice) -> None:
        """Anulate invoice by credit note."""
        url = "https://api.siigo.com/v1/credit-notes"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
            "Partner-Id": "DesarrolloPropio",
        }
        payload = get_payload_credit_note(invoice)
        response = requests.request(
            "POST", url, headers=headers, data=str(payload), timeout=self.__timeout
        )
        if not response.ok:
            raise ErrorUpdatingSiigoInvoice(f"Can't cancel invoice {response.text}")


if __name__ == "__main__":

    user_name = os.getenv("SIIGO_USER_NAME")
    user_password = os.getenv("SIIGO_ACCESS_KEY")
    PATH = "/Users/julianestehe/Programs/asadero/pirpos2siigo/configuration.JSON"
    assert isinstance(user_name, str)
    assert isinstance(user_password, str)
    connector = SiigoConnector(user_name, user_password, PATH)
    connector.get_siigo_clients()
    connector.get_siigo_products()
    # test download invoices
    date_1 = datetime(2022, 9, 2)
    date_2 = datetime(2022, 10, 2)
    list_invoices = connector.get_siigo_invoices(date_1, date_2, 100)

    # test_client_json = connector.clients[0].json()
    # test_client = Client(**json.loads(test_client_json))
    # test_client.name = "Julian test2"
    # test_client.document = 1121923076
    # connector.create_clients([test_client])
    # connector._update_clients([test_client])
    # connector.update_clients([test_client])
    connector.get_siigo_products()
    product_test = connector.products[0]
    product_test.name = product_test.name.upper()
    # product.product_id = "ggg"
    # connector.create_product(product)
    # connector.update_product(product)
    pass
