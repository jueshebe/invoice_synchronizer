import json
import pandas as pd
import math
from os import listdir
from os.path import isfile, join
from typing import Callable, List, Tuple, Dict, Union, Optional
from pirpos2siigo.utils.errors import (
    ErrorLoadingPirposProducts,
    ErrorLoadingSiigoInvoices,
)


class Utils:
    @staticmethod
    def prepararArchivo(
        directory: str,
        tipoArchivo: int,
        modificarNumeracionFactura: bool = False,
        numeracionInicial: Tuple[int, int] = (0, 0),
    ) -> pd:
        """
        Prepara los archivos para que puedan leerse adecuadamente

        Parameters
        ----------
        directory : str
            directorio donde se encuentran los archios
        tipoArchivo : int
            tipo de documento recibido
            0=archivo de clientes Pirpos(read_html)
            1=archivo de clientes Siigo (read_excel)
            2=archivo de productos siigo (read_excel)
            3=archivo de ventas por productos pirpos (read_html)
            4=archivo de ventas por cliente pirpos (read_html)
        modificarNumeracionFactura: bool
            Modificar la numeracion de las facturas en orden creciente.
        numeracionInicial: (int,int)
            numeracion en el que debe empezar la primera factura POS y electronica

        Returns
        ----------
        pd
            retorna el archivo preparado para su lectura.

        """
        # pd.read_html(f"{documents}/clientes-pirpos/clientes.xls")[0]
        # pd.read_excel(f"{documents}/productos-siigo/Listado de productos _ Servicios.xlsx")

        time_column = ""
        if tipoArchivo == 0:  # archivo de clientes PirPos

            def func(file_name):
                file = pd.read_html(file_name)[0]
                encabezados = file.iloc[0, :]
                file = file.drop(labels=[0], axis=0)
                file.columns = encabezados
                file = file.reset_index(drop=True)
                return file

            extension = ".xls"
            modificarNumeracionFactura = False

        elif tipoArchivo == 1:  # archivo clientes Siigo

            def func(file_name):
                file = pd.read_excel(file_name)
                encabezados = file.iloc[5, :]
                file = file.drop(labels=[0, 1, 2, 3, 4, 5, len(file) - 1], axis=0)
                file = file.reset_index(drop=True)
                file.columns = encabezados
                file = file.dropna(subset=["Identificación"], axis=0)
                file["Identificación"] = pd.to_numeric(file["Identificación"])
                return file

            extension = ".xlsx"
            modificarNumeracionFactura = False

        elif tipoArchivo == 2:  # archivo de productos siigo

            def func(file_name):
                file = pd.read_excel(file_name)
                encabezados = file.iloc[5, :]
                file = file.drop(labels=[0, 1, 2, 3, 4, 5, len(file) - 1], axis=0)
                file = file.reset_index(drop=True)
                file.columns = encabezados
                file = file.dropna(subset=["Código"], axis=0)
                file["Nombre"] = file["Nombre"].apply(Utils.prepare_product_name)
                return file

            extension = ".xlsx"
            modificarNumeracionFactura = False

        elif tipoArchivo == 3:  # archivo ventas por producto pirpos

            def func(file_name):
                file = pd.read_html(file_name)[0]
                encabezados = file.iloc[1, :]
                file = file.drop(labels=[0, 1, len(file) - 1], axis=0)
                file.columns = encabezados
                file = file.reset_index(drop=True)
                file["Total"] = file["Total"].str.replace(",", "", regex=True)
                file["Total"] = file["Total"].str.replace(".", "", regex=True)
                file["Total"] = pd.to_numeric(file["Total"], downcast="float") / 100
                file["Cantidad"] = pd.to_numeric(file["Cantidad"], downcast="float")
                file["Producto"] = file["Producto"].apply(Utils.prepare_product_name)
                file["Fecha"] = file["Fecha"].str.replace("a. m.", "AM")
                file["Fecha"] = file["Fecha"].str.replace("p. m.", "PM")
                file["Fecha"] = pd.to_datetime(file["Fecha"], format="%Y-%m-%d %I:%M:%S %p")

                return file

            extension = ".xls"
            time_column = "Fecha"

        else:  # archivo ventas por cliente pirpos

            def func(file_name):
                file = pd.read_html(file_name)[0]
                encabezados = file.iloc[1, :]
                file = file.drop(labels=[0, 1, len(file) - 1], axis=0)
                file.columns = encabezados
                file = file.reset_index(drop=True)
                # self._ventasPCliente = self._ventasPCliente.dropna(how="all")
                file["Total"] = file["Total"].str.replace(",", "", regex=True)
                file["Total"] = file["Total"].str.replace(".", "", regex=True)
                file["Total"] = pd.to_numeric(file["Total"], downcast="float") / 100
                file["Documento"] = file["Documento"].apply(Utils.clean_document)
                file["Fecha de creación"] = file["Fecha de creación"].str.replace("a. m.", "AM")
                file["Fecha de creación"] = file["Fecha de creación"].str.replace("p. m.", "PM")
                file["Fecha de creación"] = pd.to_datetime(
                    file["Fecha de creación"], format="%d-%m-%Y %I:%M:%S %p"
                )

                return file

            extension = ".xls"
            time_column = "Fecha de creación"

        return Utils._pd_from_directory(
            directory,
            extension,
            func,
            modificarNumeracionFactura,
            time_column,
            numeracionInicial,
        )

    @staticmethod
    def _pd_from_directory(
        directory: str,
        file_extension: str,
        parse_instructions: Callable,
        modificarNumeracionFactura=False,
        time_column="",
        numeracionInicial=(0, 0),
    ) -> pd:
        """de los archivos encontrados en el directorio entrega un DatraFrame con la informacion

        Parameters
        ----------
        directory : str
            directorio que se debe revisar
        file_extension : str
            extension de los archivos que se deben leer
        parse_instructions : Callable
            funcion que lee los archivos y entrega pandas

        Returns
        -------
        pd
           objeto Dataframe
        """
        only_files = [join(directory, f) for f in listdir(directory) if isfile(join(directory, f))]
        files = [file_name for file_name in only_files if file_extension in file_name]
        if files:
            data_frames = [parse_instructions(file) for file in files]
            data_frame = pd.concat(data_frames)

            if modificarNumeracionFactura == True:
                data_frame.set_index(
                    time_column,
                    drop=False,
                    append=False,
                    inplace=True,
                    verify_integrity=False,
                )
                data_frame = data_frame.sort_index()
                data_frame = data_frame.reset_index(drop=True)
                data_frame = Utils._cambiarNumeracion(data_frame, numeracionInicial)

            return data_frame
        return None

    @staticmethod
    def _cambiarNumeracion(file: pd, numeracionInicial: Tuple[int, int]) -> pd:
        """
        Verificar que las facturas tengan un valor correcto (orden creciente)

        Parameters
        ----------
        file : pd
            Dataframe pandas con la informacion de las facturas

        numeracionInicial : (int,int)
            tupla con las numeraciones iniciales que se desean para las facturas
            (numeracio_inicial_POS, numeracion_inicial_Elect)

        Returns
        -------
        pd
            Dataframe pandas con la numeracion correcta.

        """

        # revisar como se llama la columna que contiene las facturas
        nombresColumnas = ["Factura No.", "No. Factura"]
        nombreColumna = (
            nombresColumnas[0] if nombresColumnas[0] in file.columns else nombresColumnas[1]
        )

        # definir que es una factura POS
        prefijosPOS = [
            ".",
            "LL",
        ]  ##------------------------------------------------- parametros que se pueden dejar en un yml

        # recorrer cada factura, identificar el tipo de factura y modificar consecutivo si es necesario
        filas = file.shape[0]  # filas por recorrer
        facturaSiguientePos = numeracionInicial[0]  # ajustar numeracion inicial
        facturaSiguienteElectronica = numeracionInicial[1]  # ajustar numeracion inicial

        facturaAnteriorPos = numeracionInicial[0] - 1  # ajustar numeracion inicial
        facturaAnteriorElectronica = numeracionInicial[1] - 1  # ajustar numeracion inicial

        for fila in range(filas):
            facturai = file.loc[fila, nombreColumna]
            prefijo, numeroFactura = Utils._revisarFactura(
                facturai, prefijosPOS
            )  # obtiene tipo y numero de factura

            if prefijo == "LL":
                if numeroFactura != facturaAnteriorPos:
                    facturaAnteriorPos = numeroFactura
                    if numeroFactura < facturaSiguientePos:
                        numeroFactura = facturaSiguientePos  # actualiza numeracion incorrecta POS
                    if numeroFactura > facturaSiguientePos:
                        facturaSiguientePos = numeroFactura
                    facturaSiguientePos += 1  # actualiza factura sigueinte
                file.loc[fila, nombreColumna] = "{0}{1}".format(
                    prefijo, facturaSiguientePos - 1
                )  # actualiza prefijo y numero de factura
            else:
                if numeroFactura != facturaAnteriorElectronica:
                    facturaAnteriorElectronica = numeroFactura
                    if numeroFactura < facturaSiguienteElectronica:
                        numeroFactura = facturaSiguienteElectronica  # actualiza numeracion incorrecta Electronica
                    if numeroFactura > facturaSiguienteElectronica:
                        facturaSiguienteElectronica = numeroFactura
                    facturaSiguienteElectronica += 1  # actualiza factura sigueinte
                file.loc[fila, nombreColumna] = "{0}{1}".format(
                    prefijo, facturaSiguienteElectronica - 1
                )  # actualiza prefijo y numero de factura

        return file  # archio con la numeracion correcta

    @staticmethod
    def revisarDocumentos(
        productos: pd, clientesSiigo: pd, ventasPProducto: pd, ventasPCliente: pd
    ):
        """
        Revisa que los archvios tengan la informacion adecuada

        Parameters
        ----------
        productos:pd
            productos en Siigo
        clientesSiigo:pd
            clientes en siigo
        ventasPCliente : pd
            Ventas por cliente.
        ventasPProducto : pd
            Ventas por producto

        Returns
        -------
        None.

        """
        if abs(ventasPCliente.sum()["Total"] - ventasPProducto.sum()["Total"]) >= 50:
            raise (Exception("Las ventas por productos no coinciden con las ventas por facturas."))

        # unir tablas y verificar que los merge no genenren datos vacíos
        merged_clientes = ventasPCliente.merge(
            clientesSiigo, left_on="Documento", right_on="Identificación", how="left"
        )
        missing_customers = merged_clientes.loc[
            merged_clientes["Identificación"].isna(), ["Cliente", "Documento"]
        ]
        missing_customers = missing_customers.groupby("Cliente").agg(["unique"])
        missing_customers["Cliente"] = missing_customers.index
        missing_customers = missing_customers.reset_index(drop=True)

        merged_productos = ventasPProducto.merge(
            productos, left_on="Producto", right_on="Nombre", how="left"
        )
        missing_products = merged_productos.loc[
            merged_productos["Nombre"].isna(), "Producto"
        ].unique()

        message = ""
        if missing_customers.shape[0] > 0:
            message = message + "\nSiigo no posee los siguientes clientes:\n"
            for index in range(len(missing_customers)):
                name = missing_customers.loc[index, "Cliente"][0]
                document = missing_customers.loc[index, "Documento"][0][0]
                message = message + f"  {name}, documento: {document}\n"
            message = message + "El programa debe crearlos \n"
        if missing_products.shape[0] > 0:
            message = message + "\nError, siigo no posee los siguientes productos:\n"
            for product in missing_products:
                message = message + f"  {product}\n"
            message = message + "Se deben crear manualmente \n"
        print(message)

        return missing_customers, missing_products

    @staticmethod
    def printProgressBar(
        iteration: int,
        total: int,
        prefix: str = "",
        suffix: str = "",
        decimals: int = 1,
        length: int = 40,
        fill: str = "█",
        printEnd: str = "",
    ) -> None:
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + "-" * (length - filledLength)
        print(f"\r{prefix} |{bar}| {percent}% {suffix}", end=printEnd)
        # Print New Line on Complete
        if iteration == total:
            print()

    @staticmethod
    def normalize(s: Optional[str]) -> str:
        """
        Ayuda a remover caracteres que no procesa siigo en las peticiones

        Parameters
        ----------
        s : str
            string que se va a revisar.

        Returns
        -------
        str
            string con caracteres adecuados.

        """
        if type(s) != str:
            return ""
        replacements = (
            ("á", "a"),
            ("é", "e"),
            ("í", "i"),
            ("ó", "o"),
            ("ú", "u"),
            ("ñ", "n"),
        )
        s = s.lower()
        for a, b in replacements:
            s = s.replace(a, b)
        return s

    @staticmethod
    def prepare_product_name(name: str) -> str:
        name = Utils.normalize(name)
        name = name.replace(" ", "")
        return name


