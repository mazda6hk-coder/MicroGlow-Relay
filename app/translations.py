# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Static desktop UI translations; no network at runtime."""
TRANSLATIONS = {'de': {
        '检测到更高优先级的 Claude 配置：{0} · 可能覆盖 Relay 接入，未改动': 'Claude-Konfiguration mit höherer Priorität gefunden: {0} · kann den Relay-Zugriff übersteuern (unverändert gelassen)','\n目标模型：{0}': 'Zielmodell: {0}',
        '\n该会话使用历史路由标识，按其它接入处理。': 'Diese Sitzung verwendet die historische Routenidentifikation und wird wie '
                                  'ein anderer Zugriff behandelt.',
        '\n该会话由其它工具接入。': 'Auf diese Sitzung wird von anderen Tools zugegriffen.',
        'AI 连接、路由状态与最近请求总览': 'Übersicht über KI-Verbindungen, Routing-Status und aktuelle Anfragen',
        'Codex · ChatGPT 订阅': 'Codex · ChatGPT Abonnieren',
        'Codex 已不再使用本路由器': 'Codex verwendet diesen Router nicht mehr',
        'Codex 已不再指向本路由器': 'Codex verweist nicht mehr auf diesen Router',
        'Codex 已接入': 'Codex ist verbunden',
        'Codex 已接入 · 已备份 {0}': 'Codex ist verbunden · Gesichert {0}',
        'Codex 已重新指向本路由器': 'Codex wurde zu diesem Router umgeleitet',
        'Codex 已重新接入 · 已备份 {0}': 'Codex wurde wieder verbunden · Gesichert {0}',
        'Codex 当前指向': 'Codex weist derzeit darauf hin',
        'Codex 接入': 'Codex-Zugriff',
        'Codex 接入已失效：配置被其它程序改写，请到“Codex 接入”页重新接入': 'Der Codex-Zugriff ist abgelaufen: Die Konfiguration '
                                                   'wurde von anderen Programmen überschrieben. Bitte gehen '
                                                   'Sie zur Seite „Codex-Zugriff“, um erneut darauf '
                                                   'zuzugreifen',
        'Codex 配置': 'Codex-Konfiguration',
        'Codex 配置仍然指向本地路由，请先点击“重新接入”或启动本地服务。': 'Die Codex-Konfiguration verweist weiterhin auf die lokale '
                                               'Route. Bitte klicken Sie auf „Erneut verbinden“ oder starten '
                                               'Sie zuerst den lokalen Dienst.',
        'Codex 配置在接入后被其他程序改写过（例如切换模型通道），当前请求不会经过本程序。点击“重新接入”即可按现在的情况重新写入并备份。': 'Die Codex-Konfiguration '
                                                                               'wurde nach dem Zugriff von '
                                                                               'anderen Programmen neu '
                                                                               'geschrieben (z. B. beim '
                                                                               'Wechseln des Modellkanals), '
                                                                               'und die aktuelle Anforderung '
                                                                               'wird dieses Programm nicht '
                                                                               'durchlaufen. Klicken Sie auf '
                                                                               '„Erneut verbinden“, um '
                                                                               'entsprechend der aktuellen '
                                                                               'Situation neu zu schreiben '
                                                                               'und zu sichern.',
        'Codex 配置已恢复 · 原备份 {0}': 'Codex-Konfiguration wiederhergestellt · Originalsicherung {0}',
        'Codex 配置已被其它程序改写，接入已失效，请重新接入': 'Die Codex-Konfiguration wurde von anderen Programmen überschrieben '
                                        'und der Zugriff ist abgelaufen. Bitte greifen Sie erneut zu.',
        'Ollama（本机）': 'Ollama (einheimisch)',
        'Relay 接入配置未就绪；没有备份或修改会话。': 'Die Konfiguration des Relay-Zugriffs ist nicht bereit; Es gibt keine '
                                    'Sicherungs- oder Änderungssitzungen.',
        'iOS 风格': 'iOS-Stil',
        '{0:.1f} 万': '{0:.1f} Millionen',
        '{0:.2f} 亿': '{0:.2f} Milliarden',
        '{0:.2f} 秒': '{0:.2f} Sekunden',
        '{0} 启动失败': '{0} konnte nicht gestartet werden',
        '{0} 已启动': '{0} ist aktiviert',
        '{0} 已在运行。': '{0} läuft bereits.',
        '{0} 的目标模式': 'Zielmuster für {0}',
        '上下文上限': 'Kontextkappe',
        '上下文窗口大小。': 'Größe des Kontextfensters.',
        '上次退出：有对象未切换，原配置与操作记录已保留，请检查后手动处理。': 'Letzter Ausgang: Es gibt Objekte, die nicht gewechselt wurden, '
                                             'und die ursprünglichen Konfigurations- und Betriebsdatensätze '
                                             'wurden beibehalten. Bitte überprüfen und bearbeiten Sie diese '
                                             'manuell.',
        '上游模型支持函数工具调用时开启': 'Das Upstream-Modell unterstützt das Einschalten, wenn das Funktionstool '
                           'aufgerufen wird',
        '上游模型支持图片输入时开启': 'Aktivieren Sie diese Option, wenn das Upstream-Modell die Bildeingabe unterstützt',
        '下一页': 'Nächste Seite',
        '中': 'Mitte',
        '主题 · {0}': 'Themen · {0}',
        '主题模式': 'Themenmodus',
        '仅实际退出时生效，关闭到托盘不执行。保留所有会话的模型和 Provider、全局默认模型及其它工具的配置；未检测到订阅登录或存在外部改动时不执行。': 'Es wird erst wirksam, '
                                                                                     'wenn Sie es '
                                                                                     'tatsächlich beenden. '
                                                                                     'Das Schließen des '
                                                                                     'Fachs hat keine '
                                                                                     'Wirkung. Behält die '
                                                                                     'Konfiguration von '
                                                                                     'Modellen und '
                                                                                     'Anbietern, globalen '
                                                                                     'Standardmodellen und '
                                                                                     'anderen Tools für alle '
                                                                                     'Sitzungen bei; wird '
                                                                                     'nicht ausgeführt, wenn '
                                                                                     'die '
                                                                                     'Abonnementanmeldung '
                                                                                     'nicht erkannt wird '
                                                                                     'oder externe '
                                                                                     'Änderungen vorliegen.',
        '仅调整所选会话的模型接入配置，不读取或改写历史对话；其它工具的会话不会自动接管。': 'Es wird nur die Modellzugriffskonfiguration der '
                                                    'ausgewählten Sitzung angepasst, historische '
                                                    'Konversationen werden nicht gelesen oder neu '
                                                    'geschrieben; Sitzungen anderer Tools werden nicht '
                                                    'automatisch übernommen.',
        '今日 Token 消耗': 'Heutiger Token-Verbrauch',
        '今日 Token：{0:,}': 'Heutiger Token: {0:,}',
        '今日成功率': 'Heutige Erfolgsquote',
        '今日暂无请求': 'Heute keine Anfragen',
        '今日请求': 'Fordern Sie noch heute an',
        '以下字段在接入后被其他程序改过：\n{0}\n\n仍然强制恢复为接入前的状态吗？（会先备份当前配置）': 'Folgende Felder wurden nach dem Zugriff von '
                                                              'anderen Programmen verändert:\n'
                                                              '{0}\n'
                                                              '\n'
                                                              'Immer noch gezwungen, den Zustand vor dem '
                                                              'Zugriff wiederherzustellen? (Die aktuelle '
                                                              'Konfiguration wird zuerst gesichert)',
        '会话兼容': 'Sitzungskompatibel',
        '会话兼容选项已保存': 'Sitzungskompatibilitätsoptionen gespeichert',
        '会话切换执行结果': 'Ergebnisse der Sitzungsumschaltung',
        '会话列表': 'Gesprächsliste',
        '会话列表读取状态': 'Lesestatus der Sitzungsliste',
        '会话名称': 'Sitzungsname',
        '会话配置操作正在完成，请稍后再退出。': 'Der Sitzungskonfigurationsvorgang wird abgeschlossen. Bitte beenden Sie ihn '
                              'später.',
        '会话：{0}\n当前：{1}\n目标：{2}{3}{4}\n确认 Codex 已正常退出？确定后先备份原配置，再切换并校验；不修改历史正文。': 'Sitzung: {0}\n'
                                                                                  'Aktuell: {1}\n'
                                                                                  'Ziel: {2}{3}{4}\n'
                                                                                  'Bestätigt, dass Codex '
                                                                                  'normal beendet wurde? '
                                                                                  'Sichern Sie nach der '
                                                                                  'Bestätigung zunächst die '
                                                                                  'ursprüngliche '
                                                                                  'Konfiguration, wechseln '
                                                                                  'Sie dann und überprüfen '
                                                                                  'Sie sie. Ändern Sie den '
                                                                                  'historischen Text nicht.',
        '传输中': 'Senden',
        '低': 'Niedrig',
        '使用步骤': 'Nutzungsschritte',
        '供应商': 'Anbieter',
        '供应商名称': 'Name des Lieferanten',
        '供应商未返回模型列表，请手动填写。': 'Der Lieferant hat die Modellliste nicht zurückgesandt, bitte füllen Sie sie '
                             'manuell aus.',
        '保存后使用 Windows DPAPI 加密存储。': 'Verwenden Sie Windows DPAPI, um den Speicher nach dem Speichern zu '
                                     'verschlüsseln.',
        '保存退出选项与核心路径': 'Exit-Optionen und Kernpfad speichern',
        '保存配置': 'Konfiguration speichern',
        '信息': 'Information',
        '修改模型': 'Modell ändern',
        '修改模型配置': 'Modellkonfiguration ändern',
        '修改模式为': 'Ändern Sie den Modus auf',
        '停止接入': 'Zugriff stoppen',
        '全部': 'alle',
        '共 {0} 个模型配置 · 点击卡片切换，点击铅笔图标编辑参数': 'Insgesamt {0} Modellkonfigurationen · Klicken Sie zum Wechseln '
                                           'auf die Karte und zum Bearbeiten der Parameter auf das '
                                           'Stiftsymbol',
        '关于': 'um',
        '关闭': 'Schließung',
        '关闭请求详情': 'Anfragedetails schließen',
        '其它接入': 'Anderer Zugang',
        '其它接入会话需明确选择目标；Relay 不自动接管。': 'Andere Zugriffssitzungen erfordern eine explizite Zielauswahl. Das '
                                      'Relais übernimmt nicht automatisch.',
        '准备读取会话索引。': 'Bereiten Sie sich darauf vor, den Sitzungsindex zu lesen.',
        '切换成功：{0} → {1}。原配置已备份，写入结果已校验；下方列表已刷新。': 'Umstellung erfolgreich: {0} → {1}. Die ursprüngliche '
                                                  'Konfiguration wurde gesichert und die Schreibergebnisse '
                                                  'wurden überprüft; Die folgende Liste wurde aktualisiert.',
        '切换未完成：{0}，校验通过 {1} / {2}。原配置备份与操作记录已保留，不会自动重写会话。': 'Umstellung nicht abgeschlossen: {0}, '
                                                            'Überprüfung bestanden {1}/{2}. Die '
                                                            'ursprünglichen Konfigurationssicherungs- und '
                                                            'Betriebsdatensätze wurden beibehalten und die '
                                                            'Sitzung wird nicht automatisch neu geschrieben.',
        '切换模型': 'Modell wechseln',
        '删除后将无法自动恢复，需要重新填写 API KEY。': 'Nach dem Löschen kann es nicht automatisch wiederhergestellt werden '
                                      'und der API-SCHLÜSSEL muss erneut eingegeben werden.',
        '删除此模型配置': 'Löschen Sie diese Modellkonfiguration',
        '删除这条模型配置？': 'Diese Modellkonfiguration löschen?',
        '刷新会话列表': 'Sitzungsliste aktualisieren',
        '刷新接入': 'Zugriff aktualisieren',
        '匿名使用统计': 'Anonyme Nutzungsstatistiken',
        '匿名使用统计已关闭': 'Anonyme Nutzungsstatistiken sind deaktiviert',
        '匿名使用统计已启用': 'Anonyme Nutzungsstatistiken sind aktiviert',
        '匿名使用统计明确同意开关': 'Anonyme Nutzungsstatistiken, expliziter Zustimmungsschalter',
        '单次最大输出。': 'Einzelne maximale Leistung.',
        '发起请求后，可在此查看不含正文的安全摘要。': 'Nach einer Anfrage kann hier eine Sicherheitszusammenfassung ohne Text '
                                 'eingesehen werden.',
        '取消': 'Stornieren',
        '可点击“读取”从供应商获取可用模型。': 'Sie können auf „Lesen“ klicken, um die verfügbaren Modelle vom Anbieter zu '
                              'erhalten.',
        '国家信息不由客户端采集；未来上传阶段仅允许服务端接入层瞬时推断。撤回后立即停止产生新的遥测数据。': 'Nationale Informationen werden vom Kunden nicht '
                                                            'erhoben; In der zukünftigen Upload-Phase ist '
                                                            'nur eine sofortige Schlussfolgerung auf der '
                                                            'Serverzugriffsebene zulässig. Stoppt die '
                                                            'Generierung neuer Telemetriedaten unmittelbar '
                                                            'nach der Auszahlung.',
        '图片支持': 'Bildunterstützung',
        '图片输入': 'Bildeingabe',
        '在“模型管理”页面添加至少一个模型，并点击模型卡片进行选择。': 'Fügen Sie auf der Seite „Modellverwaltung“ mindestens ein Modell '
                                          'hinzu und klicken Sie auf die Modellkarte, um es auszuwählen.',
        '填写供应商公布的完整端点；程序按原样请求，不会改写路径。': 'Geben Sie den vollständigen Endpunkt ein, wie vom Anbieter '
                                        'veröffentlicht. Das Programm fordert es unverändert an und schreibt '
                                        'den Pfad nicht neu.',
        '复制': 'Kopie',
        '外观': 'Aussehen',
        '失败': 'scheitern',
        '失败 {0}': 'Fehlgeschlagen {0}',
        '实时显示请求、连接与配置变更记录': 'Echtzeitanzeige von Anforderungs-, Verbindungs- und '
                            'Konfigurationsänderungsdatensätzen',
        '客户端接入': 'Client-Zugriff',
        '将撤销本程序对 Codex 配置所做的修改，并停止本地服务。': 'Von diesem Programm vorgenommene Änderungen an der '
                                          'Codex-Konfiguration werden rückgängig gemacht und der lokale '
                                          'Dienst wird gestoppt.',
        '尚未接入': 'Noch nicht verbunden',
        '尚未接入 Codex': 'Noch nicht mit Codex verbunden',
        '尚未配置模型': 'Modell noch nicht konfiguriert',
        '展开已读取的模型列表；也可直接手动输入模型名称': 'Erweitern Sie die Liste der Lesemodelle. Sie können den Modellnamen auch '
                                   'direkt manuell eingeben',
        '工具调用': 'Werkzeugaufruf',
        '已取消；没有备份或修改会话。': 'Abgesagt; Keine Sicherungs- oder Änderungssitzungen.',
        '已开启': 'Bereits eingeschaltet',
        '已归档': 'Archiviert',
        '已按当前模型回填全部原参数；API KEY 已解密加载并默认遮蔽。': 'Alle ursprünglichen Parameter wurden gemäß dem aktuellen '
                                             'Modell aufgefüllt; API KEY wurde standardmäßig entschlüsselt, '
                                             'geladen und maskiert.',
        '已接入': 'Bereits verbunden',
        '已接入 Codex，但端口无法启动：{0}': 'Mit Codex verbunden, aber der Port kann nicht gestartet werden: {0}',
        '已接入但服务未运行': 'Verbunden, aber der Dienst wird nicht ausgeführt',
        '已知供应商会自动匹配；自定义中转请按实际选择。': 'Bekannte Lieferanten werden automatisch abgeglichen; Für eine '
                                   'individuelle Übertragung wählen Sie bitte entsprechend den tatsächlichen '
                                   'Bedingungen aus.',
        '已读取 {0} 个模型': '{0} Modelle gelesen',
        '已读取 {0} 个模型，请从列表选择': '{0} Modelle gelesen, bitte aus der Liste auswählen',
        '帮助改进 MicroGlow Relay': 'Helfen Sie mit, MicroGlow Relay zu verbessern',
        '平均耗时 {0:.2f} 秒': 'Durchschnittlich verbrachte Zeit {0:.2f} Sekunden',
        '应用': 'Anwendung',
        '归档会话仅供查看；请先在 Codex 中取消归档，再退出 Codex 后操作。': 'Archivierte Sitzungen dienen nur der Ansicht; Bitte '
                                                   'brechen Sie zuerst die Archivierung in Codex ab und '
                                                   'beenden Sie dann Codex, bevor Sie fortfahren.',
        '当前使用': 'derzeit im Einsatz',
        '当前模型已切换': 'Das aktuelle Modell wurde umgestellt',
        '当前模式': 'Aktueller Modus',
        '当前路由模型': 'Aktuelles Routing-Modell',
        '思考强度': 'Denkintensität',
        '思考模式': 'Denkmodell',
        '恢复 Codex 配置？': 'Codex-Konfiguration wiederherstellen?',
        '恢复配置': 'Konfiguration wiederherstellen',
        '成功': 'Erfolg',
        '成功 {0} · 失败 {1}': 'Erfolg {0} · Fehler {1}',
        '所属项目名称': 'Projektname',
        '打开主界面': 'Öffnen Sie die Hauptoberfläche',
        '打开数据目录': 'Datenverzeichnis öffnen',
        '把本地路由服务接入 Codex，并在需要时完整恢复原始配置': 'Verbinden Sie lokale Routing-Dienste mit Codex und stellen Sie bei '
                                         'Bedarf die ursprüngliche Konfiguration vollständig wieder her',
        '接入 Codex': 'Greifen Sie auf den Codex zu',
        '接入信息': 'auf Informationen zugreifen',
        '接入信息已刷新': 'Die Zugangsinformationen wurden aktualisiert',
        '接入已失效': 'Der Zugriff ist abgelaufen',
        '接入时会先完整备份现有 Codex 配置，随时可以一键恢复。': 'Beim Verbinden wird die bestehende Codex-Konfiguration '
                                          'vollständig gesichert und kann jederzeit mit einem Klick '
                                          'wiederhergestellt werden.',
        '接口协议': 'Schnittstellenprotokoll',
        '接口地址': 'Schnittstellenadresse',
        '操作': 'arbeiten',
        '操作未完成；原配置与已有备份保留。请重新检查，不会回显底层数据。': 'Der Vorgang ist nicht abgeschlossen; Die ursprüngliche '
                                            'Konfiguration und vorhandene Backups bleiben erhalten. Bitte '
                                            'überprüfen Sie noch einmal, die zugrunde liegenden Daten werden '
                                            'nicht wiedergegeben.',
        '支持推理参数时开启，否则可能产生 400': 'Aktivieren Sie diese Option, wenn Inferenzparameter unterstützt werden. '
                                'Andernfalls werden möglicherweise 400 generiert',
        '收起模型': 'Modell einklappen',
        '数据传输': 'Datenübertragung',
        '数据位置': 'Datenspeicherort',
        '文本': 'Text',
        '开始日期': 'Startdatum',
        '无法读取': 'Kann nicht gelesen werden',
        '日志': 'Protokoll',
        '时间': 'Zeit',
        '结束日期': 'Enddatum',
        '是否明确同意启用匿名使用统计？\n\n仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。不收集请求或响应正文、文件、代码、密钥、IP、原始错误和逐请求记录。': 'Stimmen '
                                                                                                        'Sie '
                                                                                                        'der '
                                                                                                        'Aktivierung '
                                                                                                        'anonymer '
                                                                                                        'Nutzungsstatistiken '
                                                                                                        'ausdrücklich '
                                                                                                        'zu?\n'
                                                                                                        '\n'
                                                                                                        'Es '
                                                                                                        'werden '
                                                                                                        'nur '
                                                                                                        'die '
                                                                                                        'Anzahl '
                                                                                                        'der '
                                                                                                        'täglichen '
                                                                                                        'Aufrufe, '
                                                                                                        'Erfolge/Fehler, '
                                                                                                        'Token, '
                                                                                                        'feste '
                                                                                                        'Verzögerungsintervalle, '
                                                                                                        'Standardfehlerkategorien '
                                                                                                        'und '
                                                                                                        'Rollbacks '
                                                                                                        'akkumuliert. '
                                                                                                        'Anfrage- '
                                                                                                        'oder '
                                                                                                        'Antworttexte, '
                                                                                                        'Dateien, '
                                                                                                        'Codes, '
                                                                                                        'Schlüssel, '
                                                                                                        'IPs, '
                                                                                                        'Rohfehler '
                                                                                                        'und '
                                                                                                        'die '
                                                                                                        'Protokollierung '
                                                                                                        'pro '
                                                                                                        'Anfrage '
                                                                                                        'werden '
                                                                                                        'nicht '
                                                                                                        'erfasst.',
        '显示密钥': 'Schlüssel anzeigen',
        '智谱 AI': 'Weisheitsspektrum KI',
        '暂无日志 · 服务启动或配置变更后会显示在这里': 'Noch keine Protokolle · Wird hier angezeigt, nachdem der Dienst '
                                   'gestartet oder die Konfiguration geändert wurde.',
        '暂无记录': 'Noch keine Aufzeichnung',
        '暂无请求记录': 'Noch kein Anfragedatensatz',
        '最近活动': 'Aktuelle Aktivitäten',
        '服务已停止': 'Der Dienst wurde gestoppt',
        '服务运行中': 'Der Dienst läuft',
        '未命名会话': 'unbenannte Sitzung',
        '未开启': 'Nicht eingeschaltet',
        '未接入': 'Nicht verbunden',
        '未检测到 ChatGPT 订阅登录；没有备份或修改会话。': 'Kein ChatGPT-Abonnement-Login erkannt; Es wurden keine Sitzungen '
                                        'gesichert oder geändert.',
        '未运行': 'Läuft nicht',
        '本地地址': 'lokale Adresse',
        '本地接口只监听 127.0.0.1，并要求随机访问令牌；历史 Backup 文件保存在 Codex 配置目录，恢复凭据保存在数据目录的 microglow-relay-codex-receipt.json。': 'Die '
                                                                                                                   'lokale '
                                                                                                                   'Schnittstelle '
                                                                                                                   'überwacht '
                                                                                                                   'nur '
                                                                                                                   '127.0.0.1 '
                                                                                                                   'und '
                                                                                                                   'erfordert '
                                                                                                                   'ein '
                                                                                                                   'Direktzugriffstoken; '
                                                                                                                   'Historische '
                                                                                                                   'Sicherungsdateien '
                                                                                                                   'werden '
                                                                                                                   'im '
                                                                                                                   'Codex-Konfigurationsverzeichnis '
                                                                                                                   'gespeichert '
                                                                                                                   'und '
                                                                                                                   'Wiederherstellungsanmeldeinformationen '
                                                                                                                   'werden '
                                                                                                                   'in '
                                                                                                                   'microglow-relay-codex-receipt.json '
                                                                                                                   'im '
                                                                                                                   'Datenverzeichnis '
                                                                                                                   'gespeichert.',
        '本地服务': 'lokaler Service',
        '本地服务已停止': 'Der lokale Dienst wurde eingestellt',
        '本地模型的 API KEY 使用 Windows DPAPI 加密，仅当前账户可读取。': 'Der API-SCHLÜSSEL des lokalen Modells wird mit '
                                                       'Windows DPAPI verschlüsselt und kann nur vom '
                                                       'aktuellen Konto gelesen werden.',
        '本地端口、外观与数据位置': 'Lokale Ports, Aussehen und Datenspeicherorte',
        '本地路由服务正在运行，Codex 的新请求会通过当前模型进行路由。': 'Der lokale Routing-Dienst läuft und neue Anfragen für den '
                                             'Codex werden über das aktuelle Modell weitergeleitet.',
        '本地路由让 Codex 通过本机访问你自己的模型供应商；请求正文不会被写入磁盘。': 'Durch lokales Routing kann Codex nativ auf Ihren '
                                                    'eigenen Modellanbieter zugreifen. Der Anforderungstext '
                                                    'wird nicht auf die Festplatte geschrieben.',
        '检测到接入后的外部修改': 'Externe Änderung nach Zugriff erkannt',
        '概览': 'Überblick',
        '模型': 'Modell',
        '模型名称': 'Modellname',
        '模型已删除': 'Modell gelöscht',
        '模型管理': 'Modellmanagement',
        '模型配置保存在 microglow-relay-settings.json，用量日志保存最近 30 天且不记录正文。': 'Die Modellkonfiguration wird in '
                                                                      'microglow-relay-settings.json '
                                                                      'gespeichert und das Nutzungsprotokoll '
                                                                      'wird für die letzten 30 Tage ohne '
                                                                      'Aufzeichnung des Textes gespeichert.',
        '模型配置已保存': 'Modellkonfiguration gespeichert',
        '正在只读加载本机会话索引…（无需退出 Codex）': 'Der native Sitzungsindex wird schreibgeschützt geladen... (Codex muss '
                                     'nicht beendet werden)',
        '正在备份、切换并校验这一条会话…': 'Diese Sitzung wird gesichert, gewechselt und überprüft...',
        '正在核对：{0}…': 'Überprüfung: {0}…',
        '正在测试连接…': 'Verbindung wird getestet…',
        '正在读取供应商模型列表…': 'Liste der Lieferantenmodelle wird gelesen...',
        '测试连接': 'Testverbindung',
        '添加、修改供应商模型配置，点击卡片选择当前路由模型': 'Fügen Sie die Lieferantenmodellkonfiguration hinzu und ändern Sie sie. '
                                     'Klicken Sie auf die Karte, um das aktuelle Routing-Modell auszuwählen',
        '添加模型': 'Modell hinzufügen',
        '清空': 'Klar',
        '点击“添加模型”填写供应商、API KEY 与模型名称，保存后点击卡片即可切换路由。': 'Klicken Sie auf „Modell hinzufügen“, um den '
                                                      'Lieferanten, den API-SCHLÜSSEL und den Modellnamen '
                                                      'einzugeben. Klicken Sie nach dem Speichern auf die '
                                                      'Karte, um die Route zu wechseln.',
        '点击本页的“接入 Codex”，程序会先完整备份现有 Codex 配置。': 'Klicken Sie auf dieser Seite auf „Mit Codex verbinden“ und '
                                                'das Programm sichert zunächst die vorhandene '
                                                'Codex-Konfiguration vollständig.',
        '点击记录查看详情': 'Klicken Sie auf den Datensatz, um Details anzuzeigen',
        '状态': 'Zustand',
        '界面语言': 'Schnittstellensprache',
        '白色': 'Weiß',
        '监听端口': 'Abhörport',
        '硅基流动': 'Fluss auf Siliziumbasis',
        '确定': 'Sicher',
        '确定切换这一条会话？': 'Sind Sie sicher, dass Sie diese Konversation wechseln möchten?',
        '空闲': 'Leerlauf',
        '端口修改会在下次启动本地服务时生效；已接入 Codex 时需要重新接入以刷新地址。': 'Die Portänderung wird beim nächsten Start des lokalen '
                                                     'Dienstes wirksam; Wenn Sie mit Codex verbunden sind, '
                                                     'müssen Sie die Verbindung erneut herstellen, um die '
                                                     'Adresse zu aktualisieren.',
        '端口已保存，将在下次启动服务时生效': 'Der Port wurde gespeichert und wird beim nächsten Start des Dienstes wirksam.',
        '管理': 'verwalten',
        '耗时': 'zeitaufwendig',
        '能力与协议': 'Fähigkeiten und Protokolle',
        '能力可多选，亮色为已开启。仅选择上游支持的能力；不支持思考参数时开启可能产生 400。': 'Es können mehrere Fähigkeiten ausgewählt werden und '
                                                       'die helle Farbe bedeutet, dass sie aktiviert sind. '
                                                       'Wählen Sie nur Funktionen aus, die vom Upstream '
                                                       'unterstützt werden. Beim Einschalten wird '
                                                       'möglicherweise 400 generiert, wenn Think-Parameter '
                                                       'nicht unterstützt werden.',
        '自动寻找 Codex 桌面端核心（可手动指定 codex.exe）': 'Den Codex-Desktop-Kern automatisch finden (codex.exe kann '
                                             'manuell angegeben werden)',
        '自动滚动': 'Autoscroll',
        '自定义 / 中转服务': 'Zoll-/Transitdienst',
        '自定义中转时填写，例如：我的中转站': 'Geben Sie beim Anpassen des Transfers beispielsweise Folgendes ein: Meine '
                             'Transferstation',
        '警告': 'warnen',
        '让同一段 Codex 会话在官方订阅与 Relay 模型之间继续使用': 'Lassen Sie die gleiche Codex-Sitzung weiterhin zwischen '
                                              'offiziellen Abonnements und Relay-Modellen verwenden',
        '设置': 'aufstellen',
        '访问令牌': 'Zugriffstoken',
        '识别到历史路由模型标识，归类为其它接入；不等于 Codex 或当前 Relay。': 'Die Kennung des historischen Routing-Modells wird '
                                                    'identifiziert und als anderer Zugriff klassifiziert; '
                                                    'ungleich Codex oder aktuellem Relay.',
        '请先保存至少一个模型配置。': 'Bitte speichern Sie zunächst mindestens eine Modellkonfiguration.',
        '请先明确选择 Codex 或 Relay。': 'Bitte wählen Sie zuerst explizit Codex oder Relay aus.',
        '请先添加一个模型': 'Bitte fügen Sie zuerst ein Modell hinzu',
        '请在“模型管理”页面添加一个供应商模型。': 'Bitte fügen Sie auf der Seite „Modellverwaltung“ ein Lieferantenmodell '
                                'hinzu.',
        '请求详情': 'Details anfordern',
        '读取': 'lesen',
        '读取失败：': 'Lesen fehlgeschlagen:',
        '读取成功：当前索引中没有符合条件的会话（可切换「已归档」查看）。': 'Erfolgreich gelesen: Es gibt keine Besprechung, die den '
                                            'Kriterien im aktuellen Index entspricht (Sie können zur Ansicht '
                                            'auf „Archiviert“ wechseln).',
        '读取成功：本页 {0} 条会话。': 'Erfolgreich gelesen: {0} Sitzungen für diese Seite.',
        '赛博朋克': 'Cyberpunk',
        '路由信息': 'Routing-Informationen',
        '路由标识': 'Routen-ID',
        '输入 Token': 'Geben Sie Token ein',
        '输入与输出合计': 'Gesamtinput und -output',
        '输出 Token': 'Ausgabetoken',
        '运行中': 'Läuft',
        '还没有模型配置': 'Noch keine Modellkonfiguration',
        '进入本页时读取本机会话索引。': 'Lesen Sie den lokalen Sitzungsindex, wenn Sie diese Seite aufrufen.',
        '连接信息': 'Verbindungsinformationen',
        '退出': 'aufhören',
        '退出时，将登录方式设为 ChatGPT 订阅登录（不修改会话或默认模型）': 'Stellen Sie beim Beenden die Anmeldemethode auf '
                                                'ChatGPT-Abonnementanmeldung ein (ändern Sie nicht die '
                                                'Sitzung oder das Standardmodell).',
        '退出选项 · 仅登录设置 · 默认关闭': 'Exit-Optionen · Nur-Login-Einstellungen · Standardmäßig deaktiviert',
        '选择': 'wählen',
        '选择 Codex 桌面端核心': 'Wählen Sie Codex Desktop Core',
        '选择核心': 'Kern auswählen',
        '选项未能保存，请检查本地存储。': 'Die Optionen konnten nicht gespeichert werden. Bitte überprüfen Sie den lokalen '
                           'Speicher.',
        '配置已保存 · {0}': 'Konfiguration gespeichert · {0}',
        '重启 Codex，新建任务后选择“{0}”。': 'Starten Sie Codex neu, erstellen Sie eine neue Aufgabe '
                                    'und wählen Sie „{0}“.',
        '重新接入': 'wieder verbinden',
        '金碧辉煌': 'prächtig',
        '错误': 'Fehler',
        '隐私保护：不保存 Prompt、Response 或原始请求正文。': 'Datenschutz: Eingabeaufforderung, Antwort oder ursprünglicher '
                                             'Anfragetext werden nicht gespeichert.',
        '需要还原时点击“恢复配置”，本程序写入的字段会被撤销。': 'Wenn Sie eine Wiederherstellung durchführen müssen, klicken Sie auf '
                                       '„Konfiguration wiederherstellen“ und die von diesem Programm '
                                       'geschriebenen Felder werden widerrufen.',
        '高': 'hoch',
        '黑色': 'Schwarz',
        '默认关闭。仅在你主动同意后累计 UTC 每日计数；不记录 Prompt、Response、正文、文件、代码、密钥、IP 或原始错误。': 'Standardmäßig deaktiviert. '
                                                                              'Sammeln Sie tägliche '
                                                                              'UTC-Zählungen nur mit Ihrer '
                                                                              'aktiven Zustimmung; Es werden '
                                                                              'keine Eingabeaufforderungen, '
                                                                              'Antworten, Textkörper, '
                                                                              'Dateien, Code, Schlüssel, IPs '
                                                                              'oder Originalfehler '
                                                                              'protokolliert.',
        '（未设置）': '(nicht festgelegt)',
        '，当前使用': ', wird derzeit verwendet',
        '，点击切换': ', klicken Sie, um zu wechseln',
        '雾蓝科技': 'Mistblau Tech',
        '石墨青金': 'Graphit Türkisgold',
        '微光': 'MicroGlow',
        '夜幕': 'Nachtdämmerung',
        '金辉': 'Goldener Schimmer',
        '月白': 'Mondweiß',
        '星港': 'Sternenhafen'},
 'en': {
        '检测到更高优先级的 Claude 配置：{0} · 可能覆盖 Relay 接入，未改动': 'Higher-priority Claude config found: {0} · may override Relay access (left untouched)','\n目标模型：{0}': 'Target model: {0}',
        '\n该会话使用历史路由标识，按其它接入处理。': 'This session uses historical route identification and is treated as other '
                                  'access.',
        '\n该会话由其它工具接入。': 'This session is accessed by other tools.',
        'AI 连接、路由状态与最近请求总览': 'Overview of AI connections, routing status, and recent requests',
        'Codex · ChatGPT 订阅': 'Codex · ChatGPT Subscribe',
        'Codex 已不再使用本路由器': 'Codex no longer uses this router',
        'Codex 已不再指向本路由器': 'Codex no longer points to this router',
        'Codex 已接入': 'Codex is connected',
        'Codex 已接入 · 已备份 {0}': 'Codex is connected · Backed up {0}',
        'Codex 已重新指向本路由器': 'Codex has been redirected to this router',
        'Codex 已重新接入 · 已备份 {0}': 'Codex has been reconnected · Backed up {0}',
        'Codex 当前指向': 'Codex currently points to',
        'Codex 接入': 'Codex access',
        'Codex 接入已失效：配置被其它程序改写，请到“Codex 接入”页重新接入': 'Codex access has expired: the configuration has been '
                                                   'overwritten by other programs, please go to the "Codex '
                                                   'Access" page to re-access',
        'Codex 配置': 'Codex configuration',
        'Codex 配置仍然指向本地路由，请先点击“重新接入”或启动本地服务。': 'The Codex configuration still points to the local route. '
                                               'Please click "Reconnect" or start the local service first.',
        'Codex 配置在接入后被其他程序改写过（例如切换模型通道），当前请求不会经过本程序。点击“重新接入”即可按现在的情况重新写入并备份。': 'The Codex configuration has '
                                                                               'been rewritten by other '
                                                                               'programs after access (such '
                                                                               'as switching model '
                                                                               'channels), and the current '
                                                                               'request will not go through '
                                                                               'this program. Click '
                                                                               '"Reconnect" to rewrite and '
                                                                               'back up according to the '
                                                                               'current situation.',
        'Codex 配置已恢复 · 原备份 {0}': 'Codex configuration restored · Original backup {0}',
        'Codex 配置已被其它程序改写，接入已失效，请重新接入': 'The Codex configuration has been overwritten by other programs and '
                                        'the access has expired. Please access again.',
        'Ollama（本机）': 'Ollama (native)',
        'Relay 接入配置未就绪；没有备份或修改会话。': 'Relay access configuration is not ready; there are no backup or '
                                    'modification sessions.',
        'iOS 风格': 'iOS style',
        '{0:.1f} 万': '{0:.1f} million',
        '{0:.2f} 亿': '{0:.2f} billion',
        '{0:.2f} 秒': '{0:.2f} seconds',
        '{0} 启动失败': '{0} failed to start',
        '{0} 已启动': '{0} is activated',
        '{0} 已在运行。': '{0} is already running.',
        '{0} 的目标模式': 'Target pattern for {0}',
        '上下文上限': 'context cap',
        '上下文窗口大小。': 'Context window size.',
        '上次退出：有对象未切换，原配置与操作记录已保留，请检查后手动处理。': 'Last exit: There are objects that have not been switched, and '
                                             'the original configuration and operation records have been '
                                             'retained. Please check and handle them manually.',
        '上游模型支持函数工具调用时开启': 'The upstream model supports turning on when the function tool is called',
        '上游模型支持图片输入时开启': 'Enable when the upstream model supports image input',
        '下一页': 'Next page',
        '中': 'middle',
        '主题 · {0}': 'Topics · {0}',
        '主题模式': 'theme mode',
        '仅实际退出时生效，关闭到托盘不执行。保留所有会话的模型和 Provider、全局默认模型及其它工具的配置；未检测到订阅登录或存在外部改动时不执行。': 'It only takes effect '
                                                                                     'when you actually '
                                                                                     'exit. Closing to the '
                                                                                     'tray does not take '
                                                                                     'effect. Preserves the '
                                                                                     'configuration of '
                                                                                     'models and providers, '
                                                                                     'global default models, '
                                                                                     'and other tools for '
                                                                                     'all sessions; does not '
                                                                                     'execute when '
                                                                                     'subscription login is '
                                                                                     'not detected or there '
                                                                                     'are external changes.',
        '仅调整所选会话的模型接入配置，不读取或改写历史对话；其它工具的会话不会自动接管。': 'Only the model access configuration of the selected '
                                                    'session is adjusted, historical conversations are not '
                                                    'read or rewritten; sessions of other tools will not be '
                                                    'automatically taken over.',
        '今日 Token 消耗': 'Today’s Token consumption',
        '今日 Token：{0:,}': 'Today’s Token: {0:,}',
        '今日成功率': "Today's success rate",
        '今日暂无请求': 'No requests today',
        '今日请求': 'Request today',
        '以下字段在接入后被其他程序改过：\n{0}\n\n仍然强制恢复为接入前的状态吗？（会先备份当前配置）': 'The following fields have been changed by '
                                                              'other programs after access:\n'
                                                              '{0}\n'
                                                              '\n'
                                                              'Still forced to restore to the state before '
                                                              'access? (The current configuration will be '
                                                              'backed up first)',
        '会话兼容': 'session compatible',
        '会话兼容选项已保存': 'Session compatibility options saved',
        '会话切换执行结果': 'Session switching execution results',
        '会话列表': 'Conversation list',
        '会话列表读取状态': 'Session list read status',
        '会话名称': 'session name',
        '会话配置操作正在完成，请稍后再退出。': 'The session configuration operation is being completed, please exit later.',
        '会话：{0}\n当前：{1}\n目标：{2}{3}{4}\n确认 Codex 已正常退出？确定后先备份原配置，再切换并校验；不修改历史正文。': 'Session: {0}\n'
                                                                                  'Current: {1}\n'
                                                                                  'Target: {2}{3}{4}\n'
                                                                                  'Confirmed that Codex '
                                                                                  'exited normally? After '
                                                                                  'confirmation, back up the '
                                                                                  'original configuration '
                                                                                  'first, then switch and '
                                                                                  'verify; do not modify the '
                                                                                  'historical text.',
        '传输中': 'Transmitting',
        '低': 'Low',
        '使用步骤': 'Usage steps',
        '供应商': 'supplier',
        '供应商名称': 'Supplier name',
        '供应商未返回模型列表，请手动填写。': 'The supplier did not return the model list, please fill it in manually.',
        '保存后使用 Windows DPAPI 加密存储。': 'Use Windows DPAPI to encrypt storage after saving.',
        '保存退出选项与核心路径': 'Save exit options and core path',
        '保存配置': 'Save configuration',
        '信息': 'information',
        '修改模型': 'Modify model',
        '修改模型配置': 'Modify model configuration',
        '修改模式为': 'Modify the mode to',
        '停止接入': 'Stop access',
        '全部': 'all',
        '共 {0} 个模型配置 · 点击卡片切换，点击铅笔图标编辑参数': 'Total {0} model configurations · Click the card to switch, click '
                                           'the pencil icon to edit parameters',
        '关于': 'about',
        '关闭': 'closure',
        '关闭请求详情': 'Close request details',
        '其它接入': 'Other access',
        '其它接入会话需明确选择目标；Relay 不自动接管。': 'Other access sessions require explicit target selection; Relay does '
                                      'not automatically take over.',
        '准备读取会话索引。': 'Prepare to read session index.',
        '切换成功：{0} → {1}。原配置已备份，写入结果已校验；下方列表已刷新。': 'Switching successful: {0} → {1}. The original '
                                                  'configuration has been backed up and the writing results '
                                                  'have been verified; the list below has been refreshed.',
        '切换未完成：{0}，校验通过 {1} / {2}。原配置备份与操作记录已保留，不会自动重写会话。': 'Switching not completed: {0}, verification '
                                                            'passed {1}/{2}. The original configuration '
                                                            'backup and operation records have been '
                                                            'retained, and the session will not be '
                                                            'automatically rewritten.',
        '切换模型': 'Switch model',
        '删除后将无法自动恢复，需要重新填写 API KEY。': 'After deletion, it cannot be automatically restored and the API KEY '
                                      'needs to be filled in again.',
        '删除此模型配置': 'Delete this model configuration',
        '删除这条模型配置？': 'Delete this model configuration?',
        '刷新会话列表': 'Refresh session list',
        '刷新接入': 'Refresh access',
        '匿名使用统计': 'Anonymous usage statistics',
        '匿名使用统计已关闭': 'Anonymous usage statistics is turned off',
        '匿名使用统计已启用': 'Anonymous usage statistics is enabled',
        '匿名使用统计明确同意开关': 'Anonymous usage statistics explicit consent switch',
        '单次最大输出。': 'Single maximum output.',
        '发起请求后，可在此查看不含正文的安全摘要。': 'After a request is made, a security summary without the text can be viewed '
                                 'here.',
        '取消': 'Cancel',
        '可点击“读取”从供应商获取可用模型。': 'You can click "Read" to get the available models from the supplier.',
        '国家信息不由客户端采集；未来上传阶段仅允许服务端接入层瞬时推断。撤回后立即停止产生新的遥测数据。': 'National information is not collected by the '
                                                            'client; only instantaneous inference at the '
                                                            'server access layer is allowed in the future '
                                                            'upload phase. Stops generating new telemetry '
                                                            'data immediately after withdrawal.',
        '图片支持': 'Image support',
        '图片输入': 'Image input',
        '在“模型管理”页面添加至少一个模型，并点击模型卡片进行选择。': 'Add at least one model on the "Model Management" page and click '
                                          'the model card to select it.',
        '填写供应商公布的完整端点；程序按原样请求，不会改写路径。': 'Fill in the complete endpoint as published by the vendor; the '
                                        'program requests it as-is and does not rewrite the path.',
        '复制': 'copy',
        '外观': 'Appearance',
        '失败': 'fail',
        '失败 {0}': 'Failed {0}',
        '实时显示请求、连接与配置变更记录': 'Real-time display of request, connection and configuration change records',
        '客户端接入': 'Client access',
        '将撤销本程序对 Codex 配置所做的修改，并停止本地服务。': 'Modifications made by this program to the Codex configuration '
                                          'will be undone and the local service will be stopped.',
        '尚未接入': 'Not connected yet',
        '尚未接入 Codex': 'Not yet connected to Codex',
        '尚未配置模型': 'Model not configured yet',
        '展开已读取的模型列表；也可直接手动输入模型名称': 'Expand the list of read models; you can also directly enter the model '
                                   'name manually',
        '工具调用': 'Tool call',
        '已取消；没有备份或修改会话。': 'Canceled; no backup or modification sessions.',
        '已开启': 'Already turned on',
        '已归档': 'Archived',
        '已按当前模型回填全部原参数；API KEY 已解密加载并默认遮蔽。': 'All original parameters have been backfilled according to the '
                                             'current model; API KEY has been decrypted, loaded and masked '
                                             'by default.',
        '已接入': 'Already connected',
        '已接入 Codex，但端口无法启动：{0}': 'Connected to Codex, but the port cannot be started: {0}',
        '已接入但服务未运行': 'Connected but the service is not running',
        '已知供应商会自动匹配；自定义中转请按实际选择。': 'Known suppliers will be automatically matched; for custom transfer, '
                                   'please select according to actual conditions.',
        '已读取 {0} 个模型': '{0} models read',
        '已读取 {0} 个模型，请从列表选择': '{0} models read, please select from list',
        '帮助改进 MicroGlow Relay': 'Help improve MicroGlow Relay',
        '平均耗时 {0:.2f} 秒': 'Average time spent {0:.2f} seconds',
        '应用': 'application',
        '归档会话仅供查看；请先在 Codex 中取消归档，再退出 Codex 后操作。': 'Archived sessions are for viewing only; please cancel '
                                                   'the archive in Codex first, and then exit Codex before '
                                                   'proceeding.',
        '当前使用': 'currently in use',
        '当前模型已切换': 'The current model has been switched',
        '当前模式': 'Current mode',
        '当前路由模型': 'Current routing model',
        '思考强度': 'thinking intensity',
        '思考模式': 'Thinking model',
        '恢复 Codex 配置？': 'Restore Codex configuration?',
        '恢复配置': 'Restore configuration',
        '成功': 'success',
        '成功 {0} · 失败 {1}': 'Success {0} · Failure {1}',
        '所属项目名称': 'Project name',
        '打开主界面': 'Open the main interface',
        '打开数据目录': 'Open data directory',
        '把本地路由服务接入 Codex，并在需要时完整恢复原始配置': 'Connect local routing services to Codex and fully restore the '
                                         'original configuration if needed',
        '接入 Codex': 'Access Codex',
        '接入信息': 'access information',
        '接入信息已刷新': 'Access information has been refreshed',
        '接入已失效': 'Access has expired',
        '接入时会先完整备份现有 Codex 配置，随时可以一键恢复。': 'When connecting, the existing Codex configuration will be fully '
                                          'backed up and can be restored at any time with one click.',
        '接口协议': 'interface protocol',
        '接口地址': 'interface address',
        '操作': 'operate',
        '操作未完成；原配置与已有备份保留。请重新检查，不会回显底层数据。': 'The operation is not completed; the original configuration and '
                                            'existing backups are retained. Please recheck, the underlying '
                                            'data will not be echoed.',
        '支持推理参数时开启，否则可能产生 400': 'Enable when inference parameters are supported, otherwise 400 may be '
                                'generated',
        '收起模型': 'Collapse model',
        '数据传输': 'Data transfer',
        '数据位置': 'data location',
        '文本': 'text',
        '开始日期': 'Start date',
        '无法读取': 'Unable to read',
        '日志': 'log',
        '时间': 'time',
        '结束日期': 'End date',
        '是否明确同意启用匿名使用统计？\n\n仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。不收集请求或响应正文、文件、代码、密钥、IP、原始错误和逐请求记录。': 'Do '
                                                                                                        'you '
                                                                                                        'explicitly '
                                                                                                        'agree '
                                                                                                        'to '
                                                                                                        'enable '
                                                                                                        'anonymous '
                                                                                                        'usage '
                                                                                                        'statistics?\n'
                                                                                                        '\n'
                                                                                                        'Only '
                                                                                                        'the '
                                                                                                        'number '
                                                                                                        'of '
                                                                                                        'daily '
                                                                                                        'calls, '
                                                                                                        'successes/errors, '
                                                                                                        'tokens, '
                                                                                                        'fixed '
                                                                                                        'delay '
                                                                                                        'intervals, '
                                                                                                        'standard '
                                                                                                        'error '
                                                                                                        'categories, '
                                                                                                        'and '
                                                                                                        'rollbacks '
                                                                                                        'are '
                                                                                                        'accumulated. '
                                                                                                        'Request '
                                                                                                        'or '
                                                                                                        'response '
                                                                                                        'bodies, '
                                                                                                        'files, '
                                                                                                        'codes, '
                                                                                                        'keys, '
                                                                                                        'IPs, '
                                                                                                        'raw '
                                                                                                        'errors, '
                                                                                                        'and '
                                                                                                        'per-request '
                                                                                                        'logging '
                                                                                                        'are '
                                                                                                        'not '
                                                                                                        'collected.',
        '显示密钥': 'show key',
        '智谱 AI': 'Wisdom spectrum AI',
        '暂无日志 · 服务启动或配置变更后会显示在这里': 'No logs yet · It will be displayed here after the service is started or '
                                   'the configuration is changed.',
        '暂无记录': 'No record yet',
        '暂无请求记录': 'No request record yet',
        '最近活动': 'Recent activities',
        '服务已停止': 'Service has stopped',
        '服务运行中': 'Service is running',
        '未命名会话': 'unnamed session',
        '未开启': 'Not turned on',
        '未接入': 'Not connected',
        '未检测到 ChatGPT 订阅登录；没有备份或修改会话。': 'No ChatGPT subscription login detected; no sessions backed up or '
                                        'modified.',
        '未运行': 'Not running',
        '本地地址': 'local address',
        '本地接口只监听 127.0.0.1，并要求随机访问令牌；历史 Backup 文件保存在 Codex 配置目录，恢复凭据保存在数据目录的 microglow-relay-codex-receipt.json。': 'The '
                                                                                                                   'local '
                                                                                                                   'interface '
                                                                                                                   'only '
                                                                                                                   'listens '
                                                                                                                   'on '
                                                                                                                   '127.0.0.1 '
                                                                                                                   'and '
                                                                                                                   'requires '
                                                                                                                   'a '
                                                                                                                   'random '
                                                                                                                   'access '
                                                                                                                   'token; '
                                                                                                                   'historical '
                                                                                                                   'Backup '
                                                                                                                   'files '
                                                                                                                   'are '
                                                                                                                   'saved '
                                                                                                                   'in '
                                                                                                                   'the '
                                                                                                                   'Codex '
                                                                                                                   'configuration '
                                                                                                                   'directory, '
                                                                                                                   'and '
                                                                                                                   'recovery '
                                                                                                                   'credentials '
                                                                                                                   'are '
                                                                                                                   'saved '
                                                                                                                   'in '
                                                                                                                   'microglow-relay-codex-receipt.json '
                                                                                                                   'in '
                                                                                                                   'the '
                                                                                                                   'data '
                                                                                                                   'directory.',
        '本地服务': 'local service',
        '本地服务已停止': 'Local service has stopped',
        '本地模型的 API KEY 使用 Windows DPAPI 加密，仅当前账户可读取。': 'The API KEY of the local model is encrypted using '
                                                       'Windows DPAPI and can only be read by the current '
                                                       'account.',
        '本地端口、外观与数据位置': 'Local ports, appearance and data locations',
        '本地路由服务正在运行，Codex 的新请求会通过当前模型进行路由。': 'The local routing service is running and new requests for the '
                                             'Codex are routed through the current model.',
        '本地路由让 Codex 通过本机访问你自己的模型供应商；请求正文不会被写入磁盘。': 'Local routing lets Codex access your own model provider '
                                                    'natively; the request body is not written to disk.',
        '检测到接入后的外部修改': 'External modification detected after access',
        '概览': 'Overview',
        '模型': 'Model',
        '模型名称': 'Model name',
        '模型已删除': 'Model deleted',
        '模型管理': 'Model management',
        '模型配置保存在 microglow-relay-settings.json，用量日志保存最近 30 天且不记录正文。': 'The model configuration is saved in '
                                                                      'microglow-relay-settings.json, and '
                                                                      'the usage log is saved for the last '
                                                                      '30 days without recording the text.',
        '模型配置已保存': 'Model configuration saved',
        '正在只读加载本机会话索引…（无需退出 Codex）': 'Loading native session index read-only... (no need to exit Codex)',
        '正在备份、切换并校验这一条会话…': 'Backing up, switching and verifying this session...',
        '正在核对：{0}…': 'Checking: {0}…',
        '正在测试连接…': 'Testing connection…',
        '正在读取供应商模型列表…': 'Reading supplier model list...',
        '测试连接': 'test connection',
        '添加、修改供应商模型配置，点击卡片选择当前路由模型': 'Add and modify supplier model configuration, click the card to select '
                                     'the current routing model',
        '添加模型': 'Add model',
        '清空': 'Clear',
        '点击“添加模型”填写供应商、API KEY 与模型名称，保存后点击卡片即可切换路由。': 'Click "Add Model" to fill in the supplier, API KEY '
                                                      'and model name. After saving, click the card to '
                                                      'switch routes.',
        '点击本页的“接入 Codex”，程序会先完整备份现有 Codex 配置。': 'Click "Connect to Codex" on this page, and the program will '
                                                'first fully back up the existing Codex configuration.',
        '点击记录查看详情': 'Click the record to view details',
        '状态': 'state',
        '界面语言': 'interface language',
        '白色': 'White',
        '监听端口': 'listening port',
        '硅基流动': 'silicon based flow',
        '确定': 'Sure',
        '确定切换这一条会话？': 'Are you sure you want to switch this conversation?',
        '空闲': 'idle',
        '端口修改会在下次启动本地服务时生效；已接入 Codex 时需要重新接入以刷新地址。': 'The port modification will take effect the next time '
                                                     'the local service is started; when connected to Codex, '
                                                     'you need to reconnect to refresh the address.',
        '端口已保存，将在下次启动服务时生效': 'The port has been saved and will take effect the next time the service is '
                             'started.',
        '管理': 'manage',
        '耗时': 'time consuming',
        '能力与协议': 'Capabilities and protocols',
        '能力可多选，亮色为已开启。仅选择上游支持的能力；不支持思考参数时开启可能产生 400。': 'Multiple abilities can be selected, and the bright '
                                                       'color means they are enabled. Only select '
                                                       'capabilities supported by upstream; turning on may '
                                                       'generate 400 when think parameters are not '
                                                       'supported.',
        '自动寻找 Codex 桌面端核心（可手动指定 codex.exe）': 'Automatically find the Codex desktop core (codex.exe can be '
                                             'specified manually)',
        '自动滚动': 'autoscroll',
        '自定义 / 中转服务': 'Custom/transit service',
        '自定义中转时填写，例如：我的中转站': 'Fill in when customizing transfer, for example: My transfer station',
        '警告': 'warn',
        '让同一段 Codex 会话在官方订阅与 Relay 模型之间继续使用': 'Let the same Codex session continue to be used between '
                                              'official subscriptions and Relay models',
        '设置': 'set up',
        '访问令牌': 'access token',
        '识别到历史路由模型标识，归类为其它接入；不等于 Codex 或当前 Relay。': 'The historical routing model identifier is identified '
                                                    'and classified as other access; not equal to Codex or '
                                                    'current Relay.',
        '请先保存至少一个模型配置。': 'Please save at least one model configuration first.',
        '请先明确选择 Codex 或 Relay。': 'Please explicitly select Codex or Relay first.',
        '请先添加一个模型': 'Please add a model first',
        '请在“模型管理”页面添加一个供应商模型。': 'Please add a supplier model on the Model Management page.',
        '请求详情': 'Request details',
        '读取': 'read',
        '读取失败：': 'Read failed:',
        '读取成功：当前索引中没有符合条件的会话（可切换「已归档」查看）。': 'Read successfully: There is no meeting that meets the criteria '
                                            'in the current index (you can switch to "Archived" to view).',
        '读取成功：本页 {0} 条会话。': 'Read successfully: {0} sessions for this page.',
        '赛博朋克': 'cyberpunk',
        '路由信息': 'routing information',
        '路由标识': 'Route ID',
        '输入 Token': 'Enter Token',
        '输入与输出合计': 'Total input and output',
        '输出 Token': 'Output Token',
        '运行中': 'Running',
        '还没有模型配置': 'No model configuration yet',
        '进入本页时读取本机会话索引。': 'Read the local session index when entering this page.',
        '连接信息': 'connection information',
        '退出': 'quit',
        '退出时，将登录方式设为 ChatGPT 订阅登录（不修改会话或默认模型）': 'When exiting, set the login method to ChatGPT subscription '
                                                'login (do not modify the session or default model)',
        '退出选项 · 仅登录设置 · 默认关闭': 'Exit options · Login only settings · Off by default',
        '选择': 'choose',
        '选择 Codex 桌面端核心': 'Select Codex Desktop Core',
        '选择核心': 'Select core',
        '选项未能保存，请检查本地存储。': 'Options failed to save, please check local storage.',
        '配置已保存 · {0}': 'Configuration saved · {0}',
        '重启 Codex，新建任务后选择“{0}”。': 'Restart Codex, create a new task and select “{0}”.',
        '重新接入': 'reconnect',
        '金碧辉煌': 'splendid',
        '错误': 'mistake',
        '隐私保护：不保存 Prompt、Response 或原始请求正文。': 'Privacy Protection: Prompt, Response or original request body '
                                             'is not saved.',
        '需要还原时点击“恢复配置”，本程序写入的字段会被撤销。': 'When you need to restore, click "Restore Configuration" and the '
                                       'fields written by this program will be revoked.',
        '高': 'high',
        '黑色': 'black',
        '默认关闭。仅在你主动同意后累计 UTC 每日计数；不记录 Prompt、Response、正文、文件、代码、密钥、IP 或原始错误。': 'Off by default. Accumulate '
                                                                              'UTC daily counts only with '
                                                                              'your active consent; no '
                                                                              'prompts, responses, bodies, '
                                                                              'files, code, keys, IPs, or '
                                                                              'original errors are logged.',
        '（未设置）': '(not set)',
        '，当前使用': ', currently using',
        '，点击切换': ', click to switch',
        '雾蓝科技': 'Mist Blue Tech',
        '石墨青金': 'Graphite Teal Gold',
        '微光': 'MicroGlow',
        '夜幕': 'Nightfall',
        '金辉': 'Golden Glow',
        '月白': 'Moon White',
        '星港': 'Stellar Port'},
 'es': {
        '检测到更高优先级的 Claude 配置：{0} · 可能覆盖 Relay 接入，未改动': 'Se encontró una configuración de Claude con mayor prioridad: {0} · puede anular el acceso de Relay (sin modificar)','\n目标模型：{0}': 'Modelo de destino: {0}',
        '\n该会话使用历史路由标识，按其它接入处理。': 'Esta sesión utiliza identificación de ruta histórica y se trata como otro '
                                  'acceso.',
        '\n该会话由其它工具接入。': 'A esta sesión se accede mediante otras herramientas.',
        'AI 连接、路由状态与最近请求总览': 'Descripción general de las conexiones de IA, el estado de enrutamiento y las '
                             'solicitudes recientes',
        'Codex · ChatGPT 订阅': 'Códice · ChatGPT Suscríbete',
        'Codex 已不再使用本路由器': 'Codex ya no utiliza este enrutador',
        'Codex 已不再指向本路由器': 'Codex ya no apunta a este enrutador',
        'Codex 已接入': 'El códice está conectado.',
        'Codex 已接入 · 已备份 {0}': 'Codex está conectado · Copia de seguridad {0}',
        'Codex 已重新指向本路由器': 'Codex ha sido redirigido a este enrutador',
        'Codex 已重新接入 · 已备份 {0}': 'Se ha vuelto a conectar el Codex · Se ha realizado una copia de seguridad '
                                 '{0}',
        'Codex 当前指向': 'Actualmente el Codex apunta a',
        'Codex 接入': 'Acceso al códice',
        'Codex 接入已失效：配置被其它程序改写，请到“Codex 接入”页重新接入': 'El acceso al Codex ha caducado: la configuración ha sido '
                                                   'sobrescrita por otros programas; vaya a la página '
                                                   '"Acceso al Codex" para volver a acceder',
        'Codex 配置': 'Configuración del códice',
        'Codex 配置仍然指向本地路由，请先点击“重新接入”或启动本地服务。': 'La configuración del Codex todavía apunta a la ruta local. '
                                               'Haga clic en "Reconectar" o inicie el servicio local '
                                               'primero.',
        'Codex 配置在接入后被其他程序改写过（例如切换模型通道），当前请求不会经过本程序。点击“重新接入”即可按现在的情况重新写入并备份。': 'La configuración del Codex '
                                                                               'ha sido reescrita por otros '
                                                                               'programas después del acceso '
                                                                               '(como cambiar de canal de '
                                                                               'modelo) y la solicitud '
                                                                               'actual no pasará por este '
                                                                               'programa. Haga clic en '
                                                                               '"Reconectar" para reescribir '
                                                                               'y realizar una copia de '
                                                                               'seguridad de acuerdo con la '
                                                                               'situación actual.',
        'Codex 配置已恢复 · 原备份 {0}': 'Configuración del Codex restaurada · Copia de seguridad original {0}',
        'Codex 配置已被其它程序改写，接入已失效，请重新接入': 'La configuración del Codex ha sido sobrescrita por otros programas '
                                        'y el acceso ha caducado. Por favor acceda nuevamente.',
        'Ollama（本机）': 'Ollama (nativo)',
        'Relay 接入配置未就绪；没有备份或修改会话。': 'La configuración del acceso de retransmisión no está lista; no hay '
                                    'sesiones de copia de seguridad ni de modificación.',
        'iOS 风格': 'estilo iOS',
        '{0:.1f} 万': '{0:.1f} millones',
        '{0:.2f} 亿': '{0:.2f} mil millones',
        '{0:.2f} 秒': '{0:.2f} segundos',
        '{0} 启动失败': '{0} no pudo iniciar',
        '{0} 已启动': '{0} está activado',
        '{0} 已在运行。': '{0} ya se está ejecutando.',
        '{0} 的目标模式': 'Patrón de destino para {0}',
        '上下文上限': 'límite de contexto',
        '上下文窗口大小。': 'Tamaño de la ventana de contexto.',
        '上次退出：有对象未切换，原配置与操作记录已保留，请检查后手动处理。': 'Última salida: hay objetos que no se han cambiado y se han '
                                             'conservado los registros de configuración y operación '
                                             'originales. Verifíquelos y manéjelos manualmente.',
        '上游模型支持函数工具调用时开启': 'El modelo ascendente admite la activación cuando se llama a la herramienta de '
                           'función',
        '上游模型支持图片输入时开启': 'Habilitar cuando el modelo ascendente admita la entrada de imágenes',
        '下一页': 'Página siguiente',
        '中': 'medio',
        '主题 · {0}': 'Temas · {0}',
        '主题模式': 'modo tema',
        '仅实际退出时生效，关闭到托盘不执行。保留所有会话的模型和 Provider、全局默认模型及其它工具的配置；未检测到订阅登录或存在外部改动时不执行。': 'Sólo surte efecto '
                                                                                     'cuando realmente '
                                                                                     'sales. El cierre de la '
                                                                                     'bandeja no surte '
                                                                                     'efecto. Preserva la '
                                                                                     'configuración de '
                                                                                     'modelos y proveedores, '
                                                                                     'modelos '
                                                                                     'predeterminados '
                                                                                     'globales y otras '
                                                                                     'herramientas para '
                                                                                     'todas las sesiones; no '
                                                                                     'se ejecuta cuando no '
                                                                                     'se detecta el inicio '
                                                                                     'de sesión de '
                                                                                     'suscripción o hay '
                                                                                     'cambios externos.',
        '仅调整所选会话的模型接入配置，不读取或改写历史对话；其它工具的会话不会自动接管。': 'Sólo se ajusta la configuración de acceso al modelo de '
                                                    'la sesión seleccionada, las conversaciones históricas '
                                                    'no se leen ni se reescriben; Las sesiones de otras '
                                                    'herramientas no se tomarán automáticamente.',
        '今日 Token 消耗': 'Consumo de tokens de hoy',
        '今日 Token：{0:,}': 'Token de hoy: {0:,}',
        '今日成功率': 'La tasa de éxito actual',
        '今日暂无请求': 'No hay solicitudes hoy',
        '今日请求': 'Solicitar hoy',
        '以下字段在接入后被其他程序改过：\n{0}\n\n仍然强制恢复为接入前的状态吗？（会先备份当前配置）': 'Los siguientes campos han sido modificados '
                                                              'por otros programas después del acceso:\n'
                                                              '{0}\n'
                                                              '\n'
                                                              '¿Aún te ves obligado a restaurar el estado '
                                                              'anterior al acceso? (Primero se realizará una '
                                                              'copia de seguridad de la configuración '
                                                              'actual)',
        '会话兼容': 'sesión compatible',
        '会话兼容选项已保存': 'Opciones de compatibilidad de sesiones guardadas',
        '会话切换执行结果': 'Resultados de la ejecución del cambio de sesión',
        '会话列表': 'Lista de conversación',
        '会话列表读取状态': 'Estado de lectura de la lista de sesiones',
        '会话名称': 'nombre de la sesión',
        '会话配置操作正在完成，请稍后再退出。': 'La operación de configuración de la sesión se está completando; salga más '
                              'tarde.',
        '会话：{0}\n当前：{1}\n目标：{2}{3}{4}\n确认 Codex 已正常退出？确定后先备份原配置，再切换并校验；不修改历史正文。': 'Sesión: {0}\n'
                                                                                  'Actual: {1}\n'
                                                                                  'Objetivo: {2}{3}{4}\n'
                                                                                  '¿Confirmaste que el Codex '
                                                                                  'salió normalmente? '
                                                                                  'Después de la '
                                                                                  'confirmación, primero '
                                                                                  'haga una copia de '
                                                                                  'seguridad de la '
                                                                                  'configuración original, '
                                                                                  'luego cambie y verifique; '
                                                                                  'no modificar el texto '
                                                                                  'histórico.',
        '传输中': 'Transmitiendo',
        '低': 'Bajo',
        '使用步骤': 'Pasos de uso',
        '供应商': 'proveedor',
        '供应商名称': 'Nombre del proveedor',
        '供应商未返回模型列表，请手动填写。': 'El proveedor no devolvió la lista de modelos, complétela manualmente.',
        '保存后使用 Windows DPAPI 加密存储。': 'Utilice Windows DPAPI para cifrar el almacenamiento después de '
                                     'guardarlo.',
        '保存退出选项与核心路径': 'Guardar opciones de salida y ruta principal',
        '保存配置': 'Guardar configuración',
        '信息': 'información',
        '修改模型': 'Modificar modelo',
        '修改模型配置': 'Modificar la configuración del modelo',
        '修改模式为': 'Modifique el modo para',
        '停止接入': 'Detener el acceso',
        '全部': 'todo',
        '共 {0} 个模型配置 · 点击卡片切换，点击铅笔图标编辑参数': 'Total de configuraciones de modelo {0} · Haga clic en la tarjeta '
                                           'para cambiar, haga clic en el icono de lápiz para editar los '
                                           'parámetros',
        '关于': 'acerca de',
        '关闭': 'cierre',
        '关闭请求详情': 'Cerrar detalles de la solicitud',
        '其它接入': 'Otro acceso',
        '其它接入会话需明确选择目标；Relay 不自动接管。': 'Otras sesiones de acceso requieren una selección explícita de '
                                      'objetivos; El relé no asume el control automáticamente.',
        '准备读取会话索引。': 'Prepárese para leer el índice de la sesión.',
        '切换成功：{0} → {1}。原配置已备份，写入结果已校验；下方列表已刷新。': 'Cambio exitoso: {0} → {1}. Se realizó una copia de '
                                                  'seguridad de la configuración original y se verificaron '
                                                  'los resultados de la escritura; la lista a continuación '
                                                  'ha sido actualizada.',
        '切换未完成：{0}，校验通过 {1} / {2}。原配置备份与操作记录已保留，不会自动重写会话。': 'Cambio no completado: {0}, verificación '
                                                            'aprobada {1}/{2}. Se han conservado los '
                                                            'registros de operación y copia de seguridad de '
                                                            'la configuración original y la sesión no se '
                                                            'reescribirá automáticamente.',
        '切换模型': 'Cambiar modelo',
        '删除后将无法自动恢复，需要重新填写 API KEY。': 'Después de la eliminación, no se puede restaurar automáticamente y la '
                                      'CLAVE API debe completarse nuevamente.',
        '删除此模型配置': 'Eliminar la configuración de este modelo',
        '删除这条模型配置？': '¿Eliminar la configuración de este modelo?',
        '刷新会话列表': 'Actualizar lista de sesiones',
        '刷新接入': 'Actualizar acceso',
        '匿名使用统计': 'Estadísticas de uso anónimo',
        '匿名使用统计已关闭': 'Las estadísticas de uso anónimo están desactivadas',
        '匿名使用统计已启用': 'Las estadísticas de uso anónimas están habilitadas',
        '匿名使用统计明确同意开关': 'Cambio de consentimiento explícito de estadísticas de uso anónimo',
        '单次最大输出。': 'Salida máxima única.',
        '发起请求后，可在此查看不含正文的安全摘要。': 'Después de realizar una solicitud, se puede ver un resumen de seguridad '
                                 'sin el texto aquí.',
        '取消': 'Cancelar',
        '可点击“读取”从供应商获取可用模型。': 'Puede hacer clic en "Leer" para obtener los modelos disponibles del '
                              'proveedor.',
        '国家信息不由客户端采集；未来上传阶段仅允许服务端接入层瞬时推断。撤回后立即停止产生新的遥测数据。': 'La información nacional no es recopilada por el '
                                                            'cliente; solo se permite la inferencia '
                                                            'instantánea en la capa de acceso al servidor en '
                                                            'la fase de carga futura. Deja de generar nuevos '
                                                            'datos de telemetría inmediatamente después del '
                                                            'retiro.',
        '图片支持': 'Soporte de imagen',
        '图片输入': 'Entrada de imagen',
        '在“模型管理”页面添加至少一个模型，并点击模型卡片进行选择。': 'Agregue al menos un modelo en la página "Gestión de modelos" y '
                                          'haga clic en la tarjeta del modelo para seleccionarlo.',
        '填写供应商公布的完整端点；程序按原样请求，不会改写路径。': 'Complete el punto final completo publicado por el proveedor; el '
                                        'programa lo solicita tal cual y no reescribe la ruta.',
        '复制': 'Copiar',
        '外观': 'Apariencia',
        '失败': 'fallar',
        '失败 {0}': 'Error {0}',
        '实时显示请求、连接与配置变更记录': 'Visualización en tiempo real de registros de solicitudes, conexiones y cambios '
                            'de configuración.',
        '客户端接入': 'Acceso de cliente',
        '将撤销本程序对 Codex 配置所做的修改，并停止本地服务。': 'Las modificaciones realizadas por este programa en la '
                                          'configuración del Codex se desharán y se detendrá el servicio '
                                          'local.',
        '尚未接入': 'Aún no conectado',
        '尚未接入 Codex': 'Aún no conectado al Codex',
        '尚未配置模型': 'Modelo aún no configurado',
        '展开已读取的模型列表；也可直接手动输入模型名称': 'Ampliar la lista de modelos leídos; También puedes ingresar directamente '
                                   'el nombre del modelo manualmente.',
        '工具调用': 'llamada de herramienta',
        '已取消；没有备份或修改会话。': 'Cancelado; sin sesiones de copia de seguridad o modificación.',
        '已开启': 'Ya encendido',
        '已归档': 'Archivado',
        '已按当前模型回填全部原参数；API KEY 已解密加载并默认遮蔽。': 'Todos los parámetros originales se han completado según el '
                                             'modelo actual; La CLAVE API se ha descifrado, cargado y '
                                             'enmascarado de forma predeterminada.',
        '已接入': 'Ya conectado',
        '已接入 Codex，但端口无法启动：{0}': 'Conectado al Codex, pero el puerto no se puede iniciar: {0}',
        '已接入但服务未运行': 'Conectado pero el servicio no se está ejecutando',
        '已知供应商会自动匹配；自定义中转请按实际选择。': 'Los proveedores conocidos serán emparejados automáticamente; Para '
                                   'transferencia personalizada, seleccione según las condiciones reales.',
        '已读取 {0} 个模型': '{0} modelos leídos',
        '已读取 {0} 个模型，请从列表选择': '{0} modelos leídos, seleccione de la lista',
        '帮助改进 MicroGlow Relay': 'Ayude a mejorar MicroGlow Relay',
        '平均耗时 {0:.2f} 秒': 'Tiempo promedio empleado {0:.2f} segundos',
        '应用': 'solicitud',
        '归档会话仅供查看；请先在 Codex 中取消归档，再退出 Codex 后操作。': 'Las sesiones archivadas son sólo para visualización; '
                                                   'primero cancele el archivo en Codex y luego salga de '
                                                   'Codex antes de continuar.',
        '当前使用': 'actualmente en uso',
        '当前模型已切换': 'El modelo actual ha sido cambiado.',
        '当前模式': 'Modo actual',
        '当前路由模型': 'Modelo de enrutamiento actual',
        '思考强度': 'intensidad del pensamiento',
        '思考模式': 'modelo de pensamiento',
        '恢复 Codex 配置？': '¿Restaurar la configuración del Codex?',
        '恢复配置': 'Restaurar configuración',
        '成功': 'éxito',
        '成功 {0} · 失败 {1}': 'Éxito {0} · Fracaso {1}',
        '所属项目名称': 'Nombre del proyecto',
        '打开主界面': 'Abra la interfaz principal',
        '打开数据目录': 'Abrir directorio de datos',
        '把本地路由服务接入 Codex，并在需要时完整恢复原始配置': 'Conecte los servicios de enrutamiento local al Codex y restaure '
                                         'completamente la configuración original si es necesario',
        '接入 Codex': 'Acceder al Códice',
        '接入信息': 'acceder a la información',
        '接入信息已刷新': 'La información de acceso ha sido actualizada.',
        '接入已失效': 'El acceso ha caducado',
        '接入时会先完整备份现有 Codex 配置，随时可以一键恢复。': 'Al conectarse, se realizará una copia de seguridad completa de la '
                                          'configuración existente del Codex y se podrá restaurar en '
                                          'cualquier momento con un solo clic.',
        '接口协议': 'protocolo de interfaz',
        '接口地址': 'dirección de interfaz',
        '操作': 'funcionar',
        '操作未完成；原配置与已有备份保留。请重新检查，不会回显底层数据。': 'La operación no se completa; Se conservan la configuración '
                                            'original y las copias de seguridad existentes. Vuelva a '
                                            'verificar, los datos subyacentes no se repetirán.',
        '支持推理参数时开启，否则可能产生 400': 'Habilitar cuando se admiten parámetros de inferencia; de lo contrario, se '
                                'pueden generar 400',
        '收起模型': 'Modelo de colapso',
        '数据传输': 'Transferencia de datos',
        '数据位置': 'ubicación de datos',
        '文本': 'texto',
        '开始日期': 'Fecha de inicio',
        '无法读取': 'No puedo leer',
        '日志': 'registro',
        '时间': 'tiempo',
        '结束日期': 'Fecha de fin',
        '是否明确同意启用匿名使用统计？\n\n仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。不收集请求或响应正文、文件、代码、密钥、IP、原始错误和逐请求记录。': '¿Acepta '
                                                                                                        'explícitamente '
                                                                                                        'habilitar '
                                                                                                        'estadísticas '
                                                                                                        'de '
                                                                                                        'uso '
                                                                                                        'anónimas?\n'
                                                                                                        '\n'
                                                                                                        'Solo '
                                                                                                        'se '
                                                                                                        'acumula '
                                                                                                        'la '
                                                                                                        'cantidad '
                                                                                                        'de '
                                                                                                        'llamadas '
                                                                                                        'diarias, '
                                                                                                        'éxitos/errores, '
                                                                                                        'tokens, '
                                                                                                        'intervalos '
                                                                                                        'de '
                                                                                                        'retraso '
                                                                                                        'fijos, '
                                                                                                        'categorías '
                                                                                                        'de '
                                                                                                        'errores '
                                                                                                        'estándar '
                                                                                                        'y '
                                                                                                        'reversiones. '
                                                                                                        'No '
                                                                                                        'se '
                                                                                                        'recopilan '
                                                                                                        'los '
                                                                                                        'cuerpos '
                                                                                                        'de '
                                                                                                        'solicitud '
                                                                                                        'o '
                                                                                                        'respuesta, '
                                                                                                        'archivos, '
                                                                                                        'códigos, '
                                                                                                        'claves, '
                                                                                                        'IP, '
                                                                                                        'errores '
                                                                                                        'sin '
                                                                                                        'procesar '
                                                                                                        'ni '
                                                                                                        'registros '
                                                                                                        'por '
                                                                                                        'solicitud.',
        '显示密钥': 'mostrar clave',
        '智谱 AI': 'Espectro de sabiduría IA',
        '暂无日志 · 服务启动或配置变更后会显示在这里': 'Aún no hay registros · Se mostrará aquí después de que se inicie el '
                                   'servicio o se cambie la configuración.',
        '暂无记录': 'Aún no hay registro',
        '暂无请求记录': 'Aún no hay registro de solicitud',
        '最近活动': 'Actividades recientes',
        '服务已停止': 'El servicio se ha detenido',
        '服务运行中': 'El servicio está funcionando',
        '未命名会话': 'sesión sin nombre',
        '未开启': 'No encendido',
        '未接入': 'No conectado',
        '未检测到 ChatGPT 订阅登录；没有备份或修改会话。': 'No se detectó ningún inicio de sesión de suscripción a ChatGPT; no '
                                        'se realizan copias de seguridad ni se modifican sesiones.',
        '未运行': 'no corriendo',
        '本地地址': 'dirección local',
        '本地接口只监听 127.0.0.1，并要求随机访问令牌；历史 Backup 文件保存在 Codex 配置目录，恢复凭据保存在数据目录的 microglow-relay-codex-receipt.json。': 'La '
                                                                                                                   'interfaz '
                                                                                                                   'local '
                                                                                                                   'sólo '
                                                                                                                   'escucha '
                                                                                                                   'en '
                                                                                                                   '127.0.0.1 '
                                                                                                                   'y '
                                                                                                                   'requiere '
                                                                                                                   'un '
                                                                                                                   'token '
                                                                                                                   'de '
                                                                                                                   'acceso '
                                                                                                                   'aleatorio; '
                                                                                                                   'Los '
                                                                                                                   'archivos '
                                                                                                                   'de '
                                                                                                                   'copia '
                                                                                                                   'de '
                                                                                                                   'seguridad '
                                                                                                                   'históricos '
                                                                                                                   'se '
                                                                                                                   'guardan '
                                                                                                                   'en '
                                                                                                                   'el '
                                                                                                                   'directorio '
                                                                                                                   'de '
                                                                                                                   'configuración '
                                                                                                                   'del '
                                                                                                                   'Codex '
                                                                                                                   'y '
                                                                                                                   'las '
                                                                                                                   'credenciales '
                                                                                                                   'de '
                                                                                                                   'recuperación '
                                                                                                                   'se '
                                                                                                                   'guardan '
                                                                                                                   'en '
                                                                                                                   'microglow-relay-codex-receipt.json '
                                                                                                                   'en '
                                                                                                                   'el '
                                                                                                                   'directorio '
                                                                                                                   'de '
                                                                                                                   'datos.',
        '本地服务': 'servicio local',
        '本地服务已停止': 'El servicio local ha parado',
        '本地模型的 API KEY 使用 Windows DPAPI 加密，仅当前账户可读取。': 'La CLAVE API del modelo local está cifrada mediante '
                                                       'DPAPI de Windows y solo puede ser leída por la '
                                                       'cuenta actual.',
        '本地端口、外观与数据位置': 'Puertos locales, apariencia y ubicaciones de datos.',
        '本地路由服务正在运行，Codex 的新请求会通过当前模型进行路由。': 'El servicio de enrutamiento local está en funcionamiento y las '
                                             'nuevas solicitudes del Codex se enrutan a través del modelo '
                                             'actual.',
        '本地路由让 Codex 通过本机访问你自己的模型供应商；请求正文不会被写入磁盘。': 'El enrutamiento local permite a Codex acceder a su '
                                                    'propio proveedor de modelos de forma nativa; el cuerpo '
                                                    'de la solicitud no se escribe en el disco.',
        '检测到接入后的外部修改': 'Modificación externa detectada después del acceso.',
        '概览': 'Descripción general',
        '模型': 'Modelo',
        '模型名称': 'Nombre del modelo',
        '模型已删除': 'Modelo eliminado',
        '模型管理': 'Gestión de modelos',
        '模型配置保存在 microglow-relay-settings.json，用量日志保存最近 30 天且不记录正文。': 'La configuración del modelo se guarda '
                                                                      'en microglow-relay-settings.json y el '
                                                                      'registro de uso se guarda durante los '
                                                                      'últimos 30 días sin registrar el '
                                                                      'texto.',
        '模型配置已保存': 'Configuración del modelo guardada',
        '正在只读加载本机会话索引…（无需退出 Codex）': 'Cargando índice de sesión nativo de solo lectura... (no es necesario '
                                     'salir del Codex)',
        '正在备份、切换并校验这一条会话…': 'Copia de seguridad, cambio y verificación de esta sesión...',
        '正在核对：{0}…': 'Comprobando: {0}…',
        '正在测试连接…': 'Probando conexión…',
        '正在读取供应商模型列表…': 'Leyendo lista de modelos de proveedores...',
        '测试连接': 'conexión de prueba',
        '添加、修改供应商模型配置，点击卡片选择当前路由模型': 'Agregue y modifique la configuración del modelo de proveedor, haga '
                                     'clic en la tarjeta para seleccionar el modelo de ruta actual',
        '添加模型': 'Agregar modelo',
        '清空': 'Claro',
        '点击“添加模型”填写供应商、API KEY 与模型名称，保存后点击卡片即可切换路由。': 'Haga clic en "Agregar modelo" para completar el '
                                                      'proveedor, la CLAVE API y el nombre del modelo. '
                                                      'Después de guardar, haga clic en la tarjeta para '
                                                      'cambiar de ruta.',
        '点击本页的“接入 Codex”，程序会先完整备份现有 Codex 配置。': 'Haga clic en "Conectarse al Codex" en esta página y el '
                                                'programa primero realizará una copia de seguridad completa '
                                                'de la configuración del Codex existente.',
        '点击记录查看详情': 'Haga clic en el registro para ver los detalles',
        '状态': 'estado',
        '界面语言': 'idioma de la interfaz',
        '白色': 'Blanco',
        '监听端口': 'puerto de escucha',
        '硅基流动': 'flujo a base de silicio',
        '确定': 'Seguro',
        '确定切换这一条会话？': '¿Estás seguro de que quieres cambiar esta conversación?',
        '空闲': 'inactivo',
        '端口修改会在下次启动本地服务时生效；已接入 Codex 时需要重新接入以刷新地址。': 'La modificación del puerto entrará en vigor la próxima '
                                                     'vez que se inicie el servicio local; cuando esté '
                                                     'conectado a Codex, deberá volver a conectarse para '
                                                     'actualizar la dirección.',
        '端口已保存，将在下次启动服务时生效': 'El puerto se ha guardado y entrará en vigor la próxima vez que se inicie el '
                             'servicio.',
        '管理': 'administrar',
        '耗时': 'pérdida de tiempo',
        '能力与协议': 'Capacidades y protocolos',
        '能力可多选，亮色为已开启。仅选择上游支持的能力；不支持思考参数时开启可能产生 400。': 'Se pueden seleccionar múltiples habilidades y el '
                                                       'color brillante significa que están habilitadas. '
                                                       'Solo seleccione capacidades admitidas por upstream; '
                                                       'encenderlo puede generar 400 cuando los parámetros '
                                                       'de pensamiento no son compatibles.',
        '自动寻找 Codex 桌面端核心（可手动指定 codex.exe）': 'Encuentre automáticamente el núcleo del escritorio Codex '
                                             '(codex.exe se puede especificar manualmente)',
        '自动滚动': 'desplazamiento automático',
        '自定义 / 中转服务': 'Servicio personalizado/de tránsito',
        '自定义中转时填写，例如：我的中转站': 'Complete al personalizar la transferencia, por ejemplo: Mi estación de '
                             'transferencia',
        '警告': 'advertir',
        '让同一段 Codex 会话在官方订阅与 Relay 模型之间继续使用': 'Permitir que se siga utilizando la misma sesión del Codex '
                                              'entre las suscripciones oficiales y los modelos Relay',
        '设置': 'configuración',
        '访问令牌': 'token de acceso',
        '识别到历史路由模型标识，归类为其它接入；不等于 Codex 或当前 Relay。': 'El identificador del modelo de enrutamiento histórico '
                                                    'se identifica y clasifica como otro acceso; no es igual '
                                                    'al Codex o al Relay actual.',
        '请先保存至少一个模型配置。': 'Primero guarde al menos una configuración de modelo.',
        '请先明确选择 Codex 或 Relay。': 'Seleccione explícitamente Codex o Relay primero.',
        '请先添加一个模型': 'Por favor agregue un modelo primero',
        '请在“模型管理”页面添加一个供应商模型。': 'Agregue un modelo de proveedor en la página de Gestión de modelos.',
        '请求详情': 'Solicitar detalles',
        '读取': 'leer',
        '读取失败：': 'Error de lectura:',
        '读取成功：当前索引中没有符合条件的会话（可切换「已归档」查看）。': 'Lectura exitosa: No hay ninguna reunión que cumpla con los '
                                            'criterios en el índice actual (puede cambiar a "Archivado" para '
                                            'ver).',
        '读取成功：本页 {0} 条会话。': 'Lectura exitosa: {0} sesiones para esta página.',
        '赛博朋克': 'ciberpunk',
        '路由信息': 'información de ruta',
        '路由标识': 'ID de ruta',
        '输入 Token': 'Introducir ficha',
        '输入与输出合计': 'Entrada y salida totales',
        '输出 Token': 'Ficha de salida',
        '运行中': 'Correr',
        '还没有模型配置': 'Aún no hay configuración de modelo',
        '进入本页时读取本机会话索引。': 'Lea el índice de la sesión local al ingresar a esta página.',
        '连接信息': 'información de conexión',
        '退出': 'abandonar',
        '退出时，将登录方式设为 ChatGPT 订阅登录（不修改会话或默认模型）': 'Al salir, configure el método de inicio de sesión en inicio '
                                                'de sesión de suscripción ChatGPT (no modifique la sesión ni '
                                                'el modelo predeterminado)',
        '退出选项 · 仅登录设置 · 默认关闭': 'Opciones de salida · Configuración de solo inicio de sesión · Desactivado de '
                               'forma predeterminada',
        '选择': 'elegir',
        '选择 Codex 桌面端核心': 'Seleccione Codex Desktop Core',
        '选择核心': 'Seleccionar núcleo',
        '选项未能保存，请检查本地存储。': 'No se pudieron guardar las opciones; verifique el almacenamiento local.',
        '配置已保存 · {0}': 'Configuración guardada · {0}',
        '重启 Codex，新建任务后选择“{0}”。': 'Reinicia Codex, crea una tarea nueva y selecciona «{0}».',
        '重新接入': 'reconectar',
        '金碧辉煌': 'espléndido',
        '错误': 'error',
        '隐私保护：不保存 Prompt、Response 或原始请求正文。': 'Protección de la privacidad: el mensaje, la respuesta o el '
                                             'cuerpo de la solicitud original no se guardan.',
        '需要还原时点击“恢复配置”，本程序写入的字段会被撤销。': 'Cuando necesite restaurar, haga clic en "Restaurar configuración" y '
                                       'los campos escritos por este programa serán revocados.',
        '高': 'alto',
        '黑色': 'negro',
        '默认关闭。仅在你主动同意后累计 UTC 每日计数；不记录 Prompt、Response、正文、文件、代码、密钥、IP 或原始错误。': 'Desactivado de forma '
                                                                              'predeterminada. La '
                                                                              'acumulación diaria de UTC '
                                                                              'cuenta solo con su '
                                                                              'consentimiento activo; no se '
                                                                              'registran mensajes, '
                                                                              'respuestas, cuerpos, '
                                                                              'archivos, códigos, claves, IP '
                                                                              'ni errores originales.',
        '（未设置）': '(no establecido)',
        '，当前使用': ', actualmente usando',
        '，点击切换': ', haga clic para cambiar',
        '雾蓝科技': 'Niebla Azul Tech',
        '石墨青金': 'Grafito Turquesa Dorado',
        '微光': 'MicroGlow',
        '夜幕': 'Anochecer',
        '金辉': 'Destello Dorado',
        '月白': 'Luna Blanca',
        '星港': 'Puerto Estelar'},
 'ja': {
        '检测到更高优先级的 Claude 配置：{0} · 可能覆盖 Relay 接入，未改动': '優先度の高い Claude 設定を検出しました：{0} · Relay 接続が上書きされる可能性があります（未変更）','\n目标模型：{0}': '対象モデル: {0}',
        '\n该会话使用历史路由标识，按其它接入处理。': 'このセッションは履歴ルート識別を使用し、他のアクセスとして扱われます。',
        '\n该会话由其它工具接入。': 'このセッションは他のツールからアクセスされます。',
        'AI 连接、路由状态与最近请求总览': 'AI 接続、ルーティング ステータス、最近のリクエストの概要',
        'Codex · ChatGPT 订阅': 'コーデックス · ChatGPT 購読する',
        'Codex 已不再使用本路由器': 'Codex はこのルーターを使用しなくなりました',
        'Codex 已不再指向本路由器': 'Codex はこのルーターをポイントしなくなりました',
        'Codex 已接入': 'コーデックスが接続されています',
        'Codex 已接入 · 已备份 {0}': 'Codex が接続されています · {0} がバックアップされました',
        'Codex 已重新指向本路由器': 'コーデックスはこのルーターにリダイレクトされました',
        'Codex 已重新接入 · 已备份 {0}': 'コーデックスが再接続されました · {0} がバックアップされました',
        'Codex 当前指向': 'コーデックスが現在指しているのは、',
        'Codex 接入': 'コーデックスへのアクセス',
        'Codex 接入已失效：配置被其它程序改写，请到“Codex 接入”页重新接入': 'コーデックス アクセスの有効期限が切れています: 設定は他のプログラムによって上書きされています。「コーデックス '
                                                   'アクセス」ページにアクセスして再アクセスしてください。',
        'Codex 配置': 'コーデックス構成',
        'Codex 配置仍然指向本地路由，请先点击“重新接入”或启动本地服务。': 'Codex 設定は引き続きローカル ルートを指します。 '
                                               '「再接続」をクリックするか、最初にローカルサービスを開始してください。',
        'Codex 配置在接入后被其他程序改写过（例如切换模型通道），当前请求不会经过本程序。点击“重新接入”即可按现在的情况重新写入并备份。': 'Codex 設定はアクセス後 (モデル '
                                                                               'チャネルの切り替えなど) '
                                                                               '他のプログラムによって書き換えられており、現在のリクエストはこのプログラムを経由しません。 '
                                                                               '「再接続」をクリックすると現状に合わせて書き換え、バックアップが可能です。',
        'Codex 配置已恢复 · 原备份 {0}': 'コーデックス構成が復元されました · 元のバックアップ {0}',
        'Codex 配置已被其它程序改写，接入已失效，请重新接入': 'Codex 構成が他のプログラムによって上書きされ、アクセスの有効期限が切れました。再度アクセスしてください。',
        'Ollama（本机）': 'オラマ (ネイティブ)',
        'Relay 接入配置未就绪；没有备份或修改会话。': 'リレーアクセス構成の準備ができていません。バックアップや変更セッションはありません。',
        'iOS 风格': 'iOSスタイル',
        '{0:.1f} 万': '{0:.1f}百万',
        '{0:.2f} 亿': '{0:.2f} 億',
        '{0:.2f} 秒': '{0:.2f} 秒',
        '{0} 启动失败': '{0} を開始できませんでした',
        '{0} 已启动': '{0} が有効化されています',
        '{0} 已在运行。': '{0} はすでに実行されています。',
        '{0} 的目标模式': '{0} のターゲット パターン',
        '上下文上限': 'コンテキストキャップ',
        '上下文窗口大小。': 'コンテキストウィンドウのサイズ。',
        '上次退出：有对象未切换，原配置与操作记录已保留，请检查后手动处理。': '最終終了: 切り替えられていないオブジェクトがあり、元の構成と操作記録が保持されています。手動で確認して対処してください。',
        '上游模型支持函数工具调用时开启': '上流モデルは関数ツール呼び出し時のオンをサポートしています',
        '上游模型支持图片输入时开启': '上位モデルが画像入力をサポートしている場合に有効になります',
        '下一页': '次のページ',
        '中': '真ん中',
        '主题 · {0}': 'トピック · {0}',
        '主题模式': 'テーマモード',
        '仅实际退出时生效，关闭到托盘不执行。保留所有会话的模型和 Provider、全局默认模型及其它工具的配置；未检测到订阅登录或存在外部改动时不执行。': '実際に終了するときにのみ有効になります。トレイを閉じても効果はありません。すべてのセッションのモデルとプロバイダー、グローバルなデフォルト '
                                                                                     'モデル、およびその他のツールの構成を保持します。サブスクリプションのログインが検出されない場合、または外部の変更がある場合は実行されません。',
        '仅调整所选会话的模型接入配置，不读取或改写历史对话；其它工具的会话不会自动接管。': '選択したセッションのモデル '
                                                    'アクセス構成のみが調整され、履歴の会話は読み取られたり書き換えられたりしません。他のツールのセッションは自動的に引き継がれません。',
        '今日 Token 消耗': '今日のトークン消費量',
        '今日 Token：{0:,}': '今日のトークン: {0:,}',
        '今日成功率': '今日の成功率',
        '今日暂无请求': '今日はリクエストはありません',
        '今日请求': '今すぐリクエストしてください',
        '以下字段在接入后被其他程序改过：\n{0}\n\n仍然强制恢复为接入前的状态吗？（会先备份当前配置）': '次のフィールドは、アクセス後に他のプログラムによって変更されています。\n'
                                                              '{0}\n'
                                                              '\n'
                                                              'まだアクセス前の状態に強制的に復元されますか? (現在の構成が最初にバックアップされます)',
        '会话兼容': 'セッション互換性がある',
        '会话兼容选项已保存': 'セッション互換性オプションが保存されました',
        '会话切换执行结果': 'セッション切り替えの実行結果',
        '会话列表': '会話リスト',
        '会话列表读取状态': 'セッションリストの読み取りステータス',
        '会话名称': 'セッション名',
        '会话配置操作正在完成，请稍后再退出。': 'セッション構成操作が完了しています。後で終了してください。',
        '会话：{0}\n当前：{1}\n目标：{2}{3}{4}\n确认 Codex 已正常退出？确定后先备份原配置，再切换并校验；不修改历史正文。': 'セッション: {0}\n'
                                                                                  '現在: {1}\n'
                                                                                  'ターゲット: {2}{3}{4}\n'
                                                                                  'Codex '
                                                                                  'が正常に終了したことを確認しましたか?確認後、最初に元の構成をバックアップし、次に切り替えて検証します。歴史的なテキストを変更しないでください。',
        '传输中': '送信中',
        '低': '低い',
        '使用步骤': '利用手順',
        '供应商': 'サプライヤー',
        '供应商名称': 'サプライヤー名',
        '供应商未返回模型列表，请手动填写。': 'サプライヤーからモデル リストが返されませんでした。手動で入力してください。',
        '保存后使用 Windows DPAPI 加密存储。': 'Windows DPAPI を使用して、保存後にストレージを暗号化します。',
        '保存退出选项与核心路径': '終了オプションとコアパスを保存する',
        '保存配置': '設定の保存',
        '信息': '情報',
        '修改模型': 'モデルの変更',
        '修改模型配置': 'モデル構成を変更する',
        '修改模式为': 'モードを次のように変更します',
        '停止接入': 'アクセスを停止する',
        '全部': '全て',
        '共 {0} 个模型配置 · 点击卡片切换，点击铅笔图标编辑参数': '合計 {0} 個のモデル構成 · カードをクリックして切り替え、鉛筆アイコンをクリックしてパラメータを編集します',
        '关于': 'について',
        '关闭': '閉鎖',
        '关闭请求详情': 'クローズリクエストの詳細',
        '其它接入': 'その他のアクセス',
        '其它接入会话需明确选择目标；Relay 不自动接管。': '他のアクセス セッションでは明示的なターゲットの選択が必要です。 Relay は自動的に引き継ぎません。',
        '准备读取会话索引。': 'セッションインデックスを読み取る準備をします。',
        '切换成功：{0} → {1}。原配置已备份，写入结果已校验；下方列表已刷新。': '切り替えが成功しました: {0} → '
                                                  '{1}。元の構成はバックアップされており、書き込み結果は検証されています。以下のリストが更新されました。',
        '切换未完成：{0}，校验通过 {1} / {2}。原配置备份与操作记录已保留，不会自动重写会话。': '切り替えが完了していません: {0}、検証は {1}/{2} '
                                                            'に合格しました。元の構成バックアップと操作記録は保持されており、セッションは自動的に書き換えられません。',
        '切换模型': 'スイッチモデル',
        '删除后将无法自动恢复，需要重新填写 API KEY。': '削除後は自動的に復元できず、API KEYを再度入力する必要があります。',
        '删除此模型配置': 'このモデル構成を削除します',
        '删除这条模型配置？': 'このモデル構成を削除しますか?',
        '刷新会话列表': 'セッションリストを更新する',
        '刷新接入': 'アクセスを更新',
        '匿名使用统计': '匿名の使用統計',
        '匿名使用统计已关闭': '匿名の使用状況統計がオフになっています',
        '匿名使用统计已启用': '匿名の使用状況統計が有効になっています',
        '匿名使用统计明确同意开关': '匿名使用統計の明示的同意スイッチ',
        '单次最大输出。': '単一最大出力。',
        '发起请求后，可在此查看不含正文的安全摘要。': 'リクエストが行われた後、テキストなしのセキュリティ概要をここで表示できます。',
        '取消': 'キャンセル',
        '可点击“读取”从供应商获取可用模型。': '「読む」をクリックすると、サプライヤーから入手可能なモデルを入手できます。',
        '国家信息不由客户端采集；未来上传阶段仅允许服务端接入层瞬时推断。撤回后立即停止产生新的遥测数据。': '国内情報はクライアントによって収集されません。今後のアップロード段階では、サーバー '
                                                            'アクセス層での瞬間的な推論のみが許可されます。撤退直後に新しいテレメトリ '
                                                            'データの生成を停止します。',
        '图片支持': '画像のサポート',
        '图片输入': '画像入力',
        '在“模型管理”页面添加至少一个模型，并点击模型卡片进行选择。': '「モデル管理」ページで少なくとも 1 つのモデルを追加し、モデル カードをクリックして選択します。',
        '填写供应商公布的完整端点；程序按原样请求，不会改写路径。': 'ベンダーが公開した完全なエンドポイントを入力します。プログラムはそれをそのまま要求し、パスを書き換えません。',
        '复制': 'コピー',
        '外观': '外観',
        '失败': '失敗',
        '失败 {0}': '失敗しました {0}',
        '实时显示请求、连接与配置变更记录': 'リクエスト、接続、構成変更記録のリアルタイム表示',
        '客户端接入': 'クライアントアクセス',
        '将撤销本程序对 Codex 配置所做的修改，并停止本地服务。': 'このプログラムによって Codex 構成に加えられた変更は元に戻され、ローカル サービスは停止されます。',
        '尚未接入': 'まだ接続されていません',
        '尚未接入 Codex': 'まだコーデックスに接続されていません',
        '尚未配置模型': 'モデルはまだ設定されていません',
        '展开已读取的模型列表；也可直接手动输入模型名称': '読み取りモデルのリストを展開します。モデル名を手動で直接入力することもできます',
        '工具调用': 'ツール呼び出し',
        '已取消；没有备份或修改会话。': 'キャンセル;バックアップまたは変更セッションはありません。',
        '已开启': 'すでにオンになっています',
        '已归档': 'アーカイブ済み',
        '已按当前模型回填全部原参数；API KEY 已解密加载并默认遮蔽。': 'すべての元のパラメータは、現在のモデルに従ってバックフィルされています。 API KEY '
                                             'はデフォルトで復号化され、ロードされ、マスクされています。',
        '已接入': 'すでに接続されています',
        '已接入 Codex，但端口无法启动：{0}': 'Codex に接続しましたが、ポートを開始できません: {0}',
        '已接入但服务未运行': '接続されていますが、サービスが実行されていません',
        '已知供应商会自动匹配；自定义中转请按实际选择。': '既知のサプライヤーは自動的に照合されます。カスタム転送の場合は、実際の条件に応じて選択してください。',
        '已读取 {0} 个模型': '{0} 個のモデルが読み取られました',
        '已读取 {0} 个模型，请从列表选择': '{0} 個のモデルが読み取られています。リストから選択してください',
        '帮助改进 MicroGlow Relay': 'MicroGlow Relay の改善にご協力ください',
        '平均耗时 {0:.2f} 秒': '平均所要時間 {0:.2f} 秒',
        '应用': '応用',
        '归档会话仅供查看；请先在 Codex 中取消归档，再退出 Codex 后操作。': 'アーカイブされたセッションは閲覧専用です。まず Codex でアーカイブをキャンセルしてから、Codex '
                                                   'を終了してから続行してください。',
        '当前使用': '現在使用中',
        '当前模型已切换': '現行モデルから切り替わりました',
        '当前模式': '現在のモード',
        '当前路由模型': '現在のルーティングモデル',
        '思考强度': '思考の強さ',
        '思考模式': '思考モデル',
        '恢复 Codex 配置？': 'Codex 構成を復元しますか?',
        '恢复配置': '構成を復元する',
        '成功': '成功',
        '成功 {0} · 失败 {1}': '成功 {0} · 失敗 {1}',
        '所属项目名称': 'プロジェクト名',
        '打开主界面': 'メインインターフェイスを開きます',
        '打开数据目录': 'データディレクトリを開く',
        '把本地路由服务接入 Codex，并在需要时完整恢复原始配置': 'ローカル ルーティング サービスを Codex に接続し、必要に応じて元の構成を完全に復元します',
        '接入 Codex': 'コーデックスにアクセスする',
        '接入信息': 'アクセス情報',
        '接入信息已刷新': 'アクセス情報を更新しました',
        '接入已失效': 'アクセス期限が切れています',
        '接入时会先完整备份现有 Codex 配置，随时可以一键恢复。': '接続すると、既存の Codex 構成が完全にバックアップされ、ワンクリックでいつでも復元できます。',
        '接口协议': 'インターフェースプロトコル',
        '接口地址': 'インターフェースアドレス',
        '操作': '操作する',
        '操作未完成；原配置与已有备份保留。请重新检查，不会回显底层数据。': '操作は完了していません。元の構成と既存のバックアップは保持されます。再確認してください。基になるデータはエコーされません。',
        '支持推理参数时开启，否则可能产生 400': '推論パラメータがサポートされている場合に有効にします。それ以外の場合は 400 が生成される可能性があります',
        '收起模型': 'モデルを折りたたむ',
        '数据传输': 'データ転送',
        '数据位置': 'データの場所',
        '文本': '文章',
        '开始日期': '開始日',
        '无法读取': '読めません',
        '日志': 'ログ',
        '时间': '時間',
        '结束日期': '終了日',
        '是否明确同意启用匿名使用统计？\n\n仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。不收集请求或响应正文、文件、代码、密钥、IP、原始错误和逐请求记录。': '匿名の使用状況統計を有効にすることに明示的に同意しますか?\n'
                                                                                                        '\n'
                                                                                                        '毎日の呼び出し、成功/エラー、トークン、固定遅延間隔、標準エラー '
                                                                                                        'カテゴリ、ロールバックの数のみが蓄積されます。リクエストまたはレスポンスの本文、ファイル、コード、キー、IP、生のエラー、およびリクエストごとのログは収集されません。',
        '显示密钥': 'キーを表示',
        '智谱 AI': 'ウィズダムスペクトルAI',
        '暂无日志 · 服务启动或配置变更后会显示在这里': 'ログはまだありません · サービスが開始されるか、設定が変更されるとここに表示されます。',
        '暂无记录': 'まだ記録がありません',
        '暂无请求记录': 'まだリクエスト記録がありません',
        '最近活动': '最近の活動',
        '服务已停止': 'サービスが停止されました',
        '服务运行中': 'サービスが実行中です',
        '未命名会话': '名前のないセッション',
        '未开启': '電源が入っていない',
        '未接入': '接続されていません',
        '未检测到 ChatGPT 订阅登录；没有备份或修改会话。': 'ChatGPT サブスクリプション ログインが検出されませんでした。バックアップまたは変更されたセッションはありません。',
        '未运行': '稼働していない',
        '本地地址': 'ローカルアドレス',
        '本地接口只监听 127.0.0.1，并要求随机访问令牌；历史 Backup 文件保存在 Codex 配置目录，恢复凭据保存在数据目录的 microglow-relay-codex-receipt.json。': 'ローカル '
                                                                                                                   'インターフェイスは '
                                                                                                                   '127.0.0.1 '
                                                                                                                   'のみをリッスンし、ランダム '
                                                                                                                   'アクセス '
                                                                                                                   'トークンを必要とします。履歴バックアップ '
                                                                                                                   'ファイルは '
                                                                                                                   'Codex '
                                                                                                                   '構成ディレクトリに保存され、回復資格情報はデータ '
                                                                                                                   'ディレクトリの '
                                                                                                                   'microglow-relay-codex-receipt.json '
                                                                                                                   'に保存されます。',
        '本地服务': 'ローカルサービス',
        '本地服务已停止': 'ローカルサービスが停止しました',
        '本地模型的 API KEY 使用 Windows DPAPI 加密，仅当前账户可读取。': 'ローカル モデルの API KEY は Windows DPAPI '
                                                       'を使用して暗号化されており、現在のアカウントのみが読み取ることができます。',
        '本地端口、外观与数据位置': 'ローカルポート、外観およびデータの場所',
        '本地路由服务正在运行，Codex 的新请求会通过当前模型进行路由。': 'ローカル ルーティング サービスが実行されており、Codex に対する新しい要求は現在のモデルを通じてルーティングされます。',
        '本地路由让 Codex 通过本机访问你自己的模型供应商；请求正文不会被写入磁盘。': 'ローカル ルーティングにより、Codex は独自のモデル '
                                                    'プロバイダーにネイティブにアクセスできます。リクエスト本文はディスクに書き込まれません。',
        '检测到接入后的外部修改': 'アクセス後に外部変更が検出されました',
        '概览': '概要',
        '模型': 'モデル',
        '模型名称': '機種名',
        '模型已删除': 'モデルが削除されました',
        '模型管理': 'モデル管理',
        '模型配置保存在 microglow-relay-settings.json，用量日志保存最近 30 天且不记录正文。': 'モデル構成は microglow-relay-settings.json '
                                                                      'に保存され、使用ログはテキストを記録せずに過去 30 日間保存されます。',
        '模型配置已保存': 'モデル構成が保存されました',
        '正在只读加载本机会话索引…（无需退出 Codex）': 'ネイティブ セッション インデックスを読み取り専用でロードしています... (Codex を終了する必要はありません)',
        '正在备份、切换并校验这一条会话…': 'このセッションをバックアップ、切り替え、検証しています...',
        '正在核对：{0}…': '確認中: {0}…',
        '正在测试连接…': '接続をテスト中…',
        '正在读取供应商模型列表…': 'サプライヤーモデルリストを読んでいます...',
        '测试连接': 'テスト接続',
        '添加、修改供应商模型配置，点击卡片选择当前路由模型': 'サプライヤー モデル構成を追加および変更します。カードをクリックして現在のルーティング モデルを選択します。',
        '添加模型': 'モデルの追加',
        '清空': 'クリア',
        '点击“添加模型”填写供应商、API KEY 与模型名称，保存后点击卡片即可切换路由。': '「モデルを追加」をクリックして、サプライヤー、API '
                                                      'KEY、モデル名を入力します。保存後、カードをクリックしてルートを切り替えます。',
        '点击本页的“接入 Codex”，程序会先完整备份现有 Codex 配置。': 'このページで [Codex に接続] をクリックすると、プログラムはまず既存の Codex '
                                                '構成を完全にバックアップします。',
        '点击记录查看详情': 'レコードをクリックして詳細を表示します',
        '状态': '州',
        '界面语言': 'インターフェース言語',
        '白色': '白',
        '监听端口': 'リスニングポート',
        '硅基流动': 'シリコンベースのフロー',
        '确定': 'もちろん',
        '确定切换这一条会话？': 'この会話を切り替えてもよろしいですか?',
        '空闲': 'アイドル状態',
        '端口修改会在下次启动本地服务时生效；已接入 Codex 时需要重新接入以刷新地址。': 'ポートの変更は、次回ローカル サービスが開始されるときに有効になります。 Codex '
                                                     'に接続している場合は、アドレスを更新するために再接続する必要があります。',
        '端口已保存，将在下次启动服务时生效': 'ポートは保存されており、次回サービスを開始したときに有効になります。',
        '管理': '管理',
        '耗时': '時間がかかる',
        '能力与协议': '機能とプロトコル',
        '能力可多选，亮色为已开启。仅选择上游支持的能力；不支持思考参数时开启可能产生 400。': '複数の能力を選択でき、明るい色はそれらが有効であることを意味します。アップストリームでサポートされている機能のみを選択してください。 '
                                                       'think パラメータがサポートされていない場合、オンにすると 400 が生成される場合があります。',
        '自动寻找 Codex 桌面端核心（可手动指定 codex.exe）': 'Codex デスクトップ コアを自動的に検索します (codex.exe は手動で指定できます)',
        '自动滚动': '自動スクロール',
        '自定义 / 中转服务': 'カスタム/輸送サービス',
        '自定义中转时填写，例如：我的中转站': '乗り換えをカスタマイズするときに入力します。例: My transfer station',
        '警告': '警告する',
        '让同一段 Codex 会话在官方订阅与 Relay 模型之间继续使用': '公式サブスクリプションと Relay モデル間で同じ Codex セッションを引き続き使用できるようにする',
        '设置': '設定',
        '访问令牌': 'アクセストークン',
        '识别到历史路由模型标识，归类为其它接入；不等于 Codex 或当前 Relay。': '過去のルーティング モデル識別子は、他のアクセスとして識別され、分類されます。 Codex または現在の '
                                                    'Relay と等しくありません。',
        '请先保存至少一个模型配置。': '最初に少なくとも 1 つのモデル構成を保存してください。',
        '请先明确选择 Codex 或 Relay。': '最初に Codex または Relay を明示的に選択してください。',
        '请先添加一个模型': 'まずモデルを追加してください',
        '请在“模型管理”页面添加一个供应商模型。': 'モデル管理ページでサプライヤー モデルを追加してください。',
        '请求详情': 'リクエストの詳細',
        '读取': '読む',
        '读取失败：': '読み取りに失敗しました:',
        '读取成功：当前索引中没有符合条件的会话（可切换「已归档」查看）。': '正常に読み取られました: 現在のインデックスに条件を満たす会議はありません (「アーカイブ」に切り替えて表示できます)。',
        '读取成功：本页 {0} 条会话。': '正常に読み取りました: このページのセッションは {0} 個です。',
        '赛博朋克': 'サイバーパンク',
        '路由信息': 'ルーティング情報',
        '路由标识': 'ルートID',
        '输入 Token': 'トークンを入力してください',
        '输入与输出合计': '総入出力',
        '输出 Token': '出力トークン',
        '运行中': 'ランニング',
        '还没有模型配置': 'モデル設定がまだありません',
        '进入本页时读取本机会话索引。': 'このページに入るときは、ローカル セッション インデックスを読んでください。',
        '连接信息': '接続情報',
        '退出': 'やめる',
        '退出时，将登录方式设为 ChatGPT 订阅登录（不修改会话或默认模型）': '終了するときに、ログイン方法を ChatGPT サブスクリプション ログインに設定します (セッションまたはデフォルト '
                                                'モデルを変更しないでください)。',
        '退出选项 · 仅登录设置 · 默认关闭': '終了オプション · ログインのみの設定 · デフォルトではオフ',
        '选择': '選ぶ',
        '选择 Codex 桌面端核心': 'Codex デスクトップ コアを選択します',
        '选择核心': 'コアの選択',
        '选项未能保存，请检查本地存储。': 'オプションを保存できませんでした。ローカル ストレージを確認してください。',
        '配置已保存 · {0}': '構成が保存されました · {0}',
        '重启 Codex，新建任务后选择“{0}”。': 'Codex を再起動し、新しいタスクで「{0}」を選択します。',
        '重新接入': '再接続する',
        '金碧辉煌': '素晴らしい',
        '错误': '間違い',
        '隐私保护：不保存 Prompt、Response 或原始请求正文。': 'プライバシー保護: プロンプト、レスポンス、または元のリクエスト本文は保存されません。',
        '需要还原时点击“恢复配置”，本程序写入的字段会被撤销。': '復元する必要がある場合は、「構成の復元」をクリックすると、このプログラムによって書き込まれたフィールドが取り消されます。',
        '高': '高い',
        '黑色': '黒',
        '默认关闭。仅在你主动同意后累计 UTC 每日计数；不记录 Prompt、Response、正文、文件、代码、密钥、IP 或原始错误。': 'デフォルトではオフです。 UTC '
                                                                              'の日次カウントは、お客様の積極的な同意がある場合にのみ蓄積します。プロンプト、応答、本文、ファイル、コード、キー、IP、または元のエラーはログに記録されません。',
        '（未设置）': '(未設定)',
        '，当前使用': '、現在使用中',
        '，点击切换': '、クリックして切り替えます',
        '雾蓝科技': 'ミストブルーテック',
        '石墨青金': 'グラファイトティールゴールド',
        '微光': 'マイクログロー',
        '夜幕': 'ナイトフォール',
        '金辉': 'ゴールデングロー',
        '月白': 'ムーンホワイト',
        '星港': 'スターハーバー'},
 'ko': {
        '检测到更高优先级的 Claude 配置：{0} · 可能覆盖 Relay 接入，未改动': '우선순위가 더 높은 Claude 설정 발견: {0} · Relay 연결을 덮어쓸 수 있음 (변경하지 않음)','\n目标模型：{0}': '대상 모델: {0}',
        '\n该会话使用历史路由标识，按其它接入处理。': '이 세션은 과거 경로 식별을 사용하며 기타 액세스로 처리됩니다.',
        '\n该会话由其它工具接入。': '이 세션은 다른 도구에서 액세스됩니다.',
        'AI 连接、路由状态与最近请求总览': 'AI 연결, 라우팅 상태, 최근 요청 개요',
        'Codex · ChatGPT 订阅': '코덱스 · ChatGPT 구독',
        'Codex 已不再使用本路由器': 'Codex는 더 이상 이 라우터를 사용하지 않습니다.',
        'Codex 已不再指向本路由器': 'Codex는 더 이상 이 라우터를 가리키지 않습니다.',
        'Codex 已接入': '코덱스가 연결되었습니다',
        'Codex 已接入 · 已备份 {0}': 'Codex가 연결되었습니다 · {0} 백업되었습니다',
        'Codex 已重新指向本路由器': 'Codex가 이 라우터로 리디렉션되었습니다.',
        'Codex 已重新接入 · 已备份 {0}': '코덱스가 다시 연결되었습니다 · {0}을(를) 백업했습니다.',
        'Codex 当前指向': '코덱스는 현재 다음을 가리킨다.',
        'Codex 接入': '코덱스 액세스',
        'Codex 接入已失效：配置被其它程序改写，请到“Codex 接入”页重新接入': 'Codex 액세스가 만료되었습니다. 다른 프로그램이 구성을 덮어썼습니다. 다시 액세스하려면 '
                                                   '"Codex 액세스" 페이지로 이동하세요.',
        'Codex 配置': '코덱스 구성',
        'Codex 配置仍然指向本地路由，请先点击“重新接入”或启动本地服务。': 'Codex 구성은 여전히 \u200b\u200b로컬 경로를 가리킵니다. "다시 연결"을 클릭하거나 먼저 로컬 '
                                               '서비스를 시작하십시오.',
        'Codex 配置在接入后被其他程序改写过（例如切换模型通道），当前请求不会经过本程序。点击“重新接入”即可按现在的情况重新写入并备份。': 'Codex 구성은 액세스 후(예: 모델 채널 전환) '
                                                                               '다른 프로그램에 의해 다시 작성되었으며 현재 요청은 '
                                                                               '이 프로그램을 거치지 않습니다. 현재 상황에 따라 '
                                                                               '다시 작성하고 백업하려면 "다시 연결"을 '
                                                                               '클릭하세요.',
        'Codex 配置已恢复 · 原备份 {0}': 'Codex 구성 복원됨 · 원본 백업 {0}',
        'Codex 配置已被其它程序改写，接入已失效，请重新接入': 'Codex 구성이 다른 프로그램에 의해 덮어쓰기되어 액세스 권한이 만료되었습니다. 다시 접속해 주세요.',
        'Ollama（本机）': '올라마(원주민)',
        'Relay 接入配置未就绪；没有备份或修改会话。': '릴레이 액세스 구성이 준비되지 않았습니다. 백업 또는 수정 세션이 없습니다.',
        'iOS 风格': 'iOS 스타일',
        '{0:.1f} 万': '{0:.1f}백만',
        '{0:.2f} 亿': '{0:.2f}십억',
        '{0:.2f} 秒': '{0:.2f}초',
        '{0} 启动失败': '{0}을(를) 시작하지 못했습니다.',
        '{0} 已启动': '{0}이(가) 활성화되었습니다',
        '{0} 已在运行。': '{0}이(가) 이미 실행 중입니다.',
        '{0} 的目标模式': '{0}의 대상 패턴',
        '上下文上限': '컨텍스트 캡',
        '上下文窗口大小。': '컨텍스트 창 크기.',
        '上次退出：有对象未切换，原配置与操作记录已保留，请检查后手动处理。': '마지막 종료: 전환되지 않은 개체가 있으며 원래 구성 및 작업 기록이 유지됩니다. 수동으로 확인하고 처리하시기 '
                                             '바랍니다.',
        '上游模型支持函数工具调用时开启': '업스트림 모델은 기능 도구가 호출될 때 켜짐을 지원합니다.',
        '上游模型支持图片输入时开启': '업스트림 모델이 이미지 입력을 지원할 때 활성화',
        '下一页': '다음 페이지',
        '中': '가운데',
        '主题 · {0}': '주제 · {0}',
        '主题模式': '테마 모드',
        '仅实际退出时生效，关闭到托盘不执行。保留所有会话的模型和 Provider、全局默认模型及其它工具的配置；未检测到订阅登录或存在外部改动时不执行。': '실제로 종료할 때만 적용됩니다. 트레이를 '
                                                                                     '닫아도 효과가 없습니다. 모든 세션에 '
                                                                                     '대한 모델 및 공급자, 전역 기본 모델 '
                                                                                     '및 기타 도구의 구성을 유지합니다. 구독 '
                                                                                     '로그인이 감지되지 않거나 외부 변경 '
                                                                                     '사항이 있는 경우에는 실행되지 않습니다.',
        '仅调整所选会话的模型接入配置，不读取或改写历史对话；其它工具的会话不会自动接管。': '선택한 세션의 모델 액세스 구성만 조정되며 기록 대화는 읽거나 다시 쓰지 않습니다. 다른 도구의 '
                                                    '세션은 자동으로 인계되지 않습니다.',
        '今日 Token 消耗': '오늘의 토큰 소비',
        '今日 Token：{0:,}': '오늘의 토큰: {0:,}',
        '今日成功率': '오늘의 성공률',
        '今日暂无请求': '오늘은 요청이 없습니다',
        '今日请求': '오늘 요청하세요',
        '以下字段在接入后被其他程序改过：\n{0}\n\n仍然强制恢复为接入前的状态吗？（会先备份当前配置）': '액세스 후 다른 프로그램에 의해 다음 필드가 변경되었습니다.\n'
                                                              '{0}\n'
                                                              '\n'
                                                              '아직도 액세스 전 상태로 강제 복원해야 하나요? (현재 구성이 먼저 백업됩니다.)',
        '会话兼容': '세션 호환 가능',
        '会话兼容选项已保存': '세션 호환성 옵션이 저장되었습니다.',
        '会话切换执行结果': '세션 전환 실행 결과',
        '会话列表': '대화 목록',
        '会话列表读取状态': '세션 목록 읽기 상태',
        '会话名称': '세션 이름',
        '会话配置操作正在完成，请稍后再退出。': '세션 구성 작업이 완료 중입니다. 나중에 종료하십시오.',
        '会话：{0}\n当前：{1}\n目标：{2}{3}{4}\n确认 Codex 已正常退出？确定后先备份原配置，再切换并校验；不修改历史正文。': '세션: {0}\n'
                                                                                  '현재: {1}\n'
                                                                                  '대상: {2}{3}{4}\n'
                                                                                  'Codex가 정상적으로 종료되었는지 '
                                                                                  '확인하셨나요? 확인 후 먼저 원래 구성을 '
                                                                                  '백업한 다음 전환하고 확인하십시오. 역사적 '
                                                                                  '텍스트를 수정하지 마십시오.',
        '传输中': '전송 중',
        '低': '낮은',
        '使用步骤': '사용 단계',
        '供应商': '공급자',
        '供应商名称': '공급자 이름',
        '供应商未返回模型列表，请手动填写。': '공급업체가 모델 목록을 반환하지 않았습니다. 수동으로 작성해 주세요.',
        '保存后使用 Windows DPAPI 加密存储。': '저장 후 Windows DPAPI를 사용하여 스토리지를 암호화합니다.',
        '保存退出选项与核心路径': '종료 옵션 및 핵심 경로 저장',
        '保存配置': '구성 저장',
        '信息': '정보',
        '修改模型': '모델 수정',
        '修改模型配置': '모델 구성 수정',
        '修改模式为': '모드를 다음으로 수정하세요.',
        '停止接入': '액세스 중지',
        '全部': '모두',
        '共 {0} 个模型配置 · 点击卡片切换，点击铅笔图标编辑参数': '총 {0}개의 모델 구성 · 전환하려면 카드를 클릭하고, 매개변수를 편집하려면 연필 아이콘을 클릭하세요.',
        '关于': '~에 대한',
        '关闭': '폐쇄',
        '关闭请求详情': '요청 세부정보 닫기',
        '其它接入': '기타 액세스',
        '其它接入会话需明确选择目标；Relay 不自动接管。': '다른 액세스 세션에는 명시적인 대상 선택이 필요합니다. 릴레이는 자동으로 인계받지 않습니다.',
        '准备读取会话索引。': '세션 인덱스 읽기를 준비합니다.',
        '切换成功：{0} → {1}。原配置已备份，写入结果已校验；下方列表已刷新。': '전환 성공: {0} → {1}. 원래 구성이 백업되었으며 쓰기 결과가 확인되었습니다. 아래 목록이 새로 '
                                                  '고쳐졌습니다.',
        '切换未完成：{0}，校验通过 {1} / {2}。原配置备份与操作记录已保留，不会自动重写会话。': '전환이 완료되지 않음: {0}, 확인이 {1}/{2} 통과되었습니다. 원래 구성 백업 '
                                                            '및 작업 기록은 유지되며 세션이 자동으로 다시 작성되지 않습니다.',
        '切换模型': '모델 전환',
        '删除后将无法自动恢复，需要重新填写 API KEY。': '삭제 후에는 자동 복원이 불가능하며 API KEY를 다시 입력해야 합니다.',
        '删除此模型配置': '이 모델 구성 삭제',
        '删除这条模型配置？': '이 모델 구성을 삭제하시겠습니까?',
        '刷新会话列表': '세션 목록 새로 고침',
        '刷新接入': '액세스 새로고침',
        '匿名使用统计': '익명의 사용 통계',
        '匿名使用统计已关闭': '익명의 사용 통계가 꺼졌습니다',
        '匿名使用统计已启用': '익명의 사용 통계가 활성화되었습니다',
        '匿名使用统计明确同意开关': '익명 사용 통계 명시적 동의 스위치',
        '单次最大输出。': '단일 최대 출력.',
        '发起请求后，可在此查看不含正文的安全摘要。': '요청이 이루어진 후 여기에서 텍스트가 없는 보안 요약을 볼 수 있습니다.',
        '取消': '취소',
        '可点击“读取”从供应商获取可用模型。': '"읽기"를 클릭하면 공급업체로부터 사용 가능한 모델을 얻을 수 있습니다.',
        '国家信息不由客户端采集；未来上传阶段仅允许服务端接入层瞬时推断。撤回后立即停止产生新的遥测数据。': '국가 정보는 고객이 수집하지 않습니다. 향후 업로드 단계에서는 서버 액세스 계층에서의 '
                                                            '즉각적인 추론만 허용됩니다. 탈퇴 후 즉시 새로운 원격 측정 데이터 생성을 '
                                                            '중지합니다.',
        '图片支持': '이미지 지원',
        '图片输入': '이미지 입력',
        '在“模型管理”页面添加至少一个模型，并点击模型卡片进行选择。': "'모델 관리' 페이지에서 하나 이상의 모델을 추가하고 모델 카드를 클릭하여 선택하세요.",
        '填写供应商公布的完整端点；程序按原样请求，不会改写路径。': '공급업체가 게시한 대로 전체 엔드포인트를 입력합니다. 프로그램은 있는 그대로 요청하고 경로를 다시 쓰지 않습니다.',
        '复制': '복사',
        '外观': '모습',
        '失败': '실패하다',
        '失败 {0}': '{0} 실패',
        '实时显示请求、连接与配置变更记录': '요청, 연결 및 구성 변경 기록의 실시간 표시',
        '客户端接入': '클라이언트 액세스',
        '将撤销本程序对 Codex 配置所做的修改，并停止本地服务。': 'Codex 구성에 대한 이 프로그램의 수정 사항이 취소되고 로컬 서비스가 중지됩니다.',
        '尚未接入': '아직 연결되지 않음',
        '尚未接入 Codex': '아직 Codex에 연결되지 않았습니다.',
        '尚未配置模型': '모델이 아직 구성되지 않았습니다.',
        '展开已读取的模型列表；也可直接手动输入模型名称': '읽기 모델 목록을 확장합니다. 모델명을 수동으로 직접 입력할 수도 있습니다.',
        '工具调用': '도구 호출',
        '已取消；没有备份或修改会话。': '취소; 백업 또는 수정 세션이 없습니다.',
        '已开启': '이미 켜져 있음',
        '已归档': '보관됨',
        '已按当前模型回填全部原参数；API KEY 已解密加载并默认遮蔽。': '모든 원래 매개변수는 현재 모델에 따라 다시 채워졌습니다. API KEY는 기본적으로 복호화, 로드 및 '
                                             '마스킹되었습니다.',
        '已接入': '이미 연결됨',
        '已接入 Codex，但端口无法启动：{0}': 'Codex에 연결되었지만 포트를 시작할 수 없습니다: {0}',
        '已接入但服务未运行': '연결되었지만 서비스가 실행되고 있지 않습니다.',
        '已知供应商会自动匹配；自定义中转请按实际选择。': '알려진 공급업체가 자동으로 연결됩니다. 맞춤 송금을 원하시면 실제 상황에 따라 선택하세요.',
        '已读取 {0} 个模型': '{0}개의 모델을 읽었습니다.',
        '已读取 {0} 个模型，请从列表选择': '{0}개의 모델을 읽었습니다. 목록에서 선택하세요.',
        '帮助改进 MicroGlow Relay': 'MicroGlow Relay 개선에 참여해 주세요.',
        '平均耗时 {0:.2f} 秒': '평균 소요 시간: {0:.2f}초',
        '应用': '애플리케이션',
        '归档会话仅供查看；请先在 Codex 中取消归档，再退出 Codex 后操作。': '보관된 세션은 보기 전용입니다. 먼저 Codex에서 아카이브를 취소한 후 Codex를 종료한 후 계속 '
                                                   '진행하세요.',
        '当前使用': '현재 사용 중',
        '当前模型已切换': '현재 모델이 변경되었습니다.',
        '当前模式': '현재 모드',
        '当前路由模型': '현재 라우팅 모델',
        '思考强度': '사고 강도',
        '思考模式': '사고 모델',
        '恢复 Codex 配置？': 'Codex 구성을 복원하시겠습니까?',
        '恢复配置': '구성 복원',
        '成功': '성공',
        '成功 {0} · 失败 {1}': '성공 {0} · 실패 {1}',
        '所属项目名称': '프로젝트 이름',
        '打开主界面': '기본 인터페이스 열기',
        '打开数据目录': '데이터 디렉터리 열기',
        '把本地路由服务接入 Codex，并在需要时完整恢复原始配置': '로컬 라우팅 서비스를 Codex에 연결하고 필요한 경우 원래 구성을 완전히 복원하십시오.',
        '接入 Codex': '코덱스에 접속하세요',
        '接入信息': '액세스 정보',
        '接入信息已刷新': '액세스 정보가 새로고침되었습니다.',
        '接入已失效': '액세스가 만료되었습니다',
        '接入时会先完整备份现有 Codex 配置，随时可以一键恢复。': '연결 시 기존 Codex 구성이 완전히 백업되며 언제든지 클릭 한 번으로 복원할 수 있습니다.',
        '接口协议': '인터페이스 프로토콜',
        '接口地址': '인터페이스 주소',
        '操作': '작동하다',
        '操作未完成；原配置与已有备份保留。请重新检查，不会回显底层数据。': '작업이 완료되지 않았습니다. 원래 구성과 기존 백업은 유지됩니다. 다시 확인하세요. 기본 데이터가 에코되지 '
                                            '않습니다.',
        '支持推理参数时开启，否则可能产生 400': '추론 매개변수가 지원되면 활성화됩니다. 그렇지 않으면 400이 생성될 수 있습니다.',
        '收起模型': '모델 축소',
        '数据传输': '데이터 전송',
        '数据位置': '데이터 위치',
        '文本': '텍스트',
        '开始日期': '시작 날짜',
        '无法读取': '읽을 수 없음',
        '日志': '통나무',
        '时间': '시간',
        '结束日期': '종료 날짜',
        '是否明确同意启用匿名使用统计？\n\n仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。不收集请求或响应正文、文件、代码、密钥、IP、原始错误和逐请求记录。': '익명 '
                                                                                                        '사용 '
                                                                                                        '통계를 '
                                                                                                        '활성화하는 '
                                                                                                        '데 '
                                                                                                        '명시적으로 '
                                                                                                        '동의하십니까?\n'
                                                                                                        '\n'
                                                                                                        '일일 '
                                                                                                        '호출 '
                                                                                                        '횟수, '
                                                                                                        '성공/오류, '
                                                                                                        '토큰, '
                                                                                                        '고정 '
                                                                                                        '지연 '
                                                                                                        '간격, '
                                                                                                        '표준 '
                                                                                                        '오류 '
                                                                                                        '범주 '
                                                                                                        '및 '
                                                                                                        '롤백 '
                                                                                                        '횟수만 '
                                                                                                        '누적됩니다. '
                                                                                                        '요청 '
                                                                                                        '또는 '
                                                                                                        '응답 '
                                                                                                        '본문, '
                                                                                                        '파일, '
                                                                                                        '코드, '
                                                                                                        '키, '
                                                                                                        'IP, '
                                                                                                        '원시 '
                                                                                                        '오류 '
                                                                                                        '및 '
                                                                                                        '요청별 '
                                                                                                        '로깅은 '
                                                                                                        '수집되지 '
                                                                                                        '않습니다.',
        '显示密钥': '키 표시',
        '智谱 AI': '지혜 스펙트럼 AI',
        '暂无日志 · 服务启动或配置变更后会显示在这里': '아직 로그가 없습니다. 서비스가 시작되거나 구성이 변경되면 여기에 표시됩니다.',
        '暂无记录': '아직 기록이 없습니다',
        '暂无请求记录': '아직 요청 기록이 없습니다',
        '最近活动': '최근 활동',
        '服务已停止': '서비스가 중지되었습니다',
        '服务运行中': '서비스가 실행 중입니다.',
        '未命名会话': '이름 없는 세션',
        '未开启': '켜지지 않음',
        '未接入': '연결되지 않음',
        '未检测到 ChatGPT 订阅登录；没有备份或修改会话。': 'ChatGPT 구독 로그인이 감지되지 않았습니다. 백업되거나 수정된 \u200b\u200b세션이 없습니다.',
        '未运行': '실행되지 않음',
        '本地地址': '현지 주소',
        '本地接口只监听 127.0.0.1，并要求随机访问令牌；历史 Backup 文件保存在 Codex 配置目录，恢复凭据保存在数据目录的 microglow-relay-codex-receipt.json。': '로컬 '
                                                                                                                   '인터페이스는 '
                                                                                                                   '127.0.0.1에서만 '
                                                                                                                   '수신 '
                                                                                                                   '대기하며 '
                                                                                                                   '임의 '
                                                                                                                   '액세스 '
                                                                                                                   '토큰이 '
                                                                                                                   '필요합니다. '
                                                                                                                   '기록 '
                                                                                                                   '백업 '
                                                                                                                   '파일은 '
                                                                                                                   'Codex '
                                                                                                                   '구성 '
                                                                                                                   '디렉터리에 '
                                                                                                                   '저장되고, '
                                                                                                                   '복구 '
                                                                                                                   '자격 '
                                                                                                                   '증명은 '
                                                                                                                   '데이터 '
                                                                                                                   '디렉터리의 '
                                                                                                                   'microglow-relay-codex-receipt.json에 '
                                                                                                                   '저장됩니다.',
        '本地服务': '지역 서비스',
        '本地服务已停止': '지역 서비스가 중지되었습니다',
        '本地模型的 API KEY 使用 Windows DPAPI 加密，仅当前账户可读取。': '로컬 모델의 API KEY는 Windows DPAPI를 사용하여 암호화되며 현재 계정에서만 '
                                                       '읽을 수 있습니다.',
        '本地端口、外观与数据位置': '로컬 포트, 모양 및 데이터 위치',
        '本地路由服务正在运行，Codex 的新请求会通过当前模型进行路由。': '로컬 라우팅 서비스가 실행 중이며 Codex에 대한 새로운 요청이 현재 모델을 통해 라우팅됩니다.',
        '本地路由让 Codex 通过本机访问你自己的模型供应商；请求正文不会被写入磁盘。': '로컬 라우팅을 통해 Codex는 기본적으로 자체 모델 제공자에 액세스할 수 있습니다. 요청 본문은 '
                                                    '디스크에 기록되지 않습니다.',
        '检测到接入后的外部修改': '접근 후 외부 수정이 감지됨',
        '概览': '개요',
        '模型': '모델',
        '模型名称': '모델명',
        '模型已删除': '모델이 삭제되었습니다.',
        '模型管理': '모델 관리',
        '模型配置保存在 microglow-relay-settings.json，用量日志保存最近 30 天且不记录正文。': '모델 구성은 microglow-relay-settings.json에 '
                                                                      '저장되며, 최근 30일간의 사용 로그는 텍스트 기록 없이 '
                                                                      '저장됩니다.',
        '模型配置已保存': '모델 구성이 저장되었습니다.',
        '正在只读加载本机会话索引…（无需退出 Codex）': '기본 세션 인덱스를 읽기 전용으로 로드하는 중... (Codex를 종료할 필요 없음)',
        '正在备份、切换并校验这一条会话…': '이 세션을 백업, 전환, 확인하는 중...',
        '正在核对：{0}…': '확인 중: {0}…',
        '正在测试连接…': '연결 테스트 중…',
        '正在读取供应商模型列表…': '공급업체 모델 목록을 읽는 중...',
        '测试连接': '연결 테스트',
        '添加、修改供应商模型配置，点击卡片选择当前路由模型': '공급업체 모델 구성을 추가 및 수정합니다. 카드를 클릭하여 현재 라우팅 모델을 선택하세요.',
        '添加模型': '모델 추가',
        '清空': '분명한',
        '点击“添加模型”填写供应商、API KEY 与模型名称，保存后点击卡片即可切换路由。': '"모델 추가"를 클릭하여 공급업체, API KEY 및 모델 이름을 입력하세요. 저장 후 카드를 '
                                                      '클릭하면 경로가 전환됩니다.',
        '点击本页的“接入 Codex”，程序会先完整备份现有 Codex 配置。': '이 페이지에서 "Codex에 연결"을 클릭하면 프로그램이 먼저 기존 Codex 구성을 완전히 백업합니다.',
        '点击记录查看详情': '세부정보를 보려면 기록을 클릭하세요.',
        '状态': '상태',
        '界面语言': '인터페이스 언어',
        '白色': '하얀색',
        '监听端口': '청취 포트',
        '硅基流动': '실리콘 기반 흐름',
        '确定': '확신하는',
        '确定切换这一条会话？': '이 대화를 전환하시겠습니까?',
        '空闲': '게으른',
        '端口修改会在下次启动本地服务时生效；已接入 Codex 时需要重新接入以刷新地址。': '포트 수정은 다음에 로컬 서비스가 시작될 때 적용됩니다. Codex에 연결되면 주소를 새로 '
                                                     '고치려면 다시 연결해야 합니다.',
        '端口已保存，将在下次启动服务时生效': '포트가 저장되었으며 다음에 서비스가 시작될 때 적용됩니다.',
        '管理': '관리하다',
        '耗时': '시간이 많이 걸리는',
        '能力与协议': '기능 및 프로토콜',
        '能力可多选，亮色为已开启。仅选择上游支持的能力；不支持思考参数时开启可能产生 400。': '여러 능력을 선택할 수 있으며 밝은 색상은 해당 능력이 활성화되었음을 의미합니다. 업스트림에서 '
                                                       '지원되는 기능만 선택하세요. 생각 매개변수가 지원되지 않을 때 켜면 400이 생성될 수 '
                                                       '있습니다.',
        '自动寻找 Codex 桌面端核心（可手动指定 codex.exe）': 'Codex 데스크탑 코어 자동 찾기(codex.exe는 수동으로 지정할 수 있음)',
        '自动滚动': '자동 스크롤',
        '自定义 / 中转服务': '맞춤/운송 서비스',
        '自定义中转时填写，例如：我的中转站': '환승을 맞춤 설정할 때 입력하세요. 예: 내 환승역',
        '警告': '경고하다',
        '让同一段 Codex 会话在官方订阅与 Relay 模型之间继续使用': '공식 구독과 Relay 모델 간에 동일한 Codex 세션을 계속 사용하도록 허용',
        '设置': '설정',
        '访问令牌': '액세스 토큰',
        '识别到历史路由模型标识，归类为其它接入；不等于 Codex 或当前 Relay。': '과거 라우팅 모델 식별자는 기타 액세스로 식별 및 분류됩니다. Codex 또는 현재 Relay와 '
                                                    '동일하지 않습니다.',
        '请先保存至少一个模型配置。': '먼저 하나 이상의 모델 구성을 저장하십시오.',
        '请先明确选择 Codex 或 Relay。': '먼저 Codex 또는 Relay를 명시적으로 선택하십시오.',
        '请先添加一个模型': '먼저 모델을 추가해 주세요.',
        '请在“模型管理”页面添加一个供应商模型。': '모델 관리 페이지에서 공급업체 모델을 추가하세요.',
        '请求详情': '요청 세부정보',
        '读取': '읽다',
        '读取失败：': '읽기 실패:',
        '读取成功：当前索引中没有符合条件的会话（可切换「已归档」查看）。': '성공적으로 읽었습니다: 현재 색인의 기준을 충족하는 회의가 없습니다("보관됨"으로 전환하여 볼 수 있음).',
        '读取成功：本页 {0} 条会话。': '성공적으로 읽었습니다. 이 페이지에 대한 세션 {0}개입니다.',
        '赛博朋克': '사이버펑크',
        '路由信息': '라우팅 정보',
        '路由标识': '경로 ID',
        '输入 Token': '토큰 입력',
        '输入与输出合计': '총 입출력',
        '输出 Token': '출력 토큰',
        '运行中': '달리기',
        '还没有模型配置': '아직 모델 구성이 없습니다.',
        '进入本页时读取本机会话索引。': '이 페이지에 들어갈 때 로컬 세션 색인을 읽으십시오.',
        '连接信息': '연결정보',
        '退出': '그만두다',
        '退出时，将登录方式设为 ChatGPT 订阅登录（不修改会话或默认模型）': '종료 시 로그인 방법을 ChatGPT 구독 로그인으로 설정하세요. (세션이나 기본 모델을 수정하지 마세요)',
        '退出选项 · 仅登录设置 · 默认关闭': '종료 옵션 · 로그인 전용 설정 · 기본적으로 꺼짐',
        '选择': '선택하다',
        '选择 Codex 桌面端核心': 'Codex 데스크탑 코어 선택',
        '选择核心': '코어 선택',
        '选项未能保存，请检查本地存储。': '옵션을 저장하지 못했습니다. 로컬 저장소를 확인하세요.',
        '配置已保存 · {0}': '구성이 저장되었습니다 · {0}',
        '重启 Codex，新建任务后选择“{0}”。': 'Codex를 다시 시작한 뒤 새 작업에서 “{0}”를 선택하세요.',
        '重新接入': '다시 연결하다',
        '金碧辉煌': '화려한',
        '错误': '실수',
        '隐私保护：不保存 Prompt、Response 或原始请求正文。': '개인정보 보호: 프롬프트, 응답 또는 원본 요청 본문은 저장되지 않습니다.',
        '需要还原时点击“恢复配置”，本程序写入的字段会被撤销。': '복원해야 할 경우 "구성 복원"을 클릭하면 이 프로그램에서 작성한 필드가 취소됩니다.',
        '高': '높은',
        '黑色': '검은색',
        '默认关闭。仅在你主动同意后累计 UTC 每日计数；不记录 Prompt、Response、正文、文件、代码、密钥、IP 或原始错误。': '기본적으로 꺼져 있습니다. 귀하의 적극적인 동의가 '
                                                                              '있는 경우에만 UTC 일일 계산을 누적합니다. '
                                                                              '프롬프트, 응답, 본문, 파일, 코드, 키, IP '
                                                                              '또는 원래 오류는 기록되지 않습니다.',
        '（未设置）': '(설정되지 않음)',
        '，当前使用': ', 현재 사용 중',
        '，点击切换': ', 전환하려면 클릭하세요.',
        '雾蓝科技': '미스트블루 테크',
        '石墨青金': '그래파이트 틸 골드',
        '微光': '마이크로그로우',
        '夜幕': '나이트폴',
        '金辉': '골든글로우',
        '月白': '문화이트',
        '星港': '스타하버'},
 'th': {
        '检测到更高优先级的 Claude 配置：{0} · 可能覆盖 Relay 接入，未改动': 'พบการตั้งค่า Claude ที่มีลำดับความสำคัญสูงกว่า: {0} · อาจแทนที่การเชื่อมต่อ Relay (ไม่แก้ไข)','\n目标模型：{0}': 'โมเดลเป้าหมาย: {0}',
        '\n该会话使用历史路由标识，按其它接入处理。': 'เซสชันนี้ใช้การระบุเส้นทางในอดีตและถือเป็นการเข้าถึงอื่นๆ',
        '\n该会话由其它工具接入。': 'เซสชันนี้เข้าถึงได้โดยเครื่องมืออื่น',
        'AI 连接、路由状态与最近请求总览': 'ภาพรวมของการเชื่อมต่อ AI สถานะเส้นทาง และคำขอล่าสุด',
        'Codex · ChatGPT 订阅': 'Codex · ChatGPT สมัครสมาชิก',
        'Codex 已不再使用本路由器': 'Codex ไม่ใช้เราเตอร์นี้อีกต่อไป',
        'Codex 已不再指向本路由器': 'Codex ไม่ชี้ไปที่เราเตอร์นี้อีกต่อไป',
        'Codex 已接入': 'เชื่อมต่อ Codex แล้ว',
        'Codex 已接入 · 已备份 {0}': 'เชื่อมต่อ Codex แล้ว · สำรองข้อมูลแล้ว {0}',
        'Codex 已重新指向本路由器': 'Codex ถูกเปลี่ยนเส้นทางไปยังเราเตอร์นี้',
        'Codex 已重新接入 · 已备份 {0}': 'เชื่อมต่อ Codex ใหม่แล้ว · สำรองข้อมูลแล้ว {0}',
        'Codex 当前指向': 'ปัจจุบัน Codex ชี้ไปที่',
        'Codex 接入': 'การเข้าถึงโคเด็กซ์',
        'Codex 接入已失效：配置被其它程序改写，请到“Codex 接入”页重新接入': 'การเข้าถึง Codex หมดอายุแล้ว: '
                                                   'การกำหนดค่าถูกเขียนทับโดยโปรแกรมอื่น โปรดไปที่หน้า '
                                                   '"การเข้าถึง Codex" เพื่อเข้าถึงอีกครั้ง',
        'Codex 配置': 'การกำหนดค่าโคเด็กซ์',
        'Codex 配置仍然指向本地路由，请先点击“重新接入”或启动本地服务。': 'การกำหนดค่า Codex ยังคงชี้ไปที่เส้นทางท้องถิ่น กรุณาคลิก '
                                               '"เชื่อมต่อใหม่" หรือเริ่มบริการในพื้นที่ก่อน',
        'Codex 配置在接入后被其他程序改写过（例如切换模型通道），当前请求不会经过本程序。点击“重新接入”即可按现在的情况重新写入并备份。': 'การกำหนดค่า Codex '
                                                                               'ได้รับการเขียนใหม่โดยโปรแกรมอื่นหลังจากการเข้าถึง '
                                                                               '(เช่นการสลับช่องรูปแบบ) '
                                                                               'และคำขอปัจจุบันจะไม่ผ่านโปรแกรมนี้ '
                                                                               'คลิก "เชื่อมต่อใหม่" '
                                                                               'เพื่อเขียนใหม่และสำรองข้อมูลตามสถานการณ์ปัจจุบัน',
        'Codex 配置已恢复 · 原备份 {0}': 'คืนค่าการกำหนดค่า Codex · การสำรองข้อมูลดั้งเดิม {0}',
        'Codex 配置已被其它程序改写，接入已失效，请重新接入': 'การกำหนดค่า Codex ถูกเขียนทับโดยโปรแกรมอื่น และการเข้าถึงหมดอายุ '
                                        'กรุณาเข้าใหม่อีกครั้ง',
        'Ollama（本机）': 'โอลามา (พื้นเมือง)',
        'Relay 接入配置未就绪；没有备份或修改会话。': 'การกำหนดค่าการเข้าถึงรีเลย์ไม่พร้อม '
                                    'ไม่มีเซสชันการสำรองข้อมูลหรือการแก้ไข',
        'iOS 风格': 'สไตล์ไอโอเอส',
        '{0:.1f} 万': '{0:.1f} ล้าน',
        '{0:.2f} 亿': '{0:.2f} พันล้าน',
        '{0:.2f} 秒': '{0:.2f} วินาที',
        '{0} 启动失败': '{0} ไม่สามารถเริ่มต้นได้',
        '{0} 已启动': '{0} เปิดใช้งานแล้ว',
        '{0} 已在运行。': '{0} กำลังทำงานอยู่แล้ว',
        '{0} 的目标模式': 'รูปแบบเป้าหมายสำหรับ {0}',
        '上下文上限': 'หมวกบริบท',
        '上下文窗口大小。': 'ขนาดหน้าต่างบริบท',
        '上次退出：有对象未切换，原配置与操作记录已保留，请检查后手动处理。': 'ทางออกสุดท้าย: มีออบเจ็กต์ที่ยังไม่ได้สลับ '
                                             'และบันทึกการกำหนดค่าและการดำเนินการดั้งเดิมยังคงอยู่ '
                                             'โปรดตรวจสอบและจัดการด้วยตนเอง',
        '上游模型支持函数工具调用时开启': 'โมเดลอัปสตรีมรองรับการเปิดเมื่อมีการเรียกใช้เครื่องมือฟังก์ชัน',
        '上游模型支持图片输入时开启': 'เปิดใช้งานเมื่อโมเดลอัปสตรีมรองรับอินพุตรูปภาพ',
        '下一页': 'หน้าถัดไป',
        '中': 'กลาง',
        '主题 · {0}': 'หัวข้อ · {0}',
        '主题模式': 'โหมดธีม',
        '仅实际退出时生效，关闭到托盘不执行。保留所有会话的模型和 Provider、全局默认模型及其它工具的配置；未检测到订阅登录或存在外部改动时不执行。': 'จะมีผลเมื่อคุณออกจริงเท่านั้น '
                                                                                     'การปิดถาดไม่มีผล '
                                                                                     'รักษาการกำหนดค่าของโมเดลและผู้ให้บริการ '
                                                                                     'โมเดลเริ่มต้นส่วนกลาง '
                                                                                     'และเครื่องมืออื่น ๆ '
                                                                                     'สำหรับทุกเซสชัน '
                                                                                     'จะไม่ดำเนินการเมื่อตรวจไม่พบการเข้าสู่ระบบการสมัครสมาชิกหรือมีการเปลี่ยนแปลงภายนอก',
        '仅调整所选会话的模型接入配置，不读取或改写历史对话；其它工具的会话不会自动接管。': 'มีการปรับเฉพาะการกำหนดค่าการเข้าถึงแบบจำลองของเซสชันที่เลือก '
                                                    'การสนทนาในอดีตจะไม่ถูกอ่านหรือเขียนใหม่ '
                                                    'เซสชันของเครื่องมืออื่นๆ จะไม่ถูกยึดครองโดยอัตโนมัติ',
        '今日 Token 消耗': 'การใช้โทเค็นของวันนี้',
        '今日 Token：{0:,}': 'โทเค็นของวันนี้: {0:,}',
        '今日成功率': 'อัตราความสำเร็จของวันนี้',
        '今日暂无请求': 'วันนี้ไม่มีการร้องขอ',
        '今日请求': 'ขอวันนี้',
        '以下字段在接入后被其他程序改过：\n{0}\n\n仍然强制恢复为接入前的状态吗？（会先备份当前配置）': 'โปรแกรมอื่นได้เปลี่ยนแปลงฟิลด์ต่อไปนี้หลังจากการเข้าถึง:\n'
                                                              '{0}\n'
                                                              '\n'
                                                              'ยังถูกบังคับให้คืนสู่สถานะก่อนเข้าถึงหรือไม่? '
                                                              '(การกำหนดค่าปัจจุบันจะถูกสำรองข้อมูลก่อน)',
        '会话兼容': 'เซสชันเข้ากันได้',
        '会话兼容选项已保存': 'บันทึกตัวเลือกความเข้ากันได้ของเซสชันแล้ว',
        '会话切换执行结果': 'ผลการดำเนินการสลับเซสชัน',
        '会话列表': 'รายการสนทนา',
        '会话列表读取状态': 'สถานะการอ่านรายการเซสชัน',
        '会话名称': 'ชื่อเซสชัน',
        '会话配置操作正在完成，请稍后再退出。': 'การดำเนินการกำหนดค่าเซสชันเสร็จสมบูรณ์ โปรดออกในภายหลัง',
        '会话：{0}\n当前：{1}\n目标：{2}{3}{4}\n确认 Codex 已正常退出？确定后先备份原配置，再切换并校验；不修改历史正文。': 'เซสชัน: {0}\n'
                                                                                  'ปัจจุบัน: {1}\n'
                                                                                  'เป้าหมาย: {2}{3}{4}\n'
                                                                                  'ยืนยันว่า Codex '
                                                                                  'ออกตามปกติ? '
                                                                                  'หลังจากการยืนยัน '
                                                                                  'ให้สำรองข้อมูลการกำหนดค่าดั้งเดิมก่อน '
                                                                                  'จากนั้นจึงสลับและตรวจสอบ '
                                                                                  'ห้ามแก้ไขข้อความทางประวัติศาสตร์',
        '传输中': 'กำลังส่งสัญญาณ',
        '低': 'ต่ำ',
        '使用步骤': 'ขั้นตอนการใช้งาน',
        '供应商': 'ผู้จัดหา',
        '供应商名称': 'ชื่อซัพพลายเออร์',
        '供应商未返回模型列表，请手动填写。': 'ซัพพลายเออร์ไม่ได้คืนรายการรุ่นสินค้า โปรดกรอกด้วยตนเอง',
        '保存后使用 Windows DPAPI 加密存储。': 'ใช้ Windows DPAPI เพื่อเข้ารหัสที่เก็บข้อมูลหลังจากบันทึก',
        '保存退出选项与核心路径': 'บันทึกตัวเลือกทางออกและเส้นทางหลัก',
        '保存配置': 'บันทึกการกำหนดค่า',
        '信息': 'ข้อมูล',
        '修改模型': 'ปรับเปลี่ยนโมเดล',
        '修改模型配置': 'แก้ไขการกำหนดค่าโมเดล',
        '修改模式为': 'ปรับเปลี่ยนโหมดเป็น',
        '停止接入': 'หยุดการเข้าถึง',
        '全部': 'ทั้งหมด',
        '共 {0} 个模型配置 · 点击卡片切换，点击铅笔图标编辑参数': 'การกำหนดค่าโมเดลทั้งหมด {0} รายการ · คลิกการ์ดเพื่อสลับ '
                                           'คลิกไอคอนดินสอเพื่อแก้ไขพารามิเตอร์',
        '关于': 'เกี่ยวกับ',
        '关闭': 'ปิด',
        '关闭请求详情': 'ปิดรายละเอียดคำขอ',
        '其它接入': 'การเข้าถึงอื่น ๆ',
        '其它接入会话需明确选择目标；Relay 不自动接管。': 'เซสชันการเข้าถึงอื่นๆ จำเป็นต้องมีการเลือกเป้าหมายที่ชัดเจน '
                                      'รีเลย์ไม่เข้าควบคุมโดยอัตโนมัติ',
        '准备读取会话索引。': 'เตรียมอ่านดัชนีเซสชั่น',
        '切换成功：{0} → {1}。原配置已备份，写入结果已校验；下方列表已刷新。': 'การสลับสำเร็จ: {0} → {1} '
                                                  'การกำหนดค่าดั้งเดิมได้รับการสำรองข้อมูลและผลการเขียนได้รับการตรวจสอบแล้ว '
                                                  'รายการด้านล่างได้รับการรีเฟรชแล้ว',
        '切换未完成：{0}，校验通过 {1} / {2}。原配置备份与操作记录已保留，不会自动重写会话。': 'การสลับไม่เสร็จสมบูรณ์: {0} การตรวจสอบผ่านแล้ว '
                                                            '{1}/{2} '
                                                            'บันทึกการสำรองข้อมูลการกำหนดค่าและการดำเนินการเดิมยังคงอยู่ '
                                                            'และเซสชันจะไม่ถูกเขียนใหม่โดยอัตโนมัติ',
        '切换模型': 'สลับรุ่น',
        '删除后将无法自动恢复，需要重新填写 API KEY。': 'หลังจากลบแล้ว จะไม่สามารถกู้คืนได้โดยอัตโนมัติ และจะต้องกรอกคีย์ API '
                                      'อีกครั้ง',
        '删除此模型配置': 'ลบการกำหนดค่าแบบจำลองนี้',
        '删除这条模型配置？': 'ลบการกำหนดค่าโมเดลนี้ใช่ไหม',
        '刷新会话列表': 'รีเฟรชรายการเซสชัน',
        '刷新接入': 'รีเฟรชการเข้าถึง',
        '匿名使用统计': 'สถิติการใช้งานที่ไม่เปิดเผยตัวตน',
        '匿名使用统计已关闭': 'สถิติการใช้งานแบบไม่เปิดเผยตัวตนถูกปิด',
        '匿名使用统计已启用': 'เปิดใช้งานสถิติการใช้งานแบบไม่ระบุชื่อแล้ว',
        '匿名使用统计明确同意开关': 'สถิติการใช้งานแบบไม่เปิดเผยตัวตน สลับการยินยอมอย่างชัดแจ้ง',
        '单次最大输出。': 'เอาต์พุตสูงสุดเดี่ยว',
        '发起请求后，可在此查看不含正文的安全摘要。': 'หลังจากส่งคำขอแล้ว คุณจะดูสรุปด้านความปลอดภัยที่ไม่มีข้อความได้ที่นี่',
        '取消': 'ยกเลิก',
        '可点击“读取”从供应商获取可用模型。': 'คุณสามารถคลิก "อ่าน" เพื่อรับรุ่นที่มีจำหน่ายจากซัพพลายเออร์',
        '国家信息不由客户端采集；未来上传阶段仅允许服务端接入层瞬时推断。撤回后立即停止产生新的遥测数据。': 'ลูกค้าไม่ได้รวบรวมข้อมูลระดับชาติ '
                                                            'อนุญาตให้อนุมานทันทีที่เลเยอร์การเข้าถึงเซิร์ฟเวอร์ในขั้นตอนการอัปโหลดในอนาคต '
                                                            'หยุดการสร้างข้อมูลการวัดและส่งข้อมูลทางไกลใหม่ทันทีหลังจากถอนออก',
        '图片支持': 'การสนับสนุนรูปภาพ',
        '图片输入': 'อินพุตรูปภาพ',
        '在“模型管理”页面添加至少一个模型，并点击模型卡片进行选择。': 'เพิ่มอย่างน้อยหนึ่งโมเดลในหน้า "การจัดการโมเดล" '
                                          'และคลิกการ์ดโมเดลเพื่อเลือก',
        '填写供应商公布的完整端点；程序按原样请求，不会改写路径。': 'กรอกจุดสิ้นสุดที่สมบูรณ์ตามที่เผยแพร่โดยผู้จัดจำหน่าย '
                                        'โปรแกรมร้องขอตามที่เป็นอยู่และไม่เขียนเส้นทางใหม่',
        '复制': 'สำเนา',
        '外观': 'รูปร่าง',
        '失败': 'ล้มเหลว',
        '失败 {0}': 'ล้มเหลว {0}',
        '实时显示请求、连接与配置变更记录': 'การแสดงบันทึกการเปลี่ยนแปลงคำขอ การเชื่อมต่อ และการกำหนดค่าแบบเรียลไทม์',
        '客户端接入': 'การเข้าถึงลูกค้า',
        '将撤销本程序对 Codex 配置所做的修改，并停止本地服务。': 'การแก้ไขที่ทำโดยโปรแกรมนี้ในการกำหนดค่า Codex '
                                          'จะถูกยกเลิกและบริการภายในเครื่องจะหยุดทำงาน',
        '尚未接入': 'ยังไม่ได้เชื่อมต่อ',
        '尚未接入 Codex': 'ยังไม่ได้เชื่อมต่อกับ Codex',
        '尚未配置模型': 'ยังไม่ได้กำหนดค่าโมเดล',
        '展开已读取的模型列表；也可直接手动输入模型名称': 'ขยายรายการโมเดลการอ่าน คุณสามารถป้อนชื่อรุ่นได้โดยตรงด้วยตนเอง',
        '工具调用': 'การเรียกเครื่องมือ',
        '已取消；没有备份或修改会话。': 'ยกเลิก; ไม่มีเซสชันการสำรองข้อมูลหรือการแก้ไข',
        '已开启': 'เปิดอยู่แล้ว',
        '已归档': 'เก็บถาวรแล้ว',
        '已按当前模型回填全部原参数；API KEY 已解密加载并默认遮蔽。': 'พารามิเตอร์ดั้งเดิมทั้งหมดได้รับการทดแทนตามรุ่นปัจจุบัน API '
                                             'KEY ได้รับการถอดรหัส โหลด และปิดบังตามค่าเริ่มต้น',
        '已接入': 'เชื่อมต่อแล้ว',
        '已接入 Codex，但端口无法启动：{0}': 'เชื่อมต่อกับ Codex แล้ว แต่ไม่สามารถเริ่มพอร์ตได้: {0}',
        '已接入但服务未运行': 'เชื่อมต่อแล้ว แต่บริการไม่ทำงาน',
        '已知供应商会自动匹配；自定义中转请按实际选择。': 'ซัพพลายเออร์ที่รู้จักจะถูกจับคู่โดยอัตโนมัติ สำหรับการโอนแบบกำหนดเอง '
                                   'กรุณาเลือกตามเงื่อนไขจริง',
        '已读取 {0} 个模型': '{0} โมเดลอ่านแล้ว',
        '已读取 {0} 个模型，请从列表选择': '{0} รุ่นที่อ่านแล้ว โปรดเลือกจากรายการ',
        '帮助改进 MicroGlow Relay': 'ช่วยปรับปรุงไมโครโกลว์รีเลย์',
        '平均耗时 {0:.2f} 秒': 'เวลาเฉลี่ยที่ใช้ไป {0:.2f} วินาที',
        '应用': 'แอปพลิเคชัน',
        '归档会话仅供查看；请先在 Codex 中取消归档，再退出 Codex 后操作。': 'เซสชันที่เก็บไว้มีไว้เพื่อการดูเท่านั้น '
                                                   'โปรดยกเลิกไฟล์เก็บถาวรใน Codex ก่อน จากนั้นออกจาก Codex '
                                                   'ก่อนดำเนินการต่อ',
        '当前使用': 'ที่ใช้งานอยู่ในปัจจุบัน',
        '当前模型已切换': 'ได้มีการเปลี่ยนรูปแบบปัจจุบันแล้ว',
        '当前模式': 'โหมดปัจจุบัน',
        '当前路由模型': 'รูปแบบเส้นทางปัจจุบัน',
        '思考强度': 'ความเข้มของการคิด',
        '思考模式': 'โมเดลการคิด',
        '恢复 Codex 配置？': 'กู้คืนการกำหนดค่า Codex หรือไม่',
        '恢复配置': 'คืนค่าการกำหนดค่า',
        '成功': 'ความสำเร็จ',
        '成功 {0} · 失败 {1}': 'สำเร็จ {0} · ล้มเหลว {1}',
        '所属项目名称': 'ชื่อโครงการ',
        '打开主界面': 'เปิดอินเทอร์เฟซหลัก',
        '打开数据目录': 'เปิดไดเร็กทอรีข้อมูล',
        '把本地路由服务接入 Codex，并在需要时完整恢复原始配置': 'เชื่อมต่อบริการกำหนดเส้นทางในพื้นที่กับ Codex '
                                         'และกู้คืนการกำหนดค่าดั้งเดิมโดยสมบูรณ์หากจำเป็น',
        '接入 Codex': 'เข้าถึง Codex',
        '接入信息': 'เข้าถึงข้อมูล',
        '接入信息已刷新': 'ข้อมูลการเข้าถึงได้รับการรีเฟรชแล้ว',
        '接入已失效': 'การเข้าถึงหมดอายุแล้ว',
        '接入时会先完整备份现有 Codex 配置，随时可以一键恢复。': 'เมื่อเชื่อมต่อ การกำหนดค่า Codex '
                                          'ที่มีอยู่จะได้รับการสำรองข้อมูลอย่างสมบูรณ์และสามารถกู้คืนได้ตลอดเวลาด้วยการคลิกเพียงครั้งเดียว',
        '接口协议': 'โปรโตคอลอินเทอร์เฟซ',
        '接口地址': 'ที่อยู่อินเทอร์เฟซ',
        '操作': 'ดำเนินงาน',
        '操作未完成；原配置与已有备份保留。请重新检查，不会回显底层数据。': 'การดำเนินการยังไม่เสร็จสิ้น '
                                            'การกำหนดค่าดั้งเดิมและข้อมูลสำรองที่มีอยู่จะยังคงอยู่ '
                                            'โปรดตรวจสอบอีกครั้ง ข้อมูลพื้นฐานจะไม่ถูกสะท้อนกลับ',
        '支持推理参数时开启，否则可能产生 400': 'เปิดใช้งานเมื่อรองรับพารามิเตอร์การอนุมาน ไม่เช่นนั้นอาจสร้าง 400 รายการได้',
        '收起模型': 'ยุบโมเดล',
        '数据传输': 'การถ่ายโอนข้อมูล',
        '数据位置': 'ตำแหน่งข้อมูล',
        '文本': 'ข้อความ',
        '开始日期': 'วันที่เริ่มต้น',
        '无法读取': 'ไม่สามารถอ่านได้',
        '日志': 'บันทึก',
        '时间': 'เวลา',
        '结束日期': 'วันที่สิ้นสุด',
        '是否明确同意启用匿名使用统计？\n\n仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。不收集请求或响应正文、文件、代码、密钥、IP、原始错误和逐请求记录。': 'คุณตกลงอย่างชัดเจนที่จะเปิดใช้งานสถิติการใช้งานที่ไม่ระบุชื่อหรือไม่?\n'
                                                                                                        '\n'
                                                                                                        'มีเพียงจำนวนการโทรรายวัน '
                                                                                                        'ความสำเร็จ/ข้อผิดพลาด '
                                                                                                        'โทเค็น '
                                                                                                        'ช่วงเวลาล่าช้าคงที่ '
                                                                                                        'หมวดหมู่ข้อผิดพลาดมาตรฐาน '
                                                                                                        'และการย้อนกลับเท่านั้นที่จะถูกสะสม '
                                                                                                        'เนื้อหาคำขอหรือการตอบกลับ '
                                                                                                        'ไฟล์ '
                                                                                                        'รหัส '
                                                                                                        'คีย์ '
                                                                                                        'IP '
                                                                                                        'ข้อผิดพลาดดิบ '
                                                                                                        'และการบันทึกต่อคำขอจะไม่ถูกรวบรวม',
        '显示密钥': 'แสดงคีย์',
        '智谱 AI': 'AI สเปกตรัมแห่งปัญญา',
        '暂无日志 · 服务启动或配置变更后会显示在这里': 'ยังไม่มีบันทึก · '
                                   'มันจะแสดงที่นี่หลังจากเริ่มบริการหรือมีการเปลี่ยนแปลงการกำหนดค่า',
        '暂无记录': 'ยังไม่มีบันทึก',
        '暂无请求记录': 'ยังไม่มีบันทึกคำขอ',
        '最近活动': 'กิจกรรมล่าสุด',
        '服务已停止': 'หยุดให้บริการแล้ว',
        '服务运行中': 'บริการกำลังทำงานอยู่',
        '未命名会话': 'เซสชันที่ไม่มีชื่อ',
        '未开启': 'ไม่ได้เปิด',
        '未接入': 'ไม่ได้เชื่อมต่อ',
        '未检测到 ChatGPT 订阅登录；没有备份或修改会话。': 'ไม่พบการเข้าสู่ระบบการสมัครสมาชิก ChatGPT; '
                                        'ไม่มีการสำรองข้อมูลหรือแก้ไขเซสชัน',
        '未运行': 'ไม่ทำงาน',
        '本地地址': 'ที่อยู่ในท้องถิ่น',
        '本地接口只监听 127.0.0.1，并要求随机访问令牌；历史 Backup 文件保存在 Codex 配置目录，恢复凭据保存在数据目录的 microglow-relay-codex-receipt.json。': 'อินเทอร์เฟซภายในเครื่องรับฟังเฉพาะ '
                                                                                                                   '127.0.0.1 '
                                                                                                                   'และต้องการโทเค็นการเข้าถึงแบบสุ่ม '
                                                                                                                   'ไฟล์สำรองข้อมูลในอดีตจะถูกบันทึกไว้ในไดเร็กทอรีการกำหนดค่า '
                                                                                                                   'Codex '
                                                                                                                   'และข้อมูลรับรองการกู้คืนจะถูกบันทึกใน '
                                                                                                                   'microglow-relay-codex-receipt.json '
                                                                                                                   'ในไดเร็กทอรีข้อมูล',
        '本地服务': 'บริการท้องถิ่น',
        '本地服务已停止': 'บริการท้องถิ่นหยุดแล้ว',
        '本地模型的 API KEY 使用 Windows DPAPI 加密，仅当前账户可读取。': 'API KEY ของโมเดลในเครื่องได้รับการเข้ารหัสโดยใช้ '
                                                       'Windows DPAPI '
                                                       'และบัญชีปัจจุบันเท่านั้นที่สามารถอ่านได้',
        '本地端口、外观与数据位置': 'พอร์ตภายในเครื่อง ลักษณะที่ปรากฏ และตำแหน่งข้อมูล',
        '本地路由服务正在运行，Codex 的新请求会通过当前模型进行路由。': 'บริการกำหนดเส้นทางท้องถิ่นกำลังทำงานอยู่ และคำขอใหม่สำหรับ '
                                             'Codex จะถูกส่งผ่านโมเดลปัจจุบัน',
        '本地路由让 Codex 通过本机访问你自己的模型供应商；请求正文不会被写入磁盘。': 'การกำหนดเส้นทางท้องถิ่นช่วยให้ Codex '
                                                    'เข้าถึงผู้ให้บริการโมเดลของคุณเองได้ '
                                                    'เนื้อความคำขอไม่ได้ถูกเขียนลงดิสก์',
        '检测到接入后的外部修改': 'ตรวจพบการแก้ไขภายนอกหลังจากการเข้าถึง',
        '概览': 'ภาพรวม',
        '模型': 'แบบอย่าง',
        '模型名称': 'ชื่อรุ่น',
        '模型已删除': 'ลบโมเดลแล้ว',
        '模型管理': 'การจัดการแบบจำลอง',
        '模型配置保存在 microglow-relay-settings.json，用量日志保存最近 30 天且不记录正文。': 'การกำหนดค่าโมเดลจะถูกบันทึกไว้ใน '
                                                                      'microglow-relay-settings.json '
                                                                      'และบันทึกการใช้งานจะถูกบันทึกไว้ในช่วง '
                                                                      '30 '
                                                                      'วันที่ผ่านมาโดยไม่ต้องบันทึกข้อความ',
        '模型配置已保存': 'บันทึกการกำหนดค่าโมเดลแล้ว',
        '正在只读加载本机会话索引…（无需退出 Codex）': 'กำลังโหลดดัชนีเซสชันดั้งเดิมแบบอ่านอย่างเดียว... (ไม่จำเป็นต้องออกจาก '
                                     'Codex)',
        '正在备份、切换并校验这一条会话…': 'กำลังสำรองข้อมูล สลับ และยืนยันเซสชันนี้...',
        '正在核对：{0}…': 'กำลังตรวจสอบ: {0}…',
        '正在测试连接…': 'กำลังทดสอบการเชื่อมต่อ...',
        '正在读取供应商模型列表…': 'กำลังอ่านรายชื่อรุ่นของซัพพลายเออร์...',
        '测试连接': 'ทดสอบการเชื่อมต่อ',
        '添加、修改供应商模型配置，点击卡片选择当前路由模型': 'เพิ่มและแก้ไขการกำหนดค่าโมเดลซัพพลายเออร์ '
                                     'คลิกการ์ดเพื่อเลือกโมเดลเส้นทางปัจจุบัน',
        '添加模型': 'เพิ่มรุ่น',
        '清空': 'ชัดเจน',
        '点击“添加模型”填写供应商、API KEY 与模型名称，保存后点击卡片即可切换路由。': 'คลิก "เพิ่มรุ่น" เพื่อกรอกซัพพลายเออร์, คีย์ API '
                                                      'และชื่อรุ่น หลังจากบันทึกแล้ว '
                                                      'ให้คลิกที่การ์ดเพื่อเปลี่ยนเส้นทาง',
        '点击本页的“接入 Codex”，程序会先完整备份现有 Codex 配置。': 'คลิก "เชื่อมต่อกับ Codex" ในหน้านี้ '
                                                'จากนั้นโปรแกรมจะสำรองข้อมูลการกำหนดค่า Codex '
                                                'ที่มีอยู่อย่างสมบูรณ์ก่อน',
        '点击记录查看详情': 'คลิกบันทึกเพื่อดูรายละเอียด',
        '状态': 'สถานะ',
        '界面语言': 'ภาษาอินเทอร์เฟซ',
        '白色': 'สีขาว',
        '监听端口': 'พอร์ตการฟัง',
        '硅基流动': 'การไหลแบบซิลิคอน',
        '确定': 'แน่นอน',
        '确定切换这一条会话？': 'คุณแน่ใจหรือไม่ว่าต้องการเปลี่ยนการสนทนานี้',
        '空闲': 'ไม่ได้ใช้งาน',
        '端口修改会在下次启动本地服务时生效；已接入 Codex 时需要重新接入以刷新地址。': 'การปรับเปลี่ยนพอร์ตจะมีผลในครั้งถัดไปที่เริ่มบริการท้องถิ่น '
                                                     'เมื่อเชื่อมต่อกับ Codex '
                                                     'คุณจะต้องเชื่อมต่อใหม่เพื่อรีเฟรชที่อยู่',
        '端口已保存，将在下次启动服务时生效': 'พอร์ตได้รับการบันทึกแล้ว และจะมีผลในครั้งถัดไปที่เริ่มบริการ',
        '管理': 'จัดการ',
        '耗时': 'ใช้เวลานาน',
        '能力与协议': 'ความสามารถและโปรโตคอล',
        '能力可多选，亮色为已开启。仅选择上游支持的能力；不支持思考参数时开启可能产生 400。': 'สามารถเลือกความสามารถได้หลายแบบ '
                                                       'และสีสดใสหมายความว่าเปิดใช้งานแล้ว '
                                                       'เลือกความสามารถที่อัพสตรีมรองรับเท่านั้น '
                                                       'การเปิดอาจสร้าง 400 เมื่อคิดว่าไม่รองรับพารามิเตอร์',
        '自动寻找 Codex 桌面端核心（可手动指定 codex.exe）': 'ค้นหาแกนเดสก์ท็อป Codex โดยอัตโนมัติ (สามารถระบุ codex.exe '
                                             'ได้ด้วยตนเอง)',
        '自动滚动': 'เลื่อนอัตโนมัติ',
        '自定义 / 中转服务': 'บริการแบบกำหนดเอง/การขนส่ง',
        '自定义中转时填写，例如：我的中转站': 'กรอกข้อมูลเมื่อปรับแต่งการถ่ายโอน เช่น สถานีถ่ายโอนของฉัน',
        '警告': 'เตือน',
        '让同一段 Codex 会话在官方订阅与 Relay 模型之间继续使用': 'ปล่อยให้เซสชัน Codex '
                                              'เดียวกันยังคงใช้ต่อไประหว่างการสมัครสมาชิกอย่างเป็นทางการและรุ่น '
                                              'Relay',
        '设置': 'ตั้งค่า',
        '访问令牌': 'โทเค็นการเข้าถึง',
        '识别到历史路由模型标识，归类为其它接入；不等于 Codex 或当前 Relay。': 'ตัวระบุโมเดลการกำหนดเส้นทางเชิงประวัติจะถูกระบุและจัดประเภทเป็นการเข้าถึงอื่น '
                                                    'ไม่เท่ากับ Codex หรือรีเลย์ปัจจุบัน',
        '请先保存至少一个模型配置。': 'โปรดบันทึกการกำหนดค่าโมเดลอย่างน้อยหนึ่งรายการก่อน',
        '请先明确选择 Codex 或 Relay。': 'โปรดเลือก Codex หรือ Relay อย่างชัดเจนก่อน',
        '请先添加一个模型': 'กรุณาเพิ่มรุ่นก่อน',
        '请在“模型管理”页面添加一个供应商模型。': 'โปรดเพิ่มโมเดลซัพพลายเออร์ในหน้าการจัดการโมเดล',
        '请求详情': 'ขอรายละเอียด',
        '读取': 'อ่าน',
        '读取失败：': 'อ่านล้มเหลว:',
        '读取成功：当前索引中没有符合条件的会话（可切换「已归档」查看）。': 'อ่านสำเร็จ: ไม่มีการประชุมที่ตรงตามเกณฑ์ในดัชนีปัจจุบัน '
                                            '(คุณสามารถสลับไปที่ "เก็บถาวร" เพื่อดูได้)',
        '读取成功：本页 {0} 条会话。': 'อ่านสำเร็จ: {0} เซสชันสำหรับหน้านี้',
        '赛博朋克': 'ไซเบอร์พังค์',
        '路由信息': 'ข้อมูลเส้นทาง',
        '路由标识': 'รหัสเส้นทาง',
        '输入 Token': 'ป้อนโทเค็น',
        '输入与输出合计': 'อินพุตและเอาต์พุตทั้งหมด',
        '输出 Token': 'โทเค็นเอาท์พุต',
        '运行中': 'วิ่ง',
        '还没有模型配置': 'ยังไม่มีการกำหนดค่าโมเดล',
        '进入本页时读取本机会话索引。': 'อ่านดัชนีเซสชันท้องถิ่นเมื่อเข้าสู่หน้านี้',
        '连接信息': 'ข้อมูลการเชื่อมต่อ',
        '退出': 'ล้มเลิก',
        '退出时，将登录方式设为 ChatGPT 订阅登录（不修改会话或默认模型）': 'เมื่อออก '
                                                'ให้ตั้งค่าวิธีการเข้าสู่ระบบเป็นการเข้าสู่ระบบการสมัครสมาชิก '
                                                'ChatGPT (ห้ามแก้ไขเซสชันหรือรูปแบบเริ่มต้น)',
        '退出选项 · 仅登录设置 · 默认关闭': 'ตัวเลือกการออก · การตั้งค่าเข้าสู่ระบบเท่านั้น · ปิดตามค่าเริ่มต้น',
        '选择': 'เลือก',
        '选择 Codex 桌面端核心': 'เลือก Codex Desktop Core',
        '选择核心': 'เลือกแกน',
        '选项未能保存，请检查本地存储。': 'ไม่สามารถบันทึกตัวเลือกได้ โปรดตรวจสอบที่จัดเก็บข้อมูลในเครื่อง',
        '配置已保存 · {0}': 'บันทึกการกำหนดค่าแล้ว · {0}',
        '重启 Codex，新建任务后选择“{0}”。': 'รีสตาร์ต Codex แล้วสร้างงานใหม่และเลือก “{0}”',
        '重新接入': 'เชื่อมต่อใหม่',
        '金碧辉煌': 'งดงาม',
        '错误': 'ความผิดพลาด',
        '隐私保护：不保存 Prompt、Response 或原始请求正文。': 'การคุ้มครองความเป็นส่วนตัว: เนื้อหาคำร้องขอ การตอบสนอง '
                                             'หรือคำขอดั้งเดิมจะไม่ได้รับการบันทึก',
        '需要还原时点击“恢复配置”，本程序写入的字段会被撤销。': 'เมื่อคุณต้องการคืนค่า ให้คลิก "คืนค่าการกำหนดค่า" '
                                       'และฟิลด์ที่โปรแกรมนี้เขียนจะถูกเพิกถอน',
        '高': 'สูง',
        '黑色': 'สีดำ',
        '默认关闭。仅在你主动同意后累计 UTC 每日计数；不记录 Prompt、Response、正文、文件、代码、密钥、IP 或原始错误。': 'ปิดโดยค่าเริ่มต้น สะสมจำนวน '
                                                                              'UTC '
                                                                              'รายวันเฉพาะเมื่อได้รับความยินยอมจากคุณเท่านั้น '
                                                                              'ไม่มีการบันทึกพรอมต์ '
                                                                              'การตอบกลับ เนื้อหา ไฟล์ รหัส '
                                                                              'คีย์ IP '
                                                                              'หรือข้อผิดพลาดดั้งเดิม',
        '（未设置）': '(ไม่ได้ตั้งค่า)',
        '，当前使用': ', กำลังใช้งานอยู่',
        '，点击切换': 'คลิกเพื่อเปลี่ยน',
        '雾蓝科技': 'มิสต์บลูเทค',
        '石墨青金': 'กราไฟต์ทีลโกลด์',
        '微光': 'ไมโครโกลว์',
        '夜幕': 'ไนต์ฟอล',
        '金辉': 'โกลเด้นโกลว์',
        '月白': 'มูนไวต์',
        '星港': 'สตาร์ฮาร์เบอร์'},
 'zh-TW': {
        '检测到更高优先级的 Claude 配置：{0} · 可能覆盖 Relay 接入，未改动': '偵測到優先級更高的 Claude 設定：{0} · 可能覆蓋 Relay 接入，未改動','\n目标模型：{0}': '目標模型：{0}',
           '\n该会话使用历史路由标识，按其它接入处理。': '此會話使用歷史路由標識，按其它接入處理。',
           '\n该会话由其它工具接入。': '該會話由其它工具接入。',
           'AI 连接、路由状态与最近请求总览': 'AI 連線、路由狀態與最近請求總覽',
           'Codex · ChatGPT 订阅': 'Codex · ChatGPT 訂閱',
           'Codex 已不再使用本路由器': 'Codex 已不再使用本路由器',
           'Codex 已不再指向本路由器': 'Codex 已不再指向本路由器',
           'Codex 已接入': 'Codex 已接入',
           'Codex 已接入 · 已备份 {0}': 'Codex 已存取 · 已備份 {0}',
           'Codex 已重新指向本路由器': 'Codex 已重新指向本路由器',
           'Codex 已重新接入 · 已备份 {0}': 'Codex 已重新存取 · 已備份 {0}',
           'Codex 当前指向': 'Codex 目前指向',
           'Codex 接入': 'Codex 接入',
           'Codex 接入已失效：配置被其它程序改写，请到“Codex 接入”页重新接入': 'Codex 接入已失效：設定被其它程式改寫，請到「Codex 接入」頁重新接入',
           'Codex 配置': 'Codex 配置',
           'Codex 配置仍然指向本地路由，请先点击“重新接入”或启动本地服务。': 'Codex 設定仍指向本機路由，請先點選「重新接取」或啟動本機服務。',
           'Codex 配置在接入后被其他程序改写过（例如切换模型通道），当前请求不会经过本程序。点击“重新接入”即可按现在的情况重新写入并备份。': 'Codex '
                                                                                  '設定在存取後被其他程式改寫過（例如切換模型通道），目前請求不會經過本程式。點擊「重新接入」即可按目前的情況重新寫入並備份。',
           'Codex 配置已恢复 · 原备份 {0}': 'Codex 設定已還原 · 原始備份 {0}',
           'Codex 配置已被其它程序改写，接入已失效，请重新接入': 'Codex 配置已被其它程式改寫，接入已失效，請重新接入',
           'Ollama（本机）': 'Ollama（本機）',
           'Relay 接入配置未就绪；没有备份或修改会话。': 'Relay 接入配置未就緒；沒有備份或修改會話。',
           'iOS 风格': 'iOS 風格',
           '{0:.1f} 万': '{0:.1f} 萬',
           '{0:.2f} 亿': '{0:.2f} 億',
           '{0:.2f} 秒': '{0:.2f} 秒',
           '{0} 启动失败': '{0} 啟動失敗',
           '{0} 已启动': '{0} 已啟動',
           '{0} 已在运行。': '{0} 已在運作中。',
           '{0} 的目标模式': '{0} 的目標模式',
           '上下文上限': '上下文上限',
           '上下文窗口大小。': '上下文視窗大小。',
           '上次退出：有对象未切换，原配置与操作记录已保留，请检查后手动处理。': '上次退出：有物件未切換，原配置與操作記錄已保留，請檢查後手動處理。',
           '上游模型支持函数工具调用时开启': '上游模型支援函數工具呼叫時開啟',
           '上游模型支持图片输入时开启': '上游模型支援圖片輸入時開啟',
           '下一页': '下一頁',
           '中': '中',
           '主题 · {0}': '主題 · {0}',
           '主题模式': '主題模式',
           '仅实际退出时生效，关闭到托盘不执行。保留所有会话的模型和 Provider、全局默认模型及其它工具的配置；未检测到订阅登录或存在外部改动时不执行。': '僅實際退出時生效，關閉至托盤不執行。保留所有會話的模型和 '
                                                                                        'Provider、全域預設模型及其它工具的配置；未偵測到訂閱登入或存在外部變更時不執行。',
           '仅调整所选会话的模型接入配置，不读取或改写历史对话；其它工具的会话不会自动接管。': '僅調整所選會話的模型存取配置，不讀取或改寫歷史對話；其它工具的會話不會自動接管。',
           '今日 Token 消耗': '今日 Token 消耗',
           '今日 Token：{0:,}': '今日 Token：{0:,}',
           '今日成功率': '今日成功率',
           '今日暂无请求': '今日暫無請求',
           '今日请求': '今日請求',
           '以下字段在接入后被其他程序改过：\n{0}\n\n仍然强制恢复为接入前的状态吗？（会先备份当前配置）': '以下欄位在接入後被其他程式改過：\n'
                                                                 '{0}\n'
                                                                 '\n'
                                                                 '仍然強制恢復為存取前的狀態嗎？ （會先備份當前配置）',
           '会话兼容': '會話相容',
           '会话兼容选项已保存': '會話相容選項已儲存',
           '会话切换执行结果': '會話切換執行結果',
           '会话列表': '會話列表',
           '会话列表读取状态': '會話清單讀取狀態',
           '会话名称': '會話名稱',
           '会话配置操作正在完成，请稍后再退出。': '會話配置操作正在完成，請稍後再退出。',
           '会话：{0}\n当前：{1}\n目标：{2}{3}{4}\n确认 Codex 已正常退出？确定后先备份原配置，再切换并校验；不修改历史正文。': '會話：{0}\n'
                                                                                     '目前：{1}\n'
                                                                                     '目標：{2}{3}{4}\n'
                                                                                     '確認 Codex '
                                                                                     '已正常退出？確定後先備份原配置，再切換併校驗；不修改歷史內文。',
           '传输中': '傳輸中',
           '低': '低',
           '使用步骤': '使用步驟',
           '供应商': '供應商',
           '供应商名称': '供應商名稱',
           '供应商未返回模型列表，请手动填写。': '供應商未返回模型列表，請手動填寫。',
           '保存后使用 Windows DPAPI 加密存储。': '儲存後使用 Windows DPAPI 加密儲存。',
           '保存退出选项与核心路径': '儲存退出選項與核心路徑',
           '保存配置': '儲存配置',
           '信息': '資訊',
           '修改模型': '修改模型',
           '修改模型配置': '修改模型配置',
           '修改模式为': '修改模式為',
           '停止接入': '停止接入',
           '全部': '全部',
           '共 {0} 个模型配置 · 点击卡片切换，点击铅笔图标编辑参数': '共 {0} 個模型配置 · 點選卡片切換，點選鉛筆圖示編輯參數',
           '关于': '關於',
           '关闭': '關閉',
           '关闭请求详情': '關閉請求詳情',
           '其它接入': '其它接入',
           '其它接入会话需明确选择目标；Relay 不自动接管。': '其它接入會話需明確選擇目標；Relay 不自動接管。',
           '准备读取会话索引。': '準備讀取會話索引。',
           '切换成功：{0} → {1}。原配置已备份，写入结果已校验；下方列表已刷新。': '切換成功：{0} → {1}。原始配置已備份，寫入結果已校驗；下方清單已刷新。',
           '切换未完成：{0}，校验通过 {1} / {2}。原配置备份与操作记录已保留，不会自动重写会话。': '切換未完成：{0}，校驗透過 {1} / '
                                                               '{2}。原先配置備份與操作記錄已保留，不會自動重寫工作階段。',
           '切换模型': '切換模型',
           '删除后将无法自动恢复，需要重新填写 API KEY。': '刪除後將無法自動恢復，需要重新填寫 API KEY。',
           '删除此模型配置': '刪除此模型配置',
           '删除这条模型配置？': '刪除這條模型配置？',
           '刷新会话列表': '刷新會話列表',
           '刷新接入': '刷新存取',
           '匿名使用统计': '匿名使用統計',
           '匿名使用统计已关闭': '匿名使用統計已關閉',
           '匿名使用统计已启用': '匿名使用統計已啟用',
           '匿名使用统计明确同意开关': '匿名使用統計明確同意開關',
           '单次最大输出。': '單次最大輸出。',
           '发起请求后，可在此查看不含正文的安全摘要。': '發起請求後，可在此查看不含正文的安全摘要。',
           '取消': '取消',
           '可点击“读取”从供应商获取可用模型。': '可點選「讀取」從供應商取得可用模型。',
           '国家信息不由客户端采集；未来上传阶段仅允许服务端接入层瞬时推断。撤回后立即停止产生新的遥测数据。': '國家資訊不由客戶端採集；未來上傳階段僅允許服務端存取層瞬時推斷。撤回後立即停止產生新的遙測資料。',
           '图片支持': '圖片支持',
           '图片输入': '圖片輸入',
           '在“模型管理”页面添加至少一个模型，并点击模型卡片进行选择。': '在「模型管理」頁面中新增至少一個模型，並點選模型卡進行選擇。',
           '填写供应商公布的完整端点；程序按原样请求，不会改写路径。': '填寫供應商公佈的完整端點；程序按原樣請求，不會改寫路徑。',
           '复制': '複製',
           '外观': '外觀',
           '失败': '失敗',
           '失败 {0}': '失敗 {0}',
           '实时显示请求、连接与配置变更记录': '即時顯示請求、連線與設定變更記錄',
           '客户端接入': '用戶端接入',
           '将撤销本程序对 Codex 配置所做的修改，并停止本地服务。': '將撤銷本程式對 Codex 配置所做的修改，並停止本機服務。',
           '尚未接入': '尚未接入',
           '尚未接入 Codex': '尚未接入 Codex',
           '尚未配置模型': '尚未配置模型',
           '展开已读取的模型列表；也可直接手动输入模型名称': '展開已讀取的模型清單；也可直接手動輸入模型名稱',
           '工具调用': '工具調用',
           '已取消；没有备份或修改会话。': '已取消；沒有備份或修改會話。',
           '已开启': '已開啟',
           '已归档': '已歸檔',
           '已按当前模型回填全部原参数；API KEY 已解密加载并默认遮蔽。': '已按目前模型回填全部原參數；API KEY 已解密載入並預設遮蔽。',
           '已接入': '已存取',
           '已接入 Codex，但端口无法启动：{0}': '已接取 Codex，但連接埠無法啟動：{0}',
           '已接入但服务未运行': '已存取但服務未執行',
           '已知供应商会自动匹配；自定义中转请按实际选择。': '已知供應商會自動匹配；自訂中轉請按實際選擇。',
           '已读取 {0} 个模型': '已讀取 {0} 個模型',
           '已读取 {0} 个模型，请从列表选择': '已讀取 {0} 個模型，請從清單中選擇',
           '帮助改进 MicroGlow Relay': '幫助改進 MicroGlow Relay',
           '平均耗时 {0:.2f} 秒': '平均耗時 {0:.2f} 秒',
           '应用': '應用',
           '归档会话仅供查看；请先在 Codex 中取消归档，再退出 Codex 后操作。': '歸檔會話僅供查看；請先在 Codex 中取消歸檔，再退出 Codex 後操作。',
           '当前使用': '目前使用',
           '当前模型已切换': '目前模型已切換',
           '当前模式': '目前模式',
           '当前路由模型': '目前路由模型',
           '思考强度': '思考強度',
           '思考模式': '思考模式',
           '恢复 Codex 配置？': '恢復 Codex 配置？',
           '恢复配置': '恢復配置',
           '成功': '成功',
           '成功 {0} · 失败 {1}': '成功 {0} · 失敗 {1}',
           '所属项目名称': '所屬項目名稱',
           '打开主界面': '打開主介面',
           '打开数据目录': '開啟資料目錄',
           '把本地路由服务接入 Codex，并在需要时完整恢复原始配置': '把本地路由服務連接到 Codex，並在需要時完整恢復原始配置',
           '接入 Codex': '接上 Codex',
           '接入信息': '存取資訊',
           '接入信息已刷新': '接入資訊已刷新',
           '接入已失效': '接入已失效',
           '接入时会先完整备份现有 Codex 配置，随时可以一键恢复。': '接入時會先完整備份現有 Codex 配置，隨時可以一鍵恢復。',
           '接口协议': '介面協定',
           '接口地址': '介面位址',
           '操作': '操作',
           '操作未完成；原配置与已有备份保留。请重新检查，不会回显底层数据。': '操作未完成；原配置與已有備份保留。请重新检查，不会回显底层数据。',
           '支持推理参数时开启，否则可能产生 400': '支援推理參數時開啟，否則可能產生 400',
           '收起模型': '收起模型',
           '数据传输': '資料傳輸',
           '数据位置': '數據位置',
           '文本': '文字',
           '开始日期': '開始日期',
           '无法读取': '無法讀取',
           '日志': '紀錄',
           '时间': '時間',
           '结束日期': '結束日期',
           '是否明确同意启用匿名使用统计？\n\n仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。不收集请求或响应正文、文件、代码、密钥、IP、原始错误和逐请求记录。': '是否明確同意啟用匿名使用統計？\n'
                                                                                                           '\n'
                                                                                                           '僅累計每日呼叫、成功/錯誤、Token、固定延遲區間、標準錯誤類別和回退次數。不收集請求或回應正文、文件、代碼、金鑰、IP、原始錯誤和逐請求記錄。',
           '显示密钥': '顯示密鑰',
           '智谱 AI': '智譜 AI',
           '暂无日志 · 服务启动或配置变更后会显示在这里': '暫無日誌 · 服務啟動或設定變更後會顯示在這裡',
           '暂无记录': '暫無紀錄',
           '暂无请求记录': '暫無請求記錄',
           '最近活动': '最近活動',
           '服务已停止': '服務已停止',
           '服务运行中': '服務運作中',
           '未命名会话': '未命名會話',
           '未开启': '未開啟',
           '未接入': '未接取',
           '未检测到 ChatGPT 订阅登录；没有备份或修改会话。': '未偵測到 ChatGPT 訂閱登入；沒有備份或修改會話。',
           '未运行': '未運行',
           '本地地址': '本地地址',
           '本地接口只监听 127.0.0.1，并要求随机访问令牌；历史 Backup 文件保存在 Codex 配置目录，恢复凭据保存在数据目录的 microglow-relay-codex-receipt.json。': '本機介面只監聽 '
                                                                                                                      '127.0.0.1，並要求隨機存取令牌；歷史 '
                                                                                                                      'Backup '
                                                                                                                      '檔案保存在 '
                                                                                                                      'Codex '
                                                                                                                      '設定目錄，恢復憑證儲存在資料目錄的 '
                                                                                                                      'microglow-relay-codex-receipt.json。',
           '本地服务': '本地服務',
           '本地服务已停止': '本地服務已停止',
           '本地模型的 API KEY 使用 Windows DPAPI 加密，仅当前账户可读取。': '本機模型的 API KEY 使用 Windows DPAPI 加密，僅目前帳戶可讀取。',
           '本地端口、外观与数据位置': '本機連接埠、外觀與資料位置',
           '本地路由服务正在运行，Codex 的新请求会通过当前模型进行路由。': '本機路由服務正在運行，Codex 的新請求會透過目前模型進行路由。',
           '本地路由让 Codex 通过本机访问你自己的模型供应商；请求正文不会被写入磁盘。': '本機路由讓 Codex 透過本機存取你自己的模型供應商；請求正文不會被寫入磁碟。',
           '检测到接入后的外部修改': '偵測到存取後的外部修改',
           '概览': '概覽',
           '模型': '模型',
           '模型名称': '模型名稱',
           '模型已删除': '模型已刪除',
           '模型管理': '模型管理',
           '模型配置保存在 microglow-relay-settings.json，用量日志保存最近 30 天且不记录正文。': '模型配置保存在 '
                                                                         'microglow-relay-settings.json，用量日誌保存最近 '
                                                                         '30 天且不記錄正文。',
           '模型配置已保存': '模型配置已儲存',
           '正在只读加载本机会话索引…（无需退出 Codex）': '正在唯讀載入本機會話索引…（無需退出 Codex）',
           '正在备份、切换并校验这一条会话…': '正在備份、切換並校驗這一會話…',
           '正在核对：{0}…': '正在核對：{0}…',
           '正在测试连接…': '正在測試連線…',
           '正在读取供应商模型列表…': '正在讀取供應商模型清單…',
           '测试连接': '測試連接',
           '添加、修改供应商模型配置，点击卡片选择当前路由模型': '新增、修改供應商模型配置，點選卡片選擇目前路由模型',
           '添加模型': '新增模型',
           '清空': '清空',
           '点击“添加模型”填写供应商、API KEY 与模型名称，保存后点击卡片即可切换路由。': '點選「新增模型」填寫供應商、API KEY 與模型名稱，儲存後點選卡片即可切換路由。',
           '点击本页的“接入 Codex”，程序会先完整备份现有 Codex 配置。': '點選本頁的“接入 Codex”，程式會先完整備份現有 Codex 設定。',
           '点击记录查看详情': '點擊記錄看詳情',
           '状态': '狀態',
           '界面语言': '介面語言',
           '白色': '白色',
           '监听端口': '監聽埠',
           '硅基流动': '矽基流動',
           '确定': '確定',
           '确定切换这一条会话？': '確定切換這一會話？',
           '空闲': '空閒',
           '端口修改会在下次启动本地服务时生效；已接入 Codex 时需要重新接入以刷新地址。': '連接埠修改會在下次啟動本機服務時生效；已連接 Codex 時需要重新存取以刷新位址。',
           '端口已保存，将在下次启动服务时生效': '連接埠已儲存，將在下次啟動服務時生效',
           '管理': '管理',
           '耗时': '耗時',
           '能力与协议': '能力與協議',
           '能力可多选，亮色为已开启。仅选择上游支持的能力；不支持思考参数时开启可能产生 400。': '能力可多選，亮色為已開啟。僅選擇上游支援的能力；不支援思考參數時開啟可能產生 400。',
           '自动寻找 Codex 桌面端核心（可手动指定 codex.exe）': '自動尋找 Codex 桌面端核心（可手動指定 codex.exe）',
           '自动滚动': '自動捲動',
           '自定义 / 中转服务': '自訂 / 中轉服務',
           '自定义中转时填写，例如：我的中转站': '自訂中轉時填寫，例如：我的中繼站',
           '警告': '警告',
           '让同一段 Codex 会话在官方订阅与 Relay 模型之间继续使用': '讓同一段 Codex 會話在官方訂閱與 Relay 模型之間繼續使用',
           '设置': '設定',
           '访问令牌': '訪問令牌',
           '识别到历史路由模型标识，归类为其它接入；不等于 Codex 或当前 Relay。': '識別到歷史路由模型標識，歸類為其它接入；不等於 Codex 或當前 Relay。',
           '请先保存至少一个模型配置。': '請先儲存至少一個模型配置。',
           '请先明确选择 Codex 或 Relay。': '請先明確選擇 Codex 或 Relay。',
           '请先添加一个模型': '請先加入一個模型',
           '请在“模型管理”页面添加一个供应商模型。': '請在「模型管理」頁面中新增一個供應商模型。',
           '请求详情': '請求詳情',
           '读取': '讀取',
           '读取失败：': '讀取失敗：',
           '读取成功：当前索引中没有符合条件的会话（可切换「已归档」查看）。': '讀取成功：目前索引中沒有符合條件的會話（可切換「已歸檔」檢視）。',
           '读取成功：本页 {0} 条会话。': '讀取成功：本頁 {0} 條會話。',
           '赛博朋克': '賽博朋克',
           '路由信息': '路由資訊',
           '路由标识': '路由標識',
           '输入 Token': '輸入 Token',
           '输入与输出合计': '輸入與輸出合計',
           '输出 Token': '輸出 Token',
           '运行中': '運作中',
           '还没有模型配置': '還沒有模型配置',
           '进入本页时读取本机会话索引。': '進入本頁時請讀取本機會話索引。',
           '连接信息': '連線訊息',
           '退出': '退出',
           '退出时，将登录方式设为 ChatGPT 订阅登录（不修改会话或默认模型）': '登出時，將登入方式設為 ChatGPT 訂閱登入（不修改會話或預設模型）',
           '退出选项 · 仅登录设置 · 默认关闭': '登出選項 · 僅登入設定 · 預設為關閉',
           '选择': '選擇',
           '选择 Codex 桌面端核心': '選擇 Codex 桌面端核心',
           '选择核心': '選擇核心',
           '选项未能保存，请检查本地存储。': '選項未能儲存，請檢查本機儲存。',
           '配置已保存 · {0}': '配置已儲存 · {0}',
           '重启 Codex，新建任务后选择“{0}”。': '重新啟動 Codex，建立新任務後選擇「{0}」。',
           '重新接入': '重新存取',
           '金碧辉煌': '金碧輝煌',
           '错误': '錯誤',
           '隐私保护：不保存 Prompt、Response 或原始请求正文。': '隱私權保護：不儲存 Prompt、Response 或原始請求正文。',
           '需要还原时点击“恢复配置”，本程序写入的字段会被撤销。': '需要還原時點擊“恢復配置”，本程式寫入的欄位會被撤銷。',
           '高': '高',
           '黑色': '黑色',
           '默认关闭。仅在你主动同意后累计 UTC 每日计数；不记录 Prompt、Response、正文、文件、代码、密钥、IP 或原始错误。': '預設關閉。僅在你主動同意後累積 UTC '
                                                                                 '每日計數；不記錄 '
                                                                                 'Prompt、Response、正文、文件、代碼、密鑰、IP '
                                                                                 '或原始錯誤。',
           '（未设置）': '（未設定）',
           '，当前使用': '，當前使用',
           '，点击切换': '，點擊切換',
           '雾蓝科技': '霧藍科技',
           '石墨青金': '石墨青金',
           '微光': '微光',
           '夜幕': '夜幕',
           '金辉': '金輝',
           '月白': '月白',
           '星港': '星港'}}

