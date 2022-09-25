from pirpos2siigo import Connector

# instanciar objeto
connector = Connector(configuration_path="configuration.JSON")
connector.update_invoices("2022-08-01", "2022-08-31")

pass

# hacer que haga intentos y retome los errores del json
