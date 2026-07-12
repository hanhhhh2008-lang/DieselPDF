@echo off
set "APP=%~dp0DieselPDF.pyw"
set "PYTHONW=C:\Users\AaronHan\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" set "PYTHONW=pythonw.exe"
start "" "%PYTHONW%" "%APP%"
