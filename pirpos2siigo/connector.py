import datetime
import requests
import json
import pandas as pd
import unidecode
import math
import time
import re
from typing import Optional, Tuple, List
from . import Utils

class Connector():
    def __init__(
        self,
        documents:str="./documents",
        userName:str="industriagastronomicadm@gmail.com", 
        access_key:str="ZDFkZGJkN2YtMWVjZS00MTI5LWI2NjUtMzlmNzk5ZDQyMDJjOiM5KTlfLGlyYlo=",
        numeracionInicial:Tuple[int,int]=(0,0),
        modificarNumeroFactura:bool = True
        ):
        
        #datos del API de siigo
        self._userName = userName
        self._access_key = access_key
        self._access_token = None
        self._updateAccess_token()
        
        #clientes Pirpos
        
        #self._clientesPirPos = Utils.prepararArchivo(f"{documents}/clientes-pirpos/",0,modificarNumeroFactura,numeracionInicial)
        self._clientesSiigo = Utils.prepararArchivo(f"{documents}/clientes-siigo/",1,modificarNumeroFactura,numeracionInicial)
        self._productos = Utils.prepararArchivo(f"{documents}/productos-siigo/",2,modificarNumeroFactura,numeracionInicial)
        self._ventasPProducto = Utils.prepararArchivo(f"{documents}/ventas-por-productos/",3,modificarNumeroFactura,numeracionInicial)
        self._ventasPCliente = Utils.prepararArchivo(f"{documents}/ventas-por-clientes/",4,modificarNumeroFactura,numeracionInicial)
        
        
        #relacion PirPos Siigo
        #formas de pago
        self._formasPago = {'Efectivo':3025, 'Tarjeta débito':3027, 'Tarjeta crédito':3027,'Transferencia bancaria':7300, 'Domicilio':3025, 'Rappi':7325}
        #impuestos
        self._impuestos = {"I CONSUMO (8%)":{"valor":0.08,"id":7081}}
        #tipo Comprobante
        self._tipoComprobante = {"POS":13136, "FE":27233}
        #errores 
        self._errores = False
        
        
        #revision de archivos para eliminar errores 
        missing_customers, missing_products =Utils.revisarDocumentos(self._productos,self._clientesSiigo, self._ventasPProducto,self._ventasPCliente)
        if len(missing_customers)>0:
            self.actualizarClientes(missing_customers)
        if len(missing_products)>0:
            raise Exception("Error, se deben crear productos manualmente")
    
    #temporaly token
    @property    
    def access_token(self):
        return self._access_token
    
    def _updateAccess_token(self):
        """
        Obtiene el token de acceso para usar la API

        Raises
        ------
        Exception
            Error solicitando token, datos incorrectos.

        Returns
        -------
        None.

        """
        url = 'https://api.siigo.com/auth'
        values = {"username": self._userName ,"access_key": self._access_key }
        headers = {'Content-Type': 'application/json'}   
        response = requests.post(url, data=json.dumps(values), headers=headers)
        
        if response.ok == False:
            raise Exception("Error solicitando token, revisar userName y access_key")
        access_token = response.json()["access_token"]
        self._access_token = access_token
        
    #Getters   
    #id and product name
    @property 
    def productos(self):
        return self._productos.copy()
    #invoice id, product name, ammount and taxes
    @property 
    def ventasPProducto(self):
        return self._ventasPProducto.copy()
    #invoice id, client identification, payment method, ammount
    @property 
    def ventasPCliente(self):
        return self._ventasPCliente.copy()
    @property 
    def errores(self):
        return self._errores
    
    
    
    def actualizarClientes(self,missing_customers):
        """
        Actualiza los clientes en siigo mostrando la barra de progreso 
        en el archivo ./errores/errores_clientes.json se guardan los errores

        """

        print("\n###########################\nActualizacion de clientes\n###########################\n")
        #errores Para imprimirlos en txt
        erroresBackUp = {}
        contador_errores = 0
        
        size = len(missing_customers)
        for idx in range(size):
            Utils.printProgressBar(idx+1,size)
            identificacion = int(missing_customers.loc[idx,"Documento"][0][0])
            nombre = missing_customers.loc[idx,"Cliente"][0]
            try:
                result = self.crearCliente(identificacion,nombre)
            except Exception as e:
                contador_errores+=1
                erroresBackUp[contador_errores] = {"nombre_cliente":nombre, "identificacion":identificacion, "error":str(e)}
                self._errores = True
                    
        with open("errores_clientes.json", "w") as json_file:
            json.dump(erroresBackUp, json_file, indent = 6)
        if self._errores == True:
            raise Exception("No se ha creado algun cliente, revisar archivo errores_clientes.json")      
        print("\n###########################\nFin Actualizacion de clientes\n###########################\n")
    
        
    def crearCliente(self,identificacion:int,nombre:str)-> bool:
        """
        Crea la solicitud para hacer un cliente en Siigo

        Parameters
        ----------
        identificacion : int
            nit o cedula de la persona sin codigo de verificacion.
        nombre : str
            nombre de la persona.

        Raises
        ------
        Exception
            No se puede crear la persona.

        Returns
        -------
        bool
            estado de la operación. True= se creó cliente.

        """
        nombre = Utils.normalize(nombre)#elimina caracteres que no procesa siigo
        largo = len(nombre)
        if largo >100:
            nombre = nombre[0:100]
        
        body=  {
                  "type": "Customer",
                  "person_type": "Person",
                  "id_type": "13",
                  "identification": str(identificacion),
                  "check_digit": "4",
                  "name": [nombre,nombre],
                  "commercial_name": "",
                  "branch_office": 0,
                  # "active": "true",
                  # "vat_responsible": false,
                  "fiscal_responsibilities": [
                    {
                      "code": "R-99-PN"
                    }
                  ],
                  "address": {
                    "address": "Cra. 18 #79A - 42",
                    "city": {
                      "country_code": "Co",
                      "state_code": "19",
                      "city_code": "19001"
                    },
                    "postal_code": ""
                  },
                  "phones": [
                    {
                      "indicative": "57",
                      "number": "3006003345",
                      "extension": "132"
                    }
                  ],
                   "contacts": [
                     {
                       "first_name": "null",
                       "last_name": "null",
                       "email": "no-reply@pirpos.com",
                       "phone": {
                         "indicative": "",
                         "number": "3333333333",
                         "extension": ""
                       }
                     }
                   ]
                }   

        headers = {'Content-Type': 'application/json','Authorization': self.access_token }      
        url = "https://api.siigo.com/v1/customers"
        response = requests.post(url, data=str(body), headers=headers)
        
        if response.ok == False:
            if response.json()["Errors"][0]["Code"] == "already_exists":
                return False
            else:
                raise Exception(str(response.json()["Errors"][0]))    
        return True
    
    
    
    def enviarFacturaPrueba(self):
    
        item = []
        itemInfo ={}
        itemInfo["code"]="61d7d3349ab18205d7997fa0"
        itemInfo["description"]="Jugos Hit mango"
        itemInfo["quantity"]= 1
        itemInfo["price"]=3000
        # total_Productos += math.ceil((math.ceil(itemInfo["price"]*itemInfo["quantity"]*100)/100+math.ceil(itemInfo["price"]*itemInfo["quantity"]*0.08*100)/100)*100)/100
        total_Productos = itemInfo["price"]*itemInfo["quantity"]+round(itemInfo["price"]*itemInfo["quantity"]*0.08,2)
        # print("dato1 {0}   dato2  {1}\n".format(itemInfo["price"]*itemInfo["quantity"],itemInfo["price"]*itemInfo["quantity"]*0.08))
        # print("item "+ str(itemInfo["price"]))
        itemInfo["taxes"]=[{"id":7081}]
        item.append(itemInfo)       
        
        body={
              "document": { "id": self._tipoComprobante["POS"]},
              "number": 18,
              "date": "2022-01-01",
              "customer": {"identification": str(222222222222),"branch_office": 0},
              "seller": 709,
              "observations": "Observaciones",
              "items": item,
              "payments": [
                {
                  "id": 3025,
                  "value": total_Productos#,
                  #"due_date": "2021-03-19"
                }
              ]
            }
        headers = {'Content-Type': 'application/json','Authorization': self.access_token,'Connection':'close' }
        url = "https://api.siigo.com/v1/invoices"
        
        response = requests.post(url, data=str(body), headers=headers)
        # print(response.text)
        
    def postInvoice(self,tipoComprobante,fecha,invoiceNumber, identificacion, items, pyment, method):
        
        body={
              "document": { "id": self._tipoComprobante[tipoComprobante]},
              "number":invoiceNumber,
              "date": fecha.strftime("%Y-%m-%d"),
              "customer": {"identification": str(identificacion),"branch_office": 0},
              "seller": 709,
              "observations": "Observaciones",
              "items": items,
              "payments": [
                    {
                      "id": method,
                      "value": pyment,
                      "due_date": (fecha+datetime.timedelta(days=10)).strftime("%Y-%m-%d")# revisar para facturas normales 
                    }],
              "retentions":[{"id":18091}]
            }
        headers = {'Content-Type': 'application/json','Authorization': self.access_token,'Connection':'close' }
        url = "https://api.siigo.com/v1/invoices"
        
        for i in range(30):
            
            response = requests.post(url, data=str(body), headers=headers)
            
            # print(body)
            if response.ok == False:
                if response.json()["Errors"][0]["Code"] == "already_exists":
                    print(response.json()["Errors"][0]["Message"])
                    return False #no se puede crear porque ya existe
                
                elif response.json()["Errors"][0]["Code"] == "duplicated_document":
                    #para relizar otra peticion y ayudar al sistema
                    self.enviarFacturaPrueba()
                    print("duplicated_document error. try to send it again")
                    time.sleep(0.8)
                    if i <29:
                        continue
                    else:
                        print(response.text)
                        info = str(response.json()["Errors"])
                        raise Exception(info)
                elif response.json()["Errors"][0]["Code"] == "invalid_total_payments":
                    #el mensaje indica el valor que debe ser pagado
                    text = response.json()["Errors"][0]["Message"]
                    print(text)
                    pyment = [int(s) for s in re.findall(r'\b\d+\b', text)][0]
                    print("Se ajusta el valor a pagar de {0} a {1}".format(body["payments"][0]["value"],pyment))
                    body["payments"][0]["value"] = pyment
                    continue
                    
                else:
                    print(response.text)
                    info = str(response.json()["Errors"][0]["Code"])
                    raise Exception(info)
            return True#se crea exitosamente
        
    def enviarFacturas(self, facturas_escogidas:Optional[List[str]] = None, start_at:Optional[str]=None):
        """create readed invoices. You can use facturas_escogidas to send a group of invoices instead to send all them.\n
           If you whan continue the creation from a specific invoice use start_at with the invoice number. 

        Parameters
        ----------
        facturas_escogidas : Optional[List[str]] = None
            list of invoice numbers that must be created. If None is passed so all readed invoiced will be created 
        start_at : Optional[str] = None
            reference invoice to start to create them. Useful if the process crashes and you don't want to begin the creation from the first invoice 
        
        """
        
        print("\n###########################\nEnvio Masivo de facturas\n###########################\n")
        #concat dataframes with left join 
        join1= self.ventasPProducto.merge(self.productos, left_on='Producto', right_on='Nombre', how='left')
        join2 = pd.merge(join1,self.ventasPCliente,left_on='No. Factura', right_on='Factura No.', how='right')
        
        #numeros de facturas .
        
        facturas = join2["No. Factura"].unique()
        if facturas_escogidas != None:
            facturas = facturas_escogidas
        if facturas_escogidas == None and start_at != None:
            mask = join2["No. Factura"] == start_at
            index = join2["No. Factura"].index[mask].tolist()
            facturas = join2.loc[index[0]:,"No. Factura"].unique()
        #revisa cada factura
        
        erroresBackUp = {}
        contador_errores = 0
        size = len(facturas)
        for factura in facturas:
            
            #selecciona todos los datos asociados a esa factura 
            mask = join2["No. Factura"] == factura
            #revisa si es factura POS o Electronica
            prefijoIdentificado, numeroFactura = Utils._revisarFactura(factura,[".","LL"])# dejar estas variables globales en todo el programa ###########
            tipoComprobante = "POS" if prefijoIdentificado=="LL" else "FE"
           
            
            #de todo el dataframe obtiene solo los datos de la factura de interes
            datosFacturai = join2[mask]
            #reinicia index de las filas
            datosFacturai = datosFacturai.reset_index(drop=True)
            
            #fecha de la factura
            fecha = datosFacturai.loc[0,"Fecha"]
            
            #obtiene informacion del cliente
            documentoCliente = int(datosFacturai.loc[0,"Documento"])
            # print(type(documentoCliente))
            
            #obtiene los items de la factura
            items=[]
            total_Productos = 0
            for i in range(len(datosFacturai)):
                itemInfo ={}
                itemInfo["code"]=datosFacturai.loc[i,"Código_y"]
                itemInfo["description"]=unidecode.unidecode(datosFacturai.loc[i,"Producto"])
                itemInfo["quantity"]=datosFacturai.loc[i,"Cantidad"]
                
                if str(itemInfo["code"]) == "nan":
                    print(itemInfo["description"])
                    
                
                if itemInfo["code"] != "61f18fa3290b5f169086d712":
                    #se fija el impuesto del 8% porque siempre es comida 
                    itemInfo["price"]=round(datosFacturai.loc[i,"Total_x"]/(datosFacturai.loc[i,"Cantidad"]*1.08),2)
                    
                    valorBase = round(itemInfo["price"]*itemInfo["quantity"],2)
                    impuesto = round(valorBase*0.08,2)
                    valorItem = round(valorBase + impuesto,2)
                    total_Productos += valorItem
                    # total_Productos += round(itemInfo["price"]*itemInfo["quantity"]+itemInfo["price"]*itemInfo["quantity"]*0.08,2)
                    
                    # total_Productos += round(itemInfo["price"]*itemInfo["quantity"],2)+round(itemInfo["price"]*itemInfo["quantity"]*0.08,2)
                    
                    
                    # print("valorUnitario = {0}, cantidad = {1}".format(itemInfo["price"],itemInfo["quantity"],valorBase,impuesto,valorItem))
                    # print("valorBase = {0} => {1}".format(itemInfo["price"]*itemInfo["quantity"], valorBase))
                    # print("impuesto = {0} => {1}".format(valorBase*0.08, impuesto))
                    # print("totalItem = {0} => {1}".format(valorBase+impuesto, valorItem))
                    # print("\n")
                    itemInfo["taxes"]=[{"id":7081}]
                else:
                    #se fija el impuesto del 8% porque siempre es comida 
                    itemInfo["price"]=round(datosFacturai.loc[i,"Total_x"]/(datosFacturai.loc[i,"Cantidad"]),2)
                    total_Productos += itemInfo["price"]*itemInfo["quantity"]
                    itemInfo["taxes"]=[]
                    print("entra")
                
                #agrega item a la lista 
                items.append(itemInfo)
            
            #datos del pago 
            formaPago =  self._formasPago[datosFacturai.loc[0,"Forma de Pago"]]
            #totalPagado = total_Productos+math.floor(int(100*total_Productos*0.08))/100
            #totalPagado = datosFacturai.loc[i,"Total_y"]
            #totalPagado = 4999.99
            
            # print(totalPagado)
            # print(round(total_Productos))
            totalPagado = round(total_Productos)
            # print(totalPagado)
            # totalPagado = 47001
            # print(totalPagado)
            #se envia factura 
            try:
                result = self.postInvoice(tipoComprobante,fecha,numeroFactura, documentoCliente, items, totalPagado, formaPago)
                if result == True:
                    print("factura {0} {1} creada\n".format(tipoComprobante,numeroFactura ))
                else:
                    print("factura {0} {1} ya existe\n".format(tipoComprobante,numeroFactura))
                          
            except Exception as e:
                print("\nError en factura {0} {1}\n".format(tipoComprobante, numeroFactura))
                print(e)
                print()
                contador_errores+=1
                erroresBackUp[contador_errores] = {
                    "numero factura":numeroFactura,
                    "prefijo": prefijoIdentificado,
                    "error":str(e)}
                    
        with open("errores_facturas.json", "w") as json_file:
            json.dump(erroresBackUp, json_file, indent = 6)
        print("\n###########################\nFin Envio Masivo de facturas\n###########################\n")



