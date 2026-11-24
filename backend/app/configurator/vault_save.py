"""Save an exported table STEP file as an entry on the Table Configurations page.

Entries use the Model Vault's database and file storage, marked collection="table_config",
so they appear only on the Table Configurations page, never in the main Model Vault.
"""
import json
import re
import shutil
from pathlib import Path

from sqlalchemy import select

from ..config import settings as vault_settings
from ..db import SessionLocal
from ..models import File, Model
from .equations import _number

COLLECTION = "table_config"
CATEGORY = "Configured Table"
DESCRIPTION = "Exported from Table Configurator"


def _safe(s: str) -> str:
    # Must match safe() in app/main.py: the Model Vault deletes Models/<safe(part number)>
    # when an entry is deleted, so both must produce the same folder name.
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:180]


def save_configuration(step_file: Path, part_number: str, name: str, values: dict) -> None:
    """Create the entry and store a copy of step_file under the vault folder.

    values: the Configurator inputs SolidWorks was rebuilt with (TableLength, ...).
    On any error nothing is left behind: no database entry and no copied file.
    """
    model_dir = vault_settings.storage_root / "Models" / _safe(part_number)
    with SessionLocal() as db:
        if db.scalar(select(Model).where(Model.part_number == part_number)):
            raise RuntimeError(f"part number {part_number} already exists")
        if model_dir.exists():
            raise RuntimeError(f"storage folder for {part_number} already exists")
        try:
            source_dir = model_dir / "Source"
            source_dir.mkdir(parents=True)
            dest = source_dir / _safe(step_file.name)
            shutil.copy2(step_file, dest)
            m = Model(
                part_number=part_number,
                name=name,
                description=DESCRIPTION,
                category=CATEGORY,
                dimension_length=_number(values["TableLength"]),
                dimension_width=_number(values["TableWidth"]),
                dimension_height=_number(values["TableHeight"]),
                dimension_unit="in",
                collection=COLLECTION,
                table_config=json.dumps(values),
            )
            db.add(m)
            db.flush()
            db.add(
                File(
                    model_id=m.id,
                    role="source",  # the Model Vault viewer builds its 3D preview from this
                    original_name=step_file.name,
                    relative_path=str(dest.relative_to(vault_settings.storage_root)),
                    content_type="application/step",
                    size=dest.stat().st_size,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            shutil.rmtree(model_dir, ignore_errors=True)
            raise
