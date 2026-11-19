; Isolated persistence probe for TelemetryConsent.iss. Never shipped.
; Build with ISCC, run with /VERYSILENT plus:
;   /CONSENTPATH=<dir>\telemetry-consent.json /ALLOW=true|false
[Setup]
AppName=MicroGlow Relay Consent Probe
AppVersion=1.0
CreateAppDir=no
CreateUninstallRegKey=no
PrivilegesRequired=lowest
UninstallFilesDir={tmp}\MicroGlowConsentProbe
OutputDir={#SourcePath}\..\work\installer-consent-probe
OutputBaseFilename=ConsentProbe

[Code]
#include "TelemetryConsent.iss"

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep <> ssPostInstall then Exit;
  SaveStatisticsConsent(ExpandConstant('{param:CONSENTPATH}'),
    ExpandConstant('{param:ALLOW}') = 'true');
end;
