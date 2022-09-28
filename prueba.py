from datetime import datetime
import pandas as pd
from pirpos2siigo import Connector, pivot_invoices_per_product
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)


init_day = datetime.strptime(
    "2022-10-01",
    "%Y-%m-%d"
)
end_day = datetime.strptime(
    "2022-10-30",
    "%Y-%m-%d"
)
# instanciar objeto
connector = Connector(configuration_path="configuration.JSON")
# connector.update_invoices("2022-08-01", "2022-08-31")

# _, invoices = connector._load_pirpos_invoices_per_client(init_day, end_day, 5)
_, invoices2 = connector._load_pirpos_invoices_per_product(init_day, end_day, 5)


# best sellers per product

best = pivot_invoices_per_product(invoices2)
q = 1+1
pass

# hacer que haga intentos y retome los errores del json
