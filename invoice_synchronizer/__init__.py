"""End modules."""
__version__ = "1.0.0"

import sys
import os
import logging
from datetime import datetime
from invoice_synchronizer.clients import PirposConnector, SiigoConnector
from invoice_synchronizer.service import Updater

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
logger.addHandler(consoleHandler)

SIIGO_USER_NAME = str(os.getenv("SIIGO_USER_NAME"))
SIIGO_USER_PASSWORD = str(os.getenv("SIIGO_ACCESS_KEY"))
PIRPOS_USER_NAME = str(os.getenv("PIRPOS_USER_NAME"))
PIRPOS_USER_PASSWORD = str(os.getenv("PIRPOS_PASSWORD"))
CONFIGURATION_PATH = "/Users/julianestehe/Programs/asadero/pirpos2siigo/configuration.JSON"
pirpos_connector = PirposConnector(
    PIRPOS_USER_NAME, PIRPOS_USER_PASSWORD, CONFIGURATION_PATH, logger
)
siigo_connector = SiigoConnector(SIIGO_USER_NAME, SIIGO_USER_PASSWORD, CONFIGURATION_PATH, logger)
updater = Updater(pirpos_connector, siigo_connector, logger)

if __name__ == "__main__":
    updater.update_clients()  # TODO: change page from next_url
    updater.update_products()
    date_1 = datetime(2022, 12, 1)
    date_2 = datetime(2022, 12, 31)
    updater.update_invoices(date_1, date_2)  # TODO: download invoices by x days, not all range
