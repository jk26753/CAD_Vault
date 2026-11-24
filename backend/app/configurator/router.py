"""API for the Table Configurator. Independent of Model Vault's database and files."""
from fastapi import APIRouter, HTTPException

from . import equations, solidworks
from .settings import PARAMS, settings

router = APIRouter(prefix="/api/configurator", tags=["configurator"])
NAMES = [p[0] for p in PARAMS]


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
        "params": [{"name": n, "label": lb, "min": lo, "max": hi, "step": st}
                   for n, lb, lo, hi, st in PARAMS],
        "values": values,
    }


def _decimals(step: float) -> int:
    """Number of decimal places in a step, e.g. 0.01 -> 2, 6 -> 0."""
    s = repr(float(step))
    return 0 if s.endswith(".0") else len(s.split(".")[1])


@router.post("/apply")
def apply(values: dict[str, float]):
    clean = {}
    for name, _label, lo, hi, step in PARAMS:
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
    try:
        equations.write_values(settings.equations_file, clean)
    except Exception as e:
        raise HTTPException(500, f"File error: {e}")
    try:
        title = solidworks.rebuild()
    except Exception as e:
        return {"saved": True, "synced": False, "message": f"File saved, SolidWorks not updated: {e}"}
    return {"saved": True, "synced": True, "message": f"Synced: {title}"}
