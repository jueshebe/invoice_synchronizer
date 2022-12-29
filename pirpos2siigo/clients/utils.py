"""Utils used by clients."""
from typing import Dict, Union, List
import json
from pirpos2siigo.models import Pirpos2SiigoMap


def load_pirpos2siigo_config(
    file_path: str
) -> Pirpos2SiigoMap:
    """Read JSON configuration file.

    It contains information of how map Pirpos to Siigo

    Parameters
    ----------
    file_path : str
        file direction

    Returns
    -------
        Pirpos2SiigoMap object
    """
    try:
        with open(file_path, "rt", encoding="utf-8") as file:
            data = json.load(file)
            config_obj = Pirpos2SiigoMap(**data)
            return config_obj
    except Exception as error:
        raise ErrorConfigPirposSiigo(
            f"""error loading file {file_path}. Error msg: {error}""") from error


def clean_document(client_document: str) -> int:
    """
    Read client document and parse it to validate it.

    Parameters
    ----------
    documentoCliente : str
        identificacion del cliente en formato string
            ex: 9 0 1 5 4 7 7 5 7 - 3

    Returns
    -------
    int
        entero del documento del cliente
        ex: 901547757.

    """
    if type(client_document) == float or type(client_document) == int:
        if (
            math.isnan(client_document) == True
        ):  # ahora pirpos no pone documento de consumidor final
            client_document = 222222222222

    if type(client_document) == str:
        client_document = client_document.replace(" ", "")
        if "-" in client_document:
            client_document = client_document[: client_document.find("-")]
    if client_document == "":
        client_document = 222222222222
    return int(str(client_document))



class ErrorConfigPirposSiigo(Exception):
    """File provided doesn't have correct information."""

class ErrorPirposToken(Exception):
    """Can't obtain pirpos token."""

class ErrorLoadingPirposClients(Exception):
    """Can't download Pirpos clients."""