def read_pirpos_product(product: Dict) -> List[Dict[str, Union[str, int]]]:
    """Parse downloaded info about a product and return it as a cleaned list of dictionaries
        one product can have many subproducts, in this case only subproducts are returned

    Returns
    -------
    List[Dict[str,Union[str,int]]]

    """

    try:
        if len(product["subProducts"]) == 0:  # just one product

            product_info = {
                "name": product["name"],
                "pirpos_id": product["_id"],
                "price": product["locationsStock"][0][
                    "price"
                ],  # I suppose there is only one location
                "tax_name": product["locationsStock"][0]["tax"]["name"]
                if product["locationsStock"][0]["tax"] != None
                else None,
                "tax_value": product["locationsStock"][0]["tax"]["percentage"]
                if product["locationsStock"][0]["tax"] != None
                else None,
            }
            return [product_info]
        else:
            sub_products = product["subProducts"]
            products_info = []
            for sub_prouct in sub_products:
                product_info = {
                    "name": sub_prouct["name"],
                    "pirpos_id": sub_prouct["_id"],
                    "price": sub_prouct["locationsStock"][0]["price"],
                    "tax_name": product["locationsStock"][0]["tax"]["name"]
                    if product["locationsStock"][0]["tax"] != None
                    else None,
                    "tax_value": product["locationsStock"][0]["tax"]["percentage"]
                    if product["locationsStock"][0]["tax"] != None
                    else None,
                }
                products_info.append(product_info)
            return products_info
    except Exception as e:
        raise ErrorLoadingPirposProducts(f"error parsing Pirpos product \n{e}")


