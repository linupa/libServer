@echo off
rem Starts the CLIB Web server (Windows only: LocalDB needs it):
rem   http://127.0.0.1:8080/  the library's app      http://127.0.0.1:8081/  the self-service kiosk
rem First run: creates .venv and installs requirements.txt.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv || exit /b 1
  .venv\Scripts\python -m pip install -r requirements.txt || exit /b 1
)
.venv\Scripts\python app.py
