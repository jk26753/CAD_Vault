@echo off
cd /d %~dp0frontend
if not exist node_modules npm ci
npm run dev
