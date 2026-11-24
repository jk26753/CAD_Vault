"""Read-only diagnostic: how does this PC's SolidWorks expose GetPackAndGo to Python (pywin32)?

Background: the Configurator's Pack and Go export fails at ModelDocExtension.GetPackAndGo with
"Parameter not optional". This script reports how SolidWorks declares that call and tries
several ways of calling it, so the export can use one that works.

SAFE: it only obtains the Pack and Go object and reads from it. It copies, saves and changes
nothing, in SolidWorks or on disk.

Run from the CAD_Vault folder, with SolidWorks open and the table assembly as the active document:
    .\\backend\\.venv\\Scripts\\python.exe tools\\diagnose_pack_and_go.py
Then copy all of the output into the chat.
"""
import importlib.metadata
import sys

import pythoncom
import win32com.client
from win32com.client import VARIANT


def get(obj, name):
    """Read a zero-argument SolidWorks member whether pywin32 exposes it as a value or a method."""
    value = getattr(obj, name)
    return value() if callable(value) and not isinstance(value, win32com.client.CDispatch) else value


def describe(obj, name):
    """Print how the SolidWorks type information declares a member (what pywin32 relies on)."""
    rep = obj._olerepr_
    entry = rep.mapFuncs.get(name) or rep.propMapGet.get(name) or rep.propMap.get(name)
    if entry is None:
        print(f"  {name}: not found in the type information")
        return
    d = entry.desc
    # FUNCDESC tuple: (memid, scodes, args, funckind, invkind, callconv, cParamsOpt, oVft, rettype, flags)
    if isinstance(d, tuple) and len(d) >= 9:
        print(f"  {name}: dispid={d[0]} invkind={d[4]} args={d[2]} optional_args={d[6]} returns={d[8]}")
    else:
        print(f"  {name}: {d!r}")


def check(label, call):
    """Try one way of getting the Pack and Go object; report success and read one value from it."""
    try:
        raw = call()
        if raw is None:
            print(f"[FAIL] {label}: returned nothing")
            return
        pgo = raw if isinstance(raw, win32com.client.CDispatch) else win32com.client.Dispatch(raw)
        try:
            info = f"lists {get(pgo, 'GetDocumentNamesCount')} documents"
        except Exception:
            info = f"IncludeDrawings = {get(pgo, 'IncludeDrawings')}"
        print(f"[OK]   {label}: got the Pack and Go object ({info})")
    except Exception as e:
        print(f"[FAIL] {label}: {e}")


def main():
    print("Python", sys.version.split()[0], "| pywin32", importlib.metadata.version("pywin32"))
    sw = win32com.client.GetActiveObject("SldWorks.Application")
    try:
        print("SolidWorks revision:", get(sw, "RevisionNumber"))
    except Exception as e:
        print("SolidWorks revision: could not read", e)
    model = sw.ActiveDoc
    if model is None:
        print("No active document: open the table assembly in SolidWorks and run again.")
        return
    print("Active document:", get(model, "GetTitle"), "| type:", get(model, "GetType"), "(2 = assembly)")
    ext = model.Extension
    ole = ext._oleobj_
    dispid = ole.GetIDsOfNames("GetPackAndGo")

    print("\nHow SolidWorks declares the calls:")
    for name in ("GetPackAndGo", "SavePackAndGo"):
        try:
            describe(ext, name)
        except Exception as e:
            print(f"  {name}: could not read ({e})")

    print("\nWays of calling GetPackAndGo:")
    check("1. normal call ext.GetPackAndGo() (what the export does now)", lambda: ext.GetPackAndGo())
    check("2. raw property-get", lambda: ole.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYGET, True))
    check("3. raw method, no arguments", lambda: ole.Invoke(dispid, 0, pythoncom.DISPATCH_METHOD, True))
    check(
        "4. raw method or property-get",
        lambda: ole.Invoke(dispid, 0, pythoncom.DISPATCH_METHOD | pythoncom.DISPATCH_PROPERTYGET, True),
    )
    check(
        "5. typed call: no arguments, returns an object",
        lambda: ole.InvokeTypes(dispid, 0, pythoncom.DISPATCH_METHOD, (pythoncom.VT_DISPATCH, 0), ()),
    )

    def byref(vt):
        out = VARIANT(pythoncom.VT_BYREF | vt, None)
        result = ext.GetPackAndGo(out)
        return result if result is not None else out.value

    check("6. one output argument (object)", lambda: byref(pythoncom.VT_DISPATCH))
    check("7. one output argument (variant)", lambda: byref(pythoncom.VT_VARIANT))
    print("\nDone. Nothing was copied, saved or changed.")


if __name__ == "__main__":
    main()
