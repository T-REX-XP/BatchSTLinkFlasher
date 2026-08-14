; Inno Setup script for Batch ST-Link Flasher
; Requires: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
; Build flow:
;   1) powershell -File scripts\build_windows.ps1
;   2) powershell -File scripts\build_installer.ps1
;      (or compile this .iss in Inno Setup Compiler)

#define MyAppName "Batch ST-Link Flasher"
#define MyAppId "BatchSTLinkFlasher"
#define MyAppVersion "0.1.0.2"
#define MyAppPublisher "BatchSTLinkFlasher"
#define MyAppExeName "BatchSTLinkFlasher.exe"

[Setup]
AppId={{A7C3E8F1-2B4D-4E9A-9C1F-8D6B5A4E3210}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppId}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=BatchSTLinkFlasher-{#MyAppVersion}-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\src\batch_stlink_flasher\assets\app_icon.ico
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; PyInstaller onedir payload produced by scripts\build_windows.ps1
Source: "..\dist\BatchSTLinkFlasher\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\scripts\uninstall.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\openocd-integration.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\packaging.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  MsgBox('OpenOCD is not bundled with this installer.'#13#10#13#10 +
         'Install OpenOCD separately and ensure it is on PATH,'#13#10 +
         'or set the OpenOCD path in the application settings.',
         mbInformation, MB_OK);
end;