def _revisarFactura(factura: str, prefijosPOS: List[str]) -> Tuple[str, int]:
    """
    Obtiene la numeracion y tipo de factura

    Parameters
    ----------
    factura : str
        string con el numero de factura y el prefijo.
    prefijosPOS: [str,str]
        prefijos asociados a una factura POS, todo lo que no se encuentre aca sera tomado en cuenta como factura electronica

    Returns
    -------
    tuple(str,int)
        tupla con el prefijo y la numeracion separadas
    """

    # identificar tipo de factura
    prefijoIdentificado = None
    if sum([True if prefijo in factura else False for prefijo in prefijosPOS]) > 0:
        prefijoIdentificado = "LL"  # el prefijo es POS ---------------------------------parametro que se puede dejar en un yml
    else:
        prefijoIdentificado = (
            ""  # factura electronica -----------------------------------se puede dejar en un yml
        )

    # se obtiene el numero de la factura
    numero = int("".join([caracter if caracter.isdigit() else "" for caracter in factura]))

    return prefijoIdentificado, numero


def read_invoice_per_product_pirpos(
    invoice_info: Dict, 
    DEFAULT_CLIENT: Dict[str, Union[int, str]],
) -> Dict[str, Union[str, int]]:
    """Parse downloaded info about a invoice_per_product and return it as a cleaned dictionary

    Returns
    -------
    Dict[str,Union[str,int]]

    """
    try:

        prefix, number = _revisarFactura(invoice_info["_id"]["number"], ["LL"])
        invoiceInfo = {
            "number": prefix + str(number),
            "prefix": prefix,
            "seq": number,
            "created": invoice_info["_id"].get("createdOn"),
            "client_name": invoice_info["_id"]["client"]["name"],
            "client_last_name": invoice_info["_id"]["client"].get("lastName",""),
            "client_email": invoice_info["_id"]["client"].get("email"),
            "client_phone": invoice_info["_id"]["client"].get("phone"),
            "client_document": invoice_info["_id"]["client"].get(
                "document", DEFAULT_CLIENT["document"]
            ),
            "product_name": invoice_info["_id"]["name"],
            "product_id": invoice_info["_id"]["_id"],
            "product_quantity": invoice_info["_id"]["quantity"],
            "product_price": invoice_info["_id"]["priceNormal"],
            "seller": invoice_info["_id"]["seller"],
            "table": invoice_info["_id"]["table"],
        }
        return invoiceInfo
    except Exception as e:
        print(e)
        raise ErrorLoadingPirposProducts(f"error parsing Pirpos product \n{e}")


