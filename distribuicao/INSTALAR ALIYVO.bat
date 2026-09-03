@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title ALIYVO - Instalacao

echo ============================================
echo              ALIYVO BETA GRATIS
echo ============================================
echo.
echo Este instalador prepara o ALIYVO neste computador.
echo Nao feche esta janela durante a instalacao.
echo.

set "APPDIR=%~dp0_app"
if not exist "%APPDIR%\Aliyvo.pyw" goto app_missing
if not exist "%APPDIR%\Aliyvo.ico" goto app_missing

set "PYTHON="
for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON=%%P"
if defined PYTHON goto python_found

for /f "delims=" %%P in ('where python.exe 2^>nul') do (
  set "PYTHON=%%P"
  goto python_found
)

echo Python nao encontrado. Tentando instalar Python 3.12 para o usuario atual...
where winget.exe >nul 2>&1
if errorlevel 1 goto python_missing

winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  set "PYTHON=%LocalAppData%\Programs\Python\Python312\python.exe"
  goto python_found
)
for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON=%%P"
if not defined PYTHON goto python_missing

:python_found
echo.
echo Python encontrado: %PYTHON%
for %%D in ("%PYTHON%") do set "PYDIR=%%~dpD"
set "PYTHONW=%PYDIR%pythonw.exe"
if not exist "%PYTHONW%" goto pythonw_missing

echo.
echo Instalando componentes necessarios do ALIYVO...
"%PYTHON%" -m ensurepip --upgrade >nul 2>&1
"%PYTHON%" -m pip install --disable-pip-version-check --upgrade pip
"%PYTHON%" -m pip install --disable-pip-version-check PyQt6 PyQt6-WebEngine pyspellchecker qtwebview2==0.5.0 qtpy pythonnet
if errorlevel 1 goto deps_error

"%PYTHON%" -c "from PyQt6.QtWidgets import QApplication; from PyQt6.QtWebEngineWidgets import QWebEngineView; from qtwebview2 import QtWebView2Widget"
if errorlevel 1 goto deps_error

echo.
echo Criando atalho ALIYVO na Area de Trabalho...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$desktop=[Environment]::GetFolderPath('Desktop');" ^
 "$shortcut=Join-Path $desktop 'ALIYVO.lnk';" ^
 "if(Test-Path $shortcut){Remove-Item $shortcut -Force};" ^
 "$shell=New-Object -ComObject WScript.Shell;" ^
 "$s=$shell.CreateShortcut($shortcut);" ^
 "$s.TargetPath='%PYTHONW%';" ^
 "$s.Arguments='"""%APPDIR%\Aliyvo.pyw"""';" ^
 "$s.WorkingDirectory='%APPDIR%';" ^
 "$s.IconLocation='%APPDIR%\Aliyvo.ico,0';" ^
 "$s.Description='ALIYVO - Central comercial inteligente';" ^
 "$s.WindowStyle=1;" ^
 "$s.Save();"
if errorlevel 1 goto shortcut_error

ie4uinit.exe -show >nul 2>&1
echo.
echo ============================================
echo           INSTALACAO CONCLUIDA
echo ============================================
echo.
echo Um atalho ALIYVO foi criado na Area de Trabalho.
echo Na primeira abertura, entre no seu proprio WhatsApp.
echo Seus dados ficam somente no seu computador.
echo.
echo Abrindo ALIYVO...
start "" "%PYTHONW%" "%APPDIR%\Aliyvo.pyw"
timeout /t 3 >nul
exit /b 0

:app_missing
echo ERRO: arquivos do ALIYVO nao encontrados.
echo Extraia TODO o ZIP antes de executar o instalador.
goto fail

:python_missing
echo ERRO: nao consegui instalar o Python automaticamente.
echo Instale Python 3.12 pelo site python.org e execute este arquivo novamente.
start "" "https://www.python.org/downloads/windows/"
goto fail

:pythonw_missing
echo ERRO: pythonw.exe nao encontrado na instalacao do Python.
goto fail

:deps_error
echo ERRO: nao consegui instalar os componentes do ALIYVO.
echo Verifique a internet e execute o instalador novamente.
goto fail

:shortcut_error
echo ERRO: componentes instalados, mas nao consegui criar o atalho.
echo Execute novamente o instalador.
goto fail

:fail
echo.
pause
exit /b 1
