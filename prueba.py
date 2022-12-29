"""Tests for pirpos2siigo connector."""
from datetime import datetime
import pandas as pd
# from pirpos2siigo.utils.utils import sold_units_per_months
from pirpos2siigo import Connector, pivot_invoices_per_product

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)


init_day = datetime.strptime(
    "2022-09-01",
    "%Y-%m-%d"
)
end_day = datetime.strptime(
    "2022-09-30",
    "%Y-%m-%d"
)
# instanciar objeto
connector = Connector(configuration_path="configuration.JSON")
#connector.actualizarClientes()# revisar siigo proveedores como clientes 

#connector.update_invoices(init_day, end_day)

# _, invoices = connector._load_pirpos_invoices_per_client(init_day, end_day, 5)
# _, invoices2 = connector._load_pirpos_invoices_per_product(init_day, end_day, 5)


# best sellers per product

# best = pivot_invoices_per_product(invoices2)
# quantity, total = connector.get_history_sold_units(["2022-04", "2022-05", "2022-06"])
# quantity.to_excel("quantity.xlsx")
# total.to_excel("total.xlsx")
#q = 1+1


pass

# hacer que haga intentos y retome los errores del json
