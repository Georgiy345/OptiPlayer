; OptiPlayer installer script (Inno Setup 7)
; Build: ISCC.exe packaging\OptiPlayer.iss

#define AppName "OptiPlayer"
#define AppVersion "1.0.1"
#define AppPublisher "OptiPlayer"
#define AppExeName "OptiPlayer.exe"
#define AppId "{{7E2C4A18-5B93-4F6D-9C21-8A4E0D7B3F52}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=OptiPlayer-Setup-{#AppVersion}
SetupIconFile=..\assets\optiplayer.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
AllowNoIcons=yes
InfoAfterFile=after_install.txt
VersionInfoVersion=1.0.1.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "associate"; Description: "Открывать видеофайлы через OptiPlayer"; GroupDescription: "Интеграция с Windows:"

[Files]
Source: "..\dist\OptiPlayer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; ProgID ---------------------------------------------------------------
Root: HKCU; Subkey: "Software\Classes\OptiPlayer.Video"; ValueType: string; ValueName: ""; ValueData: "Видеофайл OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\OptiPlayer.Video\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\OptiPlayer.Video\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate

; "Открыть с помощью" ------------------------------------------------
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExeName}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExeName}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExeName}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"; Tasks: associate

; Зарегистрированные приложения (Параметры → Приложения по умолчанию)
Root: HKCU; Subkey: "Software\OptiPlayer"; ValueType: none; ValueName: ""; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#AppName}"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Быстрый видеоплеер для Windows"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: "{app}\{#AppExeName},0"; Tasks: associate
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#AppName}"; ValueData: "Software\OptiPlayer\Capabilities"; Flags: uninsdeletevalue; Tasks: associate

; Расширения: пункт «Открыть с помощью» и список в параметрах Windows

Root: HKCU; Subkey: "Software\Classes\.mp4\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.m4v\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.mov\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.mkv\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.webm\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.avi\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.wmv\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.mpg\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.mpeg\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.m2ts\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.mts\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.ts\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.flv\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.3gp\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\.ogv\OpenWithProgids"; ValueType: string; ValueData: ""; ValueName: "OptiPlayer.Video"; Flags: uninsdeletevalue; Tasks: associate

Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mp4"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".m4v"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mov"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mkv"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".webm"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".avi"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".wmv"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mpg"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mpeg"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".m2ts"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mts"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".ts"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".flv"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".3gp"; ValueData: "OptiPlayer.Video"; Tasks: associate
Root: HKCU; Subkey: "Software\OptiPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".ogv"; ValueData: "OptiPlayer.Video"; Tasks: associate

; Контекстное меню проводника «Воспроизвести в OptiPlayer»
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4v\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4v\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wmv\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wmv\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mpg\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mpg\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mpeg\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mpeg\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m2ts\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m2ts\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mts\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mts\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ts\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ts\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flv\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flv\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.3gp\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.3gp\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogv\shell\OptiPlayer"; ValueType: string; ValueName: ""; ValueData: "Воспроизвести в OptiPlayer"; Flags: uninsdeletekey; Tasks: associate
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogv\shell\OptiPlayer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
