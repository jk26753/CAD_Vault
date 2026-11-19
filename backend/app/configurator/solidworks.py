"""Tell the running SolidWorks session to reload equations.txt and rebuild.

Requires Windows, pywin32, and SolidWorks running on the same PC as the backend
with the assembly open as the active document.
"""
import logging
import threading

log = logging.getLogger(__name__)
_lock = threading.Lock()  # one rebuild at a time


def rebuild() -> str:
    """Reload the linked equations file and rebuild. Returns the document title."""
    try:
        import pythoncom
        import win32com.client
    except ImportError as e:
        raise RuntimeError(f"pywin32 is not installed or failed to load ({e})") from e

    with _lock:
        # FastAPI runs sync endpoints on worker threads, which need COM initialized.
        pythoncom.CoInitialize()
        try:
            sw = win32com.client.GetActiveObject("SldWorks.Application")
            model = sw.ActiveDoc
            if model is None:
                raise RuntimeError("No document open in SolidWorks")

            try:  # best-effort: force reload of the linked file
                model.GetEquationMgr().UpdateValuesFromExternalEquationFile()
            except Exception as e:
                log.info("equation reload step skipped: %s", e)

            rebuilt = False
            for name, call in (("ForceRebuild3", lambda: model.ForceRebuild3(False)),
                               ("EditRebuild3", lambda: model.EditRebuild3())):
                try:
                    call()
                    rebuilt = True
                    break
                except Exception as e:
                    log.info("%s failed: %s", name, e)
            if not rebuilt:
                raise RuntimeError("SolidWorks rebuild call failed")

            try:
                model.GraphicsRedraw2()
            except Exception as e:
                log.info("redraw skipped: %s", e)
            try:
                return model.GetTitle()
            except Exception:
                return "model"
        finally:
            pythoncom.CoUninitialize()
