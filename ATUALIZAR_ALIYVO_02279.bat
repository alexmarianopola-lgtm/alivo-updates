@echo off
setlocal EnableExtensions
title ALIYVO - Atualizacao de recuperacao

echo ============================================
echo       ALIYVO - ATUALIZACAO DE RECUPERACAO
echo ============================================
echo.
echo Esta ferramenta atualiza o ALIYVO para 0.22.79.
echo Seus dados pessoais nao serao apagados.
echo.

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

"%PS%" -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "Add-Type -AssemblyName System.Windows.Forms;" ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;" ^
  "$shell=New-Object -ComObject WScript.Shell;" ^
  "$links=@();" ^
  "$desktops=@([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('CommonDesktopDirectory'),(Join-Path $env:USERPROFILE 'OneDrive\Desktop'),(Join-Path $env:USERPROFILE 'OneDrive\Area de Trabalho'));" ^
  "foreach($d in $desktops){ if($d -and (Test-Path $d)){ $links += Get-ChildItem -Path $d -Filter '*.lnk' -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'ALIYVO' } } };" ^
  "if(-not $links){ throw 'Nao encontrei o atalho do ALIYVO na Area de Trabalho.' };" ^
  "$sc=$shell.CreateShortcut($links[0].FullName);" ^
  "$appdir=$sc.WorkingDirectory;" ^
  "if(-not $appdir -or -not (Test-Path (Join-Path $appdir 'main.py'))){ throw 'Nao consegui localizar a pasta _app do ALIYVO pelo atalho.' };" ^
  "$root=Split-Path $appdir -Parent;" ^
  "$target=$sc.TargetPath; $args=$sc.Arguments;" ^
  "Get-CimInstance Win32_Process | Where-Object { ($_.Name -in @('python.exe','pythonw.exe')) -and ($_.CommandLine -match 'Aliyvo.pyw|main.py') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue };" ^
  "Start-Sleep -Seconds 2;" ^
  "$tmp=Join-Path $env:TEMP ('aliyvo_update_'+[guid]::NewGuid().ToString('N')); New-Item -ItemType Directory -Force -Path $tmp | Out-Null;" ^
  "$zip=Join-Path $tmp 'aliyvo.zip';" ^
  "$url='https://github.com/alexmarianopola-lgtm/alivo-updates/releases/download/v0.22.79/ALIYVO_BETA_GRATIS_02279.zip';" ^
  "Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $zip;" ^
  "$ext=Join-Path $tmp 'ext'; Expand-Archive -Path $zip -DestinationPath $ext -Force;" ^
  "if(-not (Test-Path (Join-Path $ext '_app\main.py'))){ throw 'Pacote baixado invalido.' };" ^
  "Copy-Item -Path (Join-Path $ext '*') -Destination $root -Recurse -Force;" ^
  "Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue;" ^
  "Start-Process -FilePath $target -ArgumentList $args -WorkingDirectory $appdir;" ^
  "[System.Windows.Forms.MessageBox]::Show('ALIYVO atualizado para 0.22.79.','ALIYVO') | Out-Null;"

if errorlevel 1 (
  echo.
  echo ERRO AO ATUALIZAR.
  echo.
  echo Se aparecer uma mensagem acima, mande uma foto dela.
  echo.
  pause
  exit /b 1
)

exit /b 0
