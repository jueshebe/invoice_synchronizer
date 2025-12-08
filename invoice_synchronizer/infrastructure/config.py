"""Infrastructure configuration module."""

import os
import json
from pydantic import BaseModel
from invoice_synchronizer.domain import User


class PirposConfig(BaseModel):
    """Pirpos configuration model."""

    pirpos_username: str
    pirpos_password: str
    configuration_path: str
    batch_size: int = 200
    default_user: User


class SiigoConfig(BaseModel):
    """Siigo configuration model."""

    siigo_username: str = os.environ["SIIGO_USER_NAME"]
    siigo_access_key: str = os.environ["SIIGO_ACCESS_KEY"]
    configuration_path: str = "configuration.JSON"
    default_user: User


class SystemConfig(BaseModel):
    """System configuration model."""

    def __init__(self):

        self.default_user = self.load_default_user()

    def load_default_user(self) -> User:
        """Load default user from JSON file."""
        default_user_path = os.environ.get("DEFAULT_USER_PATH", "default_user.json")
        with open(default_user_path, "r", encoding="utf-8") as file:
            user_data = json.load(file)["default_client"]
            default_user = User(**user_data)
        return default_user

    def define_pirpos_config(self) -> PirposConfig:
        """Define system configuration."""
        pirpos_config = PirposConfig(
            pirpos_username=os.environ["PIRPOS_USER_NAME"],
            pirpos_password=os.environ["PIRPOS_PASSWORD"],
            configuration_path=os.environ.get("PIRPOS_CONFIG_PATH", "configuration.JSON"),
            batch_size=int(os.environ.get("PIRPOS_BATCH_SIZE", 200)),
        )
        return pirpos_config

    def define_siigo_config(self) -> SiigoConfig:
        """Define system configuration."""

        siigo_config = SiigoConfig(
            siigo_username=os.environ["SIIGO_USER_NAME"],
            siigo_access_key=os.environ["SIIGO_ACCESS_KEY"],
            configuration_path=os.environ.get("SIIGO_CONFIG_PATH", "configuration.JSON"),
        )
        return siigo_config
