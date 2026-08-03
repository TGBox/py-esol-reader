
from typing import TypeVar

T = TypeVar('T')

class EdifactSLLAParser:
    def __init__(self, segment_terminator="'", element_separator="+", component_separator=":"):
        self.segment_terminator = segment_terminator
        self.element_separator = element_separator
        self.component_separator = component_separator

    def parse_file(self, file_path):
        """Liest die EDIFACT Datei ein und entfernt überflüssige Zeilenumbrüche."""
        with open(file_path, 'r', encoding='iso-8859-1') as file:
            content = file.read().replace('\n', '').replace('\r', '')
            return self.parse_content(content)

    def parse_content(self, content):
        """Trennt den Inhalt in Segmente und verarbeitet diese."""
        segments = content.split(self.segment_terminator)
        parsed_data = []

        for segment in segments:
            if not segment.strip():
                continue
            
            # Trenne das Segment in seine Datenelemente
            elements = segment.split(self.element_separator)
            segment_name = elements[0]
            
            # Verarbeite das Segment basierend auf seinem Namen
            parsed_segment = self._process_segment(segment_name, elements[1:])
            if parsed_segment:
                parsed_data.append(parsed_segment)
                
        return parsed_data
    
    def _safe_get(self, elements_list: list, index: int, default: T = None) -> str | T:
        """Hilfsfunktion: Verhindert Index-Fehler bei ausgelassenen, optionalen EDIFACT-Feldern."""
        if index < len(elements_list) and elements_list[index] is not None and elements_list[index] != "":
            return elements_list[index]
        return default

    def _process_segment(self, name, elements):
        """Ordnet die Datenelemente den Spezifikationen aus der Anlage 1 zu."""
        
        # Segment FKT: Funktion (Basis-Segment)
        if name == "FKT":
            return {
                "Segment": "FKT",
                "Verarbeitungskennzeichen": elements[0] if len(elements) > 0 else None,
                "IK_Leistungserbringer": elements[2] if len(elements) > 2 else None,
                "IK_Kostentraeger": elements[3] if len(elements) > 3 else None,
                "IK_Krankenkasse": elements[4] if len(elements) > 4 else None
            }
            
        # Segment REC: Rechnung/Zahlung (Basis-Segment)
        elif name == "REC":
            # Datenelementgruppe Rechnungsnummer (Sammel:Einzel)
            rechnungs_element = elements[0].split(self.component_separator) if len(elements) > 0 else []
            return {
                "Segment": "REC",
                "Sammel_Rechnungsnummer": rechnungs_element[0] if len(rechnungs_element) > 0 else None,
                "Einzel_Rechnungsnummer": rechnungs_element[1] if len(rechnungs_element) > 1 else "0",
                "Rechnungsdatum": elements[1] if len(elements) > 1 else None,
                "Rechnungsart": elements[2] if len(elements) > 2 else None
            }
            
        # Segment INV: Information Versicherte (Basis-Segment)
        elif name == "INV":
            return {
                "Segment": "INV",
                "Versichertennummer": elements[0] if len(elements) > 0 else None,
                "Versichertenstatus": elements[1] if len(elements) > 1 else None,
                "Belegnummer": elements[3] if len(elements) > 3 else None
            }
            
        # Segment NAD: Name und Adresse Versicherter (Basis-Segment)
        elif name == "NAD":
            return {
                "Segment": "NAD",
                "Nachname": elements[0] if len(elements) > 0 else None,
                "Vorname": elements[1] if len(elements) > 1 else None,
                "Geburtsdatum": elements[2] if len(elements) > 2 else None,
                "Strasse_Nr": elements[3] if len(elements) > 3 else None,
                "PLZ": elements[4] if len(elements) > 4 else None,
                "Wohnort": elements[5] if len(elements) > 5 else None
            }

        # Segment EHE: Einzelfallnachweis Heilmittel
        elif name == "EHE":
            # Datenelementgruppe Leistungserbringergruppe (Abrechnungscode:Tarifkennzeichen)
            leistung_gruppe = self._safe_get(elements, 0, "").split(self.component_separator)
            
            return {
                "Segment": "EHE",
                "Abrechnungscode": leistung_gruppe[0] if len(leistung_gruppe) > 0 else None,
                "Tarifkennzeichen": leistung_gruppe[1] if len(leistung_gruppe) > 1 else None,
                "Abrechnungspositionsnummer": self._safe_get(elements, 1),
                "Anzahl_Menge": self._safe_get(elements, 2),
                "Einzelbetrag": self._safe_get(elements, 3),
                "Datum_Leistungserbringung": self._safe_get(elements, 4),
                "Betrag_Zuzahlung": self._safe_get(elements, 5),
                "Gefahrene_Kilometer": self._safe_get(elements, 6)
            }

        # Segment ZHE: Zusatzinfo Verordnung Heilmittel
        elif name == "ZHE":
            return {
                "Segment": "ZHE",
                "Betriebsstaettennummer": self._safe_get(elements, 0),
                "Lebenslange_Arztnummer": self._safe_get(elements, 1),
                "Verordnungsdatum": self._safe_get(elements, 2),
                "Zuzahlungskennzeichen": self._safe_get(elements, 3),
                "Diagnosegruppe": self._safe_get(elements, 4),
                "Kennzeichen_Verordnungsart": self._safe_get(elements, 5),
                "Kennzeichen_Verordnungsbesonderheiten": self._safe_get(elements, 6),
                "Unfallkennzeichen": self._safe_get(elements, 7),
                "Kennzeichen_BVG_Sonstiges": self._safe_get(elements, 8),
                # Index 9 ist der Behandlungsbeginn: Dieses Feld wird laut Spezifikation nicht mehr gefüllt.
                "Therapiebericht_angefordert": self._safe_get(elements, 10),
                "Hausbesuch": self._safe_get(elements, 11),
                "Leitsymptomatik": self._safe_get(elements, 12),
                "Patientenindividuelle_Leitsymptomatik": self._safe_get(elements, 13),
                "Dringlicher_Behandlungsbedarf": self._safe_get(elements, 14),
                "Heilmittel_Bereich": self._safe_get(elements, 15),
                "Therapiefrequenz": self._safe_get(elements, 16)
            }

        # Segment DIA: Diagnose
        elif name == "DIA":
            return {
                "Segment": "DIA",
                "Diagnoseschluessel": self._safe_get(elements, 0), # z.B. ICD-10-Code
                "Diagnosetext": self._safe_get(elements, 1)
            }

        # Segment MWS: Mehrwertsteuer (optional bei EHE)
        elif name == "MWS":
            return {
                "Segment": "MWS",
                "Mehrwertsteuersatz": self._safe_get(elements, 0),
                "Betrag_Mehrwertsteuer": self._safe_get(elements, 1)
            }

        # Segment BES: Betrags-Summen am Ende der Verordnung[cite: 1]
        elif name == "BES":
            return {
                "Segment": "BES",
                "Gesamtbetrag_Brutto": self._safe_get(elements, 0),
                "Gesamtbetrag_gesetzliche_Zuzahlung": self._safe_get(elements, 1),
                "Gesamtbetrag_prozentuale_Zuzahlung": self._safe_get(elements, 2),
                "Pauschaler_Zuzahlungsbetrag": self._safe_get(elements, 3),
                "Pauschale_Korrekturabzug": self._safe_get(elements, 4)
            }

        # Segment GZF: Gesamtbetrag Zuzahlungsforderung (für Korrekturen/Nachforderungen)[cite: 1]
        elif name == "GZF":
            return {
                "Segment": "GZF",
                "Gesamtbetrag_Forderung_gesetzliche_Zuzahlung": self._safe_get(elements, 0),
                "Gesamtbetrag_Forderung_prozentuale_Zuzahlung": self._safe_get(elements, 1),
                "Forderung_pauschaler_Zuzahlungsbetrag": self._safe_get(elements, 2)
            }
            
        # Segment URI: Ursprüngliche Rechnung/Zahlung (bei Korrekturen)[cite: 1]
        elif name == "URI":
            ursp_rechnungs_element = self._safe_get(elements, 1, "").split(self.component_separator)
            return {
                "Segment": "URI",
                "Urspruengliches_IK_Leistungserbringer": self._safe_get(elements, 0),
                "Urspruengliche_Sammel_Rechnungsnummer": ursp_rechnungs_element[0] if len(ursp_rechnungs_element) > 0 else None,
                "Urspruengliche_Einzel_Rechnungsnummer": ursp_rechnungs_element[1] if len(ursp_rechnungs_element) > 1 else None,
                "Urspruengliches_Rechnungsdatum": self._safe_get(elements, 2),
                "Urspruengliche_Belegnummer": self._safe_get(elements, 3)
            }

        # Segment IMG: Imagename (bei Imagearchiven)[cite: 1]
        elif name == "IMG":
            return {
                "Segment": "IMG",
                "Abrechnungsjahr": self._safe_get(elements, 0),
                "Abrechnungsmonat": self._safe_get(elements, 1),
                "Identifikationsmerkmal": self._safe_get(elements, 2)
            }

        # Segment EVO: Elektronische Verordnung[cite: 1]
        elif name == "EVO":
            return {
                "Segment": "EVO",
                "eVO_ID": self._safe_get(elements, 0)
            }

        # Segment TXT: Textfeld (z.B. für Begründungen zu EHE)[cite: 1]
        elif name == "TXT":
            return {
                "Segment": "TXT",
                "Text": self._safe_get(elements, 0)
            }

        # Segment SKZ: Kostenzusage (nach ZHE)[cite: 1]
        elif name == "SKZ":
            return {
                "Segment": "SKZ",
                "Genehmigungskennzeichen": self._safe_get(elements, 0),
                "Datum_der_Genehmigung": self._safe_get(elements, 1),
                "Art_der_Genehmigung": self._safe_get(elements, 2)
            }

        # Segment UNB: Nutzdaten-Kopfsegment (Start der Datei)
        elif name == "UNB":
            syntax = self._safe_get(elements, 0, "").split(self.component_separator)
            sender = self._safe_get(elements, 1, "").split(self.component_separator)
            empfaenger = self._safe_get(elements, 2, "").split(self.component_separator)
            datum_zeit = self._safe_get(elements, 3, "").split(self.component_separator)
            
            return {
                "Segment": "UNB",
                "Syntax_Kennung": syntax[0] if len(syntax) > 0 else None,
                "Syntax_Version": syntax[1] if len(syntax) > 1 else None,
                "Absender": sender[0] if len(sender) > 0 else None,
                "Empfaenger": empfaenger[0] if len(empfaenger) > 0 else None,
                "Erstellungsdatum": datum_zeit[0] if len(datum_zeit) > 0 else None,
                "Erstellungszeit": datum_zeit[1] if len(datum_zeit) > 1 else None,
                "Datenaustauschreferenz": self._safe_get(elements, 4)
            }

        # Segment UNH: Nachrichten-Kopfsegment (Start einer Einzelnachricht)
        elif name == "UNH":
            nachrichten_kennung = self._safe_get(elements, 1, "").split(self.component_separator)
            
            return {
                "Segment": "UNH",
                "Nachrichtenreferenznummer": self._safe_get(elements, 0),
                "Nachrichtentyp": nachrichten_kennung[0] if len(nachrichten_kennung) > 0 else None,
                "Versionsnummer": nachrichten_kennung[1] if len(nachrichten_kennung) > 1 else None
            }

        # Segment UNT: Nachrichten-Endesegment (Schließt das UNH-Segment ab)
        elif name == "UNT":
            return {
                "Segment": "UNT",
                "Anzahl_Segmente_in_Nachricht": self._safe_get(elements, 0),
                "Nachrichtenreferenznummer": self._safe_get(elements, 1) # Muss identisch mit UNH sein
            }

        # Segment UNZ: Nutzdaten-Endesegment (Schließt das UNB-Segment ab)
        elif name == "UNZ":
            return {
                "Segment": "UNZ",
                "Anzahl_Nachrichten_in_Datei": self._safe_get(elements, 0),
                "Datenaustauschreferenz": self._safe_get(elements, 1) # Muss identisch mit UNB sein
            }
        
        # Segment NAM: Name (Erweiterte Namensangaben)
        elif name == "NAM":
            return {
                "Segment": "NAM",
                "Name_1": self._safe_get(elements, 0),
                "Name_2": self._safe_get(elements, 1),
                "Name_3": self._safe_get(elements, 2),
                "Name_4": self._safe_get(elements, 3)
            }

        # Segment GES: Gesamtsummen der Rechnung / des Datenaustauschs
        elif name == "GES":
            return {
                "Segment": "GES",
                "Betrag_1": self._safe_get(elements, 0),
                "Betrag_2": self._safe_get(elements, 1),
                "Betrag_3": self._safe_get(elements, 2),
                # Wir legen die Rohdaten dazu, falls es mehr Betragsfelder gibt
                "Rohdaten": elements 
            }

        # Rückgabe für Segmente, die noch nicht im Parser definiert sind
        return {"Segment": name, "Rohdaten": elements}
