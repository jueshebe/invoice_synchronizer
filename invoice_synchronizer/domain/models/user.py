"""Model for clients."""

from enum import Enum
import re
from typing import Optional, Union
from pydantic import BaseModel, field_validator
from invoice_synchronizer.domain.models.utils import normalize


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
    PPT = 48
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

    @field_validator("name")
    @classmethod
    def clean_name(cls, name: str) -> str:
        """Remove upercase and accents."""
        return normalize(name)

    @field_validator("last_name")
    @classmethod
    def clean_last_name(cls, last_name: str) -> str:
        """Remove upercase and accents."""
        return normalize(last_name)

    @field_validator("address")
    @classmethod
    def clean_address(cls, address: str) -> str:
        """Remove upercase and accents."""
        return normalize(address)

    @field_validator("phone")
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

    @classmethod
    def clean_document(cls, document: Union[str, int]) -> int:
        """Read client document and validate it.

        Parameters
        ----------
        document : Union[str, int]
            ex: 9 0 1 5 4 7 7 5 7 - 3

        Returns
        -------
        str
            return -> '901547757'.
        """
        if isinstance(document, int):
            return document

        document_str = document.replace(" ", "")
        if "-" in document_str:
            document_str = document_str[: document_str.find("-")]
        return int(document_str)

    @classmethod
    def get_check_digit(cls, document_number: int) -> int:
        """Calculate check digit from document number.

        Parameters
        ----------
        document_number : int
            client document number

        Returns
        -------
        int
            check digit
        """
        weights = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
        doc_str = str(document_number)

        # Ensure document doesn't exceed maximum supported length
        if len(doc_str) > len(weights):
            raise ValueError(f"Document number too long. Maximum {len(weights)} digits supported.")

        total = sum(int(doc_str[-(i + 1)]) * weights[i] for i in range(len(doc_str)))
        remainder = total % 11
        if remainder > 1:
            return 11 - remainder
        return remainder

    @classmethod
    def create_user_with_defaults(
        cls,
        default_user: "User",
        name: str,
        last_name: Optional[str] = None,
        document_type: Optional[int] = None,
        document: Optional[str] = None,
        city_name: Optional[str] = None,
        city_state: Optional[str] = None,
        city_code: Optional[str] = None,
        country_code: Optional[str] = None,
        state_code: Optional[str] = None,
        responsibilities: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
    ) -> "User":
        """Create client object."""
        # Map document_type integer to DocumentType enum if provided
        if document_type is not None:
            mapped_document_type = DocumentType(document_type)
        else:
            mapped_document_type = default_user.document_type

        if responsibilities is not None:
            responsibilities_map = Responsibilities(responsibilities)
        else:
            responsibilities_map = default_user.responsibilities

        document_number = cls.clean_document(document) if document else default_user.document_number
        address = address.strip().lower() if address else ""
        # address = re.sub(r"[^a-zA-Z0-9_]", "", address)

        return User(
            name=name,
            last_name=last_name,
            document_type=mapped_document_type,
            document_number=document_number,
            check_digit=cls.get_check_digit(document_number),
            city_detail=CityDetail(
                city_name=city_name.strip() if city_name else default_user.city_detail.city_name,
                city_state=(
                    city_state.strip() if city_state else default_user.city_detail.city_state
                ),
                city_code=city_code if city_code else default_user.city_detail.city_code,
                country_code=(
                    country_code if country_code else default_user.city_detail.country_code
                ),
                state_code=state_code if state_code else default_user.city_detail.state_code,
            ),
            responsibilities=responsibilities_map,
            email=email.strip().lower() if email else default_user.email,
            phone=phone.strip().lower() if phone else default_user.phone,
            address=address,
        )

    @classmethod
    def name_to_compare(cls, name: str, last_name: Optional[str]) -> str:
        """Generate a comparable name string."""
        full_name = name.split(" ") + (last_name.split(" ") if last_name else [""])
        name_part, last_name_part = [full_name[0].strip(), " ".join(full_name[1:])]
        last_name_part = last_name_part if len(last_name_part) > 0 else "."
        last_name_part = last_name_part[0:50].strip()

        comparable_name = f"{name_part} {last_name_part}".strip().replace(" ", "")
        return comparable_name

    def __eq__(self, other: object) -> bool:
        """Compare two users based on their document number."""
        if not isinstance(other, User):
            return NotImplemented
        self_dict = self.model_dump()
        other_dict = other.model_dump()
        for key in self_dict.keys():
            if key in ("name", "last_name", "address"):
                continue
            if self_dict[key] != other_dict[key]:
                return False

        full_name = self.name_to_compare(self.name, self.last_name)
        other_full_name = self.name_to_compare(other.name, other.last_name)

        if full_name != other_full_name:
            return False

        address_self = re.sub(r"[^a-zA-Z0-9 ]", "", self.address).replace(" ", "")
        address_other = re.sub(r"[^a-zA-Z0-9 ]", "", other.address).replace(" ", "")
        if address_self != address_other:
            return False

        return True
