@echo off
chcp 65001 >nul
cd /d "%~dp0TaxMonitor"
TaxMonitor.exe
