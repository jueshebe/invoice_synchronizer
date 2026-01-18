"""Infrastructure configuration module."""

import os
from typing import Dict, Union, List
import json
from pydantic import BaseModel
from invoice_synchronizer.domain import User

MAPPING_VALUES = Union[str, float, int]


class SystemParameters(BaseModel):
    """System parameters model.

    It defines the main payments methods, taxes, prefixes and retentions used in the system.
    """

    payments: list[Dict[str, MAPPING_VALUES]]
    taxes: list[Dict[str, MAPPING_VALUES]]
    prefixes: list[Dict[str, MAPPING_VALUES]]
    invoice_status: list[Dict[str, MAPPING_VALUES]]
    retentions: list[Dict[str, MAPPING_VALUES]]

    @classmethod
    def from_json(cls, file_path: str) -> "SystemParameters":
        """Load system configuration from a JSON file."""
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return cls(**data)


class PirposConfig(BaseModel):
    """Pirpos configuration model."""

    pirpos_username: str
    pirpos_password: str
    batch_size: int = 200
    default_user: User
    timeout: int = 30
    system_mapping: SystemParameters


class SiigoConfig(BaseModel):
    """Siigo configuration model."""

    siigo_username: str = os.environ["SIIGO_USER_NAME"]
    siigo_access_key: str = os.environ["SIIGO_ACCESS_KEY"]
    default_user: User
    timeout: int = 30
    system_mapping: SystemParameters
    retentions: List[int] = []


class SystemConfig:
    """System configuration model."""

    def __init__(self):

        self.default_user = self.load_default_user()
        self.system_config = self.load_system_config()

    def load_default_user(self) -> User:
        """Load default user from JSON file."""
        default_user_path = os.environ.get("DEFAULT_USER_PATH", "default_user.json")
        with open(default_user_path, "r", encoding="utf-8") as file:
            user_data = json.load(file)
            default_user = User(**user_data)
        return default_user

    def load_system_config(self) -> SystemParameters:
        """Load system configuration from JSON file."""
        system_config_path = os.environ.get("SYSTEM_CONFIG_PATH", "SYSTEM_CONFIGURATION.json")
        config_data = SystemParameters.from_json(system_config_path)
        return config_data

    def define_pirpos_config(self) -> PirposConfig:
        """Define system configuration."""
        pirpos_config = PirposConfig(
            pirpos_username=os.environ["PIRPOS_USER_NAME"],
            pirpos_password=os.environ["PIRPOS_PASSWORD"],
            batch_size=int(os.environ.get("PIRPOS_BATCH_SIZE", 200)),
            default_user=self.default_user,
            system_mapping=self.system_config,
        )
        return pirpos_config

    def define_siigo_config(self) -> SiigoConfig:
        """Define system configuration."""
        file = os.environ.get("SIIGO_CONFIG_PATH", "SIIGO_CONFIGURATION.json")
        with open(file, "r", encoding="utf-8") as siigo_config_file:
            json_data = json.load(siigo_config_file)
            retentions = json_data.get("retentions", [])
        siigo_config = SiigoConfig(
            siigo_username=os.environ["SIIGO_USER_NAME"],
            siigo_access_key=os.environ["SIIGO_ACCESS_KEY"],
            default_user=self.default_user,
            system_mapping=self.system_config,
            retentions=retentions,
        )
        return siigo_config
