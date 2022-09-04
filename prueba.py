from sqlite3 import connect
from pirpos2siigo import Connector
from pirpos2siigo import utils
import numpy as np
import pandas as pd

# instanciar objeto
connector = Connector(configuration_path="configuration.JSON")

# pirpos_clients = connector._load_pirpos_clients()
# pirpos_clients = connector._load_siigo_clients()
# pirpos_products = connector._load_pirpos_products()
# siigo_products = connector._Connector__load_siigo_products()

# pirpos_invoices_per_product = connector._Connector__load_pirpos_invoices_per_product("2022-07-01","2022-07-31",31)

#     "2022-07-01", "2022-07-02"
# )
# connector.actualizarClientes()
# connector.updateProducts()
connector.update_invoices("2022-08-01", "2022-08-31")
pass


# connector.enviarFacturas(start_at="LL24746")
# connector.enviarFacturas(
#    facturas_escogidas=[
#        "LL26179",
#        "LL27091",
#        "LL29309",
#        "LL29599",
#        "LL29966",
#    ]
# )

# cuando no se encuentre producto se podria crear y enviarlo
# hacer que haga intentos y retome los errores del json
# hacer que los archivos se descarguen automaticamente


# pivot = connector.ventasPProducto.groupby(["Vendedor","Producto"]).count()
# pivot = pd.pivot_table(connector.ventasPProducto,index='Producto',columns='Vendedor',values='Cantidad',aggfunc="sum")
# pivot = pivot.fillna(0)
# pivot.to_excel("pivoteo.xlsx")


##tareas los terceros no son clientes. para siigo no se descarga actualmente todos los clientes y la comparacion no queda bien para missin clients
