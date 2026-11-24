// Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
// SPDX-License-Identifier: Apache-2.0
{ Shared by the production installer and the isolated Pascal persistence probe. }
procedure SaveStatisticsConsent(ConsentPath: String; AllowStatistics: Boolean);
var
  BackupPath, TempPath, Payload, ConsentValue, Disclosure: String;
begin
  ConsentValue := 'false';
  Disclosure := 'null';
  if AllowStatistics then begin
    ConsentValue := 'true';
    Disclosure := '"channel-exit-upload-2026-10"';
  end;
  if not ForceDirectories(ExtractFileDir(ConsentPath)) then
    RaiseException('Cannot create the statistics consent directory.');
  BackupPath := ConsentPath + '.before-installer-' + GetDateTimeString('yyyymmddhhnnsszzz', '-', ':') + '.bak';
  TempPath := ConsentPath + '.installer.tmp';
  Payload := '{"schema":1,"consent":' + ConsentValue + ',"schema_version":2,"consent_version":"v2.2026-09","upload_disclosure":' + Disclosure + '}';
  { ASCII JSON is valid UTF-8. Stage before moving the existing authorization. }
  if not SaveStringToFile(TempPath, Payload, False) then
    RaiseException('Cannot save statistics consent.');
  if FileExists(ConsentPath) and not RenameFile(ConsentPath, BackupPath) then
    RaiseException('Cannot back up existing statistics consent.');
  if not RenameFile(TempPath, ConsentPath) then begin
    if FileExists(BackupPath) then RenameFile(BackupPath, ConsentPath);
    RaiseException('Cannot finalize statistics consent.');
  end;
end;
