; Inno Setup Script for LucidCam - Step-by-Step Autonomous Windows Installer
; Designed for non-technical users on machines without Python installed.

#define MyAppName "LucidCam"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "greatware"
#define MyAppURL "https://github.com/gunther-svg/lucidcam"
#define MyAppExeName "LucidCam.exe"

[Setup]
AppId={{9F82A4B1-209B-4D18-8A3F-84D2C318F12A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=LucidCam_Setup_v1.0.0
SetupIconFile=lucidcam.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequiredOverridesAllowed=commandline dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkablealone

[Files]
; Fully self-contained application bundle (embedded Python runtime + PyQt6 + WebRTC binaries)
Source: "dist\LucidCam\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
