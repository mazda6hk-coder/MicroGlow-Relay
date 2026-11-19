# MicroGlow Relay – Benutzerhilfe

## Verbindung herstellen

1. Tragen Sie auf der Seite „Modelle“ den Anbieter-Endpunkt und den API-Schlüssel ein und fügen Sie Modelle hinzu.
2. Beenden Sie die Codex-Desktop-App und die Befehlszeilenversion regulär. Schalten Sie Relay ein, warten Sie auf die Betriebsbereitschaft und aktivieren Sie die Codex-Anbindung gemäß den Hinweisen.
3. Starten Sie Codex erneut. Verwenden Sie für Claude Code den zugehörigen Verbindungsschalter und folgen Sie den Hinweisen.

Das Ausschalten oder reguläre Beenden von Relay stellt den nativen Codex-Zugang wieder her. Das Minimieren in den Infobereich beendet die App nicht. Wählen Sie dort den Befehl zum Beenden.

Beenden Sie zuerst Codex / Claude Code und danach Relay. Relay stellt die Verbindungseinstellungen vor dem Beenden wieder her. Schlägt die Wiederherstellung fehl, bleibt Relay geöffnet und zeigt den Grund an. Beheben Sie das Problem und versuchen Sie erneut, Relay zu beenden.

## Modelle und Sitzungen

- Wählen Sie das gewünschte Modell innerhalb Ihrer Codex-Sitzung. Das Standardmodell legen Sie auf der Seite „Modelle“ fest. Dort können Sie Konfigurationen hinzufügen, bearbeiten, suchen und löschen sowie mehrere Kanäle für dasselbe Modell einrichten.
- Entspricht der gespeicherte Modellname exakt einem nativen Codex-Modellnamen, erscheint der Eintrag in der Codex-Modellauswahl. Eine Konfiguration mit dem Namen `gpt-6-astra` macht beispielsweise diesen Eintrag verfügbar. Nach dem Löschen der letzten zugehörigen Konfiguration verschwindet er. Namen ohne passende Konfiguration werden nicht angeboten.
- Ein über Relay an einen Drittanbieter weitergeleiteter nativer Eintrag kann das Gespräch fortsetzen. Verschlüsselte Denkinhalte werden dabei entfernt; der Drittanbieter erhält Zusammenfassungen der Denkschritte und Text. Nur OpenAI kann die von OpenAI verschlüsselten Inhalte lesen. Um die verschlüsselte Denkkette zu erhalten, verwenden Sie einen Kanal mit dem Endpunkt `api.openai.com` und Ihrem eigenen OpenAI-Schlüssel.
- Die Sitzungsfortsetzung ändert nur die Zugangskonfiguration der ausgewählten Sitzung, nicht den Gesprächsverlauf. Beenden Sie Codex vorher gemäß den Hinweisen regulär.
- Für beide Konvertierungsrichtungen gilt: Codex-Desktop-App und Befehlszeilenversion beenden, Sitzung und Ziel auswählen und die Änderung anwenden. Codex muss weder laufen noch angemeldet sein, und Relay muss nicht eingeschaltet sein. Vor dem Wechsel zu Relay muss eine Modellkonfiguration gespeichert sein.
- Beim Wechsel zurück zum offiziellen Zugang wird zuerst das neueste geeignete offizielle Sitzungsmodell verwendet. Ist keines verfügbar, wird die Sicherung der ursprünglichen offiziellen Metadaten dieser Sitzung genutzt. Fehlt für beides eine vertrauenswürdige Quelle, wird die Konvertierung angehalten.
- Schalten Sie nach der Konvertierung Relay ein, bevor Sie Codex mit Relay-Zugang starten. Für den offiziellen Zugang schalten Sie Relay vor dem Start von Codex aus. Bei offiziellen Diensten kann Codex weiterhin eine Anmeldung verlangen.

## Häufige Fragen

