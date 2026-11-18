@echo off
title NX1 co-op patch v0.2.8 - restore
echo ==== NX1 co-op patch v0.2.8 - restore_originals.bat ====
cd /d "%~dp0"
for %%N in (common nx_harbor nx_hospital nx_border) do (
  if exist "..\%%N.ffm.orig" (
    copy /y "..\%%N.ffm.orig" "..\%%N.ffm" >nul
    echo Restored %%N.ffm
  )
)
pause
