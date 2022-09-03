import datetime
import requests
import json
import pandas as pd
import unidecode
import math
import time
import re
from typing import Optional, Tuple, List, Dict, Union
from . import (
    utils,
    Utils,
    ErrorSiigoToken,
    ErrorPirposToken,
    ErrorLoadingPirposClients,
    ErrorLoadingSiigoClients,
    ErrorLoadingPirposProducts,
    ErrorLoadingSiigoProducts,
    ErrorLoadingPirposInvoices,
    ErrorLoadingSiigoInvoices,
    ErrorCreatingCustomer,
    constants,
)

import os


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
        self._load_pirpos2siigo_config(configuration_path)

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

        if response.ok == False:
            raise ErrorSiigoToken(
                "Error solicitando token, revisar userName y access_key"
            )
        access_token = response.json()["access_token"]
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

        if response.ok == False:
            raise ErrorPirposToken(
                "Error getting Pirpos token, check email and password"
            )
        access_token = response.json()["tokenCurrent"]
        return access_token

    # info para mapear siigo2pirpos
    def _load_pirpos2siigo_config(
        self, file_path: str
    ) -> Tuple[Dict[str, int], Dict[str, Dict["str", int]], Dict[str, int]]:
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

        constants.PAYMETHOD_PIRPOS2SIIGO = (data["pay_method_pirpos2siigo"],)
        constants.TAXES_PIRPOS2SIIGO = (data["taxes_pirpos2siigo"],)
        constants.INVOICE_TYPE_PIRPOS2SIIGO = (data["invoice_type_pirpos2siigo"],)
        constants.DEFAULT_CLIENT = data["default_client"]

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
            if response.ok == False:
                raise ErrorLoadingPirposClients(
                    f"Can't download PirPos clients\n {response.text}"
                )
            data = response.json()["data"]
            if len(data) == 0:
                break
            clients.extend(data)
            page += 1
        clients = pd.json_normalize(clients)
        default_client = {
            "name": constants.DEFAULT_CLIENT["name"],
            "document": constants.DEFAULT_CLIENT["document"],
        }
        clients.loc[len(clients.index)] = default_client
        clients = clients.fillna("")
        clients = clients.astype(str)
        clients["document"] = clients["document"].apply(utils.clean_document)

        return clients

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
        url = f"https://services.siigo.com/ACReportApi/api/v1/Report/post"
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
                response = requests.request("POST", url, headers=headers, data=payload)
                if response.ok == False:
                    raise ErrorLoadingSiigoClients(
                        f"Can't download Siigo clients\n {response.text}"
                    )
                data = response.json()["data"]["Value"]["Table"]
                if len(data) == 0:
                    break
                clients.extend(data)
                page += 1
        clients = pd.json_normalize(clients)
        clients = clients.fillna("")
        clients = clients.astype(str)
        clients["Identification"] = clients["Identification"].apply(
            utils.clean_document
        )

        return clients

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
        payload = {}
        while True:
            url = f"https://api.pirpos.com/products?pagination=true&limit={batch_products}&page={page}&name=&categoryId=undefined&useInRappi=undefined&"
            response = requests.request("GET", url, headers=headers, data=payload)
            if response.ok == False:
                raise ErrorLoadingPirposProducts("Can't download Pirpos Products")
            data: List[Dict] = response.json()["data"]
            if len(data) == 0:
                break
            for product_info in data:
                products.extend(utils.read_pirpos_product(product_info))

            page += 1

        products = pd.json_normalize(products)
        products = products.fillna("")
        products = products.astype(str)
        products["name"] = products["name"].apply(Utils.normalize)
        return products

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
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.ok == False:
                raise ErrorLoadingSiigoProducts("Can't download Siigo Products")
            data: List[Dict] = response.json()["data"]["Value"]["Table"]
            if len(data) == 0:
                break
            products.extend(data)
            page += 1

        products = pd.json_normalize(products)
        return products

    def _load_pirpos_invoices_per_product(
        self, init_day: str, end_day: str, step_days: int = 10
    ) -> pd.DataFrame:
        """get invoices per product on pirpos

        Parameters
        ----------
        init_day : str
            initial time to download invoices. year-month-day
        end_day : str
            end time to download invoices year-month-day
        step_days : int, optional
            days used to download invoices in steps, by default 10

        Returns
        -------
        pd.DataFrame
            Pirpos invoices per product in a range of time
        """

        init_day = datetime.datetime.strptime(init_day, "%Y-%m-%d")
        end_day = datetime.datetime.strptime(end_day, "%Y-%m-%d") + datetime.timedelta(
            days=1
        )
        if init_day > end_day:
            raise ErrorLoadingPirposInvoices("end_day must be greater than init_day")

        days = 0
        invoices_per_products = []
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://app.pirpos.com/",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }
        payload = {}

        while True:
            time1 = init_day + datetime.timedelta(days=days)
            time2 = (
                init_day + datetime.timedelta(days=days + step_days)
                if init_day + datetime.timedelta(days=days + step_days) <= end_day
                else end_day
            )
            days += step_days
            date1_str = datetime.datetime.strftime(time1, "%Y-%m-%dT05:00:00.000Z")
            date2_str = datetime.datetime.strftime(time2, "%Y-%m-%dT05:00:00.000Z")
            url = f"https://api.pirpos.com/reports/reportSalesByProduct?dateInitISO={date1_str}&dateEndISO={date2_str}&showProductCombo=true"
            response = requests.request("GET", url, headers=headers, data=payload)
            if response.ok == False:
                raise ErrorLoadingPirposInvoices(
                    "Can't download invoices per product from pirpos"
                )
            data: List[Dict] = response.json()["reportByProduct"]
            invoices_per_products.extend(data)
            if time2 >= end_day:
                break

        invoices_per_products = pd.json_normalize(invoices_per_products)
        return invoices_per_products

    def _load_pirpos_invoices_per_client(
        self, init_day: str, end_day: str, step_days: int = 10
    ) -> pd.DataFrame:
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

        init_day = datetime.datetime.strptime(init_day, "%Y-%m-%d")
        end_day = datetime.datetime.strptime(end_day, "%Y-%m-%d") + datetime.timedelta(
            days=1
        )
        if init_day > end_day:
            raise ErrorLoadingPirposInvoices("end_day must be greater than init_day")

        days = 0
        invoices_per_client = []
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://app.pirpos.com/",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }
        payload = {}

        while True:
            time1 = init_day + datetime.timedelta(days=days)
            time2 = (
                init_day + datetime.timedelta(days=days + step_days)
                if init_day + datetime.timedelta(days=days + step_days) <= end_day
                else end_day
            )
            days += step_days
            date1_str = datetime.datetime.strftime(time1, "%Y-%m-%dT05:00:00.000Z")
            date2_str = datetime.datetime.strftime(time2, "%Y-%m-%dT05:00:00.000Z")
            url = f"https://api.pirpos.com/reports/reportSalesInvoices?status=Pagada&dateInit={date1_str}&dateEnd={date2_str}&"
            response = requests.request("GET", url, headers=headers, data=payload)
            if response.ok == False:
                raise ErrorLoadingPirposInvoices(
                    "Can't download invoices per client from pirpos"
                )
            data: List[Dict] = response.json()

            for invoice_info in data:
                invoices_per_client.extend(
                    [utils.read_invoice_per_client(invoice_info)]
                )
            if time2 >= end_day:
                break

        invoices_per_client = pd.json_normalize(invoices_per_client)
        invoices_per_client = invoices_per_client.fillna("")
        invoices_per_client = invoices_per_client.astype(str)
        invoices_per_client["client_document"] = invoices_per_client[
            "client_document"
        ].apply(utils.clean_document)
        return invoices_per_client

    def _load_siigo_invoices(
        self, init_day: str, end_day: str, step_days: int = 10, batch_invoices=200
    ) -> Tuple[bool, pd.DataFrame]:
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

        init_day = datetime.datetime.strptime(init_day, "%Y-%m-%d")
        end_day = datetime.datetime.strptime(end_day, "%Y-%m-%d") + datetime.timedelta(
            days=1
        )
        if init_day > end_day:
            raise ErrorLoadingPirposInvoices("end_day must be greater than init_day")

        days = 0
        invoices_per_client = []
        url = f"https://services.siigo.com/ACReportApi/api/v1/Report/post"
        headers = {
            "authority": "services.siigo.com",
            "accept": "application/json, text/plain, */*",
            "authorization": self.__siigo_access_token,
            "content-type": "application/json",
        }
        
        while True:
            time1 = init_day + datetime.timedelta(days=days)
            time2 = (
                init_day + datetime.timedelta(days=days + step_days)
                if init_day + datetime.timedelta(days=days + step_days) <= end_day
                else end_day
            )
            days += step_days
            date1_str = datetime.datetime.strftime(time1, "%Y-%m-%dT05:00:00.000Z")
            date2_str = datetime.datetime.strftime(time2, "%Y-%m-%dT05:00:00.000Z")
            payload = {
                "Id":5349,
                "Skip":0,
                "Take":2000,#cuidado esto puede danarse cuando las ventas aumenten mucho 
                "Sort":" ",
                "FilterCriterias":"[{\"Field\":\"AccountID\",\"FilterType\":68,\"OperatorType\":0,\"Value\":[],\"ValueUI\":\"\",\"Source\":\"Account\"},{\"Field\":\"DocDate\",\"FilterType\":76,\"OperatorType\":9,\"Value\":[\""+init_day.strftime("%Y%m%d")+"\",\""+end_day.strftime("%Y%m%d")+"\"]},{\"Field\":\"_var_DocClass\",\"FilterType\":7,\"OperatorType\":0,\"Value\":[\"1\"],\"ValueUI\":\"Factura de venta\",\"Source\":\"SalesTransactionEnum\"},{\"Field\":\"_var_CreatedByUser\",\"FilterType\":6,\"OperatorType\":0,\"Value\":[],\"ValueUI\":\"\",\"Source\":\"12\"}]",
                "GetTotalCount":True,
                "GridOrderCriteria":None
            }
            
            response = requests.request("POST", url, headers=headers, json=payload)
            if response.ok == False:
                raise ErrorLoadingSiigoInvoices(
                    "Can't download invoices from Siigo"
                )
            data: List[Dict] = response.json()["data"]["Value"]["Table"]

            for invoice_info in data:
                invoices_per_client.extend(
                    [utils.read_invoice_per_client_siigo(invoice_info)]
                )
            if time2 >= end_day:
                break
        
        if len(invoices_per_client) > 0:
            invoices_per_client = pd.json_normalize(invoices_per_client)
            invoices_per_client = invoices_per_client.fillna("")
            return True, invoices_per_client
        else:
            return False, None
            

    def _load_pirpos_invoices_per_client(
        self, init_day: str, end_day: str, step_days: int = 10
    ) -> Tuple[bool, pd.DataFrame]:
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

        init_day = datetime.datetime.strptime(init_day, "%Y-%m-%d")
        end_day = datetime.datetime.strptime(end_day, "%Y-%m-%d") + datetime.timedelta(
            days=1
        )
        if init_day > end_day:
            raise ErrorLoadingPirposInvoices("end_day must be greater than init_day")

        days = 0
        invoices_per_client = []
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://app.pirpos.com/",
            "Authorization": f"Bearer {self.__pirpos_access_token}",
        }
        payload = {}

        while True:
            time1 = init_day + datetime.timedelta(days=days)
            time2 = (
                init_day + datetime.timedelta(days=days + step_days)
                if init_day + datetime.timedelta(days=days + step_days) <= end_day
                else end_day
            )
            days += step_days
            date1_str = datetime.datetime.strftime(time1, "%Y-%m-%dT05:00:00.000Z")
            date2_str = datetime.datetime.strftime(time2, "%Y-%m-%dT05:00:00.000Z")
            url = f"https://api.pirpos.com/reports/reportSalesInvoices?status=Pagada&dateInit={date1_str}&dateEnd={date2_str}&"
            response = requests.request("GET", url, headers=headers, data=payload)
            if response.ok == False:
                raise ErrorLoadingPirposInvoices(
                    "Can't download invoices per client from pirpos"
                )
            data: List[Dict] = response.json()

            for invoice_info in data:
                invoices_per_client.extend(
                    [utils.read_invoice_per_client_pirpos(invoice_info)]
                )

            if time2 >= end_day:
                break

        if len(invoices_per_client)>0:
            invoices_per_client = pd.json_normalize(invoices_per_client)
            invoices_per_client = invoices_per_client.fillna("")
            invoices_per_client = invoices_per_client.astype(str)
            invoices_per_client["client_document"] = invoices_per_client[
                "client_document"
            ].apply(utils.clean_document)
            return True, invoices_per_client
        else:
            return False, None

    def actualizarClientes(self):
        """
        Actualiza los clientes en siigo mostrando la barra de progreso
        en el archivo ./errores/errores_clientes.json se guardan los errores

        """

        print(
            "\n###########################\nCreating missing clients\n###########################\n"
        )
        # errores Para imprimirlos en txt
        erroresBackUp = {}
        errors = False
        contador_errores = 0

        # get missing clients
        pirpos_clients = self._load_pirpos_clients()
        siigo_clients = self._load_siigo_clients()
        missing_customers = utils.get_missing_clients(pirpos_clients, siigo_clients)
        size = len(missing_customers)
        for idx in range(size):
            Utils.printProgressBar(idx + 1, size)
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
        if errors == True:
            raise ErrorCreatingCustomer(
                "Error creating clients, check clients_errors.json file"
            )
        print(
            "\n###########################\nClients created\n###########################\n"
        )

    def crearCliente(self, client_info: pd.Series):
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
        number = client_info["phone"] if client_info["phone"] != "" else "3006003345"
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

        if response.ok == False:
            if response.json()["Errors"][0]["Code"] == "already_exists":
                return False
            else:
                raise Exception(str(response.json()["Errors"][0]))
        return True

    def updateProducts(self):
        """
        Update products
        ./errores/errores_clientes.json file save errors

        """

        print(
            "\n###########################\nCreating missing Products\n###########################\n"
        )
        # errores Para imprimirlos en txt
        erroresBackUp = {}
        errors = False
        contador_errores = 0

        # get missing products
        pirpos_products = self._load_pirpos_products()
        siigo_products = self._load_siigo_products()
        missing_products = utils.get_missing_products(pirpos_products, siigo_products)
        size = len(missing_products)
        for idx in range(size):
            Utils.printProgressBar(idx + 1, size)
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
        if errors == True:
            raise ErrorCreatingCustomer(
                "Error creating products, check clients_errors.json file"
            )
        print(
            "\n###########################\nProducts created\n###########################\n"
        )

    def create_product(self, product_info: pd.Series):
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
            # "additional_fields": {
            #     "barcode": "B0123",
            #     "brand": "Gef",
            #     "tariff": "151612",
            #     "model": "Loiry"
            # }
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.__siigo_access_token,
        }
        url = "https://api.siigo.com/v1/products"
        response = requests.post(url, data=str(body), headers=headers)

        if response.ok == False:
            if response.json()["Errors"][0]["Code"] == "already_exists":
                return False
            else:
                raise Exception(str(response.json()["Errors"][0]))
        return True

    def enviarFacturaPrueba(self):

        item = []
        itemInfo = {}
        itemInfo["code"] = "61d7d3349ab18205d7997fa0"
        itemInfo["description"] = "Jugos Hit mango"
        itemInfo["quantity"] = 1
        itemInfo["price"] = 3000
        # total_Productos += math.ceil((math.ceil(itemInfo["price"]*itemInfo["quantity"]*100)/100+math.ceil(itemInfo["price"]*itemInfo["quantity"]*0.08*100)/100)*100)/100
        total_Productos = itemInfo["price"] * itemInfo["quantity"] + round(
            itemInfo["price"] * itemInfo["quantity"] * 0.08, 2
        )
        # print("dato1 {0}   dato2  {1}\n".format(itemInfo["price"]*itemInfo["quantity"],itemInfo["price"]*itemInfo["quantity"]*0.08))
        # print("item "+ str(itemInfo["price"]))
        itemInfo["taxes"] = [{"id": 7081}]
        item.append(itemInfo)

        body = {
            "document": {"id": self._tipoComprobante["POS"]},
            "number": 18,
            "date": "2022-01-01",
            "customer": {"identification": str(222222222222), "branch_office": 0},
            "seller": 709,
            "observations": "Observaciones",
            "items": item,
            "payments": [
                {
                    "id": 3025,
                    "value": total_Productos  # ,
                    # "due_date": "2021-03-19"
                }
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.access_token,
            "Connection": "close",
        }
        url = "https://api.siigo.com/v1/invoices"

        response = requests.post(url, data=str(body), headers=headers)
        # print(response.text)

    def postInvoice(
        self,
        tipoComprobante,
        fecha,
        invoiceNumber,
        identificacion,
        items,
        pyment,
        method,
    ):

        body = {
            "document": {"id": self._tipoComprobante[tipoComprobante]},
            "number": invoiceNumber,
            "date": fecha.strftime("%Y-%m-%d"),
            "customer": {"identification": str(identificacion), "branch_office": 0},
            "seller": 709,
            "observations": "Observaciones",
            "items": items,
            "payments": [
                {
                    "id": method,
                    "value": pyment,
                    "due_date": (fecha + datetime.timedelta(days=10)).strftime(
                        "%Y-%m-%d"
                    ),  # revisar para facturas normales
                }
            ],
            "retentions": [{"id": 18091}],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.access_token,
            "Connection": "close",
        }
        url = "https://api.siigo.com/v1/invoices"

        for i in range(30):

            response = requests.post(url, data=str(body), headers=headers)

            # print(body)
            if response.ok == False:
                if response.json()["Errors"][0]["Code"] == "already_exists":
                    print(response.json()["Errors"][0]["Message"])
                    return False  # no se puede crear porque ya existe

                elif response.json()["Errors"][0]["Code"] == "duplicated_document":
                    # para relizar otra peticion y ayudar al sistema
                    self.enviarFacturaPrueba()
                    print("duplicated_document error. try to send it again")
                    time.sleep(0.8)
                    if i < 29:
                        continue
                    else:
                        print(response.text)
                        info = str(response.json()["Errors"])
                        raise Exception(info)
                elif response.json()["Errors"][0]["Code"] == "invalid_total_payments":
                    # el mensaje indica el valor que debe ser pagado
                    text = response.json()["Errors"][0]["Message"]
                    print(text)
                    pyment = [int(s) for s in re.findall(r"\b\d+\b", text)][0]
                    print(
                        "Se ajusta el valor a pagar de {0} a {1}".format(
                            body["payments"][0]["value"], pyment
                        )
                    )
                    body["payments"][0]["value"] = pyment
                    continue

                else:
                    print(response.text)
                    info = str(response.json()["Errors"][0]["Code"])
                    raise Exception(info)
            return True  # se crea exitosamente

    # def enviarFacturas(self):
    #     """create readed invoices. You can use facturas_escogidas to send a group of invoices instead to send all them.\n
    #        If you whan continue the creation from a specific invoice use start_at with the invoice number.

    #     Parameters
    #     ----------
    #     facturas_escogidas : Optional[List[str]] = None
    #         list of invoice numbers that must be created. If None is passed so all readed invoiced will be created
    #     start_at : Optional[str] = None
    #         reference invoice to start to create them. Useful if the process crashes and you don't want to begin the creation from the first invoice

    #     """

    #     print(
    #         "\n###########################\nEnvio Masivo de facturas\n###########################\n"
    #     )

    #     # numeros de facturas .
    #     facturas = self._load_pirpos_invoices_per_client()
    #     if facturas_escogidas != None:
    #         facturas = facturas_escogidas
    #     if facturas_escogidas == None and start_at != None:
    #         mask = join2["No. Factura"] == start_at
    #         index = join2["No. Factura"].index[mask].tolist()
    #         facturas = join2.loc[index[0] :, "No. Factura"].unique()
    #     # revisa cada factura

    #     erroresBackUp = {}
    #     contador_errores = 0
    #     size = len(facturas)
    #     for factura in facturas:

    #         # selecciona todos los datos asociados a esa factura
    #         mask = join2["No. Factura"] == factura
    #         # revisa si es factura POS o Electronica
    #         prefijoIdentificado, numeroFactura = Utils._revisarFactura(
    #             factura, [".", "LL"]
    #         )  # dejar estas variables globales en todo el programa ###########
    #         tipoComprobante = "POS" if prefijoIdentificado == "LL" else "FE"

    #         # de todo el dataframe obtiene solo los datos de la factura de interes
    #         datosFacturai = join2[mask]
    #         # reinicia index de las filas
    #         datosFacturai = datosFacturai.reset_index(drop=True)

    #         # fecha de la factura
    #         fecha = datosFacturai.loc[0, "Fecha"]

    #         # obtiene informacion del cliente
    #         documentoCliente = int(datosFacturai.loc[0, "Documento"])
    #         # print(type(documentoCliente))

    #         # obtiene los items de la factura
    #         items = []
    #         total_Productos = 0
    #         for i in range(len(datosFacturai)):
    #             itemInfo = {}
    #             itemInfo["code"] = datosFacturai.loc[i, "Código_y"]
    #             itemInfo["description"] = unidecode.unidecode(
    #                 datosFacturai.loc[i, "Producto"]
    #             )
    #             itemInfo["quantity"] = datosFacturai.loc[i, "Cantidad"]

    #             if str(itemInfo["code"]) == "nan":
    #                 print(itemInfo["description"])

    #             if itemInfo["code"] != "61f18fa3290b5f169086d712":
    #                 # se fija el impuesto del 8% porque siempre es comida
    #                 itemInfo["price"] = round(
    #                     datosFacturai.loc[i, "Total_x"]
    #                     / (datosFacturai.loc[i, "Cantidad"] * 1.08),
    #                     2,
    #                 )

    #                 valorBase = round(itemInfo["price"] * itemInfo["quantity"], 2)
    #                 impuesto = round(valorBase * 0.08, 2)
    #                 valorItem = round(valorBase + impuesto, 2)
    #                 total_Productos += valorItem
    #                 # total_Productos += round(itemInfo["price"]*itemInfo["quantity"]+itemInfo["price"]*itemInfo["quantity"]*0.08,2)

    #                 # total_Productos += round(itemInfo["price"]*itemInfo["quantity"],2)+round(itemInfo["price"]*itemInfo["quantity"]*0.08,2)

    #                 # print("valorUnitario = {0}, cantidad = {1}".format(itemInfo["price"],itemInfo["quantity"],valorBase,impuesto,valorItem))
    #                 # print("valorBase = {0} => {1}".format(itemInfo["price"]*itemInfo["quantity"], valorBase))
    #                 # print("impuesto = {0} => {1}".format(valorBase*0.08, impuesto))
    #                 # print("totalItem = {0} => {1}".format(valorBase+impuesto, valorItem))
    #                 # print("\n")
    #                 itemInfo["taxes"] = [{"id": 7081}]
    #             else:
    #                 # se fija el impuesto del 8% porque siempre es comida
    #                 itemInfo["price"] = round(
    #                     datosFacturai.loc[i, "Total_x"]
    #                     / (datosFacturai.loc[i, "Cantidad"]),
    #                     2,
    #                 )
    #                 total_Productos += itemInfo["price"] * itemInfo["quantity"]
    #                 itemInfo["taxes"] = []
    #                 print("entra")

    #             # agrega item a la lista
    #             items.append(itemInfo)

    #         # datos del pago
    #         formaPago = self._formasPago[datosFacturai.loc[0, "Forma de Pago"]]
    #         # totalPagado = total_Productos+math.floor(int(100*total_Productos*0.08))/100
    #         # totalPagado = datosFacturai.loc[i,"Total_y"]
    #         # totalPagado = 4999.99

    #         # print(totalPagado)
    #         # print(round(total_Productos))
    #         totalPagado = round(total_Productos)
    #         # print(totalPagado)
    #         # totalPagado = 47001
    #         # print(totalPagado)
    #         # se envia factura
    #         try:
    #             result = self.postInvoice(
    #                 tipoComprobante,
    #                 fecha,
    #                 numeroFactura,
    #                 documentoCliente,
    #                 items,
    #                 totalPagado,
    #                 formaPago,
    #             )
    #             if result == True:
    #                 print(
    #                     "factura {0} {1} creada\n".format(
    #                         tipoComprobante, numeroFactura
    #                     )
    #                 )
    #             else:
    #                 print(
    #                     "factura {0} {1} ya existe\n".format(
    #                         tipoComprobante, numeroFactura
    #                     )
    #                 )

    #         except Exception as e:
    #             print(
    #                 "\nError en factura {0} {1}\n".format(
    #                     tipoComprobante, numeroFactura
    #                 )
    #             )
    #             print(e)
    #             print()
    #             contador_errores += 1
    #             erroresBackUp[contador_errores] = {
    #                 "numero factura": numeroFactura,
    #                 "prefijo": prefijoIdentificado,
    #                 "error": str(e),
    #             }

    #     with open("errores_facturas.json", "w") as json_file:
    #         json.dump(erroresBackUp, json_file, indent=6)
    #     print(
    #         "\n###########################\nFin Envio Masivo de facturas\n###########################\n"
    #     )