# Release/update UI terms are kept alongside the offline catalog.
_UPDATE_TRANSLATIONS = {
    'de': ('Nach Updates suchen', 'Updatequelle nicht konfiguriert', 'Bereits auf dem neuesten Stand',
           'Neue Version verfügbar', 'Version {0} verfügbar. Downloadseite öffnen?',
           'Updateprüfung fehlgeschlagen. Bitte später erneut versuchen.',
           'Nicht veröffentlicht', 'Neue Version {0} verfügbar', 'Kein offizielles Update verfügbar'),
    'en': ('Check for updates', 'Update source is not configured', 'Already up to date',
           'New version available', 'Version {0} is available. Open the download page?',
           'Update check failed. Please try again later.',
           'Unreleased', 'New version {0} available', 'No official update available'),
    'es': ('Buscar actualizaciones', 'La fuente de actualizaciones no está configurada',
           'Ya tienes la última versión', 'Nueva versión disponible',
           'La versión {0} está disponible. ¿Abrir la página de descarga?',
           'No se pudo buscar actualizaciones. Inténtalo de nuevo más tarde.',
           'Sin publicar', 'Nueva versión {0} disponible', 'No hay actualización oficial'),
    'ja': ('更新を確認', '更新元が設定されていません', '最新バージョンです', '新しいバージョンがあります',
           'バージョン {0} があります。ダウンロードページを開きますか？',
           '更新を確認できませんでした。後でもう一度お試しください。',
           '未リリース', '新しいバージョン {0} があります', '正式な更新はありません'),
    'ko': ('업데이트 확인', '업데이트 출처가 설정되지 않았습니다', '이미 최신 버전입니다',
           '새 버전 사용 가능', '버전 {0}이 있습니다. 다운로드 페이지를 열까요?',
           '업데이트 확인에 실패했습니다. 나중에 다시 시도하세요.',
           '미출시', '새 버전 {0} 사용 가능', '공식 업데이트 없음'),
    'th': ('ตรวจสอบการอัปเดต', 'ยังไม่ได้ตั้งค่าแหล่งอัปเดต', 'เป็นเวอร์ชันล่าสุดแล้ว',
           'มีเวอร์ชันใหม่', 'มีเวอร์ชัน {0} ต้องการเปิดหน้าดาวน์โหลดหรือไม่',
           'ตรวจสอบการอัปเดตไม่สำเร็จ โปรดลองอีกครั้งภายหลัง',
           'ยังไม่เผยแพร่', 'พบเวอร์ชันใหม่ {0}', 'ยังไม่มีการอัปเดตอย่างเป็นทางการ'),
    'zh-TW': ('檢查更新', '尚未設定更新來源', '已是最新版本', '發現新版本',
              '發現新版本 {0}，是否開啟下載頁面？', '檢查更新失敗，請稍後再試',
              '未發布', '發現新版本 {0}', '暫無正式更新'),
}
_UPDATE_KEYS = ('检查更新', '更新源尚未配置', '已是最新版本', '发现新版本',
                '发现新版本 {0}，是否打开下载页面？', '检查更新失败，请稍后重试',
                '未发布', '发现新版本 {0}', '暂无正式更新')
