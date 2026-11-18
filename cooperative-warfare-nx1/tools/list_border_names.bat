@echo off
title NX1 name lister
echo ==== NX1 name lister (read-only) ====
cd /d "%~dp0"
if not exist "..\nx_border.ffm" (
  echo This folder must sit directly inside your NX1 folder.
  pause & exit /b 1
)
echo Reading nx_border.ffm (about a minute, needs ~1.5 GB of free memory)...
python nx1_strings.py "..\nx_border.ffm" "..\border_names.zip"
if errorlevel 1 (
  echo Failed. Send me the text above.
  pause & exit /b 1
)
echo Done. Tell me and I will read ..\border_names.zip from your NX1 folder.
pause
