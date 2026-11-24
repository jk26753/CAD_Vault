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

# (variable name in equations.txt, label, min, max, step, slider step)
# step:        smallest allowed increment; enforced by the server and used for typed values.
# slider step: increment the slider moves in. Must be a multiple of step.
# Width steps by 6 because PlateQTY = Width / 6 must be a whole number.
# Length and height can be typed in 0.01 in; their sliders move in 0.5 in.
PARAMS = [
    ("TableLength", "LENGTH", 24, 120, 0.01, 0.5),
    ("TableWidth", "WIDTH", 24, 96, 6, 6),
    ("TableHeight", "HEIGHT", 24, 96, 0.01, 0.5),
]

# On/off options shown as checkboxes.
# (variable name in equations.txt, label, value when checked, value when unchecked)
# Casters: the model suppresses the four leveling casters when Casters = 1.
OPTIONS = [
    ("Casters", "Add Leveling Casters", 0, 1),
]
