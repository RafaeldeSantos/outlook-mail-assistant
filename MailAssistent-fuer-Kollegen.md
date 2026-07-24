# Mail Assistent – Einrichtung (für Kollegen)

Ein KI-Assistent direkt in Outlook: Antworten aus Stichworten generieren, kontextbezogene Antwortvorschläge, Kurzantworten, Termin-Antworten – in Deutsch/Englisch, mit passender Anrede und deiner Signatur.

**Du musst nichts programmieren und nichts hosten.** Der Assistent läuft bereits auf einem gehosteten Server; du brauchst nur einmal das Add-in in Outlook laden und deine Daten eintragen.

## Voraussetzungen
- **Klassisches Outlook** für Windows (nicht „neues Outlook") – der Schalter „Neues Outlook" oben rechts muss **AUS** sein.
- Ein **Claude API Key** (kostet pro Mail ~0,5 Cent). Anlegen unter **console.anthropic.com → API Keys → Create Key**, Wert (`sk-ant-...`) kopieren.

---

## Variante A – mit Claude Code (empfohlen, führt dich durch)

Öffne Claude Code in einem beliebigen leeren Ordner und füge **exakt diesen Prompt** ein:

````text
Ich möchte ein Outlook-Add-in ("Mail Assistent") auf meinem klassischen Outlook (Windows) installieren. Bitte:

1. Lege im aktuellen Ordner eine Datei "manifest.xml" mit GENAU folgendem Inhalt an (unverändert, UTF-8):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<OfficeApp
  xmlns="http://schemas.microsoft.com/office/appforoffice/1.1"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns:bt="http://schemas.microsoft.com/office/officeappbasictypes/1.0"
  xmlns:mailappor="http://schemas.microsoft.com/office/mailappversionoverrides/1.0"
  xsi:type="MailApp">

  <Id>faff5f48-da9b-4263-b4e2-41c3afb174b9</Id>
  <Version>1.2.0</Version>
  <ProviderName>LSJ Advisory</ProviderName>
  <DefaultLocale>de-DE</DefaultLocale>
  <DisplayName DefaultValue="Mail Assistent"/>
  <Description DefaultValue="Schnelle Mail-Antworten mit KI — Stichworte rein, fertige Antwort raus."/>
  <IconUrl DefaultValue="https://rafaeldesantos.github.io/outlook-mail-assistant/assets/icon-32.png"/>
  <HighResolutionIconUrl DefaultValue="https://rafaeldesantos.github.io/outlook-mail-assistant/assets/icon-64.png"/>
  <SupportUrl DefaultValue="https://rafaeldesantos.github.io/outlook-mail-assistant"/>

  <Hosts>
    <Host Name="Mailbox"/>
  </Hosts>

  <Requirements>
    <Sets>
      <Set Name="Mailbox" MinVersion="1.1"/>
    </Sets>
  </Requirements>

  <FormSettings>
    <Form xsi:type="ItemRead">
      <DesktopSettings>
        <SourceLocation DefaultValue="https://rafaeldesantos.github.io/outlook-mail-assistant/taskpane.html"/>
        <RequestedHeight>450</RequestedHeight>
      </DesktopSettings>
    </Form>
  </FormSettings>

  <Permissions>ReadWriteItem</Permissions>

  <Rule xsi:type="RuleCollection" Mode="Or">
    <Rule xsi:type="ItemIs" ItemType="Message" FormType="Read"/>
  </Rule>

  <DisableEntityHighlighting>true</DisableEntityHighlighting>

  <VersionOverrides xmlns="http://schemas.microsoft.com/office/mailappversionoverrides" xsi:type="VersionOverridesV1_0">
    <Requirements>
      <bt:Sets DefaultMinVersion="1.3">
        <bt:Set Name="Mailbox"/>
      </bt:Sets>
    </Requirements>

    <Hosts>
      <Host xsi:type="MailHost">
        <DesktopFormFactor>
          <ExtensionPoint xsi:type="MessageReadCommandSurface">
            <OfficeTab id="TabDefault">
              <Group id="msgReadGroup">
                <Label resid="groupLabel"/>
                <Control xsi:type="Button" id="taskPaneBtn">
                  <Label resid="btnLabel"/>
                  <Supertip>
                    <Title resid="btnLabel"/>
                    <Description resid="btnDesc"/>
                  </Supertip>
                  <Icon>
                    <bt:Image size="16" resid="icon16"/>
                    <bt:Image size="32" resid="icon32"/>
                    <bt:Image size="80" resid="icon80"/>
                  </Icon>
                  <Action xsi:type="ShowTaskpane">
                    <SourceLocation resid="taskPaneUrl"/>
                  </Action>
                </Control>
              </Group>
            </OfficeTab>
          </ExtensionPoint>
          <ExtensionPoint xsi:type="MessageComposeCommandSurface">
            <OfficeTab id="TabDefaultCompose">
              <Group id="msgComposeGroup">
                <Label resid="groupLabel"/>
                <Control xsi:type="Button" id="taskPaneBtnCompose">
                  <Label resid="btnLabelCompose"/>
                  <Supertip>
                    <Title resid="btnLabelCompose"/>
                    <Description resid="btnDescCompose"/>
                  </Supertip>
                  <Icon>
                    <bt:Image size="16" resid="icon16"/>
                    <bt:Image size="32" resid="icon32"/>
                    <bt:Image size="80" resid="icon80"/>
                  </Icon>
                  <Action xsi:type="ShowTaskpane">
                    <SourceLocation resid="taskPaneUrl"/>
                  </Action>
                </Control>
              </Group>
            </OfficeTab>
          </ExtensionPoint>
          <ExtensionPoint xsi:type="AppointmentAttendeeCommandSurface">
            <OfficeTab id="TabDefaultApptRead">
              <Group id="apptReadGroup">
                <Label resid="groupLabel"/>
                <Control xsi:type="Button" id="taskPaneBtnApptRead">
                  <Label resid="btnLabel"/>
                  <Supertip>
                    <Title resid="btnLabel"/>
                    <Description resid="btnDesc"/>
                  </Supertip>
                  <Icon>
                    <bt:Image size="16" resid="icon16"/>
                    <bt:Image size="32" resid="icon32"/>
                    <bt:Image size="80" resid="icon80"/>
                  </Icon>
                  <Action xsi:type="ShowTaskpane">
                    <SourceLocation resid="taskPaneUrl"/>
                  </Action>
                </Control>
              </Group>
            </OfficeTab>
          </ExtensionPoint>
          <ExtensionPoint xsi:type="AppointmentOrganizerCommandSurface">
            <OfficeTab id="TabDefaultApptCompose">
              <Group id="apptComposeGroup">
                <Label resid="groupLabel"/>
                <Control xsi:type="Button" id="taskPaneBtnApptCompose">
                  <Label resid="btnLabelCompose"/>
                  <Supertip>
                    <Title resid="btnLabelCompose"/>
                    <Description resid="btnDescCompose"/>
                  </Supertip>
                  <Icon>
                    <bt:Image size="16" resid="icon16"/>
                    <bt:Image size="32" resid="icon32"/>
                    <bt:Image size="80" resid="icon80"/>
                  </Icon>
                  <Action xsi:type="ShowTaskpane">
                    <SourceLocation resid="taskPaneUrl"/>
                  </Action>
                </Control>
              </Group>
            </OfficeTab>
          </ExtensionPoint>
        </DesktopFormFactor>
      </Host>
    </Hosts>

    <Resources>
      <bt:Images>
        <bt:Image id="icon16" DefaultValue="https://rafaeldesantos.github.io/outlook-mail-assistant/assets/icon-16.png"/>
        <bt:Image id="icon32" DefaultValue="https://rafaeldesantos.github.io/outlook-mail-assistant/assets/icon-32.png"/>
        <bt:Image id="icon80" DefaultValue="https://rafaeldesantos.github.io/outlook-mail-assistant/assets/icon-80.png"/>
      </bt:Images>
      <bt:Urls>
        <bt:Url id="taskPaneUrl" DefaultValue="https://rafaeldesantos.github.io/outlook-mail-assistant/taskpane.html"/>
      </bt:Urls>
      <bt:ShortStrings>
        <bt:String id="groupLabel" DefaultValue="Mail Assistent"/>
        <bt:String id="btnLabel" DefaultValue="Antwort generieren"/>
        <bt:String id="btnLabelCompose" DefaultValue="Mail verfassen"/>
      </bt:ShortStrings>
      <bt:LongStrings>
        <bt:String id="btnDesc" DefaultValue="Oeffnet den KI Mail-Assistenten zum schnellen Beantworten von Mails"/>
        <bt:String id="btnDescCompose" DefaultValue="Oeffnet den KI Mail-Assistenten zum Verfassen neuer Mails aus Stichworten"/>
      </bt:LongStrings>
    </Resources>
  </VersionOverrides>
</OfficeApp>
```

2. Zeige mir den vollständigen Pfad zur erzeugten manifest.xml.
3. Erkläre mir Schritt für Schritt, wie ich diese manifest.xml in KLASSISCHEM Outlook (Windows) sideloade: Menüband "Start" → "Add-Ins abrufen" bzw. "Add-Ins verwalten" → "Eigene Add-Ins" → "Benutzerdefiniertes Add-In hinzufügen" → "Aus Datei..." → die manifest.xml auswählen → bestätigen.
4. Weise mich darauf hin, Outlook nach dem Hinzufügen einmal komplett neu zu starten (outlook.exe im Task-Manager beenden), damit der Button erscheint.
5. Erkläre mir, dass der Button "Mail Assistent" NICHT direkt im Menüband sichtbar ist, sondern unter dem Knopf "Alle Apps" (beim Lesen UND beim Verfassen). Nichts installieren, nichts kompilieren – die App wird von einem gehosteten Server geladen.

Die App selbst muss NICHT gehostet oder gebaut werden. Erzeuge NUR die manifest.xml und führe mich durch das Sideloaden.
````

Claude Code legt dann die `manifest.xml` an und führt dich durch den Rest.

---

## Variante B – ganz ohne Claude Code

1. Die beiliegende Datei **`manifest-kollege.xml`** irgendwo speichern (z. B. Dokumente).
2. In klassischem Outlook: **Start → Add-Ins verwalten** (bzw. „Add-Ins abrufen") → **Eigene Add-Ins** → **Benutzerdefiniertes Add-In hinzufügen → Aus Datei…** → die `manifest-kollege.xml` auswählen → bestätigen.
3. **Outlook komplett neu starten** (im Task-Manager prüfen, dass `outlook.exe` beendet ist).

---

## Nach der Installation – einmalig einrichten

1. Eine Mail öffnen → im Menüband **„Alle Apps" → „Mail Assistent"** (der Button ist dort gebündelt, nicht direkt sichtbar).
2. Im Assistenten auf **„Einstellungen (Key & Signatur)"**:
   - **Claude API Key** einfügen (`sk-ant-...`)
   - **Dein Name (voll)** – z. B. `Max Mustermann` (steht beim Siezen unter dem Gruß)
   - **Vorname** – z. B. `Max` (beim Duzen und auf Englisch)
   - **Signatur** – optional; nur wenn du eine reine Text-Signatur unter Antworten willst. Wenn du deine echte Outlook-Signatur mit Logo nutzt (siehe unten), lass das Feld **leer**.
   - **Speichern**. (Key, Name & Signatur bleiben dauerhaft gespeichert – auch nach Neustart.)
3. **Empfohlen für die Logo-Signatur:** In Outlook unter **Datei → Optionen → E-Mail → Signaturen** bei **„Antworten/Weiterleitungen"** deine Signatur auswählen (nicht „(ohne)"). Dann hängt Outlook bei Antworten automatisch deine komplette Signatur inkl. Logo an.

## Bedienung
- **Antwort generieren:** Stichworte eintippen (oder Mikro), Sprache + Tonfall wählen → „Antwort generieren" → Text prüfen → „In Mail einfügen".
- **Antwortvorschläge:** „Vorschläge laden" → 2–3 kontextbezogene Chips anklicken.
- **Kurzantwort DE/EN:** Eingangsbestätigung mit einem Klick.
- Beim Einfügen wird automatisch **„Allen antworten"** genutzt (CC bleibt erhalten).

## Falls der Button nicht erscheint
- Outlook wirklich **komplett** neu gestartet? (Task-Manager: kein `outlook.exe`)
- Add-in-Cache leeren: Outlook schließen → Ordner `%LOCALAPPDATA%\Microsoft\Office\16.0\Wef` leeren → Outlook starten.
- Prüfen, dass es **klassisches** Outlook ist (Schalter „Neues Outlook" AUS).

---

*Technischer Hinweis: Die App wird von `rafaeldesantos.github.io/outlook-mail-assistant` geladen. Jeder Nutzer nutzt seinen eigenen API Key (eigene Abrechnung); Key/Name/Signatur werden pro Postfach separat gespeichert.*
