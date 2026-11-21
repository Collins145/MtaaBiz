@echo off
rem Launch MtaaBiz dev server using the project virtualenv and open the site in the browser.
cd /d "%~dp0"
if not exist "mtaa\Scripts\python.exe" (
    echo Virtualenv not found at mtaa\Scripts\python.exe. Create it first: python -m venv mtaa
    exit /b 1
)
start "" http://127.0.0.1:8000/
cd backend
..\mtaa\Scripts\python.exe manage.py runserver 127.0.0.1:8000
