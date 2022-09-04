from sqlite3 import connect
from pirpos2siigo import Connector
from pirpos2siigo import utils
import numpy as np
import pandas as pd

# instanciar objeto
connector = Connector(configuration_path="configuration.JSON")


connector.update_invoices("2022-08-01", "2022-08-31")
pass

# hacer que haga intentos y retome los errores del json

