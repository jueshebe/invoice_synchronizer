import pandas as pd 
from pirpos2siigo import Connector, best_sellers
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
# instanciar objeto
connector = Connector(configuration_path="configuration.JSON")
# connector.update_invoices("2022-08-01", "2022-08-31")

# _, invoices = connector._load_pirpos_invoices_per_client("2022-08-01", "2022-08-31", 5)
_, invoices2 = connector._load_pirpos_invoices_per_product("2022-08-01", "2022-08-31", 5)

# best sellers per product
best = best_sellers(invoices2)
q = 1+1 
pass

# hacer que haga intentos y retome los errores del json
