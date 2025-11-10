from typing import Tuple, List, Dict, Union, Optional
from datetime import datetime, timedelta
import requests
import numpy as np
import json
import pandas as pd
import unidecode
import calendar
import time
import re
import os
from invoice_synchronizer.utils.utils import (
    Utils,
    clean_document,
    read_pirpos_product,
    read_invoice_per_client_pirpos,
    read_invoice_per_product_pirpos,
    read_invoice_per_client_siigo,
    get_missing_clients,
    get_missing_products,
    get_missing_invoices,
)
from invoice_synchronizer.utils.errors import (
    ErrorSiigoToken,
    ErrorPirposToken,
    ErrorLoadingPirposClients,
    ErrorLoadingSiigoClients,
    ErrorLoadingPirposProducts,
    ErrorLoadingSiigoProducts,
    ErrorLoadingPirposInvoices,
    ErrorLoadingSiigoInvoices,
    ErrorCreatingCustomer,
    ErrorCreatingProduct,
    ErrorSendingInvoices,
    ErrorNoneInvoice,
)


class Connector:
    def __init__(
        self,
        siigo_userName: str = os.environ["SIIGO_USER_NAME"],
        siigo_access_key: str = os.environ["SIIGO_ACCESS_KEY"],
        pirpos_userName: str = os.environ["PIRPOS_USER_NAME"],
        pirpos_password: str = os.environ["PIRPOS_PASSWORD"],
        configuration_path: str = "configuration.JSON",
    ):

        # Siigo API info
        self.__siigo_userName = siigo_userName
        self.__siigo_access_key = siigo_access_key
        self.__siigo_access_token = self.__get_siigo_access_token()

        # Pirpos API info
        self.__pirpos_userName = pirpos_userName
        self.__pirpos_passwd = pirpos_password
        self.__pirpos_access_token = self.__get_pirpos_access_token()

        # Pirpos to Siigo mapings
        (
            self.PAYMETHOD_PIRPOS2SIIGO,
            self.TAXES_PIRPOS2SIIGO,
            self.INVOICE_TYPE_PIRPOS2SIIGO,
            self.DEFAULT_CLIENT,
        ) = self._load_pirpos2siigo_config(configuration_path)

    # token para acceso
    def __get_siigo_access_token(self) -> str:
        """
        Obtiene el token de acceso para usar la API de SIIGO

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
            "username": self.__siigo_userName,
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

    def __get_pirpos_access_token(self) -> str:
        """
        Obtiene el token de acceso para usar la API de PIRPOS

        Raises
        ------
        ErrorPirposToken
            Error solicitando token, datos incorrectos.

        Returns
        -------
        str
            access_token

        """
        url = "https://api.pirpos.com/login"
        values = {
            "name": "",
            "email": self.__pirpos_userName,
            "password": self.__pirpos_passwd,
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

    # info para mapear siigo2pirpos
    def _load_pirpos2siigo_config(
        self, file_path: str
    ) -> List[Union[Dict[str, int], Dict[str, Union[int, str]]]]:
        """read JSON configuration file.
        It contains information of how map Pirpos to Siigo

        Parameters
        ----------
        file_path : str
            file direction

        Returns
        -------
        Tuple[Dict[str,int],Dict[str,Dict["str",int]],Dict[str,int]]
            returns a tuple with info to map data from Pirpos to Siigo
            (pay_method_maping,taxes_maping, invout_tipe_maping)

        """

        with open(file_path) as file:
            data = json.load(file)

        PAYMETHOD_PIRPOS2SIIGO = data["pay_method_pirpos2siigo"]
        TAXES_PIRPOS2SIIGO = data["taxes_pirpos2siigo"]
        INVOICE_TYPE_PIRPOS2SIIGO = data["invoice_type_pirpos2siigo"]
        DEFAULT_CLIENT = data["default_client"]
        return [
            PAYMETHOD_PIRPOS2SIIGO,
            TAXES_PIRPOS2SIIGO,
            INVOICE_TYPE_PIRPOS2SIIGO,
            DEFAULT_CLIENT,
        ]

    # cargar clientes
    def _load_pirpos_clients(self, batch_clients: int = 200) -> pd.DataFrame:
        """load pirpos clients

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
            url = f"https://api.pirpos.com/clients?pagination=true&limit={batch_clients}&page={page}&clientData=&"
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
            "name": self.DEFAULT_CLIENT["name"],
            "document": self.DEFAULT_CLIENT["document"],
        }

        # adding default client
        clients_db.loc[len(clients_db.index)] = default_client
        clients_db = clients_db.fillna("")
        clients_db = clients_db.astype(str)
        clients_db["document"] = clients_db["document"].apply(clean_document)

        return clients_db

    def _load_siigo_clients(self, batch_clients: int = 200) -> pd.DataFrame:
        """load Siigo clients

        Parameters
        ----------
        batch_clients : int, optional
            batch used to download clients, by default 200

        Returns
        -------
        pd.Dataframe
          Dataframe with Siigo clients
        """
        url = "https://services.siigo.com/ACReportApi/api/v1/Report/post"
        headers = {
            "authority": "services.siigo.com",
            "accept": "application/json, text/plain, */*",
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }

        clients = []
        for type_client in ["Clientes", "Proveedores"]:
            page = 0
            while True:
                payload = json.dumps(
                    {
                        "Id": 5461,
                        "Skip": batch_clients * page,
                        "Take": batch_clients,
                        "Sort": " ",
                        "FilterCriterias": '[{"Field":"var_State","FilterType":7,"OperatorType":0,"Value":["1"],"ValueUI":"Activo","Source":"FixedAssetStateEnum"},{"Field":"var_Type","FilterType":7,"OperatorType":0,"Value":["2"],"ValueUI":"'
                        + type_client
                        + '","Source":"LightAccountTypeEnum"}]',
                        "Params": '{"TabID":"1511","pTabID":"1511"}',
                        "GetTotalCount": True,
                        "GridOrderCriteria": None,
                    }
                )
                response = requests.request(
                    "POST", url, headers=headers, data=payload
                )
                if not response.ok:
                    raise ErrorLoadingSiigoClients(
                        f"Can't download Siigo clients\n {response.text}"
                    )
                data = response.json()["data"]["Value"]["Table"]
                if len(data) == 0:
                    break
                clients.extend(data)
                page += 1
        clients_db = pd.json_normalize(clients)
        clients_db = clients_db.fillna("")
        clients_db = clients_db.astype(str)
        clients_db["Identification"] = clients_db["Identification"].apply(
            clean_document
        )
        clients_db = clients_db.drop_duplicates()
        return clients_db

    # cargar productos
    def _load_pirpos_products(self, batch_products: int = 200) -> pd.DataFrame:
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

    def _load_siigo_products(self, batch_products: int = 200) -> pd.DataFrame:
        """get created products on Siigo

        Parameters
        ----------
        batch_products : int, optional
            batch used to download products, by default 200

        Returns
        -------
        pd.DataFrame
            Siigo products
        """

        url = "https://services.siigo.com/ACReportApi/api/v1/Report/post"
        headers = {
            "authority": "services.siigo.com",
            "accept": "application/json, text/plain, */*",
            "authority": "services.siigo.com",
            "accept": "application/json, text/plain, */*",
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }

        page = 0
        products = []

        while True:
            payload = json.dumps(
                {
                    "Id": 5054,
                    "Skip": batch_products * page,
                    "Take": batch_products,
                    "Sort": " ",
                    "FilterCriterias": '[{"Field":"_vGroup","FilterType":2,"OperatorType":0,"Value":[-1],"ValueUI":"","Source":"[{\\"id\\":1590,\\"name\\":\\"Domicilios\\"},{\\"id\\":1487,\\"name\\":\\"Insumos\\"},{\\"id\\":673,\\"name\\":\\"Productos\\"},{\\"id\\":674,\\"name\\":\\"Servicios\\"}]"},{"Field":"_vType","FilterType":7,"OperatorType":0,"Value":[-1],"ValueUI":"","Source":"TypeProductEnum"},{"Field":"_vProduct","FilterType":6,"OperatorType":0,"Value":[],"ValueUI":"","Source":"40"},{"Field":"_vBalance","FilterType":7,"OperatorType":0,"Value":["3"],"ValueUI":"Todos","Source":"ProductBalancesEnum"},{"Field":"_vState","FilterType":7,"OperatorType":0,"Value":["1"],"ValueUI":"Activo","Source":"ProductStateEnum"},{"Field":"Currency","FilterType":65,"OperatorType":0,"Value":["ALL"],"ValueUI":"Moneda Local","Source":null}]',
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
            products.extend(data)
            page += 1

        products_db = pd.json_normalize(products)
        return products_db

    def _load_pirpos_invoices_per_product(
        self,
        init_day: datetime,
        end_day: datetime,
        step_days: Optional[int] = 10,
    ) -> Tuple[bool, Optional[pd.DataFrame]]:
        """get invoices per product on pirpos

        Parameters
        ----------
        init_day : datetime
            initial time to download invoices. year-month-day
        end_day : datetime
            end time to download invoices year-month-day
        step_days : int, optional
            days used to download invoices in steps, by default 10

        Returns
        -------
        pd.DataFrame
            Pirpos invoices per product in a range of time
        """

        end_day += timedelta(days=1)
        if init_day > end_day:
            raise ErrorLoadingPirposInvoices(
                "end_day must be greater than init_day"
            )

        days = 0
        invoices_per_products = []
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
            url = f"https://api.pirpos.com/reports/reportSalesByProduct?dateInitISO={date1_str}&dateEndISO={date2_str}&showProductCombo=true"
            response = requests.request("GET", url, headers=headers)
            if not response.ok:
                raise ErrorLoadingPirposInvoices(
                    "Can't download invoices per product from pirpos"
                )
            data = response.json()["reportByProduct"]
            for invoice_info in data:
                invoices_per_products.extend(
                    [
                        read_invoice_per_product_pirpos(
                            invoice_info, self.DEFAULT_CLIENT
                        )
                    ]
                )
            if time2 >= end_day:
                break

        if len(invoices_per_products) > 0:
            invoices_per_products_db = pd.json_normalize(invoices_per_products)
            invoices_per_products_db = invoices_per_products_db.fillna("")
            return True, invoices_per_products_db
        else:
            return False, None

    def _load_pirpos_invoices_per_client(
        self, init_day: datetime, end_day: datetime, step_days: int = 10
    ) -> Tuple[bool, Optional[pd.DataFrame]]:
        """get invoices per client on pirpos

        Parameters
        ----------
        init_day : str
            initial time to download invoices. year-month-day
        end_day : str
            end time to download invoices year-month-day
        batch_invoices : int, optional
            days used to download invoices in steps, by default 10

        Returns
        -------
        pd.DataFrame
            Pirpos invoices per client in a range of time
        """

        end_day += timedelta(days=1)
        if init_day > end_day:
            raise ErrorLoadingPirposInvoices(
                "end_day must be greater than init_day"
            )

        days = 0
        invoices_per_client: List[Dict[str, Union[str, int]]] = []
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
            url = f"https://api.pirpos.com/reports/reportSalesInvoices?status=Pagada&dateInit={date1_str}&dateEnd={date2_str}&"
            response = requests.request("GET", url, headers=headers)
            if not response.ok:
                raise ErrorLoadingPirposInvoices(
                    "Can't download invoices per client from pirpos"
                )
            data = response.json()

            for invoice_info in data:
                try:
                    invoices_per_client.extend(
                        [
                            read_invoice_per_client_pirpos(
                                invoice_info, self.DEFAULT_CLIENT
                            )
                        ]
                    )
                except ErrorNoneInvoice:
                    print(f"Factura None {invoice_info['number']}"),
                    continue
            if time2 >= end_day:
                break

        if len(invoices_per_client) > 0:
            invoices_per_client_db = pd.json_normalize(invoices_per_client)
            invoices_per_client_db = invoices_per_client_db.fillna("")
            invoices_per_client_db = invoices_per_client_db.astype(str)
            invoices_per_client_db["client_document"] = invoices_per_client_db[
                "client_document"
            ].apply(clean_document)
            return True, invoices_per_client_db
        else:
            return False, None

    def _load_siigo_invoices(
        self,
        init_day: datetime,
        end_day: datetime,
        step_days: int = 10,
        batch_invoices: int = 200,
    ) -> Tuple[bool, Optional[pd.DataFrame]]:
        """get created invoices from siigo

        Parameters
        ----------
        init_day : str
            initial time to download invoices. year-month-day
        end_day : str
            end time to download invoices year-month-day
        batch_invoices : int, optional
            days used to download invoices in steps, by default 10

        Returns
        -------
        pd.DataFrame
            Siigo created invoices in a range of time
        """

        end_day += timedelta(days=0)
        if init_day > end_day:
            raise ErrorLoadingSiigoInvoices(
                "end_day must be greater than init_day"
            )

        days = 0
        invoices_per_client = []
        url = "https://services.siigo.com/ACReportApi/api/v1/Report/post"
        headers = {
            "authority": "services.siigo.com",
            "accept": "application/json, text/plain, */*",
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }

        while True:
            time1 = init_day + timedelta(days=days)
            time2 = (
                init_day + timedelta(days=days + step_days)
                if init_day + timedelta(days=days + step_days) <= end_day
                else end_day
            )
            days += step_days
            payload = {
                "Id": 5349,
                "Skip": 0,
                "Take": 2000,  # cuidado esto puede danarse cuando las ventas aumenten mucho
                "Sort": " ",
                "FilterCriterias": '[{"Field":"AccountID","FilterType":68,"OperatorType":0,"Value":[],"ValueUI":"","Source":"Account"},{"Field":"DocDate","FilterType":76,"OperatorType":9,"Value":["'
                + time1.strftime("%Y%m%d")
                + '","'
                + time2.strftime("%Y%m%d")
                + '"]},{"Field":"_var_DocClass","FilterType":7,"OperatorType":0,"Value":["1"],"ValueUI":"Factura de venta","Source":"SalesTransactionEnum"},{"Field":"_var_CreatedByUser","FilterType":6,"OperatorType":0,"Value":[],"ValueUI":"","Source":"12"}]',
                "GetTotalCount": True,
                "GridOrderCriteria": None,
            }

            response = requests.request(
                "POST", url, headers=headers, json=payload
            )
            if not response.ok:
                raise ErrorLoadingSiigoInvoices(
                    "Can't download invoices from Siigo"
                )
            data = response.json()["data"]["Value"]["Table"]

            for invoice_info in data:
                invoices_per_client.extend(
                    [read_invoice_per_client_siigo(invoice_info)]
                )
            if time2 >= end_day or len(data) == 0:
                break

        if len(invoices_per_client) > 0:
            invoices_per_client_df = pd.json_normalize(invoices_per_client)
            invoices_per_client_df = invoices_per_client_df.fillna("")
            return True, invoices_per_client_df
        else:
            return False, None

    def actualizarClientes(self) -> None:
        """
        Actualiza los clientes en siigo mostrando la barra de progreso
        en el archivo ./errores/errores_clientes.json se guardan los errores

        """

        # errores Para imprimirlos en txt
        erroresBackUp = {}
        errors = False
        contador_errores = 0

        # get missing clients
        pirpos_clients = self._load_pirpos_clients()
        siigo_clients = self._load_siigo_clients()
        missing_customers = get_missing_clients(pirpos_clients, siigo_clients)
        size = len(missing_customers)
        for idx in range(size):
            # Utils.printProgressBar(idx + 1, size)
            client_info = missing_customers.iloc[idx, :]
            try:
                self.crearCliente(client_info)
            except Exception as e:
                contador_errores += 1
                erroresBackUp[contador_errores] = {
                    "name_cliente": client_info["name"],
                    "identificacion": str(client_info["document"]),
                    "error": str(e),
                }
                errors = True

        with open("clients_errors.json", "w") as json_file:
            json.dump(erroresBackUp, json_file, indent=6)
        if errors:
            raise ErrorCreatingCustomer(
                "Error creating clients, check clients_errors.json file"
            )

    def crearCliente(self, client_info: pd.Series) -> bool:
        """
        Crea la solicitud para hacer un cliente en Siigo

        Parameters
        ----------
        client_info:pd.Series
            client info in pandas Series object

        Raises
        ------
        Exception
            No se puede crear la persona.

        Returns
        -------
        bool
            estado de la operación. True= se creó cliente.

        """
        id_type = (
            int(client_info["idDocumentType"])
            if client_info["idDocumentType"].isnumeric()
            else "13"
        )
        checkDigit = (
            int(client_info["checkDigit"])
            if client_info["checkDigit"].isnumeric()
            else "9"
        )
        name = Utils.normalize(
            client_info["name"]
        )  # elimina caracteres que no procesa siigo
        name = name if len(name) < 100 else name[0:100]
        name = name if len(name) > 0 else "."
        last_name = Utils.normalize(
            client_info["lastName"]
        )  # elimina caracteres que no procesa siigo
        last_name = last_name if len(last_name) < 100 else last_name[0:100]
        last_name = last_name if len(last_name) > 0 else "."
        fiscal_resp = (
            client_info["responsibilities"]
            if client_info["responsibilities"] != ""
            else "R-99-PN"
        )
        address = (
            client_info["address"]
            if client_info["address"] != ""
            else "Cra. 18 #79A - 42"
        )
        country_code = (
            client_info["cityDetail.countryCode"]
            if client_info["cityDetail.countryCode"] != ""
            else "CO"
        )
        state_code = (
            client_info["cityDetail.stateCode"]
            if client_info["cityDetail.stateCode"] != ""
            else "11"
        )
        city_code = (
            client_info["cityDetail.cityCode"]
            if client_info["cityDetail.cityCode"] != ""
            else "11001"
        )
        number = (
            client_info["phone"] if client_info["phone"] != "" else "3006003345"
        )
        email = (
            client_info["email"]
            if client_info["email"] != ""
            else "default@default.com"
        )
        body = {
            "type": "Customer",
            "person_type": "Company"
            if client_info["idDocumentType"] == 31
            else "Person",
            "id_type": id_type,
            "identification": str(client_info["document"]),
            "check_digit": checkDigit,
            "name": [name]
            if client_info["idDocumentType"] == 31
            else [name, last_name],
            "commercial_name": "",
            "branch_office": 0,
            # "active": "true",
            # "vat_responsible": false,
            "fiscal_responsibilities": [{"code": fiscal_resp}],
            "address": {
                "address": address,
                "city": {
                    "country_code": country_code,
                    "state_code": state_code,
                    "city_code": city_code,
                },
                "postal_code": "",
            },
            "phones": [{"indicative": "", "number": number, "extension": ""}],
            "contacts": [
                {
                    "first_name": "null",
                    "last_name": "null",
                    "email": email,
                    "phone": {
                        "indicative": "",
                        "number": number,
                        "extension": "",
                    },
                }
            ],
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.__siigo_access_token,
        }
        url = "https://api.siigo.com/v1/customers"
        response = requests.post(url, data=str(body), headers=headers)

        if not response.ok:
            if response.json()["Errors"][0]["Code"] == "already_exists":
                return False
            else:
                raise Exception(str(response.json()["Errors"][0]))
        return True

    def updateProducts(self) -> None:
        """
        Update products
        ./errores/errores_clientes.json file save errors

        """

        # errores Para imprimirlos en txt
        erroresBackUp = {}
        errors = False
        contador_errores = 0

        # get missing products
        pirpos_products = self._load_pirpos_products()
        siigo_products = self._load_siigo_products()
        missing_products = get_missing_products(pirpos_products, siigo_products)
        size = len(missing_products)
        for idx in range(size):
            # Utils.printProgressBar(idx + 1, size)
            product_info = missing_products.iloc[idx, :]
            try:
                self.create_product(product_info)
            except Exception as e:
                contador_errores += 1
                erroresBackUp[contador_errores] = {
                    "code": product_info["pirpos_id"],
                    "name": product_info["name"],
                    "error": str(e),
                }
                errors = True

        with open("products_errors.json", "w") as json_file:
            json.dump(erroresBackUp, json_file, indent=6)
        if errors:
            raise ErrorCreatingProduct(
                "Error creating products, check clients_errors.json file"
            )

    def create_product(self, product_info: pd.Series) -> bool:
        """
        request the product creation

        Parameters
        ----------
        product_info:pd.Series
            product info

        Raises
        ------
        Exception
            can't create product

        Returns
        -------
        bool
            response of operation. True= product created.

        """

        body = {
            "code": product_info["pirpos_id"],
            "name": product_info["name"],
            "account_group": 673,
            "type": "Product",
            "stock_control": "false",
            "active": "true",
            "tax_classification": "Taxed",
            "tax_included": "true",
            "tax_consumption_value": 8,
            "taxes": [{"id": 7081}],
            "prices": [
                {
                    "currency_code": "COP",
                    "price_list": [
                        {
                            "position": 1,
                            "value": product_info["price"]
                            if int(product_info["price"]) > 0
                            else 1,
                        }
                    ],
                }
            ],
            "unit": "94",
            "unit_label": "unidad",
            "reference": "REF1",
            "description": ".",
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.__siigo_access_token,
        }
        url = "https://api.siigo.com/v1/products"
        response = requests.post(url, data=str(body), headers=headers)

        if not response.ok:
            if response.json()["Errors"][0]["Code"] == "already_exists":
                return False
            else:
                raise Exception(str(response.json()["Errors"][0]))
        return True

    def postInvoice(
        self,
        invoice_type: int,
        invoice_date: str,
        invoice_number: int,
        client_document: int,
        items: List[Dict[str, Union[str, int]]],
        payments: List[Dict[str, Union[str, int]]],
    ) -> bool:

        body = {
            "document": {"id": invoice_type},
            "number": invoice_number,
            "date": invoice_date[0:10],
            "customer": {
                "identification": str(client_document),
                "branch_office": 0,
            },
            "seller": 709,
            "observations": "Observaciones",
            "items": items,
            "payments": payments,
            "retentions": [{"id": 18091}],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.__siigo_access_token,
        }
        url = "https://api.siigo.com/v1/invoices"

        for i in range(30):

            response = requests.post(url, data=str(body), headers=headers)

            # print(body)
            if not response.ok:
                if response.json()["Errors"][0]["Code"] == "already_exists":
                    print(response.json()["Errors"][0]["Message"])
                    return False  # no se puede crear porque ya existe

                elif (
                    response.json()["Errors"][0]["Code"]
                    == "duplicated_document"
                ):
                    # para relizar otra peticion y ayudar al sistema
                    # self.enviarFacturaPrueba()
                    print(response.status_code)
                    print("duplicated_document error. try to send it again")
                    time.sleep(2)
                    if i < 0:
                        continue
                    else:
                        print(response.text)
                        info = str(response.json()["Errors"])
                        raise Exception(info)
                elif (
                    response.json()["Errors"][0]["Code"]
                    == "invalid_total_payments"
                ):
                    # el mensaje indica el valor que debe ser pagado
                    text = response.json()["Errors"][0]["Message"]
                    print(text)
                    pyment = [int(s) for s in re.findall(r"\b\d+\b", text)][0]
                    print(
                        "Se ajusta el valor a pagar de {0} a {1}".format(
                            body["payments"][0]["value"], pyment
                        )
                    )
                    body[
                        "payments"
                    ] = [  # este ajuste elimina otros metedos de pago asociados !!cuidado!!
                        {
                            "id": body["payments"][0]["id"],
                            "value": pyment,
                        }
                    ]
                    continue

                else:
                    print(response.text)
                    info = str(response.json()["Errors"][0]["Code"])
                    raise Exception(info)
            return True  # se crea exitosamente

    def _update_invoices(self, in_date: datetime, end_date: datetime) -> int:

        """update invoices in a range of time on siigo

        Parameters
        ----------
        in_date:datetime
            initial date to update invoices
        end_date:datetime
            end date to update invoices
        """

        (
            successful_pirpos,
            pirpos_invoices_per_client,
        ) = self._load_pirpos_invoices_per_client(in_date, end_date)
        successful_siigo, siigo_invoices = self._load_siigo_invoices(
            in_date, end_date
        )

        if successful_pirpos and successful_siigo:
            assert isinstance(pirpos_invoices_per_client, pd.DataFrame)
            assert isinstance(siigo_invoices, pd.DataFrame)
            invoices, _ = get_missing_invoices(
                pirpos_invoices_per_client, siigo_invoices
            )
            if len(invoices) == 0:
                print("there aren't invoices to update")
                return 0

        elif successful_pirpos:
            assert isinstance(pirpos_invoices_per_client, pd.DataFrame)
            invoices = pirpos_invoices_per_client
        else:
            print("there aren't invoices to update")
            return 0
        erroresBackUp = {}
        contador_errores = 0
        for _, invoice_info in invoices.iterrows():
            invoice_type = self.INVOICE_TYPE_PIRPOS2SIIGO[
                invoice_info["prefix"]
            ]
            invoice_number = invoice_info["seq"]
            invoice_date = invoice_info["created"]
            client_document = invoice_info["client_document"]
            products = json.loads(invoice_info["products"])
            # obtiene los items de la factura
            items = []
            for product_info in products:
                product_info["tax_value"] = (
                    product_info["tax_value"] if product_info["tax_name"] else 8
                )
                product_info["tax_name"] = (
                    product_info["tax_name"]
                    if product_info["tax_name"]
                    else "I CONSUMO"
                )
                item_info = {}
                item_info["code"] = product_info["id"]
                item_info["description"] = unidecode.unidecode(
                    product_info["name"]
                )
                item_info["quantity"] = product_info["quantity"]
                item_info["price"] = round(
                    product_info["price"]
                    / ((1 + product_info["tax_value"] / 100)),
                    2,
                )

                item_info["taxes"] = [
                    {
                        "id": self.TAXES_PIRPOS2SIIGO[product_info["tax_name"]][
                            "id"
                        ]
                    }
                ]
                items.append(item_info)

            # datos del pago
            paiments_info = json.loads(invoice_info["paid"])
            payments = [
                {
                    "id": self.PAYMETHOD_PIRPOS2SIIGO[
                        paiment_info["pay_method"]
                    ],
                    "value": paiment_info[
                        "value"
                    ],  # revisar para facturas normales
                    "due_date": invoice_info["created"][0:10],
                }
                for paiment_info in paiments_info
            ]

            try:
                result = self.postInvoice(
                    invoice_type,
                    invoice_date,
                    invoice_number,
                    client_document,
                    items,
                    payments,
                )
                if result:
                    print(f"factura {invoice_info['number']} creada\n")
                else:
                    print(f"factura {invoice_info['number']} ya existe\n")

            except Exception as e:
                print(f"Error en factura {invoice_info['number']}\n")
                print(e)
                print()
                contador_errores += 1
                erroresBackUp[contador_errores] = {
                    "numero factura": invoice_info["number"],
                    "error": str(e),
                }
            finally:
                time.sleep(1)
        print("guardando json")
        a = "1234"
        # TODO revisar save cuando se hacen thears y la ruta
        with open("errores_facturas.json", "w") as json_file:
            json.dump(erroresBackUp, json_file, indent=6)
        return contador_errores

    def update_invoices(self, init_day: datetime, end_day: datetime) -> None:
        """send invoices to siigo"""
        # day1 = datetime.strptime(init_day, "%Y-%m-%d")
        # day2 = datetime.strptime(end_day, "%Y-%m-%d")
        for i in range(20):
            print((f"intento {i}"))
            errors = self._update_invoices(init_day, end_day)
            print(f"errores {errors}")
            if errors == 0:
                break
            print("intentando volver a enviar facturas con error")
        if errors > 0:
            raise ErrorSendingInvoices(
                "Error actualizando facturas revisar archivos"
            )

    def _get_sold_units(
        self, init_day: datetime, end_day: datetime
    ) -> pd.DataFrame:
        "get quantity and total for each product in a range of time"

        end_day += timedelta(days=1)

        if init_day > end_day:
            raise ErrorLoadingPirposInvoices(
                "end_day must be greater than init_day"
            )

        date1_str = datetime.strftime(init_day, "%Y-%m-%dT05:00:00.000Z")
        date2_str = datetime.strftime(end_day, "%Y-%m-%dT05:00:00.000Z")
        url = f"https://api.pirpos.com/stats/totalInvoicesByProducts?dateInitISO={date1_str}&dateEndISO={date2_str}&sortBy=total&"

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://app.pirpos.com/",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }
        products_quantity_total = []

        response = requests.request("GET", url, headers=headers)
        if not response.ok:
            raise ErrorLoadingSiigoProducts(
                "Can't download Siigo sold units per Products"
            )
        data = response.json()
        if len(data) > 0:
            for product in data:
                quantity = float(product["quantity"])
                total = float(product["total"])
                name = product["_id"]["product"]["name"]
                products_quantity_total.append([name, quantity, total])
            np_pqt = np.array(products_quantity_total)
            data_frame = pd.DataFrame(
                np_pqt[:, 1:], index=np_pqt[:, 0], columns=["quantity", "total"]
            )
            data_frame[["quantity", "total"]] = data_frame[
                ["quantity", "total"]
            ].apply(pd.to_numeric)
        else:
            data_frame = pd.DataFrame([], columns=["quantity", "total"])
        return data_frame

    def get_history_sold_units(
        self, years_months: List[str]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """get quantity and total sold for each product in a list of periods [year-month]

        Parameters
        ----------
        years_months : List[str]

        Returns
        -------
        Tuple[pd.DataFrame, pd.DataFrame]
            quantity per product, total sold per product
        """
        history_df_quantity = pd.DataFrame([])
        history_df_total = pd.DataFrame([])
        for year_month in years_months:
            date1 = datetime.strptime(year_month, "%Y-%m")
            date2 = datetime(
                date1.year,
                date1.month,
                calendar.monthrange(date1.year, date1.month)[1],
            )
            info_df = self._get_sold_units(date1, date2)
            history_df_quantity[date1.strftime("%Y-%m")] = info_df["quantity"]
            history_df_total[date1.strftime("%Y-%m")] = info_df["total"]
        history_df_quantity["Total"] = history_df_quantity.sum(axis=1)
        history_df_total["Total"] = history_df_total.sum(axis=1)

        history_df_quantity = history_df_quantity.sort_values(
            by=["Total"], axis=0, ascending=False
        )
        history_df_total = history_df_total.sort_values(
            by=["Total"], axis=0, ascending=False
        )

        history_df_quantity = history_df_quantity.applymap(
            lambda x: round(x, 2)
        )
        history_df_total = history_df_total.applymap(lambda x: round(x, 2))
        return history_df_quantity, history_df_total

    def check_invoices_integrity(
        self, in_date: datetime, end_date: datetime
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Check integrity of invoices exported to siigo."""
        (
            successful_pirpos,
            pirpos_invoices_per_client,
        ) = self._load_pirpos_invoices_per_client(in_date, end_date)
        successful_siigo, siigo_invoices = self._load_siigo_invoices(
            in_date, end_date
        )

        if successful_pirpos and successful_siigo:
            assert isinstance(pirpos_invoices_per_client, pd.DataFrame)
            assert isinstance(siigo_invoices, pd.DataFrame)
            missing_invoices, left_merge = get_missing_invoices(
                pirpos_invoices_per_client, siigo_invoices
            )

        elif successful_pirpos:
            assert isinstance(pirpos_invoices_per_client, pd.DataFrame)
            missing_invoices = pirpos_invoices_per_client
        else:
            print("There aren't invoices to compare")
            return 0
