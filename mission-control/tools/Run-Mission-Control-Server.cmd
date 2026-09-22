@echo off
set "PY=C:\Users\Usuario\AppData\Local\Programs\Python\Python312\python.exe"
set "SERVER=C:\Users\Usuario\01_DEVELOPMENT\Mission-Control\MissionControlServer.py"
set "LOG=C:\Users\Usuario\01_DEVELOPMENT\Mission-Control\mission-control-server.log"
"%PY%" "%SERVER%" >> "%LOG%" 2>&1
