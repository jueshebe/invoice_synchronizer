"""PirPos client."""

from typing import List
import json
from logging import Logger
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import requests  # type: ignore
from tqdm import tqdm
from invoice_synchronizer.domain import (
    User,
    Product,
    Invoice,
    InvoiceStatus,
    PlatformConnector,
    AuthenticationError,
    FetchDataError,
)
from invoice_synchronizer.infrastructure.repositories.pirpos.utils import (
    define_pirpos_product_subproducts,
    define_pirpos_invoices,
)
from invoice_synchronizer.infrastructure.config import PirposConfig


class PirposConnector(PlatformConnector):
    """Class to manage pirpos invoices, products and clients."""

    def __init__(
        self,
        pirpos_config: PirposConfig,
        logger: Logger = logging.getLogger(),
    ):
        """Parameters used to make a connection."""
        self.__logger = logger
        self.__pirpos_username = pirpos_config.pirpos_username
        self.__pirpos_password = pirpos_config.pirpos_password
        self.__configuration = pirpos_config.system_mapping
        self.__batch_size = pirpos_config.batch_size
        self.__requests_timeout = pirpos_config.timeout
        self.__days_step = 10
        self.__default_user = pirpos_config.default_user

        self.__pirpos_access_token = self.__get_pirpos_access_token()
        self.__logger.info("Pirpos connector initialized.")

    def __get_pirpos_access_token(self) -> str:
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
        response = requests.post(
            url, data=json.dumps(values), headers=headers, timeout=self.__requests_timeout
        )

        if not response.ok:
            raise AuthenticationError("Error getting Pirpos token, check email and password")

        data = response.json()
        if "tokenCurrent" in data.keys():
            access_token = data["tokenCurrent"]
            assert isinstance(access_token, str)
        else:
            raise AuthenticationError("tokenCurrent key is not present in the respose")

        return access_token

    def get_clients(self) -> List[User]:
        """Get pirpos clients.

        Parameters
        ----------
        batch_clients : int, optional
            batch used to download clients, by default 200
        """
        page = 0
        clients_by_id = defaultdict(list)
        clients: List[User] = []
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }

        while True:
            url = (
                "https://api.pirpos.com/clients?pagination=true"
                f"&limit={self.__batch_size}&page={page}&clientData=&"
            )

            response = requests.request(
                "GET", url, headers=headers, timeout=self.__requests_timeout
            )
            if not response.ok:
                raise FetchDataError(f"Can't download PirPos clients\n {response.text}")

            data = response.json()["data"]
            if len(data) == 0:
                break

            for client_data in data:
                name = client_data["name"]
                # pirpos_id=client_data.get("_id"),
                phone = client_data.get("phone")
                phone = phone.replace(" ", "")[0:10] if phone else phone

                if not client_data.get("document"):
                    continue

                client = User.create_user_with_defaults(
                    default_user=self.__default_user,
                    name=name,
                    last_name=client_data.get("lastName"),
                    document_type=client_data.get("idDocumentType"),
                    document=client_data.get("document"),
                    city_name=client_data.get("cityDetail", {}).get("cityName"),
                    city_state=client_data.get("cityDetail", {}).get("stateName"),
                    city_code=client_data.get("cityDetail", {}).get("cityCode"),
                    country_code=client_data.get("cityDetail", {}).get("countryCode"),
                    state_code=client_data.get("cityDetail", {}).get("stateCode"),
                    responsibilities=client_data.get("responsibilities"),
                    email=client_data.get("email"),
                    phone=phone,
                    address=client_data.get("address"),
                )
                modified_on = datetime.fromisoformat(
                    client_data["modifiedOn"].replace("Z", "+00:00")
                )
                clients_by_id[client.document_number].append((client, modified_on))
            page += 1

        for client_list in clients_by_id.values():
            # Sort clients by modified_on date in descending order and take the most recent one
            most_recent_client = max(client_list, key=lambda x: x[1])[0]
            clients.append(most_recent_client)
        clients.append(self.__default_user)
        return clients

    def create_client(self, client: User) -> None:
        """Create a client on pirpos.

        Parameters
        ----------
        client : User
            client to create
        """
        raise NotImplementedError("Method not implemented yet.")

    def update_client(self, client: User) -> None:
        """Update a client on pirpos.

        Parameters
        ----------
        client : User
            client to update
        """
        raise NotImplementedError("Method not implemented yet.")

    def get_products(self) -> List[Product]:
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
                f"{self.__batch_size}&page={page}&name=&categoryId=undefined&useInRappi=undefined&"
            )
            response = requests.request(
                "GET", url, headers=headers, timeout=self.__requests_timeout
            )
            if not response.ok:
                raise FetchDataError("Can't download Pirpos Products")
            data = response.json()["data"]
            if len(data) == 0:
                break
            for product_info in data:
                product_id = product_info["_id"]
                name = product_info["name"]
                location_stock = product_info["locationsStock"][0]
                sub_products = product_info["subProducts"]
                products.extend(
                    define_pirpos_product_subproducts(
                        self.__configuration,
                        product_id,
                        name,
                        location_stock,
                        sub_products,
                    )
                )

            page += 1
        return products

    def create_product(self, product: Product) -> None:
        """Create product on pirpos.

        Parameters
        ----------
        product : Product
            product to create
        """
        raise NotImplementedError("Method not implemented yet.")

    def update_product(self, product: Product) -> None:
        """Update product on pirpos.

        Parameters
        ----------
        product : Product
            product to update
        """
        raise NotImplementedError("Method not implemented yet.")

    def __get_invoices_by_status(
        self,
        init_day: datetime,
        end_day: datetime,
        status: InvoiceStatus,
        clients: List[User],
        pbar: tqdm,
    ) -> List[Invoice]:
        """Get invoices from pirpos.

        Parameters
        ----------
        init_day : datetime
            initial time to download invoices. year-month-day
        end_day : datetime
            end time to download invoices year-month-day

        Returns
        -------
        List[Invoice]
            Pirpos invoices in a range of time
        """

        end_day += timedelta(days=1)
        if init_day > end_day:
            raise FetchDataError("end_day must be greater than init_day")
        days = 0
        invoices_per_client: List[Invoice] = []
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://app.pirpos.com/",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }

        # products = self.get_products()
        while True:
            time1 = init_day + timedelta(days=days)
            time2 = (
                init_day + timedelta(days=days + self.__days_step)
                if init_day + timedelta(days=days + self.__days_step) <= end_day
                else end_day
            )
            days += self.__days_step
            date1_str = datetime.strftime(time1, "%Y-%m-%dT05:00:00.000Z")
            date2_str = datetime.strftime(time2, "%Y-%m-%dT05:00:00.000Z")

            status_query_param = ""
            if status == InvoiceStatus.ANULATED:
                status_query_param = "Anulada"
            elif status == InvoiceStatus.PAID:
                status_query_param = "Pagada"
            else:
                raise FetchDataError(f"Status {status} not recognized")

            url = (
                f"https://api.pirpos.com/reports/reportSalesInvoices?"
                f"status={status_query_param}&dateInit={date1_str}&dateEnd={date2_str}&"
            )

            response = requests.request(
                "GET", url, headers=headers, timeout=self.__requests_timeout
            )
            if not response.ok:
                raise FetchDataError("Can't download invoices per client from pirpos")
            data = response.json()

            invoices_per_client.extend(define_pirpos_invoices(data, self.__configuration, clients))
            pbar.update(len(data))
            if time2 >= end_day:
                break

        return invoices_per_client

    def get_invoices(self, init_day: datetime, end_day: datetime) -> List[Invoice]:
        """Get invoices from pirpos.

        Parameters
        ----------
        init_day : datetime
            initial time to download invoices. year-month-day
        end_day : datetime
            end time to download invoices year-month-day

        Returns
        -------
        List[Invoice]
            Pirpos invoices in a range of time
        """
        clients = self.get_clients()

        with tqdm(desc="Downloading invoices from Loggro", unit=" invoices") as pbar:
            invoices_anulated = self.__get_invoices_by_status(
                init_day, end_day, InvoiceStatus.ANULATED, clients, pbar
            )
            invoices_paid = self.__get_invoices_by_status(
                init_day, end_day, InvoiceStatus.PAID, clients, pbar
            )
        all_invoices = invoices_paid + invoices_anulated
        return all_invoices

    def create_invoice(self, invoice: Invoice) -> None:
        """Create an invoice on pirpos.

        Parameters
        ----------
        invoice : Invoice
            invoice to create
        """
        raise NotImplementedError("Method not implemented yet.")

    def update_invoice(self, invoice: Invoice) -> None:
        """Update an invoice on pirpos.

        Parameters
        ----------
        invoice : Invoice
            invoice to update
        """
        raise NotImplementedError("Method not implemented yet.")

    def credit_note(self, invoice: Invoice) -> None:
        """Create credit/anulate note for an invoice.

        Parameters
        ----------
        invoice : Invoice
            invoice to anulate
        """
        raise NotImplementedError("Method not implemented yet.")
