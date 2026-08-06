@echo off
setlocal
set "CROP_DETECTOR_ENDPOINT=http://127.0.0.1:8870/v1/detect"
set "CROP_STORAGE_DIR=runtime"
set "CROP_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000"
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
