; Installer di Prisma — Inno Setup 6 (https://jrsoftware.org/isinfo.php)
; Non compilare a mano: lo fa build.py, che passa la versione con /DAppVersion=...

#ifndef AppVersion
  #define AppVersion "1.0"
#endif
#define AppName "Prisma"
#define AppExe "Prisma.exe"
#define AppPublisher "Cesa028"
#ifndef SrcDir
  #define SrcDir "..\build\package"
#endif

[Setup]
AppId={{4C53E658-D80E-4953-8D3C-903BDECE5D8A}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=© 2026 {#AppPublisher} — Licenza MIT
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} Setup
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; installazione senza permessi di amministratore (solo per l'utente),
; con possibilità di scegliere "per tutti gli utenti"
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=license-page.txt
SetupIconFile=..\build\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardSizePercent=110
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
OutputDir=..\dist
OutputBaseFilename=Prisma-Setup-{#AppVersion}

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
italian.SendToIcon=Aggiungi "Prisma - Converti immagini" al menu Invia a
english.SendToIcon=Add "Prisma - Converti immagini" to the Send To menu

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "sendto"; Description: "{cm:SendToIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SrcDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{usersendto}\Prisma - Converti immagini"; Filename: "{app}\{#AppExe}"; Tasks: sendto

[UninstallDelete]
; alla disinstallazione rimuove anche impostazioni, preset, strumenti scaricati
; e i collegamenti creati dal programma (Invia a / Desktop)
Type: filesandordirs; Name: "{userappdata}\Prisma"
Type: filesandordirs; Name: "{localappdata}\Prisma"
Type: files; Name: "{usersendto}\Prisma - Converti immagini.lnk"
Type: files; Name: "{userdesktop}\Prisma.lnk"

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
