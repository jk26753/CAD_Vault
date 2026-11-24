"""Settings for the Table Configurator, kept separate from Model Vault's settings.

Override in backend/configurator.env (see configurator.env.example), for example:
    CONFIGURATOR_EQUATIONS_FILE=C:\\TSLOTSProjects\\testParametric\\equations.txt
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfiguratorSettings(BaseSettings):
    equations_file: Path = Path(r"C:\TSLOTSProjects\testParametric\equations.txt")

    model_config = SettingsConfigDict(env_file="configurator.env", env_prefix="CONFIGURATOR_", extra="ignore")


settings = ConfiguratorSettings()

# (variable name in equations.txt, label, min, max, step)
# Width steps by 6 because PlateQTY = Width / 6 must be a whole number.
# Length steps by 0.01 in (hundredths of an inch).
PARAMS = [
    ("TableLength", "LENGTH", 24, 120, 0.01),
    ("TableWidth", "WIDTH", 24, 96, 6),
    ("TableHeight", "HEIGHT", 24, 96, 1),
]
