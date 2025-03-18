"""End modules."""
__version__ = "0.1.2"

import sys
import os
import logging
from datetime import datetime
import pandas as pd
from pirpos2siigo.clients import PirposConnector, SiigoConnector
from pirpos2siigo.service import Updater
from pirpos2siigo.models import InvoiceStatus

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
logStreamFormatter = logging.Formatter(
    fmt=(
        "%(levelname)-8s %(asctime)s \t %(filename)s @function"
        "%(funcName)s line %(lineno)s \n%(message)s\n"
    ),
    datefmt="%H:%M:%S",
)
consoleHandler = logging.StreamHandler(stream=sys.stdout)
consoleHandler.setFormatter(logStreamFormatter)
consoleHandler.setLevel(level=logging.DEBUG)

file_handler = logging.FileHandler(filename="../logs.txt")
file_handler.setFormatter(logStreamFormatter)
file_handler.setLevel(level=logging.DEBUG)

logger.addHandler(file_handler)
logger.addHandler(consoleHandler)

siigo_user_name = str(os.getenv("SIIGO_USER_NAME"))
siigo_user_password = str(os.getenv("SIIGO_ACCESS_KEY"))
pirpos_user_name = str(os.getenv("PIRPOS_USER_NAME"))
pirpos_user_password = str(os.getenv("PIRPOS_PASSWORD"))
# CONFIGURATION_PATH = (
#     "/home/julian/projects/pirpos2siigo/configuration.JSON"
# )
CONFIGURATION_PATH = "/Users/julianestehe/Programs/personal/asadero/pirpos2siigo/configuration.JSON"

if __name__ == "__main__":
    pirpos_connector = PirposConnector(
        pirpos_user_name, pirpos_user_password, CONFIGURATION_PATH, logger
    )
    siigo_connector = SiigoConnector(
        siigo_user_name, siigo_user_password, CONFIGURATION_PATH, logger
    )
    updater = Updater(pirpos_connector, siigo_connector, logger)
    # updater.update_clients()  # TODO:f change page from next_url
    # updater.update_products()
    date_1 = datetime(2025, 2, 1)
    date_2 = datetime(2025, 2, 28)
    # updater.update_invoices(
    #     date_1, date_2
    # )  # TODO: download invoices by x days, not all rang
    updater.update_canceled_invoices(date_1, date_2)


    # invoices = pirpos_connector.get_pirpos_invoices_per_client(
    #     init_day=date_1, end_day=date_2, status=InvoiceStatus.CANCELED
    # )
    # dict_invoices = [
    #     {
    #         "FECHA": invoice.created_on,
    #         "PREFIJO": invoice.invoice_prefix.prefix,
    #         "NUMERO": invoice.invoice_number,
    #         "DOCUMENTO": invoice.client.document,
    #         "VALOR FACTURA": invoice.total,
    #     }
    #     for invoice in invoices if invoice.payment_method
    # ]
    # invoices_df = pd.DataFrame(dict_invoices)
    # invoices_df.to_csv("invoices.csv")
    # print()