for _code, _values in _UPDATE_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_UPDATE_KEYS, _values))

# Reviewed terminology is part of the complete offline catalog as well as
# the runtime override layer, so newly added UI labels are covered by tests.
from .translation_overrides import OVERRIDES as _REVIEWED_TRANSLATIONS
for _code, _values in _REVIEWED_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(_values)

# ---- Token 小计（TRIP A / B）
# 顺序与 _TRIP_KEYS 一一对应，zip 装配，避免键值错位。
_TRIP_KEYS = ('Token 小计', '清零', '清零只重置小计，不影响日总量与历史记录',
              '入 {0}　出 {1}　{2} 次　·　已累计 {3}', '刚刚',
              '{0} 分钟', '{0} 小时 {1} 分', '{0} 天 {1} 小时', '{0} 小时', '{0} 天',
              '入 {0}　出 {1}　{2} 次　·　尚未开始计时')
_TRIP_TRANSLATIONS = {
    'zh-TW': ('Token 小計', '歸零', '歸零只重設小計，不影響日總量與歷史記錄',
              '入 {0}　出 {1}　{2} 次　·　已累計 {3}', '剛剛',
              '{0} 分鐘', '{0} 小時 {1} 分', '{0} 天 {1} 小時', '{0} 小時', '{0} 天',
              '入 {0}　出 {1}　{2} 次　·　尚未開始計時'),
    'en': ('Token subtotal', 'Reset',
           "Reset clears only this subtotal; today's total and the history log stay untouched",
           'In {0} · Out {1} · {2} calls · Accumulated {3}', 'Just now',
           '{0} min', '{0} h {1} min', '{0} d {1} h', '{0} h', '{0} d',
           'In {0} · Out {1} · {2} calls · Timer not started'),
    'de': ('Token-Zwischensumme', 'Zurücksetzen',
           'Zurücksetzen betrifft nur diese Zwischensumme; Tageswert und Verlauf bleiben unverändert',
           'Ein {0} · Aus {1} · {2} Aufrufe · Gesammelt {3}', 'Gerade eben',
           '{0} Min.', '{0} Std. {1} Min.', '{0} T. {1} Std.', '{0} Std.', '{0} T.',
           'Ein {0} · Aus {1} · {2} Aufrufe · Timer noch nicht gestartet'),
    'ja': ('トークン小計', 'リセット', 'リセットはこの小計のみ。日次合計と履歴は変わりません',
           '入力 {0}　出力 {1}　{2} 回　·　累計 {3}', 'たった今',
           '{0} 分', '{0} 時間 {1} 分', '{0} 日 {1} 時間', '{0} 時間', '{0} 日',
           '入力 {0}　出力 {1}　{2} 回　·　計測はまだ始まっていません'),
    'th': ('ยอดย่อยโทเคน', 'รีเซ็ต',
           'การรีเซ็ตมีผลเฉพาะยอดย่อยนี้ ยอดรวมของวันและประวัติยังคงเดิม',
           'เข้า {0} · ออก {1} · {2} ครั้ง · สะสม {3}', 'เมื่อสักครู่',
           '{0} นาที', '{0} ชม. {1} นาที', '{0} วัน {1} ชม.', '{0} ชม.', '{0} วัน',
           'เข้า {0} · ออก {1} · {2} ครั้ง · ยังไม่เริ่มจับเวลา'),
    'es': ('Subtotal de tokens', 'Reiniciar',
           'Reiniciar solo borra este subtotal; el total del día y el historial no cambian',
           'Entrada {0} · Salida {1} · {2} llamadas · Acumulado {3}', 'Ahora mismo',
           '{0} min', '{0} h {1} min', '{0} d {1} h', '{0} h', '{0} d',
           'Entrada {0} · Salida {1} · {2} llamadas · Temporizador no iniciado'),
    'ko': ('토큰 소계', '초기화', '초기화는 이 소계만 지우며 일일 합계와 기록은 그대로입니다',
           '입력 {0}　출력 {1}　{2} 회　·　누적 {3}', '방금',
           '{0} 분', '{0} 시간 {1} 분', '{0} 일 {1} 시간', '{0} 시간', '{0} 일',
           '입력 {0}　출력 {1}　{2} 회　·　계측이 아직 시작되지 않았습니다'),
}
for _code, _values in _TRIP_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_TRIP_KEYS, _values))
# ---- Trip 读数口径三档（全局|Codex|Claude）：账按协议分桶并行累计，口径只是视角
_SCOPE_KEYS = ('全局',
               '小计读数口径：全局 = 全部请求；Codex = 仅 Responses 协议；Claude = 仅 Anthropic 协议')
