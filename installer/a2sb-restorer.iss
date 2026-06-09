#define MyAppName "A2SB Restorer"
#define MyAppVersion "0.1.0-alpha"
#define MyAppPublisher "RollingEdit"
#define MyAppURL "https://github.com/rollingedit/diffusion-audio-restoration-windows"
#define MyAppExeName "A2SB Restorer.exe"

[Setup]
AppId={{F65F7B76-DBD2-41DE-A67A-057E6B50B3F2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
DefaultDirName={localappdata}\Programs\RollingEdit\A2SB Restorer
UsePreviousAppDir=yes
CloseApplications=yes
RestartApplications=no
DefaultGroupName=RollingEdit\A2SB Restorer
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=A2SB-Restorer-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
LicenseFile=..\LICENSES\NVIDIA_A2SB_LICENSE.txt
SetupIconFile=assets\setup.ico

[Files]
Source: "..\rolling_a2sb\*"; DestDir: "{app}\rolling_a2sb"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,*\__pycache__\*,.DS_Store,*.DS_Store"
Source: "..\audio_transforms\*"; DestDir: "{app}\audio_transforms"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,*\__pycache__\*,.DS_Store,*.DS_Store"
Source: "..\configs\*"; DestDir: "{app}\configs"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,*\__pycache__\*,.DS_Store,*.DS_Store"
Source: "..\corruption\*"; DestDir: "{app}\corruption"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,*\__pycache__\*,.DS_Store,*.DS_Store"
Source: "..\datasets\*"; DestDir: "{app}\datasets"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,*\__pycache__\*,.DS_Store,*.DS_Store"
Source: "..\inference\*"; DestDir: "{app}\inference"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,*\__pycache__\*,.DS_Store,*.DS_Store"
Source: "..\requirements\*"; DestDir: "{app}\requirements"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,*\__pycache__\*,.DS_Store,*.DS_Store"
Source: "..\scripts\*"; DestDir: "{app}\scripts"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,*\__pycache__\*,.DS_Store,*.DS_Store"
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,*\__pycache__\*,.DS_Store,*.DS_Store"
Source: "..\LICENSES\*"; DestDir: "{app}\LICENSES"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,*\__pycache__\*,.DS_Store,*.DS_Store"
Source: "..\bin\ffmpeg.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "..\bin\ffprobe.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "..\A2SB_lightning_module.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\A2SB_lightning_module_api.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\audio_utils.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\diffusion.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\ensembled_inference.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\ensembled_inference_api.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\networks.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\plotting_utils.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\utils.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README-WINDOWS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\installer\assets\app.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\dist\A2SB Restorer\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\A2SB Restorer"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\A2SB Doctor"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\doctor.ps1"""
Name: "{group}\Repair Runtime"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\repair_runtime.ps1"""
Name: "{group}\Open Models Folder"; Filename: "powershell.exe"; Parameters: "-NoProfile -Command ""$p = Join-Path '{app}' '.local_app_data\A2SB Restorer\models'; New-Item -ItemType Directory -Force -Path $p | Out-Null; Invoke-Item $p"""
Name: "{group}\Open Logs Folder"; Filename: "powershell.exe"; Parameters: "-NoProfile -Command ""$p = Join-Path '{app}' '.local_app_data\A2SB Restorer\Logs'; New-Item -ItemType Directory -Force -Path $p | Out-Null; Invoke-Item $p"""

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\setup_runtime.ps1"""; StatusMsg: "Installing private ML runtime..."; Flags: waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "Launch A2SB Restorer"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\runtime"
