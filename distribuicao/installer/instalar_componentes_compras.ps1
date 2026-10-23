param(
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$AppDir
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$logDir = Join-Path $env:LOCALAPPDATA 'ALIYVO_COMPRAS\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'INSTALACAO.log'

function RunPython {
    param([Parameter(Mandatory=$true, Position=0)][string[]]$PyArgs)
    $oldEap = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Python @PyArgs 2>&1 | Tee-Object -FilePath $log -Append | Out-Null
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $oldEap }
    if ($code -ne 0) { throw "Falha ao instalar: $($PyArgs -join ' ')" }
}

try {
    RunPython -PyArgs @('-m','ensurepip','--upgrade')
    RunPython -PyArgs @('-m','pip','install','--disable-pip-version-check','--prefer-binary',
        'PyQt6','PyQt6-WebEngine','qtwebview2==0.5.0','qtpy','pythonnet','pyspellchecker','pillow')
    $test = 'from PyQt6.QtWidgets import QApplication; from PyQt6.QtWebEngineWidgets import QWebEngineView; from qtwebview2 import QtWebView2Widget; import PIL,clr; print("ALIYVO_COMPRAS_OK")'
    & $Python -c $test 2>&1 | Tee-Object -FilePath $log -Append | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Teste dos componentes essenciais falhou.' }
    $marker = Join-Path (Split-Path $Python -Parent) '.aliyvo_componentes_v1.ok'
    Set-Content -Path $marker -Value ('compras ok ' + (Get-Date -Format o)) -Encoding UTF8
    exit 0
} catch {
    Add-Content -Path $log -Value ('ERRO: ' + $_.Exception.Message) -Encoding UTF8
    Write-Error $_
    exit 1
}
