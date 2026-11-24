"""Export the rebuilt table from SolidWorks as a STEP file.

Requires Windows, pywin32, and SolidWorks running on the same PC as the backend
with the master table assembly open as the active document (same as rebuild).

The page only allows export after a successful Apply & Rebuild, so the active
assembly reflects the values shown on the page.

NOTE: written against the SolidWorks API documentation; it cannot be run outside
Windows/SolidWorks, so the first real test is on the engineering PC.
"""

import re
from contextlib import contextmanager
from pathlib import Path

from .solidworks import (
    _lock,
)  # shared lock: one SolidWorks job (rebuild or export) at a time

# SolidWorks API constants (swconst.tlb)
SW_SAVE_SILENT = 1  # swSaveAsOptions_e.swSaveAsOptions_Silent
SW_SAVE_COPY = 2  # swSaveAsOptions_e.swSaveAsOptions_Copy
SW_SAVE_CURRENT_VERSION = 0  # swSaveAsVersion_e.swSaveAsCurrentVersion


def safe_name(name: str) -> str:
    """Make a user-typed name safe as a Windows file name."""
    name = re.sub(r"[^A-Za-z0-9 ._-]+", "_", name).strip(" .")
    return name[:120]


@contextmanager
def _solidworks():
    """Yield (sw, com helpers) with COM initialised on this worker thread, under the lock."""
    try:
        import pythoncom
        import win32com.client
    except ImportError as e:
        raise RuntimeError(f"pywin32 is not installed or failed to load ({e})") from e
    with _lock:
        pythoncom.CoInitialize()
        try:
            sw = win32com.client.GetActiveObject("SldWorks.Application")
            yield sw, pythoncom, win32com.client
        finally:
            pythoncom.CoUninitialize()


def _byref_int(pythoncom, client):
    """An int output parameter (errors/warnings) for a COM call."""
    return client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def _active_doc(sw):
    model = sw.ActiveDoc
    if model is None:
        raise RuntimeError("No document open in SolidWorks")
    return model


def export_step(out_file: Path) -> None:
    """Save the active document as a STEP copy (the open document is unchanged).

    The STEP version (AP203/AP214/AP242) follows SolidWorks' own export setting
    (Tools > Options > Export > STEP).
    """
    with _solidworks() as (sw, pythoncom, client):
        model = _active_doc(sw)
        errors, warnings = _byref_int(pythoncom, client), _byref_int(pythoncom, client)
        no_export_data = client.VARIANT(pythoncom.VT_DISPATCH, None)
        ok = model.Extension.SaveAs(
            str(out_file),
            SW_SAVE_CURRENT_VERSION,
            SW_SAVE_SILENT | SW_SAVE_COPY,
            no_export_data,
            errors,
            warnings,
        )
        if not ok or not out_file.exists():
            raise RuntimeError(
                f"STEP export failed (SolidWorks error code {errors.value})"
            )
