"""Model for clients."""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, validator
from invoice_synchronizer.models.utils import normalize


class CityDetail(BaseModel):
    """City info."""

    city_name: str
    city_state: str
    city_code: str
    country_code: str
    state_code: str


class Responsibilities(Enum):
    """Dian responsibilities."""

    O_13 = "O-13"  # gran contribuyente
    O_15 = "O-15"  # autoretenedor
    O_23 = "O-23"  # agente de retencion IVA
    O_47 = "O-47"  # regimen simple de tributacion
    R_99_PN = "R-99-PN"  # no responsable


class DocumentType(Enum):
    """DIAN document types (obtained from siigo api)."""

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


class User(BaseModel):
    """User info.
    
    This model is used to represent any user in the system, such as
    clients, employees, companies, system owner, or other types of users.
    any person/compny is considered a user.
    """

    name: str
    last_name: Optional[str] = None
    document_type: DocumentType
    document_number: int
    check_digit: Optional[int]
    city_detail: CityDetail
    responsibilities: Responsibilities
    email: str
    phone: str
    address: str

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
