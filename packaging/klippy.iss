#define AppVersion "0.7.0-preview.1"
[Setup]
AppId={{D51FBA83-D0C3-4CA5-BA79-EE038805EC21}
AppName=Klippy Assistant Engineering Preview
AppVersion={#AppVersion}
AppPublisher=Klippy Assistant
DefaultDirName={localappdata}\Programs\KlippyAssistant
DefaultGroupName=Klippy Assistant
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=Klippy-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Klippy.exe
CloseApplications=yes
RestartApplications=no
InfoBeforeFile=preview-notice.txt

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
Name: "startup"; Description: "Start Klippy with Windows (hidden in tray)"; Flags: unchecked

[Files]
Source: "..\dist\Klippy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\RELEASE_CHECKLIST.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\RELEASE_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\ROADMAP.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\TEST_PLAN.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LOGBOOK.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PREVIEW3_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PREVIEW4_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PREVIEW5_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PREVIEW6_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PREVIEW7_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PREVIEW61_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PREVIEW51_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PHASE2_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Klippy Assistant"; Filename: "{app}\Klippy.exe"; Parameters: "--show"
Name: "{group}\Uninstall Klippy Assistant"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Klippy Assistant"; Filename: "{app}\Klippy.exe"; Parameters: "--show"; Tasks: desktopicon
Name: "{userstartup}\Klippy Assistant"; Filename: "{app}\Klippy.exe"; Tasks: startup

[Run]
Filename: "{app}\Klippy.exe"; Parameters: "--show"; Description: "Open Klippy Assistant"; Flags: nowait postinstall skipifsilent

; Settings and Windows vault credentials are deliberately preserved on upgrade/uninstall.
; The README describes private backup/reset and manual removal. No broad data deletion.
