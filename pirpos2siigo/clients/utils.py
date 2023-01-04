"""Utils used by clients."""
from typing import Optional
import json
from pirpos2siigo.models import Pirpos2SiigoMap, Client, CityDetail


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


def create_client(
    configuration_file: Pirpos2SiigoMap,
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    document: Optional[str] = None,
    check_digit: Optional[str] = None,
    document_type: Optional[str] = None,
    responsibilities: Optional[str] = None,
    city_name: Optional[str] = None,
    city_state: Optional[str] = None,
    city_code: Optional[str] = None,
    country_code: Optional[str] = None
) -> Client:
    """Create client object."""
    default_client = configuration_file.default_client
    return Client(
        name=name,
        email=email if email else default_client.email,
        phone=phone if phone else default_client.phone,
        address=address if address else default_client.address,
        document=document if document else default_client.document,
        check_digit=check_digit if check_digit else default_client.check_digit,
        document_type=document_type if document_type else default_client.document_type,
        responsibilities=responsibilities if responsibilities else default_client.responsibilities,
        city_detail=CityDetail(
            city_name=city_name if city_name else default_client.city_detail.city_name,
            city_state=city_state if city_state else default_client.city_detail.city_state,
            city_code=city_code if city_code else default_client.city_detail.city_code,
            country_code=country_code if country_code else default_client.city_detail.country_code
        )
    )


class ErrorConfigPirposSiigo(Exception):
    """File provided doesn't have correct information."""


class ErrorPirposToken(Exception):
    """Can't obtain pirpos token."""


class ErrorLoadingPirposClients(Exception):
    """Can't download Pirpos clients."""