def read_invoice_per_client_pirpos(
    invoice_info: Dict,
    DEFAULT_CLIENT: Dict[str, Union[int, str]],
) -> Dict[str, Union[str, int]]:
    """Parse downloaded info about a invoice_per_client and return it as a cleaned list of dictionaries
        one invoice can have many products, one element is returned for each product

    Returns
    -------
    Dict[str,Union[str,int]]

    """
    try:

        prefix, _ = _revisarFactura(invoice_info["number"], ["LL"])
        invoiceInfo = {
            "number": prefix + str(invoice_info["seq"]),
            "prefix": prefix,
            "seq": invoice_info["seq"],
            "created": invoice_info["paid"].get("createdOn"),
            "client_name": invoice_info["client"]["name"],
            "client_email": invoice_info["client"].get("email"),
            "client_phone": invoice_info["client"].get("phone"),
            "client_document": invoice_info["client"].get(
                "document", DEFAULT_CLIENT["document"]
            ),
            "client_check_digit": invoice_info["client"].get("checkDigit"),
            "client_address": invoice_info["client"].get("address"),
            "client_document_type": invoice_info["client"].get("docuentName"),
            "client_city_name": invoice_info["client"].get("cityDetail", {}).get("cityName"),
            "client_city_code": invoice_info["client"].get("cityDetail", {}).get("cityCode"),
            "client_state_code": invoice_info["client"].get("cityDetail", {}).get("stateCode"),
            "client_country_code": invoice_info["client"].get("cityDetail", {}).get("countryCode"),
            "paid": json.dumps(
                [
                    {"pay_method": subpay["paymentMethod"], "value": subpay["value"]}
                    for subpay in invoice_info.get("paid", {}).get("paymentMethodValue", [{}])
                ]
            ),
            "taxes": json.dumps(
                [
                    {"name": subtax["name"], "value": subtax["value"]}
                    if "name" in subtax and "value" in subtax
                    else [{"name": "I CONSUMO", "value": 0.08}]
                    for subtax in invoice_info.get("taxes", [{}])
                ]
            ),
            "products": json.dumps(
                [
                    {
                        "id": subprod.get("idInternal"),
                        "name": subprod.get("name"),
                        "price": subprod.get("price"),
                        "quantity": subprod.get("quantity"),
                        "tax_name": subprod.get("taxName"),
                        "tax_value": subprod.get("tax"),
                        "discount": subprod.get("discount"),
                    }
                    for subprod in invoice_info.get("products", [])
                ]
            ),
            "total_bruto": invoice_info["totalBruto"],
            "total_discount": invoice_info["totalDiscount"],
            "sub_total": invoice_info["subTotal"],
            "total_base_tax": invoice_info["totalBaseTax"],
            "total_taxes": invoice_info["totalTaxes"],
            "total_paid": invoice_info["totalPaid"],
            "seller": invoice_info["seller"].get("name", "")
        }
        return invoiceInfo
    except Exception as e:
        raise ErrorLoadingPirposProducts(f"error parsing Pirpos product \n{e}")


