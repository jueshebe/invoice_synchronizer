"""Siigo client."""

from typing import List, Dict, Optional, Any
import os
import json
from datetime import datetime, timedelta
from logging import Logger
import requests  # type: ignore
from tqdm import tqdm
from invoice_synchronizer.domain import (
    User,
    Product,
    Invoice,
    InvoiceStatus,
    AuthenticationError,
    FetchDataError,
    UploadError,
    UpdateError,
    PlatformConnector,
)
from invoice_synchronizer.infrastructure.config import SiigoConfig
from invoice_synchronizer.infrastructure.repositories.siigo.utils import (
    user_to_siigo_payload,
    define_siigo_product,
    product_to_siigo_payload,
    define_siigo_invoice,
    update_invoices_with_credit_notes,
    invoice_to_siigo_payload,
    get_payload_credit_note,
    get_invoice_number_2_siigo_id_mapping,
)
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
        self.__page_size = 200
        self.__timeout = siigo_config.timeout
        self.default_client = siigo_config.default_user
        self.retentions = siigo_config.retentions
        self.credit_note_document_id = siigo_config.credit_note_id
        self.seller_id = siigo_config.seller_id
        self._rate_limiter = RateLimiter(
            max_requests_per_minute=siigo_config.max_requests_per_minute, logger=logger
        )
        self.__token_max_hours_time_alive = siigo_config.token_max_hours_time_alive
        self.__siigo_access_token = self.__get_siigo_access_token()

        # Credit note date range configuration
        self.credit_note_forward_days = siigo_config.credit_note_forward_days

        # ids mapping to operate with API
        self.__documents_to_siigo_id: Dict[int, str] = {}
        self.__documents_to_raw_user: Dict[int, Any] = {}
        self.__productid_to_siigo_id: Dict[str, str] = {}
        self.__invoice_number_to_siigo_id: Dict[str, str] = {}
        self.__invoice_id_to_credit_note_acentry_id: Dict[str, str] = {}
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
        path_folder = os.path.join(os.path.expanduser("~"), ".config/pirpos2siigo")
        file_path = os.path.join(path_folder, "token.json")
        os.makedirs(path_folder, exist_ok=True)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                dict_data = json.loads(file.read())
            access_token = dict_data["token"]
            saved_time = datetime.strptime(dict_data["time"], "%Y-%m-%d-%H-%M")
            if (
                datetime.now() - saved_time
            ).total_seconds() / 3600 < self.__token_max_hours_time_alive:
                return str(access_token)

        url = "https://api.siigo.com/auth"
        values = {
            "username": self.__siigo_username,
            "access_key": self.__siigo_access_key,
        }
        headers = {
            "Content-Type": "application/json",
            "Partner-Id": "DesarrolloPropio",
        }
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

        with open(file_path, "w", encoding="utf-8") as file:
            json_data = json.dumps(
                {
                    "token": access_token,
                    "time": datetime.now().strftime("%Y-%m-%d-%H-%M"),
                }
            )
            file.write(json_data)

        return access_token

    def get_clients(self) -> List[User]:
        """Load Siigo clients.

        Returns
        -------
          List[User]
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
                    city_name=client_data.get("address", {}).get("city", {}).get("city_name"),
                    city_state=client_data.get("address", {}).get("city", {}).get("state_name"),
                    city_code=client_data.get("address", {}).get("city", {}).get("city_code"),
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
                self.__documents_to_siigo_id[client.document_number] = client_data["id"]
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
        user_siigo_id = self.__documents_to_siigo_id.get(client.document_number)
        if user_siigo_id is None:
            self.get_clients()
            user_siigo_id = self.__documents_to_siigo_id.get(client.document_number)
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

    def get_products(self) -> List[Product]:
        """Get created products on Siigo.

        Returns
        -------
        List[Product]
            Siigo products
        """
        url = f"https://api.siigo.com/v1/products?page_size={self.__page_size}"
        headers = {
            "content-type": "application/json; charset=UTF-8",
            "Authorization": self.__siigo_access_token,
            "Partner-Id": "DesarrolloPropio",
        }

        products: List[Product] = []

        while True:
            self._rate_limiter.wait_if_needed()
            response = requests.request("GET", url, headers=headers, timeout=self.__timeout)
            if not response.ok:
                raise FetchDataError("Can't download Siigo Products")
            data = response.json()
            if len(data) == 0:
                break

            for product_info in data["results"]:
                if product_info["type"] != "Product":
                    continue

                prices = product_info.get("prices", None)
                if prices is None or len(prices) == 0:
                    price = 0.0
                else:
                    price = float(prices[0]["price_list"][0]["value"])

                product = define_siigo_product(
                    self.__configuration,
                    product_info["code"],
                    product_info["name"],
                    price,
                    product_info.get("taxes") or [],
                )
                products.append(product)
                self.__productid_to_siigo_id[product.product_id] = product_info["id"]

            if data["_links"].get("next") is None:
                break
            else:
                url = data["_links"]["next"]["href"]

        return products

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
            "Partner-Id": "DesarrolloPropio",
        }

        payload = product_to_siigo_payload(
            self.__configuration,
            product,
        )
        self._rate_limiter.wait_if_needed()
        response = requests.request(
            "POST",
            url,
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False),
            timeout=self.__timeout,
        )
        if not response.ok:
            raise UploadError(f"Can't create product\n {response.text}")

    # def get_taxes_mapping(self) -> Dict[str, str]:

    def update_product(self, product: Product) -> None:
        """Update product.

        Parameters
        ----------
        products : Product
            product to be updated
        """
        product_id = self.__productid_to_siigo_id.get(product.product_id)
        if product_id is None:
            self.get_products()
            product_id = self.__productid_to_siigo_id.get(product.product_id)
            if product_id is None:
                raise UpdateError(f"Siigo ID for product {product.product_id} not found.")

        url = f"https://api.siigo.com/v1/products/{product_id}"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
            "Partner-Id": "DesarrolloPropio",
        }
        payload = product_to_siigo_payload(
            self.__configuration,
            product,
        )
        self._rate_limiter.wait_if_needed()
        response = requests.request(
            "PUT",
            url,
            headers=headers,
            data=str(payload),
            timeout=self.__timeout,
        )
        if not response.ok:
            raise UpdateError(f"Can't update product\n {response.text}")

    def _get_credit_note(self, init_day: datetime, end_day: datetime) -> List[Dict[str, Any]]:
        """Load Siigo credit notes.

        Parameters
        ----------
        init_day : datetime
            Start date for credit notes search
        end_day : datetime
            End date for credit notes search

        Returns
        -------
        List[Dict[str, Any]]
            List with Siigo credit notes data
        """
        day1 = init_day.strftime("%Y-%m-%d")
        day2 = (end_day + timedelta(days=1)).strftime("%Y-%m-%d")
        url = (
            f"https://api.siigo.com/v1/credit-notes?page_size={self.__page_size}&created_end={day2}"
            f"&created_start={day1}"
        )
        headers = {
            "Authorization": self.__siigo_access_token,
            "Content-Type": "application/json",
            "Partner-Id": "DesarrolloPropio",
        }

        errors_count = 0
        credit_notes: List[Dict[str, Any]] = []

        while True:
            self._rate_limiter.wait_if_needed()
            response = requests.request(
                "GET",
                url,
                headers=headers,
                timeout=self.__timeout,
            )

            if not response.ok:
                if errors_count > 5:
                    raise FetchDataError(f"Can't download Siigo credit notes\n {response.text}")

                # Handle specific Siigo API errors
                response_data = response.json()
                if (
                    "Errors" in response_data
                    and len(response_data["Errors"]) > 0
                    and response_data["Errors"][0]["Code"] == "document_query_service"
                ):
                    errors_count += 1
                    continue
                raise FetchDataError(f"Can't download Siigo credit notes\n {response.text}")

            response_ob = response.json()
            data = response_ob.get("results", [])

            # Add all credit notes from this page
            credit_notes.extend(data)

            # Check for next page
            next_link = response_ob.get("_links", {}).get("next", {}).get("href")
            if len(data) == 0 or next_link is None:
                break
            else:
                url = next_link

        return credit_notes

    def get_invoices(self, init_day: datetime, end_day: datetime) -> List[Invoice]:
        """Load Siigo invoices.

        Returns
        -------
          List[Invoice]
          List with Siigo invoices
        """
        clients = self.get_clients()
        credit_note_end_date = end_day + timedelta(days=self.credit_note_forward_days)
        credit_note_data = self._get_credit_note(init_day, credit_note_end_date)
        credit_note_doc_name_acentry = self.get_credit_note_acentryid(
            init_day, credit_note_end_date
        )

        day1 = init_day.strftime("%Y-%m-%d")
        day2 = (end_day + timedelta(days=1)).strftime("%Y-%m-%d")
        url = (
            f"https://api.siigo.com/v1/invoices?page_size={self.__page_size}&date_end={day2}" f"&date_start={day1}"
        )
        headers = {
            "Authorization": self.__siigo_access_token,
            "Content-Type": "application/json",
            "Partner-Id": "DesarrolloPropio",
        }

        errors_count = 0
        invoices_by_id: Dict[str, Invoice] = {}
        with tqdm(desc="Downloading invoices from Siigo", unit=" invoices") as pbar:
            while True:
                self._rate_limiter.wait_if_needed()
                response = requests.request(
                    "GET",
                    url,
                    headers=headers,
                    timeout=self.__timeout,
                )
                if not response.ok:
                    if errors_count > 5:
                        raise FetchDataError(f"Can't download Siigo invoices\n {response.text}")

                    if response.json()["Errors"][0]["Code"] == "document_query_service":
                        errors_count += 1
                        continue
                    raise FetchDataError(f"Can't download Siigo invoices\n {response.text}")

                response_ob = response.json()
                data = response_ob["results"]
                pbar.update(len(data))
                batch_invoices = define_siigo_invoice(
                    system_parameters=self.__configuration,
                    data=data,
                    clients=clients,
                )
                invoices_by_id.update(batch_invoices)
                self.__invoice_number_to_siigo_id.update(
                    get_invoice_number_2_siigo_id_mapping(invoices_by_id)
                )

                next_link = response_ob["_links"].get("next", {"href": None})["href"]
                if len(data) == 0 or next_link is None:
                    break
                else:
                    url = next_link
        invoices, invoice_id_to_credit_note_id = update_invoices_with_credit_notes(
            invoices_by_id, credit_note_data, credit_note_doc_name_acentry
        )
        self.__invoice_id_to_credit_note_acentry_id.update(invoice_id_to_credit_note_id)
        return invoices

    def get_credit_note_acentryid(self, init_day: datetime, end_day: datetime) -> Dict[str, str]:
        url = "https://services.siigo.com/document/api/v1/reports/getreport"
        headers = {
            "Authorization": self.__siigo_access_token,
            "Content-Type": "application/json",
        }
        take = 100
        skip = 0
        credit_note_acentry: Dict[str, str] = {}
        while True:
            payload = json.dumps(
                {
                    "Id": 5349,
                    "Skip": skip,
                    "Take": take,
                    "Sort": " ",
                    "FilterCriterias": '[{"Field":"DocDate","Value":["'
                    + init_day.strftime("%Y%m%d")
                    + '","'
                    + end_day.strftime("%Y%m%d")
                    + '"],"Source":"[]"},{"Field":"_var_DocClass","FilterType":7,"OperatorType":0,"Value":["3"],"ValueUI":"Nota crédito","Source":"SalesTransactionEnum"}]',
                    "GetTotalCount": True,
                    "GridOrderCriteria": None,
                    "AddOns": None,
                }
            )
            self._rate_limiter.wait_if_needed()
            response = requests.request(
                "POST",
                url,
                headers=headers,
                data=payload,
                timeout=self.__timeout,
            )
            if not response.ok:
                raise FetchDataError(
                    f"Can't download Siigo credit notes ACEntryID\n {response.text}"
                )
            data = response.json()["data"]["Value"]["Table"]
            for credit_note in data:
                doc_name = credit_note["DocName"]
                credit_note_acentry[doc_name] = credit_note["ACEntryID"]
            if len(data) == 0:
                break
            skip += take
        return credit_note_acentry

    def create_invoice(self, invoice: Invoice, retry_count: int = 0) -> None:
        """Create invoice."""
        url = "https://api.siigo.com/v1/invoices"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
            "Partner-Id": "DesarrolloPropio",
        }

        payload = invoice_to_siigo_payload(
            self.__configuration, invoice, self.retentions, self.seller_id
        )
        self._rate_limiter.wait_if_needed()
        response = requests.request(
            "POST", url, headers=headers, data=str(payload), timeout=self.__timeout
        )
        if not response.ok:
            if response.json()["Errors"][0]["Code"] == "already_exists":
                self.__logger.warning(
                    f"Document {invoice.invoice_id.prefix}{invoice.invoice_id.number} already exists"
                )
            elif (
                response.json()["Errors"][0]["Code"] == "invalid_total_payments"
            ):
                if retry_count >= 1:
                    raise UploadError(f"Can't create invoice\n {response.text}")
                message = response.json()["Errors"][0]["Message"]
                payment = float(message.split(" ")[-1])
                fix_payment = payment - invoice.total
                invoice.payments[0].value += round(fix_payment, 2)
                invoice.total = round(payment, 2)
                return self.create_invoice(invoice, 1)
            else:
                raise UploadError(f"Can't create invoice\n {response.text}")

        if invoice.status == InvoiceStatus.ANULATED:
            invoice_id = response.json()["id"]
            self._create_credit_note(invoice, invoice_id)

    def _create_credit_note(self, invoice: Invoice, invoice_id: str) -> None:
        """Anulate invoice by credit note."""
        url = "https://api.siigo.com/v1/credit-notes"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
            "Partner-Id": "DesarrolloPropio",
        }
        payload = get_payload_credit_note(
            invoice_id, invoice, self.__configuration, self.credit_note_document_id
        )
        self._rate_limiter.wait_if_needed()
        response = requests.request(
            "POST", url, headers=headers, data=str(payload), timeout=self.__timeout
        )
        if not response.ok:
            raise UploadError(f"Can't cancel invoice {response.text}")

    def update_invoice(self, invoice: Invoice, retry_count: int = 0) -> None:
        """Create invoice."""
        invoice_siigo_id = self.__invoice_number_to_siigo_id.get(
            f"{invoice.invoice_id.prefix}{invoice.invoice_id.number}"
        )
        if invoice_siigo_id is None:
            self.get_invoices(invoice.created_on, invoice.created_on)
            invoice_siigo_id = self.__invoice_number_to_siigo_id.get(
                f"{invoice.invoice_id.prefix}{invoice.invoice_id.number}"
            )
            if invoice_siigo_id is None:
                raise UpdateError(
                    f"Siigo ID for invoice {invoice.invoice_id.prefix}{invoice.invoice_id.number} not found."
                )

        if (
            invoice.status == InvoiceStatus.ANULATED
            and self.__invoice_id_to_credit_note_acentry_id.get(invoice_siigo_id)
        ):
            credit_note_id = self.__invoice_id_to_credit_note_acentry_id[invoice_siigo_id]
            self._delete_credit_note(invoice_siigo_id, credit_note_id)

        url = f"https://api.siigo.com/v1/invoices/{invoice_siigo_id}"
        headers = {
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
            "Partner-Id": "DesarrolloPropio",
        }

        payload = invoice_to_siigo_payload(
            self.__configuration, invoice, self.retentions, self.seller_id
        )
        self._rate_limiter.wait_if_needed()
        response = requests.request(
            "PUT", url, headers=headers, data=str(payload), timeout=self.__timeout
        )
        if not response.ok:
            if (
                response.json()["Errors"][0]["Code"] == "invalid_total_payments"
            ):
                if retry_count >= 1:
                    raise UploadError(f"Can't create invoice\n {response.text}")
                message = response.json()["Errors"][0]["Message"]
                payment = float(message.split(" ")[-1])
                fix_payment = payment - invoice.total
                invoice.payments[0].value += round(fix_payment, 2)
                invoice.total = round(payment, 2)
                return self.update_invoice(invoice, 1)
            else:
                raise UploadError(f"Can't create invoice\n {response.text}")

        if invoice.status == InvoiceStatus.ANULATED:
            self._create_credit_note(invoice, invoice_siigo_id)

    def _delete_credit_note(self, invoice_id: str, ac_entry_id: str) -> None:
        """Update invoice credit note."""
        url = f"https://servicespd.siigo.com/ACEntryApi/api/v2/CreditNote/Remove/{ac_entry_id}"
        headers = {
            "accept": "application/json, text/plain, */*",
            "authorization": self.__siigo_access_token,
        }
        self._rate_limiter.wait_if_needed()
        response = requests.request("DELETE", url, headers=headers, timeout=self.__timeout)
        if not response.ok:
            raise UploadError(f"Can't cancel invoice {response.text}")

        del self.__invoice_id_to_credit_note_acentry_id[invoice_id]