_SCOPE_TRANSLATIONS = {
    'zh-TW': ('全域', '小計讀數口徑：全域 = 全部請求；Codex = 僅 Responses 協定；Claude = 僅 Anthropic 協定'),
    'en': ('All', 'Subtotal reading scope: All = every request; Codex = Responses protocol '
                  'only; Claude = Anthropic protocol only'),
    'de': ('Alle', 'Zählerbereich der Zwischensumme: Alle = jede Anfrage; Codex = nur '
                   'Responses-Protokoll; Claude = nur Anthropic-Protokoll'),
    'ja': ('全体', '小計の読み取り範囲：全体 = すべてのリクエスト；Codex = Responses プロトコルのみ；'
                   'Claude = Anthropic プロトコルのみ'),
    'th': ('ทั้งหมด', 'ขอบเขตการอ่านยอดย่อย: ทั้งหมด = ทุกคำขอ; Codex = เฉพาะโปรโตคอล '
                     'Responses; Claude = เฉพาะโปรโตคอล Anthropic'),
    'es': ('Todo', 'Ámbito de lectura del subtotal: Todo = todas las solicitudes; Codex = solo '
                   'protocolo Responses; Claude = solo protocolo Anthropic'),
    'ko': ('전체', '소계 읽기 범위: 전체 = 모든 요청; Codex = Responses 프로토콜만; '
                   'Claude = Anthropic 프로토콜만'),
}
for _code, _values in _SCOPE_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_SCOPE_KEYS, _values))
# ---- 总里程 ODO 面板（任务书第 5 节）
_ODO_KEYS = ('总里程', '自安装以来累计 Token，永不清零',
             '已陪伴 {0} 天', '累计请求 {0} 次', '日均 {0} 万 Token')
