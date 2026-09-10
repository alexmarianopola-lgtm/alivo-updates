#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef PayloadDir
  #define PayloadDir "payload"
#endif
#ifndef PythonInstaller
  #define PythonInstaller "python-3.12.10-amd64.exe"
#endif
#ifndef WebView2Installer
  #define WebView2Installer "MicrosoftEdgeWebview2Setup.exe"
#endif

#define MyAppName "ALIYVO"
#define MyPublisher "ALIYVO"
#define CompactVersion StringChange(AppVersion, ".", "")

[Setup]
AppId={{A71B54D8-3B4F-4D91-AB7F-2D21DB1D83A9}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyPublisher}
DefaultDirName={localappdata}\Programs\ALIYVO
DefaultGroupName=ALIYVO
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=ALIYVO_BETA_SETUP_{#CompactVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#PayloadDir}\_app\Aliyvo.ico
UninstallDisplayIcon={app}\_app\Aliyvo.ico
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
UsePreviousAppDir=yes
UsePreviousGroup=yes
CreateUninstallRegKey=yes
Uninstallable=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "{#PayloadDir}\_app\*"; DestDir: "{app}\_app"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "copiloto.db,ALIYVO_ERRO.txt,captured_images\*,captured_audio\*,downloads\*"
Source: "{#PayloadDir}\_app\copiloto.db"; DestDir: "{app}\_app"; Flags: onlyifdoesntexist
Source: "{#PayloadDir}\LEIA-ME-ALIYVO.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PythonInstaller}"; DestDir: "{tmp}"; DestName: "python-aliyvo.exe"; Flags: deleteafterinstall
Source: "{#WebView2Installer}"; DestDir: "{tmp}"; DestName: "MicrosoftEdgeWebview2Setup.exe"; Flags: deleteafterinstall
Source: "instalar_componentes.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{autodesktop}\ALIYVO"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\_app\Aliyvo.pyw"""; WorkingDir: "{app}\_app"; IconFilename: "{app}\_app\Aliyvo.ico"; Comment: "ALIYVO - Central comercial inteligente"
Name: "{userprograms}\ALIYVO\ALIYVO"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\_app\Aliyvo.pyw"""; WorkingDir: "{app}\_app"; IconFilename: "{app}\_app\Aliyvo.ico"
Name: "{userprograms}\ALIYVO\Desinstalar ALIYVO"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\_app\Aliyvo.pyw"""; WorkingDir: "{app}\_app"; Description: "Abrir ALIYVO"; Flags: nowait postinstall skipifsilent

[Code]
function RuntimeReady(): Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\runtime\python.exe'));
end;

function ComponentsReady(): Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\runtime\.aliyvo_componentes_v1.ok'));
end;

function ExecChecked(const FileName, Params, StatusText: String): Boolean;
var
  ResultCode: Integer;
begin
  WizardForm.StatusLabel.Caption := StatusText;
  WizardForm.StatusLabel.Refresh;
  Result := Exec(FileName, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := Result and (ResultCode = 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  PythonExe, Params, ScriptPath, AppDir: String;
begin
  if CurStep <> ssPostInstall then
    exit;

  { O WebView2 normalmente ja existe no Windows 10/11. O bootstrapper e executado
    de forma silenciosa para garantir o runtime sem exigir acao do usuario. }
  if FileExists(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe')) then
    ExecChecked(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'), '/silent /install',
      'Verificando o navegador interno do ALIYVO...');

  if not RuntimeReady() then
  begin
    Params := '/quiet InstallAllUsers=0 Include_launcher=0 InstallLauncherAllUsers=0 PrependPath=0 AssociateFiles=0 Shortcuts=0 Include_test=0 Include_doc=0 Include_dev=0 Include_debug=0 Include_tcltk=0 Include_pip=1 TargetDir="' + ExpandConstant('{app}\runtime') + '"';
    if not ExecChecked(ExpandConstant('{tmp}\python-aliyvo.exe'), Params,
      'Preparando o mecanismo interno do ALIYVO...') then
      RaiseException('Nao foi possivel preparar o Python interno do ALIYVO. Execute o instalador novamente.');
  end;

  PythonExe := ExpandConstant('{app}\runtime\python.exe');
  if not FileExists(PythonExe) then
    RaiseException('O mecanismo interno do ALIYVO nao foi encontrado apos a instalacao.');

  if not ComponentsReady() then
  begin
    ScriptPath := ExpandConstant('{tmp}\instalar_componentes.ps1');
    AppDir := ExpandConstant('{app}\_app');
    Params := '-NoProfile -ExecutionPolicy Bypass -File "' + ScriptPath + '" -Python "' + PythonExe + '" -AppDir "' + AppDir + '"';
    if not ExecChecked(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params,
      'Instalando audio, corretor, OCR e componentes do ALIYVO. Isso pode levar alguns minutos...') then
      RaiseException('Falha ao instalar os componentes do ALIYVO. Veja %LOCALAPPDATA%\ALIYVO\logs\INSTALACAO.log e execute o instalador novamente.');
  end;

  if not ComponentsReady() then
    RaiseException('A instalacao dos componentes nao foi concluida.');

  WizardForm.StatusLabel.Caption := 'ALIYVO pronto para usar.';
  WizardForm.StatusLabel.Refresh;
end;
