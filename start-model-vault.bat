@echo off
title Model Vault

cd /d "%~dp0backend"

start "" http://localhost:8000

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
