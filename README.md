# CAD Vault

Internal engineering app for storing, browsing, previewing and configuring mechanical CAD designs.
It runs locally on one Windows PC and opens in the browser.

It contains two tools, shown as tabs at the top of the page:

- **Model Vault** (`#/vault`): a searchable library of CAD models with categories, tags,
  Design Project, compatible robots, dimensions, ROM price and pricing history, attached files
  (STEP source, Pack and Go ZIP, drawings, BOMs, documents) and an in-browser 3D STEP viewer.
- **Table Configurator** (`#/configurator`): sets `TableLength`, `TableWidth` and `TableHeight`
  in a SolidWorks `equations.txt` file and rebuilds the open SolidWorks assembly when you click
  **Apply & Rebuild**. It shares no data with the Model Vault.

## How it runs

One FastAPI/Uvicorn server on `http://127.0.0.1:8000` serves everything:

```
FastAPI / Uvicorn  :8000
 |-- /api/...               Model Vault API        (backend/app/main.py)
 |-- /api/configurator/...  Table Configurator API (backend/app/configurator/)
 |-- /                      React frontend, built into frontend/dist
```

- The frontend calls the API with relative paths (`/api/...`), so the page and the API share one
  origin. Do not change these to absolute `http://localhost:8000/...` URLs.
- The frontend must be **built** (`npm run build`) before the server can serve it. FastAPI only
  serves `frontend/dist` if that folder exists when the server starts.
