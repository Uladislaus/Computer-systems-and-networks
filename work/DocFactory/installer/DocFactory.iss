; Inno Setup script — собрать Setup.exe после build_exe.bat
; Нужен Inno Setup 6: https://jrsoftware.org/isinfo.php
; Исходный exe: ..\dist\DocFactory.exe

#define MyAppName "DocFactory"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Belhydromet / local tools"
#define MyAppExeName "DocFactory.exe"

[Setup]
AppId={{8F3C2A1B-9D47-4E6A-B2C1-DOCFACTORY0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DocFactory
DefaultGroupName=DocFactory
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=DocFactorySetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
Source: "..\dist\DocFactory.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить DocFactory"; Flags: nowait postinstall skipifsilent

[Code]
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;