_ODO_TRANSLATIONS = {
    'zh-TW': ('總里程', '自安裝以來累計 Token，永不歸零',
              '已陪伴 {0} 天', '累計請求 {0} 次', '日均 {0} 萬 Token'),
    'en': ('Total mileage', 'Cumulative tokens since installation; never reset',
           'Together for {0} days', '{0} requests in total',
           'Daily avg {0}×10k tokens'),
    'de': ('Gesamtstrecke', 'Kumulative Tokens seit der Installation; niemals zurückgesetzt',
           'Seit {0} Tagen zusammen', 'Insgesamt {0} Anfragen',
           'Täglich Ø {0}×10k Tokens'),
    'ja': ('総走行距離', 'インストール以降の累計 Token。リセットされません',
           '{0} 日間の記録', '累計 {0} 回のリクエスト', '1 日平均 {0} 万 Token'),
    'th': ('ระยะทางสะสม', 'Token สะสมตั้งแต่ติดตั้ง ไม่มีการรีเซ็ต',
           'อยู่ด้วยกันมา {0} วัน', 'รวม {0} คำขอ', 'เฉลี่ย {0} หมื่น Token ต่อวัน'),
    'es': ('Kilometraje total', 'Tokens acumulados desde la instalación; nunca se reinicia',
           '{0} días juntos', '{0} solicitudes en total',
           'Promedio diario {0}×10k tokens'),
    'ko': ('총 주행 거리', '설치 이후 누적 Token. 영구 보존',
           '함께한 지 {0} 일', '누적 {0} 회 요청', '일평균 {0} 만 Token'),
}
for _code, _values in _ODO_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_ODO_KEYS, _values))
# ---- 工作台化解波动条（任务书第 4 节）
_MITIGATION_STRIP_KEYS = ('今日已为你化解 {0} 次波动，Agent 未受打扰',
                          '限流', '超时', '临时故障', '换渠道')
