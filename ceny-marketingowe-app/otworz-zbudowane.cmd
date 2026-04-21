@echo off
cd /d "%~dp0"
if not exist "dist\index.html" (
  echo Brak folderu dist. Najpierw: npm run build
  pause
  exit /b 1
)
start "" "%~dp0dist\index.html"
