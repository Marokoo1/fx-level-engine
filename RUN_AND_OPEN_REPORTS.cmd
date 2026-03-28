@echo off
setlocal
cd /d "%~dp0"

echo Running FX Level Engine rebuild and opening reports...
echo.

powershell -ExecutionPolicy Bypass -File ".\scripts\rebuild_majors_reports.ps1" -OpenReports
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
    echo.
    echo The rebuild script ended with error code %EXIT_CODE%.
    echo Close any locked CSV/HTML preview windows and try again.
    echo.
    pause
)

endlocal
