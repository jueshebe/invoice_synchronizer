"""Model for clients."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, validator


class CityDetail(BaseModel):
    """City info."""

    city_name: str
    city_state: str
    city_code: str
    country_code: str


class Responsibilities(Enum):
    """Dian responsibilities."""

    O_13 = "O-13"
    O_15 = "O-15"
    O_23 = "O-23"
    O_47 = "O-47"
    R_99_PN = "R-99-PN"


class DocumentType(Enum):
    """DIAN document types."""

    REGISTRO_CIVIL = 11
    TARJETA_IDENTIDAD = 12
    CEDULA_CIUDADANIA = 13
    TARJETA_EXTRANJERIA = 21
    CEDULA_EXTRANJERIA = 22
    NIT = 31
    PASAPORTE = 41
    TIPO_DOCUMENTO_EXTRANJERO = 42
    SIN_IDENTIFICAR = 43


class Client(BaseModel):
    """Client info."""

    name: str
    email: str
    phone: str
    address: str
    document: str
    check_digit: Optional[str]
    document_type: DocumentType
    responsibilities: Responsibilities
    city_detail: CityDetail

    @validator("document")
    @classmethod
    def clean_document(cls, document: str) -> str:
        """Read client document and validate it.

        Parameters
        ----------
        document : str
            ex: 9 0 1 5 4 7 7 5 7 - 3

        Returns
        -------
        str
            return -> '901547757'.
        """
        # if isinstance(document, (float, int)):
        #     if math.isnan(document):
        #         document = "222222222222"

        document = document.replace(" ", "")
        if "-" in document:
            document = document[: document.find("-")]
        # if document == "":
        #      document = 222222222222
        return document

    @validator("phone")
    @classmethod
    def clean_phone(cls, phone: str) -> str:
        """Remove spaces on phone parameter.

        Parameters
        ----------
        phone : str
            client phone

        Returns
        -------
        str
        """
        return phone.replace(" ", "")