def read_invoice_per_client_siigo(
    invoice_info: Dict,
) -> Dict[str, Union[str, int]]:
    """Parse downloaded info about a invoice_per_client and return it as a cleaned list of dictionaries
        one invoice can have many products, one element is returned for each product

    Returns
    -------
    List[Dict[str,Union[str,int]]]

    """
    code_2_pirpos_prefix = {"1": "LL", "3": ""}
    try:

        invoiceInfo = {
            "DocNumber": code_2_pirpos_prefix[invoice_info["DocCode"]]
            + str(invoice_info["DocNumber"])
        }
        return invoiceInfo
    except Exception as e:
        raise ErrorLoadingSiigoInvoices(f"error parsing Pirpos product \n{e}")


def clean_document(documentoCliente: str) -> int:
    """
    lee el documento del cliente y lo entrega en tipo entero. Se revisa que la info salga adecuadamente.

    Parameters
    ----------
    documentoCliente : str
        identificacion del cliente en formato string
            ex: 9 0 1 5 4 7 7 5 7 - 3

    Returns
    -------
    int
        entero del documento del cliente
        ex: 901547757.

    """
    if type(documentoCliente) == float or type(documentoCliente) == int:
        if (
            math.isnan(documentoCliente) == True
        ):  # ahora pirpos no pone documento de consumidor final
            documentoCliente = 222222222222

    if type(documentoCliente) == str:
        documentoCliente = documentoCliente.replace(" ", "")
        if "-" in documentoCliente:
            documentoCliente = documentoCliente[: documentoCliente.find("-")]
    if documentoCliente == "":
        documentoCliente = 222222222222
    return int(str(documentoCliente))