- A separate Vite dev server is **not** needed for normal use. It is only for frontend
  development (see [Development mode](#development-mode)).

## Requirements

- Windows (the Configurator's SolidWorks link uses Windows COM through `pywin32`)
- Python 3 with `venv`. Versions 3.11 and 3.13 have both been used with this project.
- Node.js `^20.19.0` or `>=22.12.0` (required by Vite 8), with npm
- SolidWorks, only for the Table Configurator's rebuild step

## First-time setup

Run these from the repository root in PowerShell.

**1. Backend:** create the virtual environment in `backend\.venv` and install the Python packages.

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

**2. Frontend:** install the exact locked package versions, then build.

```powershell
cd frontend
npm ci
npm run build
cd ..
```

`npm ci` installs exactly what `package-lock.json` records. Use it instead of `npm install`.

**3. Data location:** create `backend\.env` (see [Data and backups](#data-and-backups)).
Without it, the app uses `data\` and `vault\` in the repository root.

**4. Table Configurator:** copy `backend\configurator.env.example` to `backend\configurator.env`
and set the path to the SolidWorks equations file:

```
CONFIGURATOR_EQUATIONS_FILE=C:\TSLOTSProjects\testParametric\equations.txt
```

## Daily use

Double-click **`start-model-vault.bat`** (or a desktop shortcut pointing to it). It:

1. changes to the `backend\` folder,
2. opens `http://localhost:8000` in the browser,
3. starts the server on `127.0.0.1:8000` (reachable from this PC only).

Close the window to stop the server. Only one copy of the app can use port 8000 at a time.

To start it by hand instead, run from the `backend\` folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### After changing code or switching branches

| What changed | What to do |
|---|---|
| Frontend (`frontend\src\...`) | `npm run build` in `frontend\`, then refresh the browser |
| Backend (`backend\app\...`) | Close the server window and start it again |
| `package.json` / `package-lock.json` | `npm ci` in `frontend\`, then `npm run build` |
| `requirements.txt` | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` in `backend\` |

The server does not reload itself, and git does not rebuild the frontend.

## Data and backups

Application data is **not** stored in git. It consists of:

- the SQLite database (`modelvault.db`)
- the vault folder, which holds uploaded files and generated previews under `Models\<part number>\`

`backend\.env` sets where these live. Example for data kept in `CAD_Vault_Data\` in the
repository root:

```
MODEL_VAULT_STORAGE_ROOT=../CAD_Vault_Data/vault
MODEL_VAULT_DATABASE_URL=sqlite:///../CAD_Vault_Data/data/modelvault.db
```

- **Relative paths are resolved from the folder the server is started in, which must be
  `backend\`.** `start-model-vault.bat` does this. Starting the server from any other folder
  silently creates a new, empty database in the wrong place.
- File paths inside the database are stored relative to the vault folder, so the database and
  vault folder can be moved together.
- `backend\.env`, `backend\configurator.env`, `data/`, `vault/` and `*.db` are git-ignored.

**Back up before testing any change that writes or deletes data.** Switching git branches undoes
code changes, not data changes. Close the app first, then:

```powershell
robocopy ".\CAD_Vault_Data" "$env:USERPROFILE\Documents\CAD_Vault_Backup_$(Get-Date -Format yyyy-MM-dd)" /E
```

## Table Configurator

- Reads and writes only the `TableLength`, `TableWidth` and `TableHeight` input lines in
  `equations.txt`. Derived equations, file encoding and line endings are preserved.
- Current limits (prototype values, set in `backend/app/configurator/settings.py`):

  | Parameter | Min | Max | Typed step | Slider step |
  |---|---|---|---|---|
  | TableLength | 24 in (609.6 mm) | 120 in (3048 mm) | 0.01 in (0.254 mm) | 0.5 in (12.7 mm) |
  | TableWidth | 24 in (609.6 mm) | 96 in (2438.4 mm) | 6 in (152.4 mm) | 6 in (152.4 mm) |
  | TableHeight | 24 in (609.6 mm) | 96 in (2438.4 mm) | 0.01 in (0.254 mm) | 0.5 in (12.7 mm) |

- **Apply & Rebuild** saves the file, then asks the running SolidWorks session to reload the
  equations and rebuild. SolidWorks must be running on the same PC with the table assembly as the
  active document. If SolidWorks is unavailable, the file is still saved and the page says
  SolidWorks was not updated.

### Export

After a successful **Apply & Rebuild**, the Export panel saves the rebuilt model and downloads it
through the browser. Export is disabled while there are unapplied changes.

- **STEP:** SolidWorks STEP export of the active assembly. The STEP version (AP203/AP214/AP242)
  follows SolidWorks' setting in Tools > Options > Export.
- **Pack and Go (ZIP):** SolidWorks Pack and Go of the active assembly, including drawings,
  Toolbox and suppressed components, zipped by the backend. Every copied file gets a short
  dimension code as a suffix (e.g. `TopPlate_L60.25W48H44.5.SLDPRT`), so it never shares a file
  name with the master; the zip itself gets the export name. In the copy, the link to
  `equations.txt` is broken, so it keeps its dimensions and is independent of the master.
- **File name:** defaults to `Table_L<length>_W<width>_H<height>_<Casters|NoCasters>_<date>`.
  Type a custom name to override it.

## Development mode

For live-reloading frontend work, run the server as usual, then in a second terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. `frontend/vite.config.ts` forwards `/api` requests to the server on
port 8000, so the backend must be running. `run_frontend.bat` does the same (`npm ci` if
`node_modules` is missing, then `npm run dev`).

Dev mode does not change `frontend/dist`. Run `npm run build` when done so port 8000 serves the
new version.

## Project layout

```
backend/
  app/main.py            Model Vault API, and serving of frontend/dist
  app/models.py          database tables (models, files, pricing_history)
  app/config.py          Model Vault settings (read from backend/.env)
  app/configurator/      Table Configurator API, equations file and SolidWorks link
  requirements.txt
  .env.example           template for backend/.env
  configurator.env.example
frontend/
  src/shell/             top bar and tool tabs
  src/App.tsx            Model Vault page
  src/components/        3D viewer, tag input, robot selector
  src/workers/           STEP parsing (occt-import-js, runs off the main thread)
  src/configurator/      Table Configurator page
  vite.config.ts         dev-server proxy (no effect on the build)
start-model-vault.bat    normal launcher
run_backend.bat          older launcher (see below)
run_frontend.bat         starts the Vite dev server
```

### Older launcher: `run_backend.bat`

Still works, but differs from `start-model-vault.bat`: it runs `pip install -r requirements.txt` on
every start, auto-reloads on backend code changes, and listens on `0.0.0.0`, which makes the app
reachable from other PCs on the network (there is no login). Prefer `start-model-vault.bat`.

## Conventions

- **Branches:** work on a short-lived branch from `main` (e.g. `feature/...`, `fix/...`), test
  it, then merge into `main`.
- **Dependencies:** npm packages are pinned to exact versions. Upgrades are deliberate changes,
  made and tested on their own branch.
- **Formatting:** keep formatting-only changes in their own commits. Frontend files have been
  formatted with Prettier (`--print-width 100 --single-quote`), backend files with Black.
- **Keep source files UTF-8.** Prefer escapes such as `'\u2014'` or `&times;` over typing
  special characters, so an editor or merge cannot corrupt them.
