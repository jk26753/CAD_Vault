"""Read-only diagnostic (round 2): find a working way to call GetPackAndGo from Python (pywin32).

Round 1 (SolidWorks 2022 SP5) showed: SolidWorks' late-bound interface expects ONE parameter
for ModelDocExtension.GetPackAndGo, and accepts an object reference for it (an output slot).
This round reads the exact declaration from SolidWorks' type library (sldworks.tlb) and tries
typed calls that declare that parameter as an output, so its value is returned to Python.

SAFE: it only obtains the Pack and Go object and reads from it. It copies, saves and changes
nothing, in SolidWorks or on disk.

Run from the CAD_Vault folder, with SolidWorks open and the table assembly as the active document:
    .\\backend\\.venv\\Scripts\\python.exe tools\\diagnose_pack_and_go.py
Then copy all of the output into the chat.
"""
import importlib.metadata
import sys
from pathlib import Path

import pythoncom
import win32com.client

VT_NAMES = {
    0: "EMPTY", 3: "I4", 9: "DISPATCH", 11: "BOOL", 12: "VARIANT", 13: "UNKNOWN",
    24: "VOID", 25: "HRESULT", 26: "PTR", 29: "USERDEFINED",
}
PARAMFLAG = {1: "in", 2: "out", 8: "retval", 16: "optional"}


def get(obj, name):
    """Read a zero-argument SolidWorks member whether pywin32 exposes it as a value or a method."""
    value = getattr(obj, name)
    return value() if callable(value) and not isinstance(value, win32com.client.CDispatch) else value


def flat_vt(td):
    """Turn a type-library type description into a plain VARIANT type number.

    pywin32 gives pointers as (VT_PTR, inner) and interfaces as (VT_USERDEFINED, ref):
    a pointer becomes VT_BYREF | inner; a user-defined interface is treated as VT_DISPATCH.
    """
    if isinstance(td, int):
        return td
    kind, inner = td[0], td[1]
    if kind == pythoncom.VT_PTR:
        return pythoncom.VT_BYREF | flat_vt(inner)
    if kind == pythoncom.VT_USERDEFINED:
        return pythoncom.VT_DISPATCH
    return kind


def vt_text(vt):
    base, flags = vt & 0x0FFF, []
    if vt & pythoncom.VT_BYREF:
        flags.append("BYREF")
    return "|".join(flags + [VT_NAMES.get(base, str(base))])


def arg_text(arg):
    # FUNCDESC arg: (vt, paramflags, default) or nested type tuples for pointers/user types
    vt, flags = arg[0], arg[1]
    vt_s = f"{vt_text(flat_vt(vt))} (raw {vt!r})"
    flag_s = "+".join(n for bit, n in PARAMFLAG.items() if flags & bit) or "none"
    return f"{vt_s} [{flag_s}]"


def find_typelib(sw):
    """sldworks.tlb lives next to sldworks.exe."""
    candidates = []
    try:
        candidates.append(Path(get(sw, "GetExecutablePath")) / "sldworks.tlb")
    except Exception as e:
        print("  could not read SolidWorks install folder:", e)
    candidates.append(Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb"))
    for c in candidates:
        if c.exists():
            return c
    print("  sldworks.tlb not found in:", ", ".join(str(c) for c in candidates))
    return None


def typelib_declarations(tlb_path, names):
    """Return {name: FUNCDESC} for IModelDocExtension members, read directly from the type library."""
    found = {}
    tlb = pythoncom.LoadTypeLib(str(tlb_path))
    for i in range(tlb.GetTypeInfoCount()):
        if tlb.GetDocumentation(i)[0] != "IModelDocExtension":
            continue
        ti = tlb.GetTypeInfo(i)
        kinds = [("as listed", ti)]
        try:  # dual interfaces: also look at the vtable side
            kinds.append(("vtable side", ti.GetRefTypeInfo(ti.GetRefTypeOfImplType(-1))))
        except Exception:
            pass
        for kind, info in kinds:
            attr = info.GetTypeAttr()
            for j in range(attr.cFuncs):
                fd = info.GetFuncDesc(j)
                fname = info.GetNames(fd.memid)[0]
                if fname in names:
                    args = ", ".join(arg_text(a) for a in fd.args) or "(none)"
                    ret = fd.rettype[0] if isinstance(fd.rettype, tuple) else fd.rettype
                    print(f"  {fname} ({kind}): invkind={fd.invkind} args: {args} "
                          f"| returns {vt_text(flat_vt(ret))} (raw {fd.rettype!r})")
                    if kind == "as listed":
                        found[fname] = fd
    return found


def check(label, call):
    """Try one way of getting the Pack and Go object; report success and read one value from it."""
    try:
        raw = call()
        if isinstance(raw, tuple):  # typed calls return (return value, output values...)
            raw = next((x for x in raw if x is not None), None)
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
    print("Active document:", get(model, "GetTitle"))
    ext = model.Extension
    ole = ext._oleobj_
    dispid = ole.GetIDsOfNames("GetPackAndGo")
    print("GetPackAndGo dispid:", dispid)

    print("\nDeclarations in SolidWorks' type library:")
    decl = {}
    tlb_path = find_typelib(sw)
    if tlb_path:
        print("  type library:", tlb_path)
        try:
            decl = typelib_declarations(tlb_path, {"GetPackAndGo", "SavePackAndGo"})
        except Exception as e:
            print("  could not read type library:", e)

    print("\nTyped calls that return the output parameter:")
    M, OUT = pythoncom.DISPATCH_METHOD, pythoncom.PARAMFLAG_FOUT
    BYREF_DISPATCH = pythoncom.VT_BYREF | pythoncom.VT_DISPATCH
    BYREF_UNKNOWN = pythoncom.VT_BYREF | pythoncom.VT_UNKNOWN
    check("A. out object, no return value",
          lambda: ole.InvokeTypes(dispid, 0, M, (pythoncom.VT_EMPTY, 0), ((BYREF_DISPATCH, OUT),), None))
    check("B. out object, returns HRESULT",
          lambda: ole.InvokeTypes(dispid, 0, M, (pythoncom.VT_HRESULT, 0), ((BYREF_DISPATCH, OUT),), None))
    check("C. in/out object, no return value",
          lambda: ole.InvokeTypes(dispid, 0, M, (pythoncom.VT_EMPTY, 0),
                                  ((BYREF_DISPATCH, OUT | pythoncom.PARAMFLAG_FIN),), None))
    check("D. out unknown, no return value",
          lambda: ole.InvokeTypes(dispid, 0, M, (pythoncom.VT_EMPTY, 0), ((BYREF_UNKNOWN, OUT),), None))
    fd = decl.get("GetPackAndGo")
    if fd is not None and fd.args:
        ret = fd.rettype[0] if isinstance(fd.rettype, tuple) else fd.rettype
        arg_types = tuple((flat_vt(a[0]), a[1]) for a in fd.args)
        check("E. exactly as declared in the type library",
              lambda: ole.InvokeTypes(dispid, 0, fd.invkind, (flat_vt(ret), 0), arg_types,
                                      *([None] * len(fd.args))))
    else:
        print("[SKIP] E. exactly as declared: declaration not available or has no arguments")
    print("\nDone. Nothing was copied, saved or changed.")


if __name__ == "__main__":
    main()
