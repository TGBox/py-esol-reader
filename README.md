# EDIFACT SLLA Parser & Viewer (§ 302 SGB V)

Eine moderne Python-Desktop-Anwendung mit grafischer Benutzeroberfläche (GUI) zum Einlesen, Analysieren, Durchsuchen und Exportieren von EDIFACT-Abrechnungsdateien (ESOL) für den Bereich des § 302 SGB V (fokusstiert auf Heilmittel und Basis-Segmente).

## 🚀 Features

* **Hierarchische Strukturansicht:** Automatische Gruppierung der flachen EDIFACT-Segmente in logische Einheiten (Nachrichten via `UNH`, Rechnungen via `REC` sowie Bündelung aufeinanderfolgender gleicher Segmente wie z.B. `EHE`).
* **Live-Suche & Hervorhebung:** Sofortige Filterung nach Begriffen, Feldnamen (Keys), Inhalten oder Strukturbezeichnungen mit automatischer farblicher Markierung der Treffer.
* **Encoding-Auswahl:** Flexibles Umschalten des Zeichensatzes zur korrekten Darstellung von Umlauten und Sonderzeichen (unterstützt `iso-8859-1`, `windows-1252`, `utf-8`, `ascii`).
* **Integriertes Abrechnungs-Dashboard:** Dauerhafte Anzeige wichtiger Kennzahlen direkt in der GUI (Absender- und Empfänger-IK, Nachrichten-, Rechnungs- und Positionsanzahl sowie Gesamtsumme Brutto).
* **Universeller Datenexport:** Export der strukturierten Abrechnungsdaten in die Formate **XLSX (Excel)**, **CSV**, **JSON** sowie als formatiertes **PDF**-Dokument.
* **Baum-Steuerung:** Kompakte Buttons zum schnellen Auf- und Zuklappen des gesamten Datenbaums (übereinander angeordnet).
* **Vollständiger Segment-Support:** Verarbeitet Umschlag-Segmente (`UNB`, `UNH`, `UNT`, `Zusatz-Segmente`), Basis-Segmente (`FKT`, `REC`, `INV`, `NAD`, `URI`, `IMG`, `EVO`) sowie spezifische Leistungsspezifische Segmente (z.B. für Heilmittel: `EHE`, `ZHE`, `DIA`, `MWS`, `BES`, `GZF`, `TXT`, `SKZ`).

---

## 🛠️ Installation & Voraussetzungen

1. **Python installieren:** Stelle sicher, dass Python 3.x auf deinem System installiert ist.
2. **Abhängigkeiten installieren:** Für den Export und die PDF-Generierung werden zusätzliche Bibliotheken (`reportlab`, `pandas`, `openpyxl`) benötigt. Installiere sie über das Terminal bzw. die Eingabeaufforderung:

```bash
pip install reportlab pandas openpyxl
```

*(Hinweis: Tkinter ist in der Standard-Python-Installation für Windows und macOS bereits enthalten).*

---

## 📂 Projektstruktur

* `esol_reader.py`: Enthält die Kern-Logik des Parsers (`EdifactSLLAParser`). `gui.py` enthält die Tkinter-GUI-Applikation (`EdifactViewerApp`).

---

## 🖥️ Verwendung

* Starte das Skript über dein Terminal oder deine Entwicklungsumgebung (z.B. VS Code):

```bash
python gui.py
```

* Klicke oben links auf **"EDIFACT Datei öffnen..."** und wähle deine Abrechnungsdatei (z. B. im `.edi`- oder `.txt`-Format) aus.
* Das **integrierte Dashboard** zeigt sofort nach dem Laden alle wichtigen Kennzahlen der Abrechnung an.
* Falls Umlaute falsch dargestellt werden, passe das Encoding im Dropdown-Menü an (Standard für § 302 SGB V ist `iso-8859-1`).
* Nutze das **Suchfeld** oben rechts, um gezielt nach Rechnungsnummern, Beträgen oder Feldnamen zu suchen, oder klappe den Baum mit den **Aufklappen / Zuklappen**-Buttons übersichtlich ein und aus.
* Klicke auf **"Daten exportieren..."**, um die strukturierten Daten in das gewünschte Format (`.xlsx`, `.csv`, `.json` oder `.pdf`) abzuspeichern.

---

## 📋 Technische Details zum Parser

Der Parser liest den unformatierten EDIFACT-Strom ein, entfernt Zeilenumbrüche und zerlegt die Daten anhand der Standard-Trennzeichen:

* `'` (Segment-Terminator)
* `+` (Datenelement-Trennzeichen)
* `:` (Komponenten-Trennzeichen)

Die Implementierung orientiert sich an den Vorgaben für den Datenaustausch im Abrechnungsverfahren nach § 302 SGB V.