_MITIGATION_STRIP_TRANSLATIONS = {
    'zh-TW': ('今日已為你化解 {0} 次波動，Agent 未受打擾',
              '限流', '超時', '臨時故障', '換渠道'),
    'en': ('{0} hiccups quietly resolved today — your agents never noticed',
           'Rate limit', 'Timeout', 'Transient fault', 'Channel switch'),
    'de': ('{0} Störungen heute automatisch abgefedert — Ihre Agents blieben ungestört',
           'Ratenlimit', 'Zeitüberschreitung', 'Vorübergehender Fehler', 'Kanalwechsel'),
    'ja': ('本日 {0} 回の波動を自動で吸収しました。Agent への影響はありません',
           'レート制限', 'タイムアウト', '一時的な障害', 'チャネル切替'),
    'th': ('วันนี้แก้ความผันผวนให้ {0} ครั้ง Agent ไม่ได้รับผลกระทบ',
           'จำกัดอัตรา', 'หมดเวลา', 'ข้อขัดข้องชั่วคราว', 'สลับช่อง'),
    'es': ('Hoy se resolvieron {0} incidencias sin molestar a tus agentes',
           'Límite de tasa', 'Tiempo agotado', 'Fallo transitorio', 'Cambio de canal'),
    'ko': ('오늘 {0} 회의 변동을 자동으로 해결했습니다. Agent 는 영향을 받지 않았습니다',
           '속도 제한', '시간 초과', '일시적 오류', '채널 전환'),
}
for _code, _values in _MITIGATION_STRIP_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_MITIGATION_STRIP_KEYS, _values))
# ---- 请求侧模型与路由结果不一致时，详情面板多出的一行
# 日志页的「模型」列是**出口模型名**（打到上游的那个名字），请求侧可能是配置 id
# 或原生 slug。两列分开写，才能看出「Codex 说用 A、实际路由到 B」这类问题。
_TRACE_KEYS = ('Codex 请求', '与所选配置一致')
_TRACE_TRANSLATIONS = {
    'zh-TW': ('Codex 請求', '與所選配置一致'),
    'en': ('Codex request', 'Matches the selected profile'),
    'de': ('Codex-Anfrage', 'Entspricht dem gewählten Profil'),
    'ja': ('Codex リクエスト', '選択中の設定と一致'),
    'th': ('คำขอจาก Codex', 'ตรงกับการตั้งค่าที่เลือก'),
    'es': ('Solicitud de Codex', 'Coincide con el perfil elegido'),
    'ko': ('Codex 요청', '선택한 설정과 일치'),
}
for _code, _values in _TRACE_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_TRACE_KEYS, _values))

# ---------------------------------------------------------------------------
# 0.9 UI 改版新增文案（皮肤标签、URL 自动补全、自动拉模型、SETUP）。
# 皮肤标签格式「{季}·{名} · {昼/夜}」由 theme.THEME_LABELS 逐字面登记。
# ---------------------------------------------------------------------------
_SKIN_UI_KEYS = (
    '春·玉兰 · 昼', '春·玉兰 · 夜', '夏·荷 · 昼', '夏·荷 · 夜',
    '秋·枫 · 昼', '秋·枫 · 夜', '冬·梅 · 昼', '冬·梅 · 夜',
    '跟随系统', '昼', '夜',
    '粘贴站根或带 /v1 的地址即可，程序按协议自动补全端点路径。',
    '已自动读取供应商模型列表…',
    '自动获取模型未成功，可手动重试或直接填写模型名称。',
)
_SKIN_UI_TRANSLATIONS = {
    'zh-TW': ('春·玉蘭 · 晝', '春·玉蘭 · 夜', '夏·荷 · 晝', '夏·荷 · 夜',
              '秋·楓 · 晝', '秋·楓 · 夜', '冬·梅 · 晝', '冬·梅 · 夜',
              '跟隨系統', '晝', '夜',
              '貼上站根或含 /v1 的位址即可，程式會按協定自動補全端點路徑。',
              '已自動讀取供應商模型清單…',
              '自動取得模型未成功，可手動重試或直接填寫模型名稱。'),
    'en': ('Spring Magnolia · Day', 'Spring Magnolia · Night',
           'Summer Lotus · Day', 'Summer Lotus · Night',
           'Autumn Maple · Day', 'Autumn Maple · Night',
           'Winter Plum · Day', 'Winter Plum · Night',
           'Follow system', 'Day', 'Night',
           'Paste the site root or a /v1 base URL; the endpoint path is completed automatically.',
           'Model list fetched automatically…',
           'Automatic model fetch failed; retry manually or type the model name.'),
    'de': ('Frühjahrsmagnolie · Tag', 'Frühjahrsmagnolie · Nacht',
           'Sommerlotus · Tag', 'Sommerlotus · Nacht',
           'Herbstahorn · Tag', 'Herbstahorn · Nacht',
           'Winterpflaume · Tag', 'Winterpflaume · Nacht',
           'System folgen', 'Tag', 'Nacht',
           'Stamm-URL oder /v1-Basis einfügen; der Endpunktpfad wird automatisch ergänzt.',
           'Modellliste automatisch abgerufen…',
           'Automatischer Modellabruf fehlgeschlagen; manuell wiederholen oder Modellnamen eingeben.'),
    'ja': ('春・玉蘭 · 昼', '春・玉蘭 · 夜', '夏・蓮 · 昼', '夏・蓮 · 夜',
           '秋・楓 · 昼', '秋・楓 · 夜', '冬・梅 · 昼', '冬・梅 · 夜',
           'システムに従う', '昼', '夜',
           'サイトのルートまたは /v1 付きのアドレスを貼り付けてください。エンドポイントのパスは自動補完されます。',
           'モデル一覧を自動取得しました…',
           'モデルの自動取得に失敗しました。手動で再試行するか、モデル名を直接入力してください。'),
    'th': ('แมกโนเลียฤดูใบไม้ผลิ · กลางวัน', 'แมกโนเลียฤดูใบไม้ผลิ · กลางคืน',
           'บัวฤดูร้อน · กลางวัน', 'บัวฤดูร้อน · กลางคืน',
           'เมเปิลฤดูใบไม้ร่วง · กลางวัน', 'เมเปิลฤดูใบไม้ร่วง · กลางคืน',
           'ดอกพลัมฤดูหนาว · กลางวัน', 'ดอกพลัมฤดูหนาว · กลางคืน',
           'ตามระบบ', 'กลางวัน', 'กลางคืน',
           'วางรากเว็บไซต์หรือที่อยู่ที่มี /v1 ระบบจะเติมเส้นทางปลายทางให้อัตโนมัติ',
           'ดึงรายการโมเดลอัตโนมัติแล้ว…',
           'ดึงโมเดลอัตโนมัติไม่สำเร็จ ลองใหม่ด้วยตนเองหรือพิมพ์ชื่อโมเดล'),
    'es': ('Magnolia de primavera · Día', 'Magnolia de primavera · Noche',
           'Loto de verano · Día', 'Loto de verano · Noche',
           'Arce de otoño · Día', 'Arce de otoño · Noche',
           'Ciruelo de invierno · Día', 'Ciruelo de invierno · Noche',
           'Según el sistema', 'Día', 'Noche',
           'Pega la raíz del sitio o una URL base con /v1; la ruta del endpoint se completa automáticamente.',
           'Lista de modelos obtenida automáticamente…',
           'La obtención automática de modelos falló; reintenta manualmente o escribe el nombre del modelo.'),
    'ko': ('春(춘)·목련 · 낮', '春(춘)·목련 · 밤', '夏(하)·연꽃 · 낮', '夏(하)·연꽃 · 밤',
           '秋(추)·단풍 · 낮', '秋(추)·단풍 · 밤', '冬(동)·매화 · 낮', '冬(동)·매화 · 밤',
           '시스템 따르기', '낮', '밤',
           '사이트 루트 또는 /v1이 포함된 주소를 붙여넣으면 엔드포인트 경로가 자동 완성됩니다.',
           '모델 목록을 자동으로 가져왔습니다…',
           '모델 자동 가져오기에 실패했습니다. 수동으로 다시 시도하거나 모델 이름을 입력하세요.'),
}
assert len(_SKIN_UI_KEYS) == len(_SKIN_UI_TRANSLATIONS['zh-TW'])
for _code, _values in _SKIN_UI_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_SKIN_UI_KEYS, _values))

# ---------------------------------------------------------------------------
# 渠道组编辑器文案（任务书第 6 节）。
# ---------------------------------------------------------------------------
_CHANNEL_EDITOR_KEYS = (
    '渠道组（可选）',
    '同一模型可挂多个渠道（不同地址与密钥）。请求按权重随机选健康渠道，失败自动冷却 60 秒并换下一家。不添加则只用上方单渠道。',
    '＋ 添加渠道',
    '渠道名称，如：供应商 A',
    '留空保持原密钥',
    '启用',
    '权重',
    '删除该渠道',
    '名称',
    '状态',
)
_CHANNEL_EDITOR_TRANSLATIONS = {
    'zh-TW': ('渠道組（可選）',
              '同一模型可掛多個渠道（不同地址與密鑰）。請求按權重隨機選健康渠道，失敗自動冷卻 60 秒並換下一家。不新增則只用上方單渠道。',
              '＋ 新增渠道', '渠道名稱，如：供應商 A', '留空保持原密鑰', '啟用', '權重', '刪除該渠道', '名稱', '狀態'),
    'en': ('Channel group (optional)',
           'One model can have multiple channels (different URLs and keys). Requests pick a healthy channel by weight; failures cool down for 60 seconds and switch. Leave empty to use the single channel above.',
           '＋ Add channel', 'Channel name, e.g. Vendor A', 'Leave empty to keep the existing key', 'Enabled', 'Weight', 'Remove this channel', 'Name', 'State'),
    'de': ('Kanalgruppe (optional)',
           'Ein Modell kann mehrere Kanäle haben (unterschiedliche URLs und Schlüssel). Anfragen wählen einen gesunden Kanal nach Gewicht; Fehler führen zu 60 Sekunden Abkühlung und Wechsel. Ohne Eintrag gilt der einzelne Kanal oben.',
           '＋ Kanal hinzufügen', 'Kanalname, z. B. Anbieter A', 'Leer lassen, um den bestehenden Schlüssel zu behalten', 'Aktiv', 'Gewicht', 'Diesen Kanal entfernen', 'Name', 'Status'),
    'ja': ('チャネルグループ（任意）',
           '同じモデルに複数のチャネル（異なる URL とキー）を設定できます。リクエストは重みに従って健全なチャネルを選び、失敗時は 60 秒冷却して次に切り替えます。追加しなければ上記の単一チャネルを使用します。',
           '＋ チャネル追加', 'チャネル名（例：提供者 A）', '空欄で既存キーを保持', '有効', '重み', 'このチャネルを削除', '名前', '状態'),
    'th': ('กลุ่มช่องทาง (ไม่บังคับ)',
           'โมเดลเดียวต่อหลายช่องทาง (URL และคีย์ต่างกัน) คำขอจะเลือกช่องทางที่ปกติตามน้ำหนัก หากล้มเหลวจะคูลดาวน์ 60 วินาทีแล้วสลับช่องถัดไป หากไม่เพิ่มจะใช้ช่องเดี่ยวด้านบน',
           '＋ เพิ่มช่องทาง', 'ชื่อช่องทาง เช่น ผู้ให้บริการ A', 'เว้นว่างเพื่อคงคีย์เดิม', 'เปิดใช้งาน', 'น้ำหนัก', 'ลบช่องทางนี้', 'ชื่อ', 'สถานะ'),
    'es': ('Grupo de canales (opcional)',
           'Un modelo puede tener varios canales (distintas URL y claves). Las peticiones eligen un canal sano por peso; los fallos se enfrían 60 segundos y cambian. Sin añadir, se usa el canal único de arriba.',
           '＋ Añadir canal', 'Nombre del canal, p. ej. Proveedor A', 'Dejar vacío para conservar la clave', 'Activado', 'Peso', 'Eliminar este canal', 'Nombre', 'Estado'),
    'ko': ('채널 그룹 (선택)',
           '하나의 모델에 여러 채널(서로 다른 URL과 키)을 연결할 수 있습니다. 요청은 가중치에 따라 건강한 채널을 선택하고, 실패 시 60초 冷却 후 다음 채널로 전환합니다. 추가하지 않으면 위의 단일 채널을 사용합니다.',
           '＋ 채널 추가', '채널 이름 (예: 공급자 A)', '비워 두면 기존 키 유지', '활성화', '가중치', '이 채널 삭제', '이름', '상태'),
}
assert len(_CHANNEL_EDITOR_KEYS) == len(_CHANNEL_EDITOR_TRANSLATIONS['zh-TW'])
for _code, _values in _CHANNEL_EDITOR_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_CHANNEL_EDITOR_KEYS, _values))

# ---------------------------------------------------------------------------
# Trip 清零撤销条（任务书第 5 节）。
# ---------------------------------------------------------------------------
_UNDO_BAR_KEYS = (
    '{0} 已清零（清零前 {1}）· 撤销',
)
_UNDO_BAR_TRANSLATIONS = {
    'zh-TW': ('{0} 已清零（清零前 {1}）· 撤銷',),
    'en': ('{0} reset (was {1}) · Undo',),
    'de': ('{0} zurückgesetzt (vorher {1}) · Rückgängig',),
    'ja': ('{0} をリセット（以前は {1}）· 元に戻す',),
    'th': ('{0} ถูกล้างแล้ว (ก่อนหน้า {1}) · ยกเลิก',),
    'es': ('{0} restablecido (antes {1}) · Deshacer',),
    'ko': ('{0} 초기화됨 (이전 {1}) · 실행 취소',),
}
assert len(_UNDO_BAR_KEYS) == len(_UNDO_BAR_TRANSLATIONS['zh-TW'])
for _code, _values in _UNDO_BAR_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_UNDO_BAR_KEYS, _values))

