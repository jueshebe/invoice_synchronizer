import requests
import json
import pandas as pd
import unidecode
import math
import time
import re
from utils.utils import utils

class Siigo():
    def __init__(self,userName="industriagastronomicadm@gmail.com", access_key="ZDFkZGJkN2YtMWVjZS00MTI5LWI2NjUtMzlmNzk5ZDQyMDJjOiM5KTlfLGlyYlo="):
        
        #datos del API de siigo
        self._userName = userName
        self._access_key = access_key
        self._access_token = None
        # self._updateAccess_token()
        
        #datos
        modificarNumeroFactura = True
        numeracionInicial = (16259,0)
        #productos
        self._productos = utils.prepararArchivo(pd.read_excel("./archivos/Listado de productos _ Servicios.xlsx"),0,modificarNumeroFactura,numeracionInicial)
        
        #clientes Pirpos
        self._clientesPirPos = utils.prepararArchivo(pd.read_html("./archivos/clientes.xls")[0],1,modificarNumeroFactura,numeracionInicial)
        
        #ventas por producto
        self._ventasPProducto = utils.prepararArchivo(pd.read_html("./archivos/reporte-productos.xls")[0],2,modificarNumeroFactura,numeracionInicial)
        
        #ventas por cliente
        self._ventasPCliente = utils.prepararArchivo(pd.read_html("./archivos/reporte-facturas.xls")[0],3,modificarNumeroFactura,numeracionInicial)
        
        #ventas por cliente Siigo
        self._clientesSiigo = utils.prepararArchivo(pd.read_excel("./archivos/Clientes.xlsx"),4,modificarNumeroFactura,numeracionInicial)
        
        #relacion PirPos Siigo
        #formas de pago
        #revisar domicilio, no esta creada
        self._formasPago = {'Efectivo':3025, 'Tarjeta débito':3027, 'Tarjeta crédito':3027,'Transferencia bancaria':7300, 'Domicilio':3025, 'Rappi':7325}
        #impuestos
        self._impuestos = {"I CONSUMO (8%)":{"valor":0.08,"id":7081}}
        #tipo Comprobante
        self._tipoComprobante = {"POS":13136, "FE":27233}
        #errores 
        self._errores = False
        
        
        #revision de archivos para eliminar errores 
        self.a,self.b=utils.revisarDocumentos(self._productos,self._clientesSiigo, self._ventasPProducto,self._ventasPCliente)
        
        
    
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
    #client id, client information
    @property 
    def clientesPirPos(self):
        return self._clientesPirPos.copy()
    @property 
    def errores(self):
        return self._errores
    
    
    
    def actualizarClientes(self):
        """
        Actualiza los clientes en siigo mostrando la barra de progeso 
        en el archivo ./errores/errores_clientes.json se guardan los errores

        """
        
        
        print("\n###########################\nActualizacion de clientes\n###########################\n")
        #errores Para imprimirlos en txt
        erroresBackUp = {}
        contador_errores = 0
        
        #obtener clientes de siigo
        clientesRegistradosSiigo = self._clientesSiigo
        identificacionesSiigo = clientesRegistradosSiigo.iloc[:,0]
        #itera en todos los clientes de PirPos
        size = len(self._clientesPirPos)
        for idx in range(size):
            utils.printProgressBar(idx,size-1)
            identificacion = self._clientesPirPos.loc[idx,"Documento"]
            nombre = self._clientesPirPos.loc[idx,"Nombre"]
            
            try:       
                identificacion =utils.clean_document(identificacion)
            except:
                contador_errores+=1
                erroresBackUp[contador_errores] = {"nombre_cliente":nombre, "identificacion":identificacion, "fila":  idx+2, "error":"falla al convertir a entero"}
                self._errores = True
                continue
            
            if (identificacion in identificacionesSiigo.values) == False:
                #se crea cliente
                try:
                    result = self.crearCliente(identificacion,nombre)
                except Exception as e:
                    contador_errores+=1
                    erroresBackUp[contador_errores] = {"nombre_cliente":nombre, "identificacion":identificacion, "fila":  idx+2, "error":str(e)}
                    self._errores = True
                    
        with open("./errores/errores_clientes.json", "w") as json_file:
            json.dump(erroresBackUp, json_file, indent = 6)
                
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
        #revisar que el cliente tenga datos en la columna documento
        nombre = utils.normalize(nombre)#elimina caracteres que no procesa siigo
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
        #se fija el impuesto del 8% porque siempre es comida 
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
              "date": fecha,
              "customer": {"identification": str(identificacion),"branch_office": 0},
              "seller": 709,
              "observations": "Observaciones",
              "items": items,
              "payments": [
                    {
                      "id": method,
                      "value": pyment#,
                      #"due_date": "2021-03-19"
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
                        info = "factura {0} {1} genera error: ".format(tipoComprobante,invoiceNumber ) + response.json()["Errors"][0]["Code"]
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
                    info = "factura {0} {1} genera error: ".format(tipoComprobante,invoiceNumber ) + response.json()["Errors"][0]["Code"]
                    raise Exception(info)
            return True#se crea exitosamente
        
    def enviarFacturas(self, posicionInicio=0, filasEscogidas=None):
        # el nombre lo pueden cambiar en cualquier momento y no se relacionanran bien los id con los productos
        #se plantea por ahora agregar el id al codigo del producto
        #el signo - puede salir en documento, eliminarlo 
        #cuando no se encuentre producto se podria crear y enviarlo 
        #si el nombre tiene un espacio al inicio falla. es mejor poner solo codigos
        #permitir que retome las facturas con error!!
        
        print("\n###########################\nEnvio Masivo de facturas\n###########################\n")
        #concat dataframes with left join 
        join1= self.ventasPProducto.merge(self.productos, left_on='Producto', right_on='Nombre', how='left')
        join2 = pd.merge(join1,self.ventasPCliente,left_on='No. Factura', right_on='Factura No.', how='right')
        
        #numeros de facturas .
        
        facturas = join2["No. Factura"].unique()
        if filasEscogidas != None:
            facturasEscogidas = []
            for i in filasEscogidas:
                facturasEscogidas.append(facturas[i])
            facturas = facturasEscogidas
        #revisa cada factura
        
        erroresBackUp = ['errores enviando Facturas:']
        size = len(facturas)
        for fila in range(posicionInicio,size):
            
            # self.printProgressBar(fila,size-1)
            # time.sleep(0.5)
            facturai = facturas[fila]
            #selecciona todos los datos asociados a esa factura 
            mask = join2["No. Factura"] == facturai
            #revisa si es factura POS o Electronica
            tipoComprobante = None
            prefijoIdentificado, numeroFactura = utils._revisarFactura(facturai,[".","LL"])# dejar estas variables globales en todo el programa ###########
            tipoComprobante = "POS" if prefijoIdentificado=="LL" else "FE"
           
            
            #de todo el dataframe obtiene solo los datos de la factura de interes
            datosFacturai = join2[mask]
            #reinicia index de las filas
            datosFacturai = datosFacturai.reset_index(drop=True)
            
            #fecha de la factura
            fecha = datosFacturai.loc[0,"Fecha"][0:10]
            
            #obtiene informacion del cliente
            documentoCliente = datosFacturai.loc[0,"Documento"]
            # print(type(documentoCliente))
            try:
                documentoCliente = utils.clean_document(documentoCliente)
                    
            except:
                print("fila {0} factura {1} {2} genera problema por documento de cliente".format(fila, tipoComprobante,numeroFactura ))
                erroresBackUp.append("\nfila {0} factura {1} {2} genera problema por documento de cliente\n".format(fila, tipoComprobante,numeroFactura ))
                continue
            #obtiene los items de la factura
            items=[]
            total_Productos = 0
            for i in range(len(datosFacturai)):
                itemInfo ={}
                itemInfo["code"]=datosFacturai.loc[i,"Id"]
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
                    print("fila {0} factura {1} {2} creada\n".format(fila,tipoComprobante,numeroFactura ))
                else:
                    print("fila {0} factura {1} {2} ya existe\n".format(fila, tipoComprobante,numeroFactura))
                          
            except Exception as e:
                print("\nError en fila {0}\n".format(fila))
                print(e)
                print()
                erroresBackUp.append("\nError en fila {0}\n".format(fila)+str(e))
            # break   
        with open("errores facturas.txt", "w") as txt_file:
            for line in erroresBackUp:
                txt_file.write(line + "\n") 
        
        print("\n###########################\nFin Envio Masivo de facturas\n###########################\n")



if __name__ == "__main__":
     
    ##tareas
    ## crear json de errores para crear facturas como se hizo para la creacion de clientes
    #crear yml para cargar datos de configuracion como prefijos, token, usuario, numeraciones iniciales etc. 
    #modificar fucnion de crear facturas para que pueda cargar el json de errores y volver a intentar a crear las facturas automaticamnete. 
    #hacer que se imprima la barra de progreso apra la creacion de clientes 
    
    #create the connector
    siigoConnector = Siigo()
    
    # siigoConnector.actualizarClientes()
    
    #agregar codigo para verificar si todos los productos existen antes de enviarlos 
    #revisar que las uniones no dejen datos importantes en none 
    #mejorar print de las facturas creadas 
    #mejorar el reenvio de facturas con errores (posiblemente se debe cambiar como se imprima el error en el .txt)
    # siigoConnector.enviarFacturas()
    #809
    # siigoConnector.enviarFacturas(0)
    # siigoConnector.enviarFacturas(0,[3170,3425,3426,3427,3428,3731,3733])
   
    #700
    
    # inpt = input("Desea actualizar clientes? si/no: ")
    
    # # clients update  
    # if inpt == "si":
        # siigoConnector.actualizarClientes()
    
    # inpt = input("Desea actualizar facturas? si/no: ")
    # if inpt == "si": 
    #     inpt = input("Si conoce alguna posicion de inicio marquela, de lo contrario oprima enter: ")
    #     inicio = 0
    #     if inpt != "":
    #         inicio = int(inpt)
            
    #     if siigoConnector.errores == True:
    #         inpt = input("Hay errores actualizando clientes, desea continuar? si/no: ")
    #         if inpt =="si":
    #             #actualizacion de facturas 
    #             siigoConnector.enviarFacturas(inicio)
    #     else:
    #         siigoConnector.enviarFacturas(inicio)
    # print("Fin del programa")

