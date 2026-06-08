#define MyAppName "A2SB Restorer"
#define MyAppVersion "0.1.0-alpha"
#define MyAppPublisher "RollingEdit"
#define MyAppExeName "A2SB Restorer.exe"

[Setup]
AppId={{F65F7B76-DBD2-41DE-A67A-057E6B50B3F2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
DefaultDirName={localappdata}\Programs\RollingEdit\A2SB Restorer
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

[Files]
Source: "..\rolling_a2sb\*"; DestDir: "{app}\rolling_a2sb"; Flags: recursesubdirs ignoreversion
Source: "..\audio_transforms\*"; DestDir: "{app}\audio_transforms"; Flags: recursesubdirs ignoreversion
Source: "..\configs\*"; DestDir: "{app}\configs"; Flags: recursesubdirs ignoreversion
Source: "..\corruption\*"; DestDir: "{app}\corruption"; Flags: recursesubdirs ignoreversion
Source: "..\datasets\*"; DestDir: "{app}\datasets"; Flags: recursesubdirs ignoreversion
Source: "..\inference\*"; DestDir: "{app}\inference"; Flags: recursesubdirs ignoreversion
Source: "..\requirements\*"; DestDir: "{app}\requirements"; Flags: recursesubdirs ignoreversion
Source: "..\scripts\*"; DestDir: "{app}\scripts"; Flags: recursesubdirs ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: recursesubdirs ignoreversion
Source: "..\LICENSES\*"; DestDir: "{app}\LICENSES"; Flags: recursesubdirs ignoreversion
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
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\A2SB Restorer\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\A2SB Restorer"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\A2SB Doctor"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\doctor.ps1"""
Name: "{group}\Repair Runtime"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\repair_runtime.ps1"""
Name: "{group}\Open Models Folder"; Filename: "powershell.exe"; Parameters: "-NoProfile -Command ""New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA\RollingEdit\A2SB` Restorer\models | Out-Null; Invoke-Item $env:LOCALAPPDATA\RollingEdit\A2SB` Restorer\models"""
Name: "{group}\Open Logs Folder"; Filename: "powershell.exe"; Parameters: "-NoProfile -Command ""New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA\RollingEdit\A2SB` Restorer\logs | Out-Null; Invoke-Item $env:LOCALAPPDATA\RollingEdit\A2SB` Restorer\logs"""

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\setup_runtime.ps1"""; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\runtime"
