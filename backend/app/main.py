from pathlib import Path
import re, shutil, zipfile
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File as FFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, or_, text
from sqlalchemy.orm import Session, selectinload
from pydantic import BaseModel
from .db import Base, engine, get_db
from .models import Model, File, Price
from .config import settings

Base.metadata.create_all(engine)
with engine.begin() as c:
    cols = {x[1] for x in c.execute(text("PRAGMA table_info(models)"))}
    if "design_project" not in cols:
        c.execute(
            text("ALTER TABLE models ADD COLUMN design_project VARCHAR(250) DEFAULT ''")
        )
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class In(BaseModel):
    part_number: str = ""
    name: str
    design_project: str = ""
    description: str = ""
    category: str
    tags: str = ""
    compatible_robots: str = ""
    dimension_length: str = ""
    dimension_width: str = ""
    dimension_height: str = ""
    dimension_unit: str = "in"
    rom_price: str = ""
    last_quoted_on: str = ""


def query():
    return select(Model).options(selectinload(Model.files), selectinload(Model.prices))


def output(m):
    return {
        "id": m.id,
        "part_number": m.part_number,
        "name": m.name,
        "design_project": m.design_project,
        "description": m.description,
        "category": m.category,
        "tags": m.tags,
        "compatible_robots": m.compatible_robots,
        "dimension_length": m.dimension_length,
        "dimension_width": m.dimension_width,
        "dimension_height": m.dimension_height,
        "dimension_unit": m.dimension_unit,
        "rom_price": m.rom_price,
        "last_quoted_on": m.last_quoted_on,
        "files": [
            {
                "id": f.id,
                "role": f.role,
                "original_name": f.original_name,
                "size": f.size,
            }
            for f in m.files
        ],
        "pricing_history": [
            {
                "id": p.id,
                "rom_price": p.rom_price,
                "quoted_on": p.quoted_on,
                "recorded_at": p.recorded_at.isoformat(),
            }
            for p in m.prices
        ],
    }


@app.get("/api/models")
def models(qs: str = "", db: Session = Depends(get_db)):
    s = query()
    if qs:
        t = f"%{qs}%"
        s = s.where(
            or_(
                Model.name.ilike(t),
                Model.part_number.ilike(t),
                Model.tags.ilike(t),
                Model.design_project.ilike(t),
            )
        )
    return [output(x) for x in db.scalars(s.order_by(Model.updated_at.desc())).unique()]


@app.get("/api/tags")
def tags(db: Session = Depends(get_db)):
    found = {}
    for raw in db.scalars(select(Model.tags)):
        for v in (raw or "").split(","):
            tag = v.strip()
            if tag and tag.casefold() not in found:
                found[tag.casefold()] = tag
    return sorted(found.values(), key=str.casefold)


@app.post("/api/models")
def create(x: In, db: Session = Depends(get_db)):
    if db.scalar(select(Model).where(Model.part_number == x.part_number)):
        raise HTTPException(409, "Part number already exists")
    data = x.model_dump()
    data["tags"] = normalize_tags(data["tags"])
    m = Model(**data)
    db.add(m)
    db.flush()
    if x.rom_price or x.last_quoted_on:
        db.add(Price(model_id=m.id, rom_price=x.rom_price, quoted_on=x.last_quoted_on))
    db.commit()
    return output(db.scalar(query().where(Model.id == m.id)))


@app.put("/api/models/{mid}")
def update(mid: int, x: In, db: Session = Depends(get_db)):
    m = db.scalar(query().where(Model.id == mid))
    if not m:
        raise HTTPException(404, "Model not found")
    old = (m.rom_price, m.last_quoted_on)
    data = x.model_dump(exclude={"part_number"})
    data["tags"] = normalize_tags(data["tags"])
    for k, v in data.items():
        setattr(m, k, v)
    if old != (x.rom_price, x.last_quoted_on) and (x.rom_price or x.last_quoted_on):
        db.add(Price(model_id=m.id, rom_price=x.rom_price, quoted_on=x.last_quoted_on))
    db.commit()
    return output(db.scalar(query().where(Model.id == mid)))


def normalize_tags(raw):
    seen = {}
    for x in (raw or "").split(","):
        t = x.strip()
        if t and t.casefold() not in seen:
            seen[t.casefold()] = t
    return ", ".join(seen.values())


def safe(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:180]


@app.post("/api/models/{mid}/files")
async def upload(
    mid: int,
    role: str = Form("document"),
    upload: UploadFile = FFile(...),
    db: Session = Depends(get_db),
):
    m = db.get(Model, mid)
    if not m:
        raise HTTPException(404, "Model not found")
    d = (
        settings.storage_root
        / "Models"
        / safe(m.part_number)
        / {"source": "Source", "preview": "Preview", "pack_and_go": "PackAndGo"}.get(
            role, "Documents"
        )
    )
    d.mkdir(parents=True, exist_ok=True)
    p = d / safe(upload.filename or "file")
    data = await upload.read()
    p.write_bytes(data)
    if role == "pack_and_go" and p.suffix.lower() == ".zip":
        ex = d / (p.stem + "_extracted")
        ex.mkdir(exist_ok=True)
        with zipfile.ZipFile(p) as z:
            z.extractall(ex)
    f = File(
        model_id=mid,
        role=role,
        original_name=upload.filename or p.name,
        relative_path=str(p.relative_to(settings.storage_root)),
        content_type=upload.content_type or "application/octet-stream",
        size=len(data),
    )
    db.add(f)
    db.commit()
    return {"ok": True}


@app.get("/api/files/{fid}")
def download(fid: int, db: Session = Depends(get_db)):
    f = db.get(File, fid)
    p = settings.storage_root / f.relative_path if f else None
    if not f or not p.exists():
        raise HTTPException(404, "File missing")
    return FileResponse(p, filename=f.original_name)


@app.delete("/api/files/{fid}")
def remove_file(fid: int, db: Session = Depends(get_db)):
    f = db.get(File, fid)
    if not f:
        raise HTTPException(404, "File not found")
    if f.role == "preview":
        raise HTTPException(400, "Generated preview files are managed automatically")
    p = settings.storage_root / f.relative_path
    if p.exists():
        p.unlink()
    db.delete(f)
    db.commit()
    return {"ok": True}


@app.delete("/api/models/{mid}")
def delete(mid: int, db: Session = Depends(get_db)):
    m = db.get(Model, mid)
    if not m:
        raise HTTPException(404, "Model not found")
    p = settings.storage_root / "Models" / safe(m.part_number)
    db.delete(m)
    db.commit()
    shutil.rmtree(p, ignore_errors=True)
    return {"ok": True}
    # Table Configurator: a separate tool mounted at /api/configurator (see app/configurator)


from .configurator import router as configurator_router

app.include_router(configurator_router)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if frontend_dist.exists():
    app.mount(
        "/",
        StaticFiles(
            directory=str(frontend_dist),
            html=True,
        ),
        name="frontend",
    )
