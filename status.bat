@echo off
cd /d "C:\Users\bahma\Downloads\base-juridique-app"

echo === PROCESSUS PYTHON ===
tasklist /FI "IMAGENAME eq python.exe" 2>nul | find /c "python"
echo processus actifs

echo.
echo === DOCUMENTS PAR SOURCE ===
for /D %%d in (output\*) do (
    set "count=0"
    for %%f in ("%%d\*.json") do set /a count+=1
    if !count! GTR 0 echo !count! %%~nd
)

echo.
echo === DERNIERS LOGS ===
for %%l in (cce consconst_fast moniteur gallilex wallex juportal hudoc) do (
    echo --- %%l:
    if exist "logs\%%l.log" (
        for /f "usebackq delims=" %%a in (`type "logs\%%l.log" ^| findstr /n "." ^| findstr /b "[0-9]*:" ^| tail -1 2^>nul`) do echo %%a
    )
)
