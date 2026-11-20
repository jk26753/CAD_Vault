# Model Vault v8
Targeted changes only: edit-associated-files, delete confirmation, Design Project field, case-insensitive/trimmed tags with keyboard dropdown navigation, generated previews hidden from Files tab, matching viewer/info-panel borders, and Sheet Metal/Plate + Misc categories. V4-style STEP worker parsing remains.

## Table Configurator
A separate tool on its own tab (`#/configurator`). It edits the `TableLength`, `TableWidth` and `TableHeight` inputs in a SolidWorks `equations.txt` file and rebuilds the open assembly when you click **Apply & Rebuild**. It shares no data with the vault.
- Code: `backend/app/configurator/` and `frontend/src/configurator/`
- Setup: copy `backend/configurator.env.example` to `backend/configurator.env` and set the equations file path. SolidWorks must be running on the same PC as the backend, with the assembly active.
