@echo off
REM Uruchamia webowy serwer produkcji (port 5000).
REM Po starcie: otworz na telefonie http://<IP-komputera>:5000
REM Haslo to to samo co w GicleeApp.

cd /d "%~dp0"
python -m Komponenty.produkcja.web_server
pause