# ---------------------------------------------------------------------------
# 顶栏骨架文案（任务书第 1 节）。
# ---------------------------------------------------------------------------
_SKELETON_KEYS = ('SETUP',)
# SETUP 作为专有页名保留原文（各语言一致），但登记进目录避免看门狗漏检。
_SKELETON_TRANSLATIONS = {
    'zh-TW': ('SETUP',),
    'en': ('SETUP',),
    'de': ('SETUP',),
    'ja': ('SETUP',),
    'th': ('SETUP',),
    'es': ('SETUP',),
    'ko': ('SETUP',),
}
for _code, _values in _SKELETON_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_SKELETON_KEYS, _values))

# 昼夜切换 tooltip（顶栏）。
_DAYNIGHT_TIP_KEYS = ('昼夜 · {0}',)
_DAYNIGHT_TIP_TRANSLATIONS = {
    'zh-TW': ('晝夜 · {0}',),
    'en': ('Day/Night · {0}',),
    'de': ('Tag/Nacht · {0}',),
    'ja': ('昼/夜 · {0}',),
    'th': ('กลางวัน/กลางคืน · {0}',),
    'es': ('Día/Noche · {0}',),
    'ko': ('낮/밤 · {0}',),
}
for _code, _values in _DAYNIGHT_TIP_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_DAYNIGHT_TIP_KEYS, _values))

# ---------------------------------------------------------------------------
# 日志页三分类 + SETUP 客户端接入（任务书第 7/8 节）。
# ---------------------------------------------------------------------------
_LOGS_SETUP_KEYS = (
    '已为你化解波动',
    '本期 Agent 未受打扰',
    '限流 {0} · 超时 {1} · 临时故障 {2}',
    '本期无错误',
    '已自动化解 {0}',
    '已告知 Agent {0}',
    '需你处理 {0}',
    '客户端接入',
    '接入开关在工作台顶部；Codex 退出接入后自动还原原生配置。',
    '已接入',
    '未接入',
    '独立选择模型 / 跟随 Relay 选择；退出后自动还原原生配置。',
    '配置完好，未检测到被其他程序改动。',
    '通过本地网关接入；模型选择跟随 Relay 或独立设置。',
    'Claude Code 以 Relay 为上游时接入；未接入时使用官方配置。',
)
_LOGS_SETUP_TRANSLATIONS = {
    'zh-TW': ('已為你化解波動', '本期 Agent 未受打擾', '限流 {0} · 逾時 {1} · 臨時故障 {2}',
              '本期無錯誤', '已自動化解 {0}', '已告知 Agent {0}', '需你處理 {0}',
              '用戶端接入', '接入開關在工作台頂部；Codex 退出接入後自動還原原生配置。',
              '已接入', '未接入', '獨立選擇模型 / 跟隨 Relay 選擇；退出後自動還原原生配置。',
              '配置完好，未檢測到被其他程式改動。', '透過本地閘道接入；模型選擇跟隨 Relay 或獨立設定。',
              'Claude Code 以 Relay 為上游時接入；未接入時使用官方配置。'),
    'en': ('Fluctuations resolved for you', 'No disturbance to your Agent this period',
           'Rate-limited {0} · Timeout {1} · Transient {2}', 'No errors this period',
           'Auto-resolved {0}', 'Agent notified {0}', 'Needs your attention {0}',
           'Client access', 'Access switches are at the top of the dashboard; Codex restores its native config after disconnect.',
           'Connected', 'Not connected', 'Choose a model independently / follow the Relay selection; native config is restored on disconnect.',
           'Config intact; no external modification detected.', 'Connected via the local gateway; model selection follows Relay or is set independently.',
           'Claude Code connects with Relay as upstream; otherwise the official config is used.'),
    'de': ('Für dich behobene Schwankungen', 'In diesem Zeitraum keine Störung für deinen Agent',
           'Ratenlimit {0} · Zeitüberschreitung {1} · Vorübergehend {2}', 'Keine Fehler in diesem Zeitraum',
           'Automatisch behoben {0}', 'Agent informiert {0}', 'Braucht deine Aufmerksamkeit {0}',
           'Client-Zugang', 'Zugangsschalter oben im Dashboard; Codex stellt die native Konfiguration nach dem Trennen wieder her.',
           'Verbunden', 'Nicht verbunden', 'Modell unabhängig wählen / der Relay-Auswahl folgen; native Konfiguration wird beim Trennen wiederhergestellt.',
           'Konfiguration intakt; keine externen Änderungen erkannt.', 'Über das lokale Gateway verbunden; Modellauswahl folgt Relay oder ist unabhängig.',
           'Claude Code verbindet sich mit Relay als Upstream; andernfalls wird die offizielle Konfiguration verwendet.'),
    'ja': ('あなたのために解消した変動', '今期 Agent への妨げなし',
           'レート制限 {0} · タイムアウト {1} · 一時障害 {2}', '今期エラーなし',
           '自動解消 {0}', 'Agent に通知 {0}', '要対応 {0}',
           'クライアント接続', '接続スイッチはダッシュボード上部にあります。Codex は切断後にネイティブ設定へ自動復元します。',
           '接続済み', '未接続', 'モデルを個別選択 / Relay の選択に追従。切断後にネイティブ設定へ自動復元。',
           '設定は完全です。他プログラムによる改変は検出されませんでした。', 'ローカルゲートウェイ経由で接続。モデル選択は Relay 追従または個別設定。',
           'Claude Code は Relay をアップストリームとして接続。未接続時は公式設定を使用します。'),
    'th': ('ฟลักชูเอชันที่จัดการให้คุณ', 'ช่วงนี้ Agent ของคุณไม่ถูกรบกวน',
           'จำกัดอัตรา {0} · หมดเวลา {1} · ชั่วคราว {2}', 'ไม่มีข้อผิดพลาดในช่วงนี้',
           'แก้ให้อัตโนมัติ {0}', 'แจ้ง Agent แล้ว {0}', 'ต้องการให้คุณดำเนินการ {0}',
           'การเชื่อมต่อไคลเอนต์', 'สวิตช์เชื่อมต่ออยู่ด้านบนแดชบอร์ด Codex จะคืนค่าดั้งเดิมหลังยกเลิกเชื่อมต่อ',
           'เชื่อมต่อแล้ว', 'ยังไม่เชื่อมต่อ', 'เลือกโมเดลแยก / ตามการเลือกของ Relay ยกเลิกแล้วคืนค่าดั้งเดิม',
           'การตั้งค่าสมบูรณ์ ไม่พบการแก้ไขจากโปรแกรมอื่น', 'เชื่อมต่อผ่านเกตเวย์ภายใน การเลือกโมเดลตาม Relay หรือตั้งแยก',
           'Claude Code เชื่อมต่อโดยใช้ Relay เป็นอัปสตรีม หากไม่เชื่อมต่อจะใช้การตั้งค่าทางการ'),
    'es': ('Fluctuaciones resueltas para ti', 'Ninguna interrupción para tu Agent en este período',
           'Límite de tasa {0} · Tiempo de espera {1} · Transitorio {2}', 'Sin errores en este período',
           'Resuelto automáticamente {0}', 'Agent notificado {0}', 'Requiere tu atención {0}',
           'Acceso de clientes', 'Los interruptores de acceso están en la parte superior del panel; Codex restaura su configuración nativa al desconectar.',
           'Conectado', 'No conectado', 'Elige un modelo de forma independiente / sigue la selección de Relay; la configuración nativa se restaura al desconectar.',
           'Configuración intacta; no se detectaron modificaciones externas.', 'Conectado mediante la pasarela local; la selección del modelo sigue Relay o se establece de forma independiente.',
           'Claude Code se conecta con Relay como upstream; de lo contrario se usa la configuración oficial.'),
    'ko': ('당신을 위해 해소한 변동', '이번 기간 Agent 방해 없음',
           '속도 제한 {0} · 시간 초과 {1} · 일시적 장애 {2}', '이번 기간 오류 없음',
           '자동 해소 {0}', 'Agent에 알림 {0}', '주의 필요 {0}',
           '클라이언트 연결', '연결 스위치는 대시보드 상단에 있습니다. Codex는 연결 해제 후 원래 설정을 자동 복원합니다.',
           '연결됨', '연결 안 됨', '모델 독립 선택 / Relay 선택 따르기; 해제 후 원래 설정 자동 복원.',
           '설정 완전함. 다른 프로그램 변경 감지 안 됨.', '로컬 게이트웨이로 연결됨. 모델 선택은 Relay 따르기 또는 독립 설정.',
           'Claude Code는 Relay를 업스트림으로 연결합니다. 미연결 시 공식 설정을 사용합니다.'),
}
assert len(_LOGS_SETUP_KEYS) == len(_LOGS_SETUP_TRANSLATIONS['zh-TW'])
for _code, _values in _LOGS_SETUP_TRANSLATIONS.items():
    TRANSLATIONS[_code].update(zip(_LOGS_SETUP_KEYS, _values))

# ---- 0.9 版式新增文案（工作台 Hero / Trip 单卡 / 模型渠道 / 日志三分类 / SETUP）
_EXTRA = {
    'API Key 与本地令牌经 DPAPI 加密；正文不保存，推理摘要短期缓存。': {
        'zh-TW': 'API Key 與本機權杖經 DPAPI 加密；正文不儲存，推理摘要短期快取。',
        'en': 'API keys and the local token are DPAPI-encrypted; bodies are not stored, reasoning text is cached briefly.',
        'de': 'API-Schlüssel und lokales Token sind DPAPI-verschlüsselt; Inhalte werden nicht gespeichert, Denktext kurz zwischengespeichert.',
        'ja': 'APIキーとローカルトークンはDPAPIで暗号化。本文は保存せず、推論テキストは短期間キャッシュします。',
        'ko': 'API 키와 로컬 토큰은 DPAPI로 암호화됩니다. 본문은 저장하지 않으며 추론 텍스트만 짧게 캐시합니다.',
        'es': 'Las claves API y el token local usan DPAPI; los cuerpos no se guardan y el texto de razonamiento se cachea brevemente.',
        'th': 'คีย์ API และโทเคนในเครื่องเข้ารหัสด้วย DPAPI ไม่บันทึกเนื้อหา แคชข้อความการคิดชั่วคราว',
    },
    'Codex CLI': {
        'zh-TW': 'Codex CLI',
        'en': 'Codex CLI',
        'de': 'Codex CLI',
        'ja': 'Codex CLI',
        'ko': 'Codex CLI',
        'es': 'Codex CLI',
        'th': 'Codex CLI',
    },
    'Claude Code': {
        'zh-TW': 'Claude Code',
        'en': 'Claude Code',
        'de': 'Claude Code',
        'ja': 'Claude Code',
        'ko': 'Claude Code',
        'es': 'Claude Code',
        'th': 'Claude Code',
    },
    'Codex 与 Claude Code 各自独立，互不干扰': {
        'zh-TW': 'Codex 與 Claude Code 各自獨立，互不干擾',
        'en': 'Codex and Claude Code are independent and do not affect each other',
        'de': 'Codex und Claude Code sind unabhängig und beeinflussen sich nicht',
        'ja': 'Codex と Claude Code は独立しており、互いに影響しません',
        'ko': 'Codex와 Claude Code는 서로 독립적이며 영향을 주지 않습니다',
        'es': 'Codex y Claude Code son independientes y no se afectan entre sí',
        'th': 'Codex และ Claude Code แยกจากกันและไม่รบกวนกัน',
    },
    'Codex 退出后自动还原原生配置': {
        'zh-TW': 'Codex 退出後自動還原原生設定',
        'en': 'Native config is restored after Codex exits',
        'de': 'Nach dem Beenden von Codex wird die Originalkonfiguration wiederhergestellt',
        'ja': 'Codex の終了後に元の設定へ自動で戻します',
        'ko': 'Codex가 종료되면 원래 설정으로 자동 복원됩니다',
        'es': 'La configuración original se restaura al cerrar Codex',
        'th': 'การตั้งค่าเดิมจะถูกคืนค่าอัตโนมัติเมื่อ Codex ปิด',
    },
    'GitHub 仓库': {
        'zh-TW': 'GitHub 儲存庫',
        'en': 'GitHub repository',
        'de': 'GitHub-Repository',
        'ja': 'GitHub リポジトリ',
        'ko': 'GitHub 저장소',
        'es': 'Repositorio de GitHub',
        'th': 'ที่เก็บ GitHub',
    },
    'Relay 已关闭': {
        'zh-TW': 'Relay 已關閉',
        'en': 'Relay is off',
        'de': 'Relay ist aus',
        'ja': 'Relay は停止中',
        'ko': 'Relay 꺼짐',
        'es': 'Relay está apagado',
        'th': 'Relay ปิดอยู่',
    },
    'Relay 运行中': {
        'zh-TW': 'Relay 執行中',
        'en': 'Relay is running',
        'de': 'Relay läuft',
        'ja': 'Relay 稼働中',
        'ko': 'Relay 실행 중',
        'es': 'Relay en marcha',
        'th': 'Relay กำลังทำงาน',
    },
    'TRIP {0}': {
        'zh-TW': 'TRIP {0}',
        'en': 'TRIP {0}',
        'de': 'TRIP {0}',
        'ja': 'TRIP {0}',
        'ko': 'TRIP {0}',
        'es': 'TRIP {0}',
        'th': 'TRIP {0}',
    },
    'Token 使用量': {
        'zh-TW': 'Token 使用量',
        'en': 'Token usage',
        'de': 'Token-Nutzung',
        'ja': 'Token 使用量',
        'ko': 'Token 사용량',
        'es': 'Uso de tokens',
        'th': 'การใช้ Token',
    },
    'Trip 账本': {
        'zh-TW': 'Trip 帳本',
        'en': 'Trip ledger',
        'de': 'Trip-Kontobuch',
        'ja': 'Trip 台帳',
        'ko': 'Trip 장부',
        'es': 'Libro de Trip',
        'th': 'สมุดบัญชี Trip',
    },
    '{0} 个渠道 · 加权': {
        'zh-TW': '{0} 個通路 · 加權',
        'en': '{0} channels · weighted',
        'de': '{0} Kanäle · gewichtet',
        'ja': '{0} チャネル · 重み付き',
        'ko': '채널 {0}개 · 가중',
        'es': '{0} canales · ponderado',
        'th': '{0} ช่องทาง · ถ่วงน้ำหนัก',
    },
    '{0}{1}% {2}': {
        'zh-TW': '{0}{1}% {2}',
        'en': '{0}{1}% {2}',
        'de': '{0}{1}% {2}',
        'ja': '{0}{1}% {2}',
        'ko': '{0}{1}% {2}',
        'es': '{0}{1}% {2}',
        'th': '{0}{1}% {2}',
    },
    '一个接入时，另一侧退出不会停止共享网关': {
        'zh-TW': '一個接入時，另一側退出不會停止共享閘道',
        'en': 'When one is connected, quitting the other does not stop the shared gateway',
        'de': 'Ist eines verbunden, stoppt das Beenden des anderen das gemeinsame Gateway nicht',
        'ja': '片方が接続中なら、もう片方が終了しても共有ゲートウェイは停止しません',
        'ko': '한쪽이 연결된 상태에서 다른 쪽을 종료해도 공유 게이트웨이는 중지되지 않습니다',
        'es': 'Con una conexión activa, cerrar la otra no detiene la puerta de enlace compartida',
        'th': 'เมื่อฝั่งหนึ่งเชื่อมต่ออยู่ การปิดอีกฝั่งจะไม่หยุดเกตเวย์ที่ใช้ร่วมกัน',
    },
    '上次检查：{0}': {
        'zh-TW': '上次檢查：{0}',
        'en': 'Last checked: {0}',
        'de': 'Zuletzt geprüft: {0}',
        'ja': '前回の確認：{0}',
        'ko': '마지막 확인: {0}',
        'es': 'Última comprobación: {0}',
        'th': 'ตรวจสอบล่าสุด: {0}',
    },
    '下次启动生效；已接入的客户端需重新接入。': {
        'zh-TW': '下次啟動生效；已接入的用戶端需重新接入。',
        'en': 'Takes effect on the next start; connected clients must reconnect.',
        'de': 'Wirkt beim nächsten Start; verbundene Clients müssen neu verbinden.',
        'ja': '次回起動時に有効になります。接続済みのクライアントは再接続が必要です。',
        'ko': '다음 시작 시 적용됩니다. 연결된 클라이언트는 다시 연결해야 합니다.',
        'es': 'Se aplica en el próximo inicio; los clientes conectados deben reconectarse.',
        'th': 'มีผลเมื่อเริ่มครั้งถัดไป ไคลเอนต์ที่เชื่อมต่ออยู่ต้องเชื่อมต่อใหม่',
    },
    '为提示新版本，Relay 每天启动时最多访问一次更新服务。服务器会看到你的 IP 与软件版本，用于估算使用人数。': {
        'zh-TW': '為提示新版本，Relay 每天啟動時最多造訪一次更新服務。伺服器會看到你的 IP 與軟體版本，用於估算使用人數。',
        'en': 'To announce new versions, Relay contacts the update service at most once per day at startup. The server sees your IP and version, used only to estimate the user count.',
        'de': 'Um neue Versionen anzukündigen, kontaktiert Relay den Update-Dienst beim Start höchstens einmal täglich. Der Server sieht Ihre IP und Version, nur zur Schätzung der Nutzerzahl.',
        'ja': '新しいバージョンの通知のため、Relay は起動時に 1 日 1 回まで更新サービスへ接続します。サーバーは IP とバージョンを参照し、利用者数の推定にのみ使用します。',
        'ko': '새 버전 알림을 위해 Relay는 시작 시 하루 최대 한 번 업데이트 서비스에 접속합니다. 서버는 IP와 버전을 확인하며 사용자 수 추정에만 사용합니다.',
        'es': 'Para avisar de nuevas versiones, Relay contacta el servicio de actualización como máximo una vez al día al iniciar. El servidor ve tu IP y versión, solo para estimar el número de usuarios.',
        'th': 'เพื่อแจ้งเวอร์ชันใหม่ Relay จะติดต่อบริการอัปเดตไม่เกินวันละครั้งตอนเริ่มทำงาน เซิร์ฟเวอร์จะเห็น IP และเวอร์ชันของคุณ เพื่อใช้ประมาณจำนวนผู้ใช้เท่านั้น',
    },
    '仅本地统计': {
        'zh-TW': '僅本機統計',
        'en': 'Local stats only',
        'de': 'Nur lokale Statistik',
        'ja': 'ローカル統計のみ',
        'ko': '로컬 통계만',
        'es': 'Solo estadísticas locales',
        'th': 'สถิติในเครื่องเท่านั้น',
    },
    '仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。\n\n不收集请求或响应正文、文件、代码、密钥、IP、原始错误和逐请求记录。\n\n上传包含随机安装标识、版本、供应商类别、模型、活跃分钟及官方/中转/未知渠道分类，不上传实际地址。仅正常退出时尝试一次；失败或拒绝保留批次，下次退出重试。\n\n国家/地区仅由服务器依据网络连接粗略判断。': {
        'zh-TW': '僅累計每日呼叫、成功/錯誤、Token、固定延遲區間、標準錯誤類別和回退次數。\n\n不收集請求或回應正文、檔案、程式碼、金鑰、IP、原始錯誤和逐請求記錄。\n\n上傳包含隨機安裝識別、版本、供應商類別、模型、活躍分鐘及官方/中轉/未知通路分類，不上傳實際位址。僅正常退出時嘗試一次；失敗或拒絕保留批次，下次退出重試。\n\n國家/地區僅由伺服器依據網路連線粗略判斷。',
        'en': 'Only daily call counts, success/errors, tokens, fixed latency buckets, standard error categories and fallback counts are accumulated.\n\nRequest or response bodies, files, code, keys, IPs, raw errors and per-request records are never collected.\n\nUploads contain a random install id, version, provider category, model, active minutes and official/relay/unknown channel class — never the actual address. Upload is attempted once on normal exit; failures are kept for the next exit. Country is only coarsely inferred by the server from the connection.',
        'de': 'Nur tägliche Aufrufzahlen, Erfolg/Fehler, Token, feste Latenzbereiche, Standardfehlerkategorien und Fallback-Zahlen werden summiert.\n\nAnfrage- oder Antworttexte, Dateien, Code, Schlüssel, IPs, Rohfehler und Einzelanfragen werden nie erfasst.\n\nUploads enthalten eine zufällige Installations-ID, Version, Anbieterkategorie, Modell, aktive Minuten und die Kanalart (offiziell/Relay/unbekannt) – nie die echte Adresse. Der Upload wird beim normalen Beenden einmal versucht; Fehlschläge bleiben bis zum nächsten Beenden. Das Land schätzt der Server nur grob anhand der Verbindung.',
        'ja': '累計するのは日次の呼び出し回数、成功/エラー、Token、固定の遅延区分、標準エラー分類、フォールバック回数のみです。\n\nリクエストや応答の本文、ファイル、コード、鍵、IP、生のエラー、リクエスト単位の記録は収集しません。\n\nアップロードにはランダムなインストール ID、バージョン、プロバイダ分類、モデル、アクティブ時間、チャネル区分（公式/リレー/不明）が含まれ、実際のアドレスは含みません。正常終了時に一度だけ試行し、失敗分は次回終了時に再試行します。国・地域はサーバーが接続状況から大まかに推定するのみです。',
        'ko': '일별 호출 수, 성공/오류, Token, 고정 지연 구간, 표준 오류 분류, 대체 횟수만 누적합니다.\n\n요청·응답 본문, 파일, 코드, 키, IP, 원시 오류, 요청별 기록은 수집하지 않습니다.\n\n업로드에는 무작위 설치 ID, 버전, 공급자 분류, 모델, 활성 분, 채널 구분(공식/릴레이/알 수 없음)이 포함되며 실제 주소는 포함되지 않습니다. 정상 종료 시 한 번 시도하고, 실패분은 다음 종료 시 재시도합니다. 국가/지역은 서버가 연결 정보로 대략 추정할 뿐입니다.',
        'es': 'Solo se acumulan llamadas diarias, éxitos/errores, tokens, rangos fijos de latencia, categorías de error estándar y recuentos de reserva.\n\nNunca se recogen cuerpos de solicitud o respuesta, archivos, código, claves, IP, errores en bruto ni registros por solicitud.\n\nLa carga contiene un id de instalación aleatorio, versión, categoría de proveedor, modelo, minutos activos y clase de canal (oficial/relay/desconocido); nunca la dirección real. Se intenta una vez al salir normalmente; los fallos se conservan para el siguiente cierre. El país solo se estima de forma aproximada por el servidor según la conexión.',
        'th': 'จะสะสมเฉพาะจำนวนการเรียกต่อวัน ความสำเร็จ/ข้อผิดพลาด Token ช่วงเวลาตอบสนองคงที่ หมวดข้อผิดพลาดมาตรฐาน และจำนวนการสำรอง\n\nไม่เก็บเนื้อหาคำขอหรือการตอบกลับ ไฟล์ โค้ด คีย์ IP ข้อผิดพลาดดิบ หรือบันทึกรายคำขอ\n\nการอัปโหลดมีรหัสติดตั้งแบบสุ่ม เวอร์ชัน หมวดผู้ให้บริการ โมเดล นาทีที่ใช้งาน และประเภทช่องทาง (ทางการ/รีเลย์/ไม่ทราบ) ไม่มีที่อยู่จริง จะพยายามอัปโหลดครั้งเดียวเมื่อออกตามปกติ หากล้มเหลวจะเก็บไว้ลองใหม่ครั้งถัดไป ประเทศประมาณจากฝั่งเซิร์ฟเวอร์ตามการเชื่อมต่อเท่านั้น',
    },
    '仅累计调用与用量摘要；不记录 Prompt、回复、正文、代码、密钥或 IP。上传需你明确同意，仅正常退出时尝试一次。': {
        'zh-TW': '僅累計呼叫與用量摘要；不記錄 Prompt、回覆、正文、程式碼、金鑰或 IP。上傳需你明確同意，僅正常退出時嘗試一次。',
        'en': 'Only call and usage summaries are accumulated; prompts, replies, bodies, code, keys and IPs are never recorded. Upload requires your explicit consent and is attempted once on normal exit.',
        'de': 'Nur Aufruf- und Nutzungssummen werden gesammelt; Prompts, Antworten, Texte, Code, Schlüssel und IPs werden nie erfasst. Der Upload erfordert Ihre ausdrückliche Zustimmung und wird beim normalen Beenden einmal versucht.',
        'ja': '累計するのは呼び出しと使用量の要約のみです。プロンプト、応答、本文、コード、鍵、IP は記録しません。アップロードには明示的な同意が必要で、正常終了時に一度だけ試行します。',
        'ko': '호출과 사용량 요약만 누적하며 프롬프트, 응답, 본문, 코드, 키, IP는 기록하지 않습니다. 업로드는 명시적 동의가 필요하며 정상 종료 시 한 번 시도합니다.',
        'es': 'Solo se acumulan resúmenes de llamadas y uso; nunca se registran prompts, respuestas, cuerpos, código, claves ni IP. La carga requiere tu consentimiento explícito y se intenta una vez al salir normalmente.',
        'th': 'สะสมเฉพาะสรุปการเรียกและปริมาณการใช้ ไม่บันทึกพรอมป์ต์ คำตอบ เนื้อหา โค้ด คีย์ หรือ IP การอัปโหลดต้องได้รับความยินยอมชัดเจนและลองครั้งเดียวเมื่อออกตามปกติ',
    },
    '今日用量': {
        'zh-TW': '今日用量',
        'en': "Today's usage",
        'de': 'Heutige Nutzung',
        'ja': '本日の使用量',
        'ko': '오늘 사용량',
        'es': 'Uso de hoy',
        'th': 'การใช้วันนี้',
    },
    '今日请求数': {
        'zh-TW': '今日請求數',
        'en': 'Requests today',
        'de': 'Anfragen heute',
        'ja': '本日のリクエスト数',
        'ko': '오늘 요청 수',
        'es': 'Solicitudes de hoy',
        'th': 'จำนวนคำขอวันนี้',
    },
    '健康': {
        'zh-TW': '健康',
        'en': 'Healthy',
        'de': 'Gesund',
        'ja': '正常',
        'ko': '정상',
        'es': 'Correcto',
        'th': 'ปกติ',
    },
    '共 8 种语言': {
        'zh-TW': '共 8 種語言',
        'en': '8 languages',
        'de': '8 Sprachen',
        'ja': '8 言語',
        'ko': '8개 언어',
        'es': '8 idiomas',
        'th': '8 ภาษา',
    },
    '共 {0} 个模型配置，已合并为 {1} 个模型组': {
        'zh-TW': '共 {0} 個模型設定，已合併為 {1} 個模型組',
        'en': '{0} profiles, merged into {1} model groups',
        'de': '{0} Profile, zusammengefasst zu {1} Modellgruppen',
        'ja': '{0} 件の設定を {1} 個のモデルグループに統合',
        'ko': '모델 설정 {0}개, {1}개 그룹으로 통합',
        'es': '{0} perfiles, agrupados en {1} grupos de modelos',
        'th': 'โปรไฟล์ {0} รายการ รวมเป็น {1} กลุ่มโมเดล',
    },
    '共 {0} 条记录': {
        'zh-TW': '共 {0} 筆記錄',
        'en': '{0} records',
        'de': '{0} Einträge',
        'ja': '{0} 件の記録',
        'ko': '기록 {0}건',
        'es': '{0} registros',
        'th': '{0} รายการ',
    },
    '写入 BASE_URL、令牌与模型三项，关闭开关即还原。': {
        'zh-TW': '寫入 BASE_URL、權杖與模型三項，關閉開關即還原。',
        'en': 'Writes BASE_URL, token and model; turning the switch off restores them.',
        'de': 'Schreibt BASE_URL, Token und Modell; beim Ausschalten wird zurückgesetzt.',
        'ja': 'BASE_URL・トークン・モデルの 3 項目を書き込み、スイッチを切ると元に戻します。',
        'ko': 'BASE_URL, 토큰, 모델 세 항목을 쓰며 스위치를 끄면 복원됩니다.',
        'es': 'Escribe BASE_URL, token y modelo; al apagar el interruptor se restaura.',
        'th': 'เขียน BASE_URL โทเคน และโมเดล ปิดสวิตช์แล้วจะคืนค่าเดิม',
    },
    '冷却中 · 约 {0} 分钟后可再试': {
        'zh-TW': '冷卻中 · 約 {0} 分鐘後可再試',
        'en': 'Cooling down · retry in about {0} min',
        'de': 'Abkühlung · erneut in etwa {0} Min.',
        'ja': 'クールダウン中 · 約 {0} 分後に再試行',
        'ko': '쿨다운 중 · 약 {0}분 후 재시도',
        'es': 'En enfriamiento · reintentar en unos {0} min',
        'th': 'กำลังคูลดาวน์ · ลองใหม่ในอีกประมาณ {0} นาที',
    },
    '分段名称': {
        'zh-TW': '分段名稱',
        'en': 'Segment name',
        'de': 'Segmentname',
        'ja': '区間名',
        'ko': '구간 이름',
        'es': 'Nombre del tramo',
        'th': 'ชื่อช่วง',
    },
    '动效': {
        'zh-TW': '動效',
        'en': 'Motion',
        'de': 'Bewegung',
        'ja': '動き',
        'ko': '움직임',
        'es': 'Movimiento',
        'th': 'แอนิเมชัน',
    },
    '化解波动': {
        'zh-TW': '化解波動',
        'en': 'Waves absorbed',
        'de': 'Geglättete Störungen',
        'ja': '吸収した揺らぎ',
        'ko': '완화한 변동',
        'es': 'Ondas absorbidas',
        'th': 'คลื่นที่จัดการแล้ว',
    },
    '区间': {
        'zh-TW': '區間',
        'en': 'Range',
        'de': 'Zeitraum',
        'ja': '区間',
        'ko': '구간',
        'es': 'Rango',
        'th': 'ช่วง',
    },
    '单渠道': {
        'zh-TW': '單通路',
        'en': 'Single channel',
        'de': 'Einzelkanal',
        'ja': '単一チャネル',
        'ko': '단일 채널',
        'es': 'Canal único',
        'th': 'ช่องทางเดียว',
    },
    '只下载图片，不执行任何内容；断网时使用内置皮肤。': {
        'zh-TW': '只下載圖片，不執行任何內容；斷網時使用內建皮膚。',
        'en': 'Downloads images only, never executes anything; the built-in skin is used offline.',
        'de': 'Lädt nur Bilder, führt nichts aus; offline wird die eingebaute Haut verwendet.',
        'ja': '画像のみを取得し、何も実行しません。オフライン時は内蔵スキンを使用します。',
        'ko': '이미지만 내려받으며 아무것도 실행하지 않습니다. 오프라인에서는 내장 스킨을 사용합니다.',
        'es': 'Solo descarga imágenes, nunca ejecuta nada; sin conexión se usa el tema integrado.',
        'th': 'ดาวน์โหลดเฉพาะรูปภาพ ไม่รันสิ่งใด ใช้ออร์ฟไลน์จะใช้สกินในตัว',
    },
    '可随时清零的分段计数': {
        'zh-TW': '可隨時歸零的分段計數',
        'en': 'Segmented counters you can reset anytime',
        'de': 'Segmentzähler, jederzeit zurücksetzbar',
        'ja': 'いつでもリセットできる区間カウント',
        'ko': '언제든 초기화할 수 있는 구간 카운터',
        'es': 'Contadores por tramo que puedes reiniciar',
        'th': 'ตัวนับแบบแบ่งช่วงที่รีเซ็ตได้ทุกเมื่อ',
    },
    '同一模型的多个渠道按权重随机选择，失败后冷却 60 秒再试；拖动把手可调整渠道顺序。': {
        'zh-TW': '同一模型的多個通路按權重隨機選擇，失敗後冷卻 60 秒再試；拖曳把手可調整通路順序。',
        'en': 'Channels of one model are picked at random by weight; a failed channel cools down for 60 seconds. Drag the handle to reorder.',
        'de': 'Kanäle eines Modells werden gewichtet zufällig gewählt; ein fehlgeschlagener Kanal kühlt 60 Sekunden ab. Ziehen Sie am Griff, um die Reihenfolge zu ändern.',
        'ja': '同じモデルの複数チャネルは重みに応じてランダムに選ばれ、失敗したチャネルは 60 秒間クールダウンします。ハンドルをドラッグして順序を変更できます。',
        'ko': '같은 모델의 채널은 가중치에 따라 무작위로 선택되며, 실패한 채널은 60초 동안 쿨다운됩니다. 손잡이를 끌어 순서를 바꿀 수 있습니다.',
        'es': 'Los canales de un modelo se eligen al azar por peso; el que falla se enfría 60 segundos. Arrastra el asa para reordenar.',
        'th': 'ช่องทางของโมเดลเดียวกันจะถูกสุ่มตามน้ำหนัก ช่องทางที่ล้มเหลวจะคูลดาวน์ 60 วินาที ลากที่จับเพื่อจัดลำดับ',
    },
    '完整': {
        'zh-TW': '完整',
        'en': 'Full',
        'de': 'Vollständig',
        'ja': 'フル',
        'ko': '전체',
        'es': 'Completo',
        'th': 'เต็ม',
    },
    '官方网站': {
        'zh-TW': '官方網站',
        'en': 'Website',
        'de': 'Website',
        'ja': '公式サイト',
        'ko': '공식 웹사이트',
        'es': 'Sitio web',
        'th': 'เว็บไซต์',
    },
    '对外截图请遮挡用户名。': {
        'zh-TW': '對外截圖請遮蔽使用者名稱。',
        'en': 'Mask your user name in public screenshots.',
        'de': 'Verdecken Sie Ihren Benutzernamen in öffentlichen Screenshots.',
        'ja': '外部に共有するスクリーンショットではユーザー名を隠してください。',
        'ko': '외부 공유용 스크린샷에서는 사용자 이름을 가려 주세요.',
        'es': 'Oculta tu nombre de usuario en capturas públicas.',
        'th': 'โปรดปิดบังชื่อผู้ใช้ในภาพหน้าจอที่เผยแพร่',
    },
    '导出': {
        'zh-TW': '匯出',
        'en': 'Export',
        'de': 'Exportieren',
        'ja': 'エクスポート',
        'ko': '내보내기',
        'es': 'Exportar',
        'th': 'ส่งออก',
    },
    '导出 CSV': {
        'zh-TW': '匯出 CSV',
        'en': 'Export CSV',
        'de': 'CSV exportieren',
        'ja': 'CSV を書き出す',
        'ko': 'CSV 내보내기',
        'es': 'Exportar CSV',
        'th': 'ส่งออก CSV',
    },
    '导出日志': {
        'zh-TW': '匯出日誌',
        'en': 'Export logs',
        'de': 'Protokolle exportieren',
        'ja': 'ログを書き出す',
        'ko': '로그 내보내기',
        'es': 'Exportar registros',
        'th': 'ส่งออกบันทึก',
    },
    '导出账本': {
        'zh-TW': '匯出帳本',
        'en': 'Export ledger',
        'de': 'Kontobuch exportieren',
        'ja': '台帳を書き出す',
        'ko': '장부 내보내기',
        'es': 'Exportar libro',
        'th': 'ส่งออกสมุดบัญชี',
    },
    '将移除 Relay 写入的接入配置，恢复接入前的设置。': {
        'zh-TW': '將移除 Relay 寫入的接入設定，恢復接入前的設定。',
        'en': 'Removes the connection settings written by Relay and restores the previous configuration.',
        'de': 'Entfernt die von Relay geschriebenen Verbindungseinstellungen und stellt die vorherige Konfiguration wieder her.',
        'ja': 'Relay が書き込んだ接続設定を削除し、接続前の設定に戻します。',
        'ko': 'Relay가 기록한 연결 설정을 제거하고 이전 설정으로 되돌립니다.',
        'es': 'Elimina la configuración escrita por Relay y restaura la anterior.',
        'th': 'จะลบการตั้งค่าการเชื่อมต่อที่ Relay เขียนไว้และคืนค่าก่อนหน้านี้',
    },
    '已使用内置皮肤': {
        'zh-TW': '已使用內建皮膚',
        'en': 'Built-in skin is in use',
        'de': 'Eingebaute Haut wird verwendet',
        'ja': '内蔵スキンを使用中',
        'ko': '내장 스킨 사용 중',
        'es': 'Se usa el tema integrado',
        'th': 'ใช้สกินในตัวแล้ว',
    },
    '已告知 Agent': {
        'zh-TW': '已告知 Agent',
        'en': 'Reported to Agent',
        'de': 'An Agent gemeldet',
        'ja': 'Agent に通知済み',
        'ko': 'Agent에 알림',
        'es': 'Informado al Agent',
        'th': 'แจ้ง Agent แล้ว',
    },
    '已导出 {0} 条记录': {
        'zh-TW': '已匯出 {0} 筆記錄',
        'en': 'Exported {0} records',
        'de': '{0} Einträge exportiert',
        'ja': '{0} 件を書き出しました',
        'ko': '{0}건을 내보냈습니다',
        'es': 'Se exportaron {0} registros',
        'th': 'ส่งออกแล้ว {0} รายการ',
    },
    '已自动化解': {
        'zh-TW': '已自動化解',
        'en': 'Auto-resolved',
        'de': 'Automatisch gelöst',
        'ja': '自動で解消',
        'ko': '자동 해결',
        'es': 'Resuelto automáticamente',
        'th': 'แก้ไขอัตโนมัติแล้ว',
    },
    '开机自动启动 Relay': {
        'zh-TW': '開機自動啟動 Relay',
        'en': 'Start Relay at login',
        'de': 'Relay bei der Anmeldung starten',
        'ja': 'ログイン時に Relay を起動',
        'ko': '로그인 시 Relay 시작',
        'es': 'Iniciar Relay al entrar',
        'th': 'เริ่ม Relay เมื่อเข้าสู่ระบบ',
    },
    '开源说明：核心网关以源码发布；第三方组件与许可证见 docs。': {
        'zh-TW': '開源說明：核心閘道以原始碼發布；第三方元件與授權見 docs。',
        'en': 'Open source: the core gateway ships as source; third-party components and licenses are in docs.',
        'de': 'Open Source: Das Kern-Gateway wird als Quellcode ausgeliefert; Drittanbieter und Lizenzen siehe docs.',
        'ja': 'オープンソース：中核ゲートウェイはソースで提供されます。第三者コンポーネントとライセンスは docs を参照。',
        'ko': '오픈 소스: 핵심 게이트웨이는 소스로 배포됩니다. 서드파티 구성 요소와 라이선스는 docs를 참고하세요.',
        'es': 'Código abierto: la puerta de enlace principal se distribuye como código fuente; componentes y licencias de terceros en docs.',
        'th': 'โอเพนซอร์ส: เกตเวย์หลักเผยแพร่เป็นซอร์สโค้ด คอมโพเนนต์และไลเซนส์ของบุคคลที่สามดูใน docs',
    },
    '总 Token': {
        'zh-TW': '總 Token',
        'en': 'Total tokens',
        'de': 'Token gesamt',
        'ja': '合計 Token',
        'ko': '총 Token',
        'es': 'Tokens totales',
        'th': 'Token รวม',
    },
    '恢复 Claude Code 配置？': {
        'zh-TW': '恢復 Claude Code 設定？',
        'en': 'Restore the Claude Code configuration?',
        'de': 'Claude-Code-Konfiguration wiederherstellen?',
        'ja': 'Claude Code の設定を戻しますか？',
        'ko': 'Claude Code 설정을 복원할까요?',
        'es': '¿Restaurar la configuración de Claude Code?',
        'th': 'คืนค่าการตั้งค่า Claude Code หรือไม่?',
    },
    '恢复为当前区间': {
        'zh-TW': '恢復為目前區間',
        'en': 'Restore as current range',
        'de': 'Als aktuellen Zeitraum wiederherstellen',
        'ja': '現在の区間として復元',
        'ko': '현재 구간으로 복원',
        'es': 'Restaurar como rango actual',
        'th': 'คืนค่าเป็นช่วงปัจจุบัน',
    },
    '恢复内置皮肤': {
        'zh-TW': '恢復內建皮膚',
        'en': 'Restore built-in skin',
        'de': 'Eingebaute Haut wiederherstellen',
        'ja': '内蔵スキンに戻す',
        'ko': '내장 스킨 복원',
        'es': 'Restaurar tema integrado',
        'th': 'คืนค่าสกินในตัว',
    },
    '恢复原配置': {
        'zh-TW': '恢復原設定',
        'en': 'Restore original',
        'de': 'Original wiederherstellen',
        'ja': '元の設定に戻す',
        'ko': '원래 설정 복원',
        'es': 'Restaurar original',
        'th': 'คืนค่าเดิม',
    },
    '打开文件夹': {
        'zh-TW': '開啟資料夾',
        'en': 'Open folder',
        'de': 'Ordner öffnen',
        'ja': 'フォルダーを開く',
        'ko': '폴더 열기',
        'es': 'Abrir carpeta',
        'th': 'เปิดโฟลเดอร์',
    },
    '拖动调整渠道顺序': {
        'zh-TW': '拖曳調整通路順序',
        'en': 'Drag to reorder channels',
        'de': 'Ziehen, um Kanäle zu ordnen',
        'ja': 'ドラッグでチャネル順を変更',
        'ko': '끌어서 채널 순서 변경',
        'es': 'Arrastra para reordenar canales',
        'th': 'ลากเพื่อจัดลำดับช่องทาง',
    },
    '接入方式': {
        'zh-TW': '接入方式',
        'en': 'Connection mode',
        'de': 'Verbindungsmodus',
        'ja': '接続方式',
        'ko': '연결 방식',
        'es': 'Modo de conexión',
        'th': 'รูปแบบการเชื่อมต่อ',
    },
    '新输入 {0}\u3000缓存读取 {1}\u3000缓存写入 {2}': {
        'zh-TW': '新輸入 {0}\u3000快取讀取 {1}\u3000快取寫入 {2}',
        'en': 'New input {0}\u3000Cache read {1}\u3000Cache write {2}',
        'de': 'Neue Eingabe {0}\u3000Cache gelesen {1}\u3000Cache geschrieben {2}',
        'ja': '新規入力 {0}\u3000キャッシュ読取 {1}\u3000キャッシュ書込 {2}',
        'ko': '새 입력 {0}\u3000캐시 읽기 {1}\u3000캐시 쓰기 {2}',
        'es': 'Entrada nueva {0}\u3000Lectura de caché {1}\u3000Escritura de caché {2}',
        'th': 'อินพุตใหม่ {0}\u3000อ่านแคช {1}\u3000เขียนแคช {2}',
    },
    '昼夜': {
        'zh-TW': '晝夜',
        'en': 'Day & night',
        'de': 'Tag & Nacht',
        'ja': '昼夜',
        'ko': '주야',
        'es': 'Día y noche',
        'th': 'กลางวันและกลางคืน',
    },
    '未接入 Relay，Claude Code 使用官方配置。': {
        'zh-TW': '未接入 Relay，Claude Code 使用官方設定。',
        'en': 'Not connected to Relay; Claude Code uses its official configuration.',
        'de': 'Nicht mit Relay verbunden; Claude Code nutzt die offizielle Konfiguration.',
        'ja': 'Relay に未接続。Claude Code は公式設定を使用します。',
        'ko': 'Relay에 연결되지 않았습니다. Claude Code는 공식 설정을 사용합니다.',
        'es': 'Sin conexión a Relay; Claude Code usa su configuración oficial.',
        'th': 'ยังไม่เชื่อมต่อ Relay Claude Code ใช้การตั้งค่าทางการ',
    },
    '未接入 Relay，Codex 使用原生配置。': {
        'zh-TW': '未接入 Relay，Codex 使用原生設定。',
        'en': 'Not connected to Relay; Codex uses its native configuration.',
        'de': 'Nicht mit Relay verbunden; Codex nutzt die native Konfiguration.',
        'ja': 'Relay に未接続。Codex は元の設定を使用します。',
        'ko': 'Relay에 연결되지 않았습니다. Codex는 기본 설정을 사용합니다.',
        'es': 'Sin conexión a Relay; Codex usa su configuración nativa.',
        'th': 'ยังไม่เชื่อมต่อ Relay Codex ใช้การตั้งค่าเดิม',
    },
    '未能修改开机自启设置': {
        'zh-TW': '未能修改開機自啟設定',
        'en': 'Could not change the startup setting',
        'de': 'Autostart-Einstellung konnte nicht geändert werden',
        'ja': '自動起動の設定を変更できませんでした',
        'ko': '자동 시작 설정을 변경하지 못했습니다',
        'es': 'No se pudo cambiar el inicio automático',
        'th': 'ไม่สามารถเปลี่ยนการตั้งค่าเริ่มอัตโนมัติ',
    },
    '未设置默认模型': {
        'zh-TW': '未設定預設模型',
        'en': 'No default model',
        'de': 'Kein Standardmodell',
        'ja': '既定モデル未設定',
        'ko': '기본 모델 없음',
        'es': 'Sin modelo predeterminado',
        'th': 'ยังไม่ได้ตั้งโมเดลเริ่มต้น',
    },
    '权重 {0}': {
        'zh-TW': '權重 {0}',
        'en': 'Weight {0}',
        'de': 'Gewicht {0}',
        'ja': '重み {0}',
        'ko': '가중치 {0}',
        'es': 'Peso {0}',
        'th': 'น้ำหนัก {0}',
    },
    '来路': {
        'zh-TW': '來源',
        'en': 'Source',
        'de': 'Quelle',
        'ja': '経路',
        'ko': '경로',
        'es': 'Origen',
        'th': 'ที่มา',
    },
    '查看全部': {
        'zh-TW': '查看全部',
        'en': 'View all',
        'de': 'Alle ansehen',
        'ja': 'すべて表示',
        'ko': '전체 보기',
        'es': 'Ver todo',
        'th': 'ดูทั้งหมด',
    },
    '查看将上传的内容': {
        'zh-TW': '查看將上傳的內容',
        'en': 'See what is uploaded',
        'de': 'Ansehen, was hochgeladen wird',
        'ja': 'アップロード内容を確認',
        'ko': '업로드 내용 보기',
        'es': 'Ver qué se sube',
        'th': 'ดูสิ่งที่จะอัปโหลด',
    },
    '模型配置保存在 microglow-relay-settings.json；用量记录文件不会自动清理。': {
        'zh-TW': '模型設定保存在 microglow-relay-settings.json；用量記錄檔不會自動清理。',
        'en': 'Profiles live in microglow-relay-settings.json; usage records are never cleaned automatically.',
        'de': 'Profile liegen in microglow-relay-settings.json; Nutzungsdaten werden nie automatisch gelöscht.',
        'ja': '設定は microglow-relay-settings.json に保存され、使用量の記録は自動削除されません。',
        'ko': '모델 설정은 microglow-relay-settings.json에 저장되며 사용 기록은 자동 정리되지 않습니다.',
        'es': 'Los perfiles están en microglow-relay-settings.json; los registros de uso no se borran automáticamente.',
        'th': 'โปรไฟล์เก็บใน microglow-relay-settings.json บันทึกการใช้งานจะไม่ถูกลบอัตโนมัติ',
    },
    '每天最多一次': {
        'zh-TW': '每天最多一次',
        'en': 'Once a day at most',
        'de': 'Höchstens einmal täglich',
        'ja': '1 日 1 回まで',
        'ko': '하루 최대 1회',
        'es': 'Como máximo una vez al día',
        'th': 'ไม่เกินวันละครั้ง',
    },
    '渠道': {
        'zh-TW': '通路',
        'en': 'Channels',
        'de': 'Kanäle',
        'ja': 'チャネル',
        'ko': '채널',
        'es': 'Canales',
        'th': 'ช่องทาง',
    },
    '渠道 {0}': {
        'zh-TW': '通路 {0}',
        'en': 'Channel {0}',
        'de': 'Kanal {0}',
        'ja': 'チャネル {0}',
        'ko': '채널 {0}',
        'es': 'Canal {0}',
        'th': 'ช่องทาง {0}',
    },
    '点击修改分段名称': {
        'zh-TW': '點擊修改分段名稱',
        'en': 'Click to rename this segment',
        'de': 'Klicken, um das Segment umzubenennen',
        'ja': 'クリックして区間名を変更',
        'ko': '클릭하여 구간 이름 변경',
        'es': 'Haz clic para renombrar el tramo',
        'th': 'คลิกเพื่อเปลี่ยนชื่อช่วง',
    },
    '版本、更新与数据': {
        'zh-TW': '版本、更新與資料',
        'en': 'Version, updates and data',
        'de': 'Version, Updates und Daten',
        'ja': 'バージョン・更新・データ',
        'ko': '버전, 업데이트, 데이터',
        'es': 'Versión, actualizaciones y datos',
        'th': 'เวอร์ชัน การอัปเดต และข้อมูล',
    },
    '皮肤与昼夜彼此独立，共 8 种组合': {
        'zh-TW': '皮膚與晝夜彼此獨立，共 8 種組合',
        'en': 'Skin and day/night are independent — 8 combinations',
        'de': 'Haut und Tag/Nacht sind unabhängig – 8 Kombinationen',
        'ja': 'スキンと昼夜は独立しており、8 通りの組み合わせがあります',
        'ko': '스킨과 주야는 독립적이며 8가지 조합이 있습니다',
        'es': 'Tema y día/noche son independientes: 8 combinaciones',
        'th': 'สกินและกลางวัน/กลางคืนแยกกัน รวม 8 แบบ',
    },
    '皮肤更新': {
        'zh-TW': '皮膚更新',
        'en': 'Skin updates',
        'de': 'Haut-Updates',
        'ja': 'スキン更新',
        'ko': '스킨 업데이트',
        'es': 'Actualización de temas',
        'th': 'อัปเดตสกิน',
    },
    '示意数据：错误去了哪里': {
        'zh-TW': '示意資料：錯誤去了哪裡',
        'en': 'Illustrative: where errors went',
        'de': 'Illustrativ: wohin Fehler gingen',
        'ja': '参考：エラーの行き先',
        'ko': '예시: 오류가 간 곳',
        'es': 'Ilustrativo: a dónde fueron los errores',
        'th': 'ตัวอย่าง: ข้อผิดพลาดไปที่ใด',
    },
    '窗口最小化或被遮挡时自动暂停；系统开启「减少动态效果」时自动静态': {
        'zh-TW': '視窗最小化或被遮擋時自動暫停；系統開啟「減少動態效果」時自動靜態',
        'en': 'Pauses when minimized or covered; static automatically when the system reduces motion',
        'de': 'Pausiert beim Minimieren oder Verdecken; statisch, wenn das System Bewegung reduziert',
        'ja': '最小化や他ウィンドウに隠れたときは一時停止し、システムの「視差効果を減らす」で静止します',
        'ko': '최소화되거나 가려지면 일시정지하고, 시스템이 동작 줄이기를 켜면 정적으로 전환합니다',
        'es': 'Se pausa al minimizar u ocultar; estático si el sistema reduce el movimiento',
        'th': 'หยุดชั่วคราวเมื่อย่อหรือถูกบัง และหยุดนิ่งเมื่อระบบลดการเคลื่อนไหว',
    },
    '立即检查': {
        'zh-TW': '立即檢查',
        'en': 'Check now',
        'de': 'Jetzt prüfen',
        'ja': '今すぐ確認',
        'ko': '지금 확인',
        'es': 'Comprobar ahora',
        'th': 'ตรวจสอบตอนนี้',
    },
    '自动更新皮肤图片': {
        'zh-TW': '自動更新皮膚圖片',
        'en': 'Update skin images automatically',
        'de': 'Hautbilder automatisch aktualisieren',
        'ja': 'スキン画像を自動更新',
        'ko': '스킨 이미지 자동 업데이트',
        'es': 'Actualizar imágenes de tema automáticamente',
        'th': 'อัปเดตรูปสกินอัตโนมัติ',
    },
    '自动检查更新': {
        'zh-TW': '自動檢查更新',
        'en': 'Check for updates automatically',
        'de': 'Automatisch nach Updates suchen',
        'ja': '更新を自動確認',
        'ko': '자동으로 업데이트 확인',
        'es': 'Buscar actualizaciones automáticamente',
        'th': 'ตรวจหาการอัปเดตอัตโนมัติ',
    },
    '自安装以来累计 Token\n永不清零': {
        'zh-TW': '自安裝以來累計 Token\n永不清零',
        'en': 'Tokens since install\nnever reset',
        'de': 'Token seit Installation\nnie zurückgesetzt',
        'ja': 'インストールからの累計 Token\nリセットされません',
        'ko': '설치 이후 누적 Token\n초기화되지 않음',
        'es': 'Tokens desde la instalación\nnunca se reinicia',
        'th': 'Token สะสมตั้งแต่ติดตั้ง\nไม่รีเซ็ต',
    },
    '许可证': {
        'zh-TW': '授權條款',
        'en': 'License',
        'de': 'Lizenz',
        'ja': 'ライセンス',
        'ko': '라이선스',
        'es': 'Licencia',
        'th': 'ไลเซนส์',
    },
    '请求数': {
        'zh-TW': '請求數',
        'en': 'Requests',
        'de': 'Anfragen',
        'ja': 'リクエスト数',
        'ko': '요청 수',
        'es': 'Solicitudes',
        'th': 'จำนวนคำขอ',
    },
    '账本': {
        'zh-TW': '帳本',
        'en': 'Ledger',
        'de': 'Kontobuch',
        'ja': '台帳',
        'ko': '장부',
        'es': 'Libro',
        'th': 'สมุดบัญชี',
    },
    '起止时间': {
        'zh-TW': '起止時間',
        'en': 'From – to',
        'de': 'Von – bis',
        'ja': '開始〜終了',
        'ko': '시작–종료',
        'es': 'Desde – hasta',
        'th': 'เริ่ม – สิ้นสุด',
    },
    '还没有清零记录。清零时会把当时的读数存进账本。': {
        'zh-TW': '還沒有歸零記錄。歸零時會把當時的讀數存進帳本。',
        'en': 'No resets yet. Resetting stores the reading in the ledger.',
        'de': 'Noch keine Rücksetzungen. Beim Zurücksetzen wird der Stand im Kontobuch gespeichert.',
        'ja': 'まだリセット記録はありません。リセット時にその時点の値を台帳へ保存します。',
        'ko': '아직 초기화 기록이 없습니다. 초기화 시 그 시점의 값을 장부에 저장합니다.',
        'es': 'Aún no hay reinicios. Al reiniciar se guarda la lectura en el libro.',
        'th': 'ยังไม่มีการรีเซ็ต เมื่อรีเซ็ตจะบันทึกค่านั้นลงสมุดบัญชี',
    },
    '这一段叫什么？': {
        'zh-TW': '這一段叫什麼？',
        'en': 'What is this segment called?',
        'de': 'Wie heißt dieses Segment?',
        'ja': 'この区間の名前は？',
        'ko': '이 구간의 이름은?',
        'es': '¿Cómo se llama este tramo?',
        'th': 'ช่วงนี้ชื่ออะไร',
    },
    '退出 Codex 后自动还原': {
        'zh-TW': '退出 Codex 後自動還原',
        'en': 'Restored automatically after Codex exits',
        'de': 'Automatisch zurückgesetzt, wenn Codex endet',
        'ja': 'Codex 終了後に自動で戻します',
        'ko': 'Codex 종료 후 자동 복원',
        'es': 'Se restaura al cerrar Codex',
        'th': 'คืนค่าอัตโนมัติเมื่อ Codex ปิด',
    },
    '配置完好，未检测到被其他程序改动': {
        'zh-TW': '設定完好，未偵測到被其他程式改動',
        'en': 'Configuration intact, no external changes detected',
        'de': 'Konfiguration intakt, keine externen Änderungen',
        'ja': '設定は正常で、外部からの変更は検出されていません',
        'ko': '설정이 정상이며 외부 변경이 감지되지 않았습니다',
        'es': 'Configuración intacta, sin cambios externos',
        'th': 'การตั้งค่าปกติ ไม่พบการแก้ไขจากภายนอก',
    },
    '重试后成功': {
        'zh-TW': '重試後成功',
        'en': 'Succeeded after retry',
        'de': 'Nach Wiederholung erfolgreich',
        'ja': '再試行で成功',
        'ko': '재시도 후 성공',
        'es': 'Éxito tras reintento',
        'th': 'สำเร็จหลังลองใหม่',
    },
    '隐私与安全': {
        'zh-TW': '隱私與安全',
        'en': 'Privacy & security',
        'de': 'Datenschutz & Sicherheit',
        'ja': 'プライバシーとセキュリティ',
        'ko': '개인정보 및 보안',
        'es': 'Privacidad y seguridad',
        'th': 'ความเป็นส่วนตัวและความปลอดภัย',
    },
    '需你处理': {
        'zh-TW': '需你處理',
        'en': 'Needs you',
        'de': 'Ihre Aufgabe',
        'ja': '対応が必要',
        'ko': '직접 처리 필요',
        'es': 'Requiere tu acción',
        'th': 'ต้องจัดการเอง',
    },
    '静态': {
        'zh-TW': '靜態',
        'en': 'Static',
        'de': 'Statisch',
        'ja': '静止',
        'ko': '정적',
        'es': 'Estático',
        'th': 'นิ่ง',
    },
    '默认关闭': {
        'zh-TW': '預設關閉',
        'en': 'Off by default',
        'de': 'Standardmäßig aus',
        'ja': '既定はオフ',
        'ko': '기본 꺼짐',
        'es': 'Desactivado por defecto',
        'th': 'ปิดโดยค่าเริ่มต้น',
    },
    '默认模型 {0}': {
        'zh-TW': '預設模型 {0}',
        'en': 'Default model {0}',
        'de': 'Standardmodell {0}',
        'ja': '既定モデル {0}',
        'ko': '기본 모델 {0}',
        'es': 'Modelo predeterminado {0}',
        'th': 'โมเดลเริ่มต้น {0}',
    },
    '默认模型只在 Codex 未指定模型时使用': {
        'zh-TW': '預設模型只在 Codex 未指定模型時使用',
        'en': 'The default model is used only when Codex does not specify one',
        'de': 'Das Standardmodell wird nur genutzt, wenn Codex keines vorgibt',
        'ja': '既定モデルは Codex がモデルを指定しない場合にのみ使われます',
        'ko': '기본 모델은 Codex가 모델을 지정하지 않을 때만 사용됩니다',
        'es': 'El modelo predeterminado solo se usa si Codex no especifica uno',
        'th': 'โมเดลเริ่มต้นใช้เฉพาะเมื่อ Codex ไม่ได้ระบุโมเดล',
    },
}
for _text, _values in _EXTRA.items():
    for _code, _translated in _values.items():
        TRANSLATIONS.setdefault(_code, {})[_text] = _translated

