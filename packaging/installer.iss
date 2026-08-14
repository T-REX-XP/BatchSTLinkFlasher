; Inno Setup script for Batch ST-Link Flasher
; Requires: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
; Build flow (produces a single Setup.exe for operators):
;   1) powershell -File scripts\build_app.ps1
;   2) powershell -File scripts\build_installer.ps1 [-InstallInno] [-ZipPortable]
;
; Or: powershell -File scripts\build_all.ps1 -ZipPortable -InstallInno
;
; App payload is PyInstaller onedir under dist\BatchSTLinkFlasher\
; (EXE + Qt + tools\openocd from build_installer.ps1).

#define MyAppName "Batch ST-Link Flasher"
#define MyAppId "BatchSTLinkFlasher"
#define MyAppVersion "0.1.0.5"
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
WizardImageFile=..\src\batch_stlink_flasher\assets\wizard_image.bmp
WizardSmallImageFile=..\src\batch_stlink_flasher\assets\wizard_small.bmp
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; PyInstaller onedir from scripts\build_app.ps1 (+ OpenOCD from build_installer.ps1)
Source: "..\dist\BatchSTLinkFlasher\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\scripts\uninstall.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\openocd-integration.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\packaging.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
