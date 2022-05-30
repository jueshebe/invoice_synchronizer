import pandas as pd
import re
import math
class utils():
    
    @staticmethod
    def prepararArchivo(file:pd, tipoArchivo:int, modificarNumeroFactura:bool=False, numeracionInicial:(int,int)=(0,0))->pd: 
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
        modificarNumeroFactura: bool
            Modificar la numeracion de las facturas en orden creciente. 
        numeracionInicial: (int,int)
            numeracion que debe seguir la primer factura POS y electronica
            
        Returns
        ----------
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
            file = utils._cambiarNumeracion(file,numeracionInicial)
            
        elif tipoArchivo == 3:#archivo ventas por cliente
            encabezados = file.iloc[1,:]
            file = file.drop(labels=[0,1,len(file)-1],axis=0)
            file.columns = encabezados
            file = file.reset_index(drop=True)
            # self._ventasPCliente = self._ventasPCliente.dropna(how="all")
            file["Total"] = file["Total"].str.replace(',','',regex=True)
            file["Total"] = file["Total"].str.replace('.','',regex=True)
            file["Total"] = pd.to_numeric(file["Total"], downcast="float")/100
            file = utils._cambiarNumeracion(file,numeracionInicial)
            
        else: #archivo clientes Siigo
            encabezados = file.iloc[5,:]
            file = file.drop(labels=[0,1,2,3,4,5,len(file)-1],axis=0)
            file = file.reset_index(drop=True)
            file.columns = encabezados
            file = file.dropna(subset=['Identificación'],axis=0)
            file["Identificación"] = pd.to_numeric(file["Identificación"])
            
        return file
    
    
    @staticmethod
    def _cambiarNumeracion(file:pd, numeracionInicial:(int,int))->pd:
        """
        Verificar que las facturas tengan un valor correcto (orden creciente)

        Parameters
        ----------
        file : pd
            Dataframe pandas con la informacion de las facturas 
            
        numeracionInicial : (int,int)
            tupla con las numeraciones iniciales que se desean para las facturas 
        
        Returns
        -------
        pd
            Dataframe pandas con la numeracion correcta.

        """
        
        #revisar como se llama la columna que contiene las facturas 
        nombresColumnas = ["Factura No.","No. Factura"]
        nombreColumna = nombresColumnas[0] if nombresColumnas[0] in file.columns else nombresColumnas[1]
        
        #definir que es una factura POS 
        prefijosPOS = [".","LL"]## esto puede que se tenga que dejar dinamico ------------!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        
        
        #recorrer cada factura, identificar el tipo de factura y modificar consecutivo si es necesario 
        filas = file.shape[0]#filas por recorrer
        facturaSiguientePos = numeracionInicial[0]#ajustar numeracion inicial
        facturaSiguienteElectronica = numeracionInicial[1]#ajustar numeracion inicial
        
        facturaAnteriorPos = numeracionInicial[0]-1#ajustar numeracion inicial
        facturaAnteriorElectronica = numeracionInicial[1]-1#ajustar numeracion inicial
        
        for i in range(filas):
           facturai = file.loc[i,nombreColumna]  
           prefijo,numeroFactura = utils._revisarFactura(facturai,prefijosPOS)#obtiene tipo y numero de factura
           
           if prefijo == "LL":
               if numeroFactura != facturaAnteriorPos:
                   facturaAnteriorPos = numeroFactura
                   if numeroFactura < facturaSiguientePos:
                       numeroFactura = facturaSiguientePos#actualiza numeracion incorrecta POS
                   if numeroFactura > facturaSiguientePos:
                       facturaSiguientePos = numeroFactura
                   facturaSiguientePos+=1 #actualiza factura sigueinte                   
               file.loc[i,nombreColumna] = "{0}{1}".format(prefijo,facturaSiguientePos-1)#actualiza prefijo y numero de factura 
           else:
               if numeroFactura != facturaAnteriorElectronica:
                   facturaAnteriorElectronica = numeroFactura
                   # print("entra")
                   # print(facturaSiguientePos)
                   # print(numeroFactura)
                   if numeroFactura < facturaSiguienteElectronica:
                       numeroFactura = facturaSiguienteElectronica#actualiza numeracion incorrecta Electronica
                   if numeroFactura > facturaSiguienteElectronica:
                       facturaSiguienteElectronica = numeroFactura
                   facturaSiguienteElectronica+=1 #actualiza factura sigueinte
               file.loc[i,nombreColumna] = "{0}{1}".format(prefijo,facturaSiguienteElectronica-1)#actualiza prefijo y numero de factura 
                   
           
        return file #archio con la numeracion correcta 
           
    def _revisarFactura(factura:str, prefijosPOS:[str,str])->(str,int):
        """
        Obtiene la numeracion y tipo de factura

        Parameters
        ----------
        factura : str
            string con el numero de factura y el prefijo.

        Returns
        -------
        tuple(str,int)
            tupla con el prefijo y la numeracion separadas
        """
        
        #identificar tipo de factura 
        prefijoIdentificado = None
        if  sum([True if prefijo in factura else False for prefijo in prefijosPOS]) >0:
            prefijoIdentificado = "LL"#el prefijo es POS
        else:
            prefijoIdentificado = "" #factura electronica 
        
        #se obtiene el numero de la factura 
        numero = int("".join([caracter if caracter.isdigit() else "" for caracter in factura]))
        
        return prefijoIdentificado, numero
        

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
    
    @staticmethod
    def clean_document(documentoCliente:str)->int:
                       
        if type(documentoCliente)== float or type(documentoCliente)== int:
            if math.isnan(documentoCliente) == True: # ahora pirpos no pone documento de consumidor final
                documentoCliente = 222222222222	
        
        if type(documentoCliente) == str:
            documentoCliente = documentoCliente.replace(" ","")
            if "-" in documentoCliente:
                documentoCliente = int(documentoCliente[:documentoCliente.find("-")])
        return documentoCliente