_EXTRA_2 = {
    '删除': {'zh-TW': '刪除', 'en': 'Delete', 'de': 'Löschen', 'ja': '削除',
             'ko': '삭제', 'es': 'Eliminar', 'th': 'ลบ'},
    '已恢复为当前区间': {'zh-TW': '已恢復為目前區間', 'en': 'Restored as the current range',
                        'de': 'Als aktueller Zeitraum wiederhergestellt',
                        'ja': '現在の区間として復元しました', 'ko': '현재 구간으로 복원했습니다',
                        'es': 'Restaurado como rango actual', 'th': 'คืนค่าเป็นช่วงปัจจุบันแล้ว'},
    '适配 ChatGPT · Codex 与 Claude Code；郑州微光智能科技中心。': {
        'zh-TW': '適配 ChatGPT · Codex 與 Claude Code；鄭州微光智能科技中心。',
        'en': 'Works with ChatGPT · Codex and Claude Code. Zhengzhou MicroGlow Intelligent Technology Center.',
        'de': 'Funktioniert mit ChatGPT · Codex und Claude Code. Zhengzhou MicroGlow Intelligent Technology Center.',
        'ja': 'ChatGPT · Codex と Claude Code に対応。鄭州微光智能科技中心。',
        'ko': 'ChatGPT · Codex 및 Claude Code 지원. 정저우 웨이광 지능과학기술센터.',
        'es': 'Compatible con ChatGPT · Codex y Claude Code. Centro de Tecnología Inteligente MicroGlow de Zhengzhou.',
        'th': 'รองรับ ChatGPT · Codex และ Claude Code; ศูนย์เทคโนโลยีอัจฉริยะ MicroGlow เจิ้งโจว'},
}
for _text, _values in _EXTRA_2.items():
    for _code, _translated in _values.items():
        TRANSLATIONS.setdefault(_code, {})[_text] = _translated

_EXTRA_3 = {
    '　·　起算于 {0}': {'zh-TW': '　·　起算於 {0}', 'en': '　·　since {0}',
                     'de': '　·　seit {0}', 'ja': '　·　{0} から',
                     'ko': '　·　{0}부터', 'es': '　·　desde {0}',
                     'th': '　·　ตั้งแต่ {0}'},
}
for _text, _values in _EXTRA_3.items():
    for _code, _translated in _values.items():
        TRANSLATIONS.setdefault(_code, {})[_text] = _translated

# 0.9 UI 收口新增文案：八语言译文（人工校订）。
_EXTRA_4 = {
    'API Key 与本地令牌经 DPAPI 加密；正文不保存，推理摘要短期缓存。': {
        'zh-TW': 'API Key 與本機權杖經 DPAPI 加密；正文不儲存，推理摘要短期快取。',
        'en': 'API keys and the local token are DPAPI-encrypted; bodies are not stored, reasoning text is cached briefly.',
        'de': 'API-Schlüssel und lokales Token sind DPAPI-verschlüsselt; Inhalte werden nicht gespeichert, Denktext kurz zwischengespeichert.',
        'ja': 'APIキーとローカルトークンはDPAPIで暗号化。本文は保存せず、推論テキストは短期間キャッシュします。',
        'ko': 'API 키와 로컬 토큰은 DPAPI로 암호화됩니다. 본문은 저장하지 않으며 추론 텍스트만 짧게 캐시합니다.',
        'es': 'Las claves API y el token local usan DPAPI; los cuerpos no se guardan y el texto de razonamiento se cachea brevemente.',
        'th': 'คีย์ API และโทเคนในเครื่องเข้ารหัสด้วย DPAPI ไม่บันทึกเนื้อหา แคชข้อความการคิดชั่วคราว',
    },
    '{0} 个模型组 · {1} 个渠道': {
        'zh-TW': '{0} 個模型組 · {1} 個通路',
        'en': '{0} model groups · {1} channels',
        'de': '{0} Modellgruppen · {1} Kanäle',
        'ja': '{0} モデルグループ · {1} チャネル',
        'ko': '모델 그룹 {0}개 · 채널 {1}개',
        'es': '{0} grupos de modelos · {1} canales',
        'th': '{0} กลุ่มโมเดล · {1} ช่องทาง',
    },
    '上传仅含调用与用量摘要，不含正文、代码、密钥或 IP；连接来源对服务端可见。需明确同意，仅正常退出时尝试一次。': {
        'zh-TW': '上傳僅含呼叫與用量摘要，不含正文、程式碼、金鑰或 IP；連線來源對伺服器可見。需明確同意，僅正常結束時嘗試一次。',
        'en': 'Uploads contain usage summaries only — no prompts, code, keys or IP; the server can see the connection source. Explicit consent required; one attempt on normal exit.',
        'de': 'Uploads enthalten nur Nutzungszusammenfassungen, keine Inhalte, Code, Schlüssel oder IP; der Server sieht die Verbindungsquelle. Nur mit Zustimmung, ein Versuch beim normalen Beenden.',
        'ja': '送信は利用量の集計のみで、本文・コード・鍵・IP は含みません。サーバーには接続元が見えます。明示的な同意が必要で、正常終了時に一度だけ試行します。',
        'ko': '업로드에는 사용량 요약만 포함되며 본문·코드·키·IP는 없습니다. 서버는 연결 출처를 볼 수 있습니다. 명시적 동의가 필요하며 정상 종료 시 한 번 시도합니다.',
        'es': 'Las subidas solo contienen resúmenes de uso, sin contenidos, código, claves ni IP; el servidor ve el origen de la conexión. Requiere consentimiento explícito; un intento al salir normalmente.',
        'th': 'ข้อมูลที่ส่งมีเพียงสรุปการใช้งาน ไม่มีเนื้อหา โค้ด คีย์ หรือ IP แต่เซิร์ฟเวอร์เห็นต้นทางการเชื่อมต่อ ต้องยินยอมชัดเจน และลองครั้งเดียวเมื่อออกตามปกติ',
    },
    '仅下载图片；断网时使用内置皮肤。': {
        'zh-TW': '僅下載圖片；離線時使用內建皮膚。',
        'en': 'Images only; built-in skins are used offline.',
        'de': 'Nur Bilder; offline werden eingebaute Designs genutzt.',
        'ja': '画像のみダウンロード。オフライン時は内蔵スキンを使用。',
        'ko': '이미지만 다운로드하며 오프라인에서는 기본 스킨을 사용합니다.',
        'es': 'Solo imágenes; sin conexión se usan los temas integrados.',
        'th': 'ดาวน์โหลดเฉพาะภาพ เมื่อออฟไลน์ใช้ธีมในตัว',
    },
    '前往工作台开启': {
        'zh-TW': '前往工作台開啟',
        'en': 'Open on dashboard',
        'de': 'Auf dem Dashboard öffnen',
        'ja': 'ダッシュボードで有効化',
        'ko': '대시보드에서 켜기',
        'es': 'Activar en el panel',
        'th': 'เปิดที่หน้าแดชบอร์ด',
    },
    '同一模型的多个渠道按权重随机选择，顺序不影响结果；失败后冷却 60 秒再试。默认模型只在 Codex 未指定模型时使用。': {
        'zh-TW': '同一模型的多個通路依權重隨機選擇，順序不影響結果；失敗後冷卻 60 秒再試。預設模型只在 Codex 未指定模型時使用。',
        'en': 'Channels of one model are picked randomly by weight; order has no effect. After a failure they cool down for 60 seconds. The default model applies only when Codex does not specify one.',
        'de': 'Kanäle eines Modells werden gewichtet zufällig gewählt; die Reihenfolge spielt keine Rolle. Nach einem Fehler 60 Sekunden Abklingzeit. Das Standardmodell gilt nur, wenn Codex keines angibt.',
        'ja': '同一モデルのチャネルは重み付きランダムで選択され、順序は結果に影響しません。失敗後は 60 秒クールダウン。既定モデルは Codex がモデルを指定しない場合のみ使用されます。',
        'ko': '한 모델의 채널은 가중치로 무작위 선택되며 순서는 결과에 영향을 주지 않습니다. 실패 후 60초 쿨다운. 기본 모델은 Codex가 모델을 지정하지 않을 때만 사용됩니다.',
        'es': 'Los canales de un modelo se eligen al azar por peso; el orden no afecta. Tras un fallo, 60 s de enfriamiento. El modelo predeterminado solo se usa si Codex no especifica uno.',
        'th': 'ช่องทางของโมเดลเดียวกันถูกเลือกแบบสุ่มตามน้ำหนัก ลำดับไม่ส่งผลต่อผลลัพธ์ หลังล้มเหลวจะคูลดาวน์ 60 วินาที โมเดลเริ่มต้นใช้เมื่อ Codex ไม่ได้ระบุโมเดลเท่านั้น',
    },
    '在 config.toml 写入 model_providers 接入项。': {
        'zh-TW': '在 config.toml 寫入 model_providers 接入項。',
        'en': 'Writes the model_providers entry in config.toml.',
        'de': 'Schreibt den Eintrag model_providers in config.toml.',
        'ja': 'config.toml に model_providers の設定を書き込みます。',
        'ko': 'config.toml에 model_providers 항목을 기록합니다.',
        'es': 'Escribe la entrada model_providers en config.toml.',
        'th': 'เขียนรายการ model_providers ลงใน config.toml',
    },
    '在 settings.json 写入 BASE_URL、令牌与模型三项。': {
        'zh-TW': '在 settings.json 寫入 BASE_URL、權杖與模型三項。',
        'en': 'Writes BASE_URL, token and model into settings.json.',
        'de': 'Schreibt BASE_URL, Token und Modell in settings.json.',
        'ja': 'settings.json に BASE_URL・トークン・モデルを書き込みます。',
        'ko': 'settings.json에 BASE_URL, 토큰, 모델을 기록합니다.',
        'es': 'Escribe BASE_URL, token y modelo en settings.json.',
        'th': 'เขียน BASE_URL, โทเค็น และโมเดลลงใน settings.json',
    },
    '每天最多访问一次更新服务；服务端可见连接 IP 与版本。': {
        'zh-TW': '每天最多造訪一次更新服務；伺服器可見連線 IP 與版本。',
        'en': 'At most one update check per day; the server sees the connection IP and app version.',
        'de': 'Höchstens eine Update-Prüfung pro Tag; der Server sieht Verbindungs-IP und Version.',
        'ja': '更新確認は 1 日 1 回まで。サーバーには接続 IP とバージョンが見えます。',
        'ko': '업데이트 확인은 하루 최대 한 번이며 서버는 연결 IP와 버전을 볼 수 있습니다.',
        'es': 'Como máximo una comprobación al día; el servidor ve la IP de conexión y la versión.',
        'th': 'ตรวจสอบอัปเดตได้สูงสุดวันละครั้ง เซิร์ฟเวอร์เห็น IP ที่เชื่อมต่อและเวอร์ชัน',
    },
    '仅累计每日调用、成功/错误、Token、固定延迟区间、标准错误类别和回退次数。\n\n不收集请求或响应正文、文件、代码、密钥、原始错误和逐请求记录；上传内容不含 IP，但服务端能看到连接来源。\n\n上传包含随机安装标识、版本、供应商类别、模型、活跃分钟及官方/中转/未知渠道分类，不上传实际地址。仅正常退出时尝试一次；失败或拒绝保留批次，下次退出重试。\n\n国家/地区仅由服务器依据网络连接粗略判断。': {
        'zh-TW': '僅累計每日呼叫、成功/錯誤、Token、固定延遲區間、標準錯誤類別與回退次數。\n\n不收集請求或回應正文、檔案、程式碼、金鑰、原始錯誤與逐筆紀錄；上傳內容不含 IP，但伺服器能看到連線來源。\n\n上傳包含隨機安裝識別、版本、供應商類別、模型、活躍分鐘及官方/中轉/未知通路分類，不上傳實際位址。僅正常結束時嘗試一次；失敗或拒絕保留批次，下次結束重試。\n\n國家/地區僅由伺服器依據網路連線粗略判斷。',
        'en': 'Only daily call counts, success/error, tokens, fixed latency bands, standard error categories and fallback counts are aggregated.\n\nNo request or response bodies, files, code, keys, raw errors or per-request records are collected; uploads contain no IP, but the server can see the connection source.\n\nUploads include a random installation ID, version, provider category, model, active minutes and official/relay/unknown channel categories, never actual addresses. One attempt on normal exit only; failed or rejected batches are kept for the next exit.\n\nCountry/region is inferred approximately by the server from the network connection only.',
        'de': 'Es werden nur tägliche Aufrufzahlen, Erfolg/Fehler, Token, feste Latenzbänder, Standardfehlerkategorien und Fallback-Zahlen zusammengefasst.\n\nKeine Anfrage- oder Antwortinhalte, Dateien, Code, Schlüssel, Rohfehler oder Einzelprotokolle; Uploads enthalten keine IP, der Server sieht aber die Verbindungsquelle.\n\nUploads enthalten eine zufällige Installations-ID, Version, Anbieterkategorie, Modell, aktive Minuten und Kategorien offiziell/Relay/unbekannt, niemals echte Adressen. Ein Versuch beim normalen Beenden; fehlgeschlagene oder abgelehnte Pakete bleiben bis zum nächsten Beenden.\n\nLand/Region wird nur vom Server grob aus der Netzwerkverbindung abgeleitet.',
        'ja': '集計するのは日次の呼び出し数、成功/エラー、Token、固定遅延帯、標準エラー分類、フォールバック回数のみです。\n\nリクエスト/応答の本文、ファイル、コード、鍵、生のエラー、逐次記録は収集しません。送信に IP は含みませんが、サーバーには接続元が見えます。\n\n送信にはランダムなインストール ID、バージョン、供給元分類、モデル、稼働分数、公式/中継/不明の分類が含まれ、実際のアドレスは含みません。正常終了時のみ 1 回試行し、失敗・拒否されたバッチは次回終了時に再試行します。\n\n国・地域はサーバーがネットワーク接続から大まかに推定するだけです。',
        'ko': '일일 호출 수, 성공/오류, 토큰, 고정 지연 구간, 표준 오류 분류, 폴백 횟수만 집계합니다.\n\n요청/응답 본문, 파일, 코드, 키, 원시 오류, 개별 기록은 수집하지 않습니다. 업로드에 IP는 없지만 서버는 연결 출처를 볼 수 있습니다.\n\n업로드에는 무작위 설치 ID, 버전, 공급자 분류, 모델, 활성 시간(분), 공식/중계/알 수 없음 분류가 포함되며 실제 주소는 없습니다. 정상 종료 시 한 번만 시도하고 실패·거부 배치는 다음 종료 때 재시도합니다.\n\n국가/지역은 서버가 네트워크 연결로만 대략 추정합니다.',
        'es': 'Solo se agregan recuentos diarios de llamadas, acierto/error, tokens, bandas de latencia fijas, categorías de error estándar y reintentos de respaldo.\n\nNo se recopilan cuerpos de petición o respuesta, archivos, código, claves, errores sin procesar ni registros por petición; las subidas no incluyen IP, pero el servidor ve el origen de la conexión.\n\nLas subidas incluyen un ID de instalación aleatorio, versión, categoría del proveedor, modelo, minutos activos y categorías oficial/relé/desconocido, nunca direcciones reales. Un intento al salir normalmente; los lotes fallidos o rechazados se conservan para la siguiente salida.\n\nEl país/región lo estima aproximadamente el servidor solo a partir de la conexión de red.',
        'th': 'สรุปเฉพาะจำนวนเรียกใช้รายวัน สำเร็จ/ข้อผิดพลาด โทเค็น ช่วงเวลาหน่วงคงที่ หมวดข้อผิดพลาดมาตรฐาน และจำนวน fallback\n\nไม่เก็บเนื้อหาคำขอ/การตอบกลับ ไฟล์ โค้ด คีย์ ข้อผิดพลาดดิบ หรือบันทึกรายคำขอ ข้อมูลที่ส่งไม่มี IP แต่เซิร์ฟเวอร์เห็นต้นทางการเชื่อมต่อ\n\nข้อมูลที่ส่งมี ID ติดตั้งแบบสุ่ม เวอร์ชัน ประเภทผู้ให้บริการ โมเดล นาทีใช้งาน และหมวดช่องทาง official/relay/unknown ไม่มีที่อยู่จริง ลองครั้งเดียวเมื่อออกตามปกติ ชุดที่ล้มเหลวหรือถูกปฏิเสธเก็บไว้รอบถัดไป\n\nประเทศ/ภูมิภาคประมาณโดยเซิร์ฟเวอร์จากการเชื่อมต่อเครือข่ายเท่านั้น',
    },
}
for _text, _values in _EXTRA_4.items():
    for _code, _translated in _values.items():
        TRANSLATIONS.setdefault(_code, {})[_text] = _translated


# UI-FINAL-IMPLEMENT: keep the final views in the same offline catalog.
from .final_translations import CODES as _FINAL_CODES, ROWS as _FINAL_ROWS
for _i, _code in enumerate(_FINAL_CODES):
    TRANSLATIONS[_code].update({source: values[_i] for source, values in _FINAL_ROWS.items()})
