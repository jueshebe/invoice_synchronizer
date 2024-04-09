"""Model for clients."""
from enum import Enum
from typing import Optional, Union
from pydantic import BaseModel, validator
from pirpos2siigo.models.utils import normalize

class CityDetail(BaseModel):
    """City info."""

    city_name: str
    city_state: str
    city_code: str
    country_code: str  # TODO: Must be Enum
    state_code: str


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
    PEP = 47
    NIT_OTRO_PAIS = 50
    NUIP = 91


class Client(BaseModel):
    """Client info."""

    siigo_id: Optional[str]
    pirpos_id: Optional[str]
    name: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    document: int
    check_digit: Optional[int]
    document_type: DocumentType
    responsibilities: Responsibilities = Responsibilities.R_99_PN
    city_detail: Optional[CityDetail]

    @validator("name")
    @classmethod
    def clean_name(cls, name: str) -> str:
        """Remove upercase and accents."""
        return normalize(name)

    @validator("address")
    @classmethod
    def clean_address(cls, address: str) -> str:
        """Remove upercase and accents."""
        return normalize(address)

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
