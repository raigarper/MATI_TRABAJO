@echo off
rem Arranca la web del viajante en local y abre el navegador.
cd /d "%~dp0"
echo Web en http://localhost:8000  (cierra esta ventana para pararla)
start "" http://localhost:8000
python -m http.server 8000
