@echo off
setlocal
set "SRC=%~dp0GicleeCrop.lrplugin"
set "MOD=%AppData%\Adobe\Lightroom\Modules"
set "DST=%MOD%\GicleeCrop.lrplugin"
set "OLD=%MOD%\GicleeCrop.lrdevplugin"

if not exist "%SRC%" (
  echo Nie znaleziono: %SRC%
  exit /b 1
)

echo Instalacja wtyczki GicleeCrop do:
echo   %DST%
echo.

if exist "%OLD%" (
  echo Usuwanie starej wersji .lrdevplugin...
  rmdir /s /q "%OLD%"
)

if exist "%DST%" (
  echo Usuwanie poprzedniej wersji...
  rmdir /s /q "%DST%"
)

xcopy /E /I /Y "%SRC%" "%DST%" >nul
if errorlevel 1 (
  echo Blad kopiowania.
  exit /b 1
)

echo Gotowe.
echo 1. Zamknij Lightroom Classic calkowicie.
echo 2. Uruchom ponownie.
echo 3. Sprawdz: Plik -^> Menedzer wtyczek -^> "Giclee Kadrowanie"
echo 4. Menu: Plik LUB Biblioteka -^> Dodatki do wtyczek
pause
