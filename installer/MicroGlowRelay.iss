; Per-user installer. Build with build-installer.ps1 after the EXE exists.
#ifndef AppVersion
  #error AppVersion must be provided by build-installer.ps1
#endif
#ifndef SourceExe
  #error SourceExe must be provided by build-installer.ps1
#endif

[Setup]
AppId={{6C96581B-6584-4AE6-BAAD-07103B833E4C}
AppName=MicroGlow Relay
AppVersion={#AppVersion}
AppPublisher=MicroGlow
AppPublisherURL=https://www.microglow.com.cn
LicenseFile=..\docs\USER-AGREEMENT.md
; 刘总 2026-11-17 要求：标准安装路径 C:\Program Files\MicroGlow Relay。
; {autopf} 在 64 位安装模式下解析为 C:\Program Files；写入需要管理员权限。
DefaultDirName={autopf}\MicroGlow Relay
DefaultGroupName=MicroGlow Relay
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist-installer
OutputBaseFilename=MicroGlow-Relay-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\MicroGlowRelay.exe
SetupIconFile=..\assets\app.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
; 简体中文为 Inno Setup 官方仓库的“非官方翻译”，并未随编译器分发。
; 随库存放，保证任何机器上都能按同一流程构建双语安装包。
Name: "chinesesimplified"; MessagesFile: "languages\ChineseSimplified.isl"

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "MicroGlowRelay.exe"; Flags: ignoreversion
Source: "..\docs\USER-AGREEMENT.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\PRIVACY-POLICY.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\USER-GUIDE.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\THIRD-PARTY-NOTICES.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\licenses\*"; DestDir: "{app}\docs\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MicroGlow Relay"; Filename: "{app}\MicroGlowRelay.exe"
Name: "{autodesktop}\MicroGlow Relay"; Filename: "{app}\MicroGlowRelay.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Run]
; 管理员安装后仍以原用户身份启动，避免提权运行 GUI。
Filename: "{app}\MicroGlowRelay.exe"; Description: "{cm:LaunchProgram,MicroGlow Relay}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
var
  StatisticsPage: TInputOptionWizardPage;
  PrivacyButton: TNewButton;
  ConsentChoice: Integer;

#include "TelemetryConsent.iss"

procedure StatisticsChanged(Sender: TObject);
begin
  if Assigned(StatisticsPage) and (WizardForm.CurPageID = StatisticsPage.ID) then
    WizardForm.NextButton.Enabled := StatisticsPage.SelectedValueIndex >= 0;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if Assigned(StatisticsPage) and (CurPageID = StatisticsPage.ID) then StatisticsChanged(nil);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if Assigned(StatisticsPage) and (CurPageID = StatisticsPage.ID) then begin
    ConsentChoice := StatisticsPage.SelectedValueIndex;
    Result := (ConsentChoice = 0) or (ConsentChoice = 1);
  end;
end;

procedure ViewPrivacyPolicy(Sender: TObject);
var
  ErrorCode: Integer;
begin
  ExtractTemporaryFile('PRIVACY-POLICY.md');
  ShellExec('open', ExpandConstant('{sys}\notepad.exe'),
    '"' + ExpandConstant('{tmp}\PRIVACY-POLICY.md') + '"', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;

procedure InitializeWizard;
var
  Description: String;
begin
  { An unattended install has no page to answer. Creating it anyway would leave
    "Next" disabled and abort the wizard; CurStepChanged already keeps a fresh
    silent install opted out, so the page is skipped entirely. }
  if WizardSilent then Exit;
  if ActiveLanguage = 'chinesesimplified' then begin
    Description := '可在《隐私政策》中查看收集的数据类型和用途。';
    StatisticsPage := CreateInputOptionPage(wpLicense, '请给我们一点光，让 Relay 越来越好用', '诚邀您加入我们的改进计划', Description, True, False);
    StatisticsPage.Add('同意加入（推荐）');
    StatisticsPage.Add('不同意加入');
  end else begin
    Description := 'See the Privacy Policy for the data types collected and their purposes.';
    StatisticsPage := CreateInputOptionPage(wpLicense, 'Give us a little light to make Relay better', 'We warmly invite you to join our improvement program.', Description, True, False);
    StatisticsPage.Add('Agree to join (Recommended)');
    StatisticsPage.Add('Do not agree to join');
  end;
  ConsentChoice := -1;
  StatisticsPage.Values[0] := False;
  StatisticsPage.Values[1] := False;
  StatisticsPage.CheckListBox.OnClickCheck := @StatisticsChanged;
  PrivacyButton := TNewButton.Create(WizardForm);
  PrivacyButton.Parent := StatisticsPage.Surface;
  PrivacyButton.SetBounds(0, StatisticsPage.SurfaceHeight - ScaleY(40), ScaleX(160), ScaleY(28));
  if ActiveLanguage = 'chinesesimplified' then PrivacyButton.Caption := '查看隐私政策'
  else PrivacyButton.Caption := 'View Privacy Policy';
  PrivacyButton.OnClick := @ViewPrivacyPolicy;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConsentPath: String;
begin
  if CurStep <> ssPostInstall then Exit;
  ConsentPath := ExpandConstant('{localappdata}\MicroGlow Relay\data\telemetry-consent.json');
  { Silent upgrades preserve existing authorization; fresh silent installs never opt in. }
  if WizardSilent and FileExists(ConsentPath) then Exit;
  if (not WizardSilent) and (ConsentChoice < 0) then
    RaiseException('Please choose whether to join the improvement program.');
  SaveStatisticsConsent(ConsentPath, (not WizardSilent) and (ConsentChoice = 0));
end;
