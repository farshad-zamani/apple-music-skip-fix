#define AppVersion "0.1.1"
[Setup]
AppId={{47D86B4E-9178-42E5-8939-88CDEB43B4CB}
AppName=Apple Music Skip Fix
AppVersion={#AppVersion}
AppPublisher=CloudTart (cloudtart.com)
AppPublisherURL=https://cloudtart.com/
AppSupportURL=https://github.com/farshad-zamani/apple-music-skip-fix/issues
VersionInfoDescription=Apple Music Skip Fix by CloudTart - cloudtart.com
DefaultDirName={localappdata}\Programs\AppleMusicSkipFix
DefaultGroupName=Apple Music Skip Fix
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.22000
OutputDir=..\dist
OutputBaseFilename=AppleMusicSkipFix-{#AppVersion}-Setup
SetupIconFile=..\build\icon.ico
UninstallDisplayIcon={app}\AppleMusicSkipFix.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\AppleMusicSkipFix\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Apple Music Skip Fix"; Filename: "{app}\AppleMusicSkipFix.exe"
Name: "{autodesktop}\Apple Music Skip Fix"; Filename: "{app}\AppleMusicSkipFix.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AppleMusicSkipFix.exe"; Description: "Open Apple Music Skip Fix"; Flags: nowait postinstall skipifsilent

; Recovery files are outside {app}. Never remove AppData backups or Apple files.
