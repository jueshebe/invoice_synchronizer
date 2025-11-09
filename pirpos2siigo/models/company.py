from pydantic import BaseModel, Field
from typing import Optional


class Company(BaseModel):
    """
    Company model representing a business entity.
    
    Attributes:
        name: Company name
        nit: Tax identification number
        address: Company address
        phone: Company phone number
        email: Company email address
        country: Country where the company is located
        state: State/province where the company is located
        city: City where the company is located
    """
    name: str = Field(..., description="Company name")
    nit: str = Field(..., description="Tax identification number")
    address: Optional[str] = Field(default=None, description="Company address")  # Optional
    phone: Optional[str] = Field(default=None, description="Company phone number")  # Optional
    email: Optional[str] = Field(default=None, description="Company email address")  # Optional
    country: str = Field(default="Colombia", description="Country where the company is located")  # Optional with default
    state: Optional[str] = Field(default=None, description="State/province where the company is located")  # Optional
    city: str = Field(..., description="City where the company is located")

    class Config:
        json_encoders = {
            # Add custom encoders if needed
        }