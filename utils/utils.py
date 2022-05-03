import pandas as pd
import time 
class utils():
    
    @staticmethod
    def prepararArchivo(file:pd,tipoArchivo:int)->pd: 
        """
        Prepara los archivos para que puedan leerse adecuadamente

        Parameters
        ----------
        file : pd
            archivo cargado con pandas.
        tipoArchivo : int
            tipo de documento recibido 
            1=archivo de productos (read_excel)
            2=archivo de clientes (read_html)
            3=archivo de ventas por producto (read_html)
            4=archivo de ventas por cliente (read_html)

        Returns
        -------
        pd
            retorna el archivo preparado para su lectura.

        """
        
        if tipoArchivo == 0:#archivo de productos
            file["Nombre"] = file["Nombre"].str.lower()
            
        elif tipoArchivo == 1:#archivo de clientes PirPos
            encabezados = file.iloc[0,:]
            file = file.drop(labels=[0],axis=0)
            file.columns = encabezados
            file = file.reset_index(drop=True)
            
        elif tipoArchivo == 2:#archivo ventas por producto
            encabezados = file.iloc[1,:]
            file = file.drop(labels=[0,1,len(file)-1],axis=0)
            file.columns = encabezados
            file = file.reset_index(drop=True)
            file["Total"] = file["Total"].str.replace(',','',regex=True)
            file["Total"] = file["Total"].str.replace('.','',regex=True)
            file["Total"] = pd.to_numeric(file["Total"], downcast="float")/100
            file["Cantidad"] = pd.to_numeric(file["Cantidad"], downcast="float")
            file["Producto"] = file["Producto"].str.lower()
            
        elif tipoArchivo == 3:#archivo ventas por cliente
            encabezados = file.iloc[1,:]
            file = file.drop(labels=[0,1,len(file)-1],axis=0)
            file.columns = encabezados
            file = file.reset_index(drop=True)
            # self._ventasPCliente = self._ventasPCliente.dropna(how="all")
            file["Total"] = file["Total"].str.replace(',','',regex=True)
            file["Total"] = file["Total"].str.replace('.','',regex=True)
            file["Total"] = pd.to_numeric(file["Total"], downcast="float")/100
        else: #archivo clientes Siigo
            encabezados = file.iloc[5,:]
            file = file.drop(labels=[0,1,2,3,4,5,len(file)-1],axis=0)
            file = file.reset_index(drop=True)
            file.columns = encabezados
            file = file.dropna(subset=['Identificación'],axis=0)
            file["Identificación"] = pd.to_numeric(file["Identificación"])
            
        return file

    @staticmethod
    def revisarVentas(ventasPCliente:pd,ventasPProducto:pd):
        """
        Revisa que los archvios de venta por productos concuerde con el de ventas por cliente

        Parameters
        ----------
        ventasPCliente : pd
            Ventas por cliente.
        ventasPProducto : pd
            Ventas por producto

        Returns
        -------
        None.

        """
        if ventasPCliente.sum()["Total"]!= ventasPProducto.sum()["Total"]:
            raise(Exception("Las ventas por productos no coinciden con las ventas por facturas."))
            
    @staticmethod
    def printProgressBar (iteration, total, prefix = '', suffix = "", decimals = 1, length = 40, fill = '█', printEnd = ""):
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
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
        # Print New Line on Complete
        if iteration == total: 
            print()
    
    @staticmethod
    def normalize(s:str)->str:
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
        for a, b in replacements:
            s = s.replace(a, b).replace(a.upper(), b.upper())
        return s    

