#define MyAppName "HojaSQL Studio"
#define MyAppVersion GetEnv("APP_VERSION")
#if MyAppVersion == ""
  #define MyAppVersion "0.0.0-dev"
#endif
#define MyAppPublisher "ZapitoLivingstone"
#define MyAppURL "https://github.com/ZapitoLivingstone/HojaSQL-Studio"
#define MyAppExeName "HojaSQLStudio.exe"

[Setup]
AppId={{D58C224A-3AA8-4A6A-A278-1EB34E0B2553}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\HojaSQLStudio
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=HojaSQLStudio-setup
SetupIconFile=chopper.ico
UninstallDisplayIcon={app}\chopper.ico

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "portable-windows\HojaSQLStudio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "chopper.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\chopper.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\chopper.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
