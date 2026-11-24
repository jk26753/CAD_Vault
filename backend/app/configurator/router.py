"""API for the Table Configurator. Independent of Model Vault's database and files."""
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from . import equations, export, export_ids, solidworks
from .settings import OPTIONS, PARAMS, settings

router = APIRouter(prefix="/api/configurator", tags=["configurator"])
NAMES = [p[0] for p in PARAMS] + [o[0] for o in OPTIONS]


@router.get("/state")
def state():
    path = settings.equations_file
    if not path.exists():
        raise HTTPException(404, f"Equations file not found: {path}")
    try:
        values = equations.read_values(path, NAMES)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {
        "equations_file": str(path),
        "params": [{"name": n, "label": lb, "min": lo, "max": hi, "step": st, "slider_step": sl}
                   for n, lb, lo, hi, st, sl in PARAMS],
        "options": [{"name": n, "label": lb, "on": on, "off": off}
                    for n, lb, on, off in OPTIONS],
        "values": values,
        "next_export_id": _next_id_or_none(),
    }


def _decimals(step: float) -> int:
    """Number of decimal places in a step, e.g. 0.01 -> 2, 6 -> 0."""
    s = repr(float(step))
    return 0 if s.endswith(".0") else len(s.split(".")[1])


@router.post("/apply")
def apply(values: dict[str, float]):
    clean = {}
    for name, _label, lo, hi, step, _slider in PARAMS:
        v = values.get(name)
        if v is None:
            raise HTTPException(422, f"Missing value for {name}")
        # Count whole steps with a small tolerance: decimal values such as 80.13 are
        # not exact in floating point, so `v % step` would give false rejections.
        n = round(v / step)
        if not lo <= v <= hi or abs(v / step - n) > 1e-6:
            raise HTTPException(422, f"{name} must be {lo}-{hi} in steps of {step}")
        # Store the exact multiple of the step, rounded to the step's decimal places.
        clean[name] = round(n * step, _decimals(step))
    for name, _label, on, off in OPTIONS:
        v = values.get(name)
        if v is None:
            raise HTTPException(422, f"Missing value for {name}")
        if v not in (on, off):
            raise HTTPException(422, f"{name} must be {on} or {off}")
        clean[name] = v
    try:
        equations.write_values(settings.equations_file, clean)
    except Exception as e:
        raise HTTPException(500, f"File error: {e}")
    try:
        title = solidworks.rebuild()
    except Exception as e:
        return {"saved": True, "synced": False, "message": f"File saved, SolidWorks not updated: {e}"}
    return {"saved": True, "synced": True, "message": f"Synced: {title}"}


class ExportRequest(BaseModel):
    format: Literal["step", "packandgo"]
    name: str  # file name without extension; the page fills in the auto name by default


@router.post("/export")
def export_model(req: ExportRequest):
    """Export the active (already rebuilt) SolidWorks assembly and send it as a download.

    Work happens in a temporary folder that is deleted after the file has been sent.
    """
    name = export.safe_name(req.name)
    if not any(c.isalnum() for c in name):
        raise HTTPException(422, "File name must contain letters or numbers")
    work = Path(tempfile.mkdtemp(prefix="cadvault_export_"))
    cleanup = BackgroundTask(shutil.rmtree, work, ignore_errors=True)
    try:
        # The export ID (e.g. IPT002) is only recorded as used if the export succeeds.
        with export_ids.reserve() as export_id:
            name = f"{name}_{export_id}"  # default and custom names both get the ID
            if req.format == "step":
                out = work / f"{name}.step"
                export.export_step(out)
            else:
                pack = work / "pack"
                pack.mkdir()
                # Copied files get a short dimension code plus the ID, e.g.
                # TopPlate_L60.25W48H44.5_IPT002.SLDPRT, using the values SolidWorks was last
                # rebuilt with. The zip itself gets the full export name.
                v = equations.read_values(
                    settings.equations_file, ["TableLength", "TableWidth", "TableHeight"]
                )
                n = equations._number
                suffix = (
                    f"_L{n(v['TableLength'])}W{n(v['TableWidth'])}H{n(v['TableHeight'])}"
                    f"_{export_id}"
                )
                export.pack_and_go(pack, suffix)
                out = export.zip_folder(pack, work / name)
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(500, f"Export failed: {e}")
    return FileResponse(out, filename=out.name, background=cleanup)


def _next_id_or_none():
    # A damaged counter file must not stop the Configurator from loading; export reports it.
    try:
        return export_ids.peek_next()
    except Exception:
        return None


@router.get("/export/next-id")
def next_export_id():
    """The ID the next successful export will get, e.g. IPT002 (null if the counter is unreadable)."""
    return {"next_export_id": _next_id_or_none()}