### Keine Modelle vorhanden?

Eine Neuinstallation enthält keine vorkonfigurierten Modelle. Fügen Sie Ihren Anbieter und Ihre Modelle hinzu. Beim Abrufen verfügbarer Modelle können Sie mehrere auswählen; jedes wird als eigene Konfiguration gespeichert.

### Anfragen schlagen fehl?

Prüfen Sie Endpunkt, API-Schlüssel, Guthaben und Modellnamen. Senden Sie bei Rückmeldungen keine Schlüssel oder Gesprächsinhalte mit.

### Woher stammen die Token-Statistiken?

Sie stammen aus den Nutzungsangaben der ursprünglichen Antwort des Anbieters. Für die verschiedenen Anzeigen werden keine zusätzlichen Anfragen gesendet.

### Wie verwende ich Trip Token A/B?

A und B sind unabhängige Zwischensummen. Jede zählt ihren ausgewählten Bereich ab ihrem eigenen Rücksetzzeitpunkt. Sie laufen über Mitternacht und Neustarts hinweg weiter und werden nur durch „Zurücksetzen“ in der jeweiligen Spalte zurückgesetzt. Tageswerte und Anfrageprotokolle bleiben erhalten; das vorherige Intervall wird im Fahrtverlauf archiviert. Nutzen und benennen Sie beide Zähler für unterschiedliche Aufgaben. Fehlgeschlagene Anfragen zählen weiterhin als Anfragen; die Token-Summe richtet sich nach den Nutzungsangaben des Anbieters.

### Wie funktionieren Datumsfilter?

Wählen Sie ein Datum sowie Tag, Woche, Monat, Quartal oder Jahr, um den entsprechenden Zeitraum anzuzeigen. Der Nenner der Fehlerquote ist die Gesamtzahl der Anfragen im gewählten Zeitraum.

### Wie funktioniert die Einwilligung für anonyme Statistiken?

Bei der Installation ist keine der beiden Einwilligungsoptionen vorausgewählt. Entscheiden Sie einmal, ob Sie teilnehmen oder ablehnen möchten. Diese Wahl steuert lokale anonyme Statistiken und die Upload-Erlaubnis ohne zweite Bestätigung. Eine Ablehnung beeinträchtigt weder Installation noch Nutzung. Sie können die Entscheidung in den Einstellungen ändern. Neue unbeaufsichtigte Installationen sind standardmäßig deaktiviert; unbeaufsichtigte Upgrades übernehmen vorhandene Einwilligungen. Ein Upload wird nur beim regulären Beenden versucht. Nach einem Fehler wird beim nächsten Beenden erneut versucht. Alle Felder und das Speicherverhalten stehen in der Datenschutzerklärung.

### Wie funktionieren Updates?

Bei aktivierter automatischer Prüfung sucht Relay nach dem Start und alle 24 Stunden im Hintergrund nach Updates. GitHub ist die Hauptquelle, die offizielle Website die Ersatzquelle. Neue Installationspakete werden automatisch heruntergeladen und auf Größe sowie SHA256 geprüft. Öffnen Sie das Installationsprogramm über „Update installieren“ in den Einstellungen und beenden Sie Relay vor der Installation regulär. Installationsprogramme werden niemals automatisch ausgeführt. Mit „Jetzt prüfen“ können Sie manuell prüfen.

### Daten und Deinstallation

Die Einstellungen zeigen das Datenverzeichnis. Eine Deinstallation behält Benutzerdaten bei. Zum Entfernen beenden Sie Relay regulär, sichern benötigte Inhalte und entfernen anschließend nur dieses Datenverzeichnis. Löschen Sie nicht das Codex-Verzeichnis.

## Kontakt

- Website: https://www.microglow.com.cn
- Produktsupport: support@microglow.com.cn
- Datenschutz: privacy@microglow.com.cn
- Sicherheitsmeldungen: security@microglow.com.cn
