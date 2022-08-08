import pandas as pd
import math
from os import listdir
from os.path import isfile, join
from typing import Callable, List, Tuple


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
                file["Fecha"] = pd.to_datetime(
                    file["Fecha"], format="%Y-%m-%d %I:%M:%S %p"
                )

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
                file["Fecha de creación"] = file["Fecha de creación"].str.replace(
                    "a. m.", "AM"
                )
                file["Fecha de creación"] = file["Fecha de creación"].str.replace(
                    "p. m.", "PM"
                )
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
        only_files = [
            join(directory, f) for f in listdir(directory) if isfile(join(directory, f))
        ]
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
            nombresColumnas[0]
            if nombresColumnas[0] in file.columns
            else nombresColumnas[1]
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
        facturaAnteriorElectronica = (
            numeracionInicial[1] - 1
        )  # ajustar numeracion inicial

        for fila in range(filas):
            facturai = file.loc[fila, nombreColumna]
            prefijo, numeroFactura = Utils._revisarFactura(
                facturai, prefijosPOS
            )  # obtiene tipo y numero de factura

            if prefijo == "LL":
                if numeroFactura != facturaAnteriorPos:
                    facturaAnteriorPos = numeroFactura
                    if numeroFactura < facturaSiguientePos:
                        numeroFactura = (
                            facturaSiguientePos  # actualiza numeracion incorrecta POS
                        )
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

    def _revisarFactura(factura: str, prefijosPOS: Tuple[str, str]) -> Tuple[str, int]:
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
            prefijoIdentificado = ""  # factura electronica -----------------------------------se puede dejar en un yml

        # se obtiene el numero de la factura
        numero = int(
            "".join([caracter if caracter.isdigit() else "" for caracter in factura])
        )

        return prefijoIdentificado, numero

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
            raise (
                Exception(
                    "Las ventas por productos no coinciden con las ventas por facturas."
                )
            )

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
        iteration,
        total,
        prefix="",
        suffix="",
        decimals=1,
        length=40,
        fill="█",
        printEnd="",
    ):
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
        percent = ("{0:." + str(decimals) + "f}").format(
            100 * (iteration / float(total))
        )
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + "-" * (length - filledLength)
        print(f"\r{prefix} |{bar}| {percent}% {suffix}", end=printEnd)
        # Print New Line on Complete
        if iteration == total:
            print()

    @staticmethod
    def normalize(s: str) -> str:
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

    @staticmethod
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

        return int(documentoCliente)
