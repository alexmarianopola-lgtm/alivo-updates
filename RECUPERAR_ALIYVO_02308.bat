@echo off
setlocal EnableExtensions
title ALIYVO - Recuperacao 0.23.08
echo ============================================
echo       ALIYVO - RECUPERACAO 0.23.08
echo ============================================
echo.
echo Este processo recupera somente os arquivos do programa.
echo Seus dados em %%LOCALAPPDATA%%\ALIYVO serao preservados.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$ErrorActionPreference='Stop';" ^
 "$desktop=[Environment]::GetFolderPath('Desktop');" ^
 "$lnk=Join-Path $desktop 'ALIYVO.lnk';" ^
 "if(!(Test-Path $lnk)){throw 'Atalho ALIYVO.lnk nao encontrado na Area de Trabalho.'};" ^
 "$ws=New-Object -ComObject WScript.Shell;" ^
 "$s=$ws.CreateShortcut($lnk);" ^
 "$arg=[Environment]::ExpandEnvironmentVariables([string]$s.Arguments);" ^
 "$m=[regex]::Match($arg,'\"([^\"]*Aliyvo\.pyw)\"');" ^
 "if(!$m.Success){$m=[regex]::Match($arg,'([A-Za-z]:\\[^ ]*Aliyvo\.pyw)')};" ^
 "if(!$m.Success){throw 'Nao consegui localizar Aliyvo.pyw pelo atalho.'};" ^
 "$pyw=$m.Groups[1].Value;" ^
 "$app=Split-Path $pyw -Parent;" ^
 "$root=Split-Path $app -Parent;" ^
 "if(!(Test-Path (Join-Path $app 'main.py'))){throw ('Instalacao ALIYVO invalida: '+$app)};" ^
 "Write-Host ('Instalacao encontrada: '+$root);" ^
 "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*Aliyvo.pyw*' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} };" ^
 "$tmp=Join-Path $env:TEMP 'ALIYVO_RECUP_02308';Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force -Path $tmp | Out-Null;" ^
 "$zip=Join-Path $tmp 'aliyvo_02308.zip';" ^
 "$url='https://github.com/alexmarianopola-lgtm/alivo-updates/releases/download/v0.23.08/ALIYVO_BETA_GRATIS_02308.zip';" ^
 "Write-Host 'Baixando ALIYVO 0.23.08...';Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing;" ^
 "$extract=Join-Path $tmp 'novo';Expand-Archive $zip -DestinationPath $extract -Force;" ^
 "if(!(Test-Path (Join-Path $extract '_app\main.py'))){throw 'Pacote baixado invalido.'};" ^
 "Write-Host 'Aplicando recuperacao...';" ^
 "Copy-Item (Join-Path $extract '*') $root -Recurse -Force;" ^
 "if(!(Select-String -Path (Join-Path $root '_app\main.py') -Pattern 'ALIYVO_VERSION = \"0.23.08\"' -Quiet)){throw 'Versao final nao conferiu.'};" ^
 "Write-Host 'ALIYVO 0.23.08 aplicado com sucesso.';" ^
 "Start-Process $lnk;" ^
 "Start-Sleep -Seconds 3"

if errorlevel 1 goto fail
echo.
echo ============================================
echo         RECUPERACAO CONCLUIDA
echo ============================================
echo.
echo O ALIYVO foi atualizado para 0.23.08 e aberto.
timeout /t 3 >nul
exit /b 0

:fail
echo.
echo A recuperacao nao terminou.
echo Tire uma foto desta janela e me envie.
pause
exit /b 1