def get_missing_clients(pirpos_clients: pd.DataFrame, siigo_clients: pd.DataFrame) -> pd.DataFrame:
    """get missing clients in siigo

    Parameters
    ----------
    pirpos_clients : pd.DataFrame
        registered cients on pirpos
    siigo_clients : pd.DataFrame
        registered clients on siigo

    Returns
    -------
    pd.DataFrame
        pandas Dataframe with missing costumers
    """

    merged_clientes = pirpos_clients.merge(
        siigo_clients, left_on="document", right_on="Identification", how="left"
    )
    missing_clients = pirpos_clients[merged_clientes["Identification"].isna()]
    return missing_clients


def get_missing_products(
    pirpos_products: pd.DataFrame, siigo_products: pd.DataFrame
) -> pd.DataFrame:
    """get missing Products in siigo

    Parameters
    ----------
    pirpos_products : pd.DataFrame
        registered products on pirpos
    siigo_products : pd.DataFrame
        registered products on siigo

    Returns
    -------
    pd.DataFrame
        pandas Dataframe with missing products
    """

    merged_products = pirpos_products.merge(
        siigo_products, left_on="pirpos_id", right_on="Code", how="left"
    )
    missing_products = pirpos_products[merged_products["Code"].isna()]
    return missing_products


def get_missing_invoices(
    pirpos_invoices: pd.DataFrame, siigo_invoices: pd.DataFrame
) -> pd.DataFrame:
    """get missing invoices in siigo

    Parameters
    ----------
    pirpos_invoices: pd.DataFrame
        registered products on pirpos
    siigo_invoices: pd.DataFrame
        registered products on siigo

    Returns
    -------
    pd.DataFrame
        pandas Dataframe with missing invoices
    """

    merged_invoices = pirpos_invoices.merge(
        siigo_invoices, left_on="number", right_on="DocNumber", how="left"
    )
    missing_invoices = merged_invoices[merged_invoices["DocNumber"].isnull()]
    return missing_invoices


def best_sellers(invoices_per_product: pd.DataFrame) -> pd.DataFrame:
    """get best sellers 

    Parameters
    ----------
    invoices_per_product : pd.Dataframe

    Returns
    -------
    pd.DataFrame
    """
    pivot = invoices_per_product.pivot_table(
        index='seller',
        columns='product_name',
        values='product_quantity',
        aggfunc="sum",
        margins=True,
        margins_name='Total',
        fill_value=0
    )

    pivot = pivot.sort_values(by=['Total'], axis=0, ascending=False)
    pivot = pivot.sort_values(by=['Total'], axis=1, ascending=False)
    return pivot.iloc[0:4,1:5]
