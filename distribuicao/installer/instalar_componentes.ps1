param(
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$AppDir
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$logDir = Join-Path $env:LOCALAPPDATA 'ALIYVO\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'INSTALACAO.log'

function Log([string]$msg) {
    $line = ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg)
    Add-Content -Path $log -Value $line -Encoding UTF8
}

function RunPython {
    param(
        [Parameter(Mandatory=$true, Position=0)]
        [string[]]$PyArgs
    )
    Log ('python ' + ($PyArgs -join ' '))
    & $Python @PyArgs 2>&1 | Tee-Object -FilePath $log -Append | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar Python: $($PyArgs -join ' ') (codigo $LASTEXITCODE)"
    }
}

try {
    Log 'Iniciando componentes ALIYVO.'
    if (-not (Test-Path $Python)) { throw "Python interno nao encontrado: $Python" }
    if (-not (Test-Path $AppDir)) { throw "Pasta do ALIYVO nao encontrada: $AppDir" }

    RunPython -PyArgs @('-m','ensurepip','--upgrade')
    RunPython -PyArgs @('-m','pip','install','--disable-pip-version-check','--upgrade','pip','setuptools','wheel')

    # Componentes principais do ALIYVO.
    RunPython -PyArgs @('-m','pip','install','--disable-pip-version-check','--prefer-binary',
        'PyQt6','PyQt6-WebEngine','pyspellchecker','qtwebview2==0.5.0','qtpy','pythonnet')

    # Audio local e transcricao. O modelo Whisper e baixado automaticamente
    # na primeira utilizacao caso ainda nao exista no cache deste usuario.
    RunPython -PyArgs @('-m','pip','install','--disable-pip-version-check','--prefer-binary','faster-whisper')

    # OCR local e imagens. Os modelos do EasyOCR tambem sao obtidos
    # automaticamente quando forem usados pela primeira vez.
    RunPython -PyArgs @('-m','pip','install','--disable-pip-version-check','--prefer-binary','easyocr','pillow')

    # Teste real dos componentes que antes exigiam instalacao manual.
    $test = @'
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from qtwebview2 import QtWebView2Widget
from spellchecker import SpellChecker
from faster_whisper import WhisperModel
import PIL
import easyocr
import clr
print('ALIYVO_COMPONENTES_OK')
'@
    & $Python -c $test 2>&1 | Tee-Object -FilePath $log -Append | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Teste dos componentes falhou.' }

    $marker = Join-Path (Split-Path $Python -Parent) '.aliyvo_componentes_v1.ok'
    Set-Content -Path $marker -Value ('ok ' + (Get-Date -Format o)) -Encoding UTF8
    Log 'Componentes ALIYVO instalados e validados.'
    exit 0
}
catch {
    Log ('ERRO: ' + $_.Exception.Message)
    Write-Error $_
    exit 1
}
