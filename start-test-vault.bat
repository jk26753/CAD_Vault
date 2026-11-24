@echo off
title CAD Vault TEST - port 8001
rem Runs CAD Vault on port 8001 against a COPY of the data, for testing changes safely.
rem The live app (start-model-vault.bat, port 8000) and live data (CAD_Vault_Data) are not touched.
rem The copy is made the first time this runs. Delete CAD_Vault_Test_Data to start again from a fresh copy.
rem NOTE: the Table Configurator still drives the real SolidWorks session and equations.txt.

cd /d "%~dp0"
if not exist "CAD_Vault_Data\data\modelvault.db" (
  echo Live data folder CAD_Vault_Data was not found next to this file, so there is nothing to copy.
  pause
  exit /b 1
)
if not exist "CAD_Vault_Test_Data" (
  echo Making a test copy of CAD_Vault_Data in CAD_Vault_Test_Data ...
  robocopy "CAD_Vault_Data" "CAD_Vault_Test_Data" /E /NFL /NDL /NJH /NJS /NP >nul
)

cd /d "%~dp0backend"
rem These override backend\.env, so this server only ever uses the test copy.
set MODEL_VAULT_STORAGE_ROOT=../CAD_Vault_Test_Data/vault
set MODEL_VAULT_DATABASE_URL=sqlite:///../CAD_Vault_Test_Data/data/modelvault.db

echo TEST server: http://localhost:8001  (data: CAD_Vault_Test_Data)
start "" http://localhost:8001

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8001

pause
