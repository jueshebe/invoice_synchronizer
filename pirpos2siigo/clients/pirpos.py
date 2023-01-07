"""PirPos client."""
from typing import List, Tuple
import os
import json
import time
from datetime import datetime, timedelta
import requests
from pirpos2siigo.models import Client, Product, Invoice
from pirpos2siigo.clients.utils import (
    load_pirpos2siigo_config,
    create_client,
    create_pirpos_product,
    create_invoice,
    ErrorPirposToken,
    ErrorLoadingPirposClients,
    ErrorLoadingPirposProducts,
    ErrorLoadingPirposInvoices,
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
        self.__configuration = load_pirpos2siigo_config(configuration_path)
        self.__pirpos_access_token = self.__get_siigo_access_token()
        self.__products: List[Product]
        self.__clients: List[Client]
        self.load_pirpos_clients()
        self.load_pirpos_products()

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

    def load_pirpos_clients(self, batch_clients: int = 200) -> None:
        """Load pirpos clients.

        Parameters
        ----------
        batch_clients : int, optional
            batch used to download clients, by default 200
        """
        page = 0
        clients: List[Client] = []
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }
        while True:
            url = (
                "https://api.pirpos.com/clients?pagination=true"
                f"&limit={batch_clients}&page={page}&clientData=&"
            )

            response = requests.request("GET", url, headers=headers)
            if not response.ok:
                raise ErrorLoadingPirposClients(
                    f"Can't download PirPos clients\n {response.text}"
                )

            data = response.json()[
                "data"
            ]  # TODO: check incoming data with BaseModel class
            if len(data) == 0:
                break

            for client_data in data:
                client = create_client(
                    configuration_file=self.__configuration,
                    name=client_data["name"],
                    email=client_data.get("email"),
                    phone=client_data.get("phone"),
                    address=client_data.get("address"),
                    document=client_data.get("document"),
                    check_digit=client_data.get("checkDigit"),
                    document_type=client_data.get("idDocumentType"),
                    responsibilities=client_data.get("responsibilities"),
                    city_name=client_data.get("cityDetail", {}).get("cityName"),
                    city_state=client_data.get("cityDetail", {}).get(
                        "stateName"
                    ),
                    city_code=client_data.get("cityDetail", {}).get("cityCode"),
                    country_code=client_data.get("cityDetail", {}).get(
                        "countryCode"
                    ),
                )
                clients.append(client)
            page += 1

        self.__clients = clients

    @property
    def clients(self) -> List[Client]:
        """Getter for clients."""
        return self.__clients

    def load_pirpos_products(self, batch_products: int = 200) -> None:
        """Get created products on pirpos.

        Parameters
        ----------
        batch_products : int, optional
            batch used to download products, by default 200
        """
        page = 0
        products: List[Product] = []
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://app.pirpos.com/",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }

        while True:
            url = (
                f"https://api.pirpos.com/products?pagination=true&limit="
                f"{batch_products}&page={page}&name=&categoryId=undefined&useInRappi=undefined&"
            )
            response = requests.request("GET", url, headers=headers)
            if not response.ok:
                raise ErrorLoadingPirposProducts(
                    "Can't download Pirpos Products"
                )
            data = response.json()[
                "data"
            ]  # TODO: check incoming data with BaseModel class
            if len(data) == 0:
                break
            for product_info in data:
                product_id = product_info["_id"]
                name = product_info["name"]
                location_stock = product_info["locationsStock"][0]
                sub_products = product_info["subProducts"]
                products.extend(
                    create_pirpos_product(
                        product_id, name, location_stock, sub_products
                    )
                )

            page += 1
        self.__products = products

    @property
    def products(self) -> List[Product]:
        """Getter for clients."""
        return self.__products

    def load_pirpos_invoices_per_client(
        self, init_day: datetime, end_day: datetime, step_days: int = 10
    ) -> List[Invoice]:
        """Get invoices per client on pirpos.

        Parameters
        ----------
        init_day : datetime
            initial time to download invoices. year-month-day
        end_day : datetime
            end time to download invoices year-month-day
        batch_invoices : int, optional
            days used to download invoices in steps, by default 10

        Returns
        -------
        List[Invoice]
            Pirpos invoices per client in a range of time
        """
        end_day += timedelta(days=1)
        if init_day > end_day:
            raise ErrorLoadingPirposInvoices(
                "end_day must be greater than init_day"
            )
        days = 0
        invoices_per_client: List[Invoice] = []
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://app.pirpos.com/",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }

        while True:
            time1 = init_day + timedelta(days=days)
            time2 = (
                init_day + timedelta(days=days + step_days)
                if init_day + timedelta(days=days + step_days) <= end_day
                else end_day
            )
            days += step_days
            date1_str = datetime.strftime(time1, "%Y-%m-%dT05:00:00.000Z")
            date2_str = datetime.strftime(time2, "%Y-%m-%dT05:00:00.000Z")
            url = (
                f"https://api.pirpos.com/reports/reportSalesInvoices?"
                f"status=Pagada&dateInit={date1_str}&dateEnd={date2_str}&"
            )
            response = requests.request("GET", url, headers=headers)
            if not response.ok:
                raise ErrorLoadingPirposInvoices(
                    "Can't download invoices per client from pirpos"
                )
            data = (
                response.json()
            )  # TODO: validate incoming data with BaseModel

            for invoice_info in data:
                try:
                    # select client
                    client_document = invoice_info["client"].get("document", None)

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
                    invoice_products: List[
                        Tuple[Product, float, int, float]
                    ] = []
                    for product_info in invoice_info["products"]:
                        product_id = product_info["idInternal"]

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
                        price = product_info["price"]
                        quantity = product_info["quantity"]
                        tax = float(invoice_info["taxes"][0]["value"]) / 100
                        invoice_products.append((product, price, quantity, tax))

                    invoice_obj = create_invoice(
                        cachier_name=invoice_info["cashier"]["name"],
                        cachier_id=invoice_info["cashier"]["idInternal"],
                        seller_name=invoice_info["seller"]["name"],
                        seller_id=invoice_info["seller"]["idInternal"],
                        client=client,
                        created_on=invoice_info["createdOn"],
                        invoice_prefix=invoice_info["invoicePrefix"],
                        invoice_number=invoice_info["seq"],
                        payment_method=[
                            (payment["paymentMethod"], payment["value"])
                            for payment in invoice_info["paid"][
                                "paymentMethodValue"
                            ] if payment["value"] is not None
                        ],
                        invoice_products=invoice_products,
                        total=invoice_info["total"],
                    )
                    invoices_per_client.append(invoice_obj)
                except Exception as error:
                    print(
                        f"Factura {invoice_info['invoicePrefix']}{invoice_info['seq']}",
                        f"raise error: {error}",
                    )
                    raise ErrorLoadingPirposInvoices(
                        (
                            f"Factura {invoice_info['invoicePrefix']}{invoice_info['seq']}"
                            f"raise error: {error}"
                        )
                    ) from error

            if time2 >= end_day:
                break

        return invoices_per_client


if __name__ == "__main__":
    user_name = os.getenv("PIRPOS_USER_NAME")
    user_password = os.getenv("PIRPOS_PASSWORD")
    PATH = (
        "/Users/julianestehe/Programs/asadero/pirpos2siigo/configuration.JSON"
    )
    assert isinstance(user_name, str)
    assert isinstance(user_password, str)
    time_1 = time.time()
    connector = PirposConnector(user_name, user_password, PATH)
    print(time.time()-time_1)
    # loaded_clients = connector.load_pirpos_clients()
    # loaded_products = connector.load_pirpos_products()
    date_1 = datetime(2022, 11, 2)
    date_2 = datetime(2022, 12, 2)
    time_1 = time.time()
    loaded_invoices = connector.load_pirpos_invoices_per_client(date_1, date_2)
    print(time.time()-time_1)
