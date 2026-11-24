"""Export the rebuilt table from SolidWorks as a STEP file or a Pack and Go zip.

Requires Windows, pywin32, and SolidWorks running on the same PC as the backend
with the master table assembly open as the active document (same as rebuild).

The page only allows export after a successful Apply & Rebuild, so the active
assembly reflects the values shown on the page.

NOTE: written against the SolidWorks API documentation; it cannot be run outside
Windows/SolidWorks, so the first real test is on the engineering PC.
"""

import logging
import re
import shutil
from contextlib import contextmanager
from pathlib import Path

from .solidworks import (
    _lock,
)  # shared lock: one SolidWorks job (rebuild or export) at a time

log = logging.getLogger(__name__)

# SolidWorks API constants (swconst.tlb)
SW_DOC_ASSEMBLY = 2  # swDocumentTypes_e.swDocASSEMBLY
SW_OPEN_SILENT = 1  # swOpenDocOptions_e.swOpenDocOptions_Silent
SW_SAVE_SILENT = 1  # swSaveAsOptions_e.swSaveAsOptions_Silent
SW_SAVE_COPY = 2  # swSaveAsOptions_e.swSaveAsOptions_Copy
SW_SAVE_CURRENT_VERSION = 0  # swSaveAsVersion_e.swSaveAsCurrentVersion


def safe_name(name: str) -> str:
    """Make a user-typed name safe as a Windows file name (and as a file-name suffix)."""
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


def _get(obj, name):
    """Read a SolidWorks API member that takes no arguments, e.g. GetTitle or GetType.

    With pywin32's late binding, SolidWorks' zero-argument methods are exposed as
    properties: obj.GetTitle is already the string, and obj.GetTitle() fails with
    "'str' object is not callable". This works whichever way the member is exposed.
    """
    value = getattr(obj, name)
    return value() if callable(value) and not hasattr(value, "_oleobj_") else value


@contextmanager
def _step(label: str):
    """Name the step in any error, e.g. 'Pack and Go failed at "opening the copied assembly": ...'."""
    try:
        yield
    except Exception as e:
        if isinstance(e, StepError):
            raise
        log.exception(
            "Export step failed: %s", label
        )  # full details in the server window
        raise StepError(f'at "{label}": {e}') from e


class StepError(RuntimeError):
    """An export error already labelled with the step it happened in."""


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


def pack_and_go(out_dir: Path, suffix: str) -> Path:
    """Pack and Go the active assembly into out_dir and make the copy independent.

    - Includes drawings, Toolbox components and suppressed components.
    - Adds `suffix` to every copied file name, so the copy never shares a file name
      with the open master (SolidWorks cannot open two files with the same name).
    - Opens the copied assembly, reloads the current equations, rebuilds, breaks the
      link to the external equations file in every copied document, saves and closes.
    Returns the copied assembly's path.
    """
    with _solidworks() as (sw, pythoncom, client):
        with _step("reading the active assembly"):
            master = _active_doc(sw)
            if _get(master, "GetType") != SW_DOC_ASSEMBLY:
                raise RuntimeError("The active SolidWorks document is not an assembly")
            master_path = Path(_get(master, "GetPathName"))
            master_title = _get(master, "GetTitle")

        # 1. Pack and Go: same engine as File > Pack and Go.
        with _step("setting up Pack and Go"):
            pgo = _get(master.Extension, "GetPackAndGo")
            for prop, value in (
                ("IncludeDrawings", True),
                ("IncludeToolboxComponents", True),
                ("IncludeSuppressed", True),
                ("IncludeSimulationResults", False),
                ("FlattenToSingleFolder", False),
            ):
                try:
                    setattr(pgo, prop, value)
                except Exception as e:  # keep going: SolidWorks default applies
                    log.warning("Pack and Go option %s not set: %s", prop, e)
        with _step("setting the Pack and Go file-name suffix"):
            pgo.AddSuffix = suffix
        with _step("setting the Pack and Go output folder"):
            if not pgo.SetSaveToName(True, str(out_dir)):
                raise RuntimeError("Pack and Go rejected the output folder")
        with _step("running Pack and Go"):
            statuses = master.Extension.SavePackAndGo(pgo)
            log.info("Pack and Go statuses: %s", statuses)

        with _step("finding the copied assembly"):
            copy_name = f"{master_path.stem}{suffix}{master_path.suffix}".lower()
            copies = [p for p in out_dir.rglob("*") if p.name.lower() == copy_name]
            if not copies:
                raise RuntimeError("Pack and Go did not produce the copied assembly")
            copy_path = copies[0]

        # 2. Make the copy independent of the master's equations file.
        with _step("opening the copied assembly"):
            errors, warnings = _byref_int(pythoncom, client), _byref_int(
                pythoncom, client
            )
            copy = sw.OpenDoc6(
                str(copy_path), SW_DOC_ASSEMBLY, SW_OPEN_SILENT, "", errors, warnings
            )
            if copy is None:
                raise RuntimeError(
                    f"Could not open the packed assembly (error code {errors.value})"
                )
        try:
            with _step("listing the copied parts"):
                # Only documents inside the export folder are ever modified or saved. If the copy
                # still references an original master file (a reference Pack and Go did not
                # redirect), that file is left untouched and the export fails instead.
                root = out_dir.resolve()

                def in_export(doc) -> bool:
                    return Path(_get(doc, "GetPathName")).resolve().is_relative_to(root)

                docs = [copy]
                for comp in copy.GetComponents(False) or []:
                    doc = _get(
                        comp, "GetModelDoc2"
                    )  # None for suppressed / not loaded components
                    if doc is None or any(
                        _get(doc, "GetPathName") == _get(d, "GetPathName") for d in docs
                    ):
                        continue
                    if not in_export(doc):
                        raise RuntimeError(
                            f"Packed copy still references the original {_get(doc, 'GetPathName')}; "
                            "nothing was changed in the master files"
                        )
                    docs.append(doc)
            try:  # load the values the master was just rebuilt with
                _get(
                    _get(copy, "GetEquationMgr"), "UpdateValuesFromExternalEquationFile"
                )
            except Exception as e:
                log.info("equation reload in copy skipped: %s", e)
            with _step("rebuilding the copy"):
                copy.ForceRebuild3(False)
            with _step("breaking the equations link in the copy"):
                for doc in docs:
                    eq = _get(doc, "GetEquationMgr")
                    if eq is not None and eq.LinkToFile:
                        eq.LinkToFile = False
            with _step("rebuilding the copy after unlinking"):
                copy.ForceRebuild3(False)
            with _step("saving the copy"):
                for doc in docs:
                    if not in_export(
                        doc
                    ):  # belt and braces: never save outside the export folder
                        continue
                    e, w = _byref_int(pythoncom, client), _byref_int(pythoncom, client)
                    if not doc.Save3(SW_SAVE_SILENT, e, w):
                        raise RuntimeError(
                            f"Could not save {_get(doc, 'GetTitle')} (error code {e.value})"
                        )
        finally:
            # Never let a cleanup problem hide the real error above; log it instead.
            try:
                sw.CloseDoc(_get(copy, "GetTitle"))
                e = _byref_int(pythoncom, client)
                sw.ActivateDoc3(
                    master_title, False, 0, e
                )  # hand the master back as active doc
            except Exception:
                log.exception(
                    "Export: closing the copy / re-activating the master failed"
                )
        return copy_path


def zip_folder(folder: Path, zip_base: Path) -> Path:
    """Zip the contents of folder into zip_base + '.zip'."""
    return Path(shutil.make_archive(str(zip_base), "zip", root_dir=folder))
