@echo off
title NX1 co-op patch v0.2.8
echo ==== NX1 co-op patch v0.2.8 - apply_all.bat ====
setlocal
cd /d "%~dp0"
rem Put this folder INSIDE your NX1 folder (next to common.ffm, nx_harbor.ffm and nx_hospital.ffm).
if not exist "..\common.ffm" (
  echo Cannot find ..\common.ffm - this folder must sit directly inside your NX1 folder.
  pause & exit /b 1
)
if not exist out mkdir out
set "FAILED=0"
for %%N in (common nx_harbor nx_hospital nx_border) do call :patch %%N
if "%FAILED%"=="1" (
  echo.
  echo One or more patches failed. Send me the text above.
  pause & exit /b 1
)
echo.
set /p GO=Install now? Your originals stay as *.ffm.orig. Type Y: 
if /i "%GO%"=="Y" (
  for %%N in (common nx_harbor nx_hospital nx_border) do (
    if exist "out\%%N.ffm" (
      if not exist "..\%%N.ffm.orig" copy /y "..\%%N.ffm" "..\%%N.ffm.orig" >nul
      copy /y "out\%%N.ffm" "..\%%N.ffm" >nul
      echo Installed %%N.ffm
    )
  )
  echo To undo, copy each *.ffm.orig over its .ffm
)
pause
exit /b 0

:patch
set "Z=..\%1.ffm"
if not exist "%Z%" (
  echo %1.ffm not found, skipping.
  exit /b 0
)
set "SRC=%Z%"
if exist "%Z%.orig" set "SRC=%Z%.orig"
echo.
echo ---- %1: patching from %SRC%
python nx1_patch.py "%SRC%" "out\%1.ffm"
if errorlevel 1 (
  set "FAILED=1"
  if exist "out\%1.ffm" del "out\%1.ffm"
)
exit /b 0
