
from pirpos2siigo import Connector
from pirpos2siigo import utils
import numpy as np
import pandas as pd
#instanciar objeto 
connector = Connector()

#connector.enviarFacturas()
#connector.enviarFacturas(start_at="LL24746")
#connector.enviarFacturas(
#    facturas_escogidas=[
#        "LL26179",
#        "LL27091",
#        "LL29309",
#        "LL29599",
#        "LL29966",
#    ]
#)

#cuando no se encuentre producto se podria crear y enviarlo 
#hacer que haga intentos y retome los errores del json 
#hacer que los archivos se descarguen automaticamente


pivot = connector.ventasPProducto.groupby(["Vendedor","Producto"]).count()
pivot = pd.pivot_table(connector.ventasPProducto,index='Producto',columns='Vendedor',values='Cantidad',aggfunc="sum")
pivot = pivot.fillna(0)
pivot.to_excel("pivoteo.xlsx")