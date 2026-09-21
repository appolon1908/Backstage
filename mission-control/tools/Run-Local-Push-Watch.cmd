@echo off
set "PY=C:\Users\Usuario\AppData\Local\Programs\Python\Python312\python.exe"
set "SCAN=C:\Users\Usuario\01_DEVELOPMENT\Mission-Control\Check-Local-Work.py"
set "LOG=C:\Users\Usuario\01_DEVELOPMENT\Mission-Control\local-push-watch.log"
"%PY%" "%SCAN%" >> "%LOG%" 2>&1
