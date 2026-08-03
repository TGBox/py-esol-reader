import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from esol_reader import EdifactSLLAParser

class EdifactViewerApp:
    def __init__(self, root, parser):
        self.root = root
        self.parser = parser
        
        self.root.title("EDIFACT SLLA Viewer - § 302 SGB V (Erweitert)")
        self.root.geometry("1000x700")
        
        self.full_hierarchy = []  # Speichert die vollständige Baumstruktur
        
        # --- UI Layout ---
        self.setup_ui()

    def setup_ui(self):
        # 1. Oberster Bereich: Buttons, Encoding und Suche
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X)

        self.btn_open = ttk.Button(top_frame, text="EDIFACT Datei öffnen...", command=self.load_file)
        self.btn_open.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_export = ttk.Button(top_frame, text="Daten exportieren...", command=self.export_data, state=tk.DISABLED)
        self.btn_export.pack(side=tk.LEFT, padx=(0, 10))

        # --- NEU: Buttons zum Auf- und Zuklappen ---
        self.btn_expand = ttk.Button(top_frame, text="Alles aufklappen", command=self.expand_all_tree, state=tk.DISABLED)
        self.btn_expand.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_collapse = ttk.Button(top_frame, text="Alles zuklappen", command=self.collapse_all_tree, state=tk.DISABLED)
        self.btn_collapse.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_filename = ttk.Label(top_frame, text="Keine Datei ausgewählt", foreground="gray")
        self.lbl_filename.pack(side=tk.LEFT, padx=(0, 20))

        # Encoding-Auswahl
        ttk.Label(top_frame, text="Encoding:").pack(side=tk.LEFT, padx=(5, 5))
        self.encoding_var = tk.StringVar(value="iso-8859-1")
        encoding_options = ["iso-8859-1", "windows-1252", "utf-8", "ascii"]
        self.combo_encoding = ttk.Combobox(top_frame, textvariable=self.encoding_var, values=encoding_options, width=12, state="readonly")
        self.combo_encoding.pack(side=tk.LEFT, padx=(0, 20))
        self.combo_encoding.bind("<<ComboboxSelected>>", self.reload_file_with_new_encoding)

        # Suchfeld
        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=tk.RIGHT)
        ttk.Label(search_frame, text="Suchen:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.perform_search())
        self.entry_search = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        self.entry_search.pack(side=tk.LEFT)

        # Integriertes Statistik-Dashboard
        self.stats_frame = ttk.LabelFrame(self.root, text="   📊 Abrechnungs-Dashboard & Kennzahlen", padding="10")
        self.stats_frame.pack(side=tk.TOP, fill=tk.X)

        self.stat_labels = {}
        metrics_keys = [
            ("sender", "Absender-IK:"),
            ("receiver", "Empfänger-IK:"),
            ("messages", "Nachrichten (UNH):"),
            ("invoices", "Rechnungen (REC):"),
            ("positions", "Positionen (EHE):"),
            ("total", "Summe Brutto:")
        ]

        for idx, (key, label_text) in enumerate(metrics_keys):
            r = idx // 3
            c = (idx % 3) * 2
            ttk.Label(self.stats_frame, text=label_text, font=("Arial", 9, "bold")).grid(row=r, column=c, sticky=tk.W, pady=2, padx=(0, 5))
            val_lbl = ttk.Label(self.stats_frame, text="-", font=("Arial", 9))
            val_lbl.grid(row=r, column=c+1, sticky=tk.W, pady=2, padx=(0, 30))
            self.stat_labels[key] = val_lbl

        # 2. Hauptbereich: Treeview
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(anchor="center", expand=True, fill=tk.BOTH)

        columns = ("Wert",)
        self.tree = ttk.Treeview(main_frame, columns=columns, selectmode="browse")
        self.tree.heading("#0", text="Segment / Struktur", anchor=tk.W)
        self.tree.heading("Wert", text="Inhalt / Wert", anchor=tk.W)
        self.tree.column("#0", width=400, minwidth=200)
        self.tree.column("Wert", width=550, minwidth=200)

        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')
        
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

    def load_file(self):
        filepath = filedialog.askopenfilename(
            title="Abrechnungsdatei auswählen",
            filetypes=[("Alle Dateien", "*.*"), ("Textdateien", "*.txt"), ("EDI Dateien", "*.edi")]
        )
        if not filepath: 
            return

        self.current_filepath = filepath
        self.lbl_filename.config(text=os.path.basename(filepath), foreground="black")
        self.search_var.set("")

        self.process_and_display()
        
        # --- Alle Aktions-Buttons nach erfolgreichem Laden aktivieren ---
        self.btn_export.config(state=tk.NORMAL)
        self.btn_expand.config(state=tk.NORMAL)
        self.btn_collapse.config(state=tk.NORMAL)

    def reload_file_with_new_encoding(self, event=None):
        """Wird aufgerufen, wenn im Dropdown ein anderes Encoding ausgewählt wird."""
        if hasattr(self, "current_filepath") and self.current_filepath:
            self.process_and_display()

    def process_and_display(self):
        """Lädt die Datei mit dem aktuell gewählten Encoding, aktualisiert den Baum und das Dashboard."""
        selected_encoding = self.encoding_var.get()
        
        try:
            flat_data = self.parse_file_with_encoding(self.current_filepath, selected_encoding)
            self.full_hierarchy = self.build_hierarchy(flat_data)
            self.display_tree(self.full_hierarchy)
            
            # --- NEU: Dashboard-Werte direkt aktualisieren ---
            self.update_statistics()
            
        except Exception as e:
            messagebox.showerror("Fehler beim Lesen", f"Die Datei konnte mit dem Encoding '{selected_encoding}' nicht gelesen werden:\n\n{e}")

    def update_statistics(self):
        """Berechnet die Kennzahlen aus der geladenen Hierarchie und füllt die Dashboard-Labels."""
        if not hasattr(self, "full_hierarchy") or not self.full_hierarchy:
            for lbl in self.stat_labels.values():
                lbl.config(text="-")
            return

        num_messages = 0
        num_invoices = 0
        num_positions = 0
        total_gross = 0.0
        sender = "Unbekannt"
        receiver = "Unbekannt"

        def analyze_nodes(nodes):
            nonlocal num_messages, num_invoices, num_positions, total_gross, sender, receiver
            for node in nodes:
                if node["type"] == "message":
                    num_messages += 1
                elif node["type"] == "invoice":
                    num_invoices += 1
                elif node["type"] == "segment":
                    seg_data = node["data"]
                    seg_name = seg_data.get("Segment")
                    
                    if seg_name == "UNB":
                        sender = seg_data.get("Absender", sender)
                        receiver = seg_data.get("Empfaenger", receiver)
                    elif seg_name == "EHE":
                        num_positions += 1
                        betrag = seg_data.get("Einzelbetrag")
                        if betrag:
                            try:
                                total_gross += float(betrag.replace(",", "."))
                            except ValueError:
                                pass
                    elif seg_name == "BES":
                        betrag = seg_data.get("Gesamtbetrag_Brutto")
                        if betrag:
                            try:
                                total_gross += float(betrag.replace(",", "."))
                            except ValueError:
                                pass
                                
                if "children" in node:
                    analyze_nodes(node["children"])

        analyze_nodes(self.full_hierarchy)

        # Labels im Dashboard aktualisieren
        self.stat_labels["sender"].config(text=sender)
        self.stat_labels["receiver"].config(text=receiver)
        self.stat_labels["messages"].config(text=str(num_messages))
        self.stat_labels["invoices"].config(text=str(num_invoices))
        self.stat_labels["positions"].config(text=str(num_positions))
        self.stat_labels["total"].config(text=f"{total_gross:,.2f} €" if total_gross > 0 else "0,00 €")
        
    def parse_file_with_encoding(self, file_path, encoding):
        """Hilfsfunktion, um die Datei mit einem spezifischen Zeichensatz einzulesen."""
        with open(file_path, 'r', encoding=encoding) as file:
            content = file.read().replace('\n', '').replace('\r', '')
            return self.parser.parse_content(content)

    # ==========================================
    # LOGIK: STRUKTURIERUNG DER DATEN
    # ==========================================
    def build_hierarchy(self, flat_data):
        """Wandelt die flache Segment-Liste in logische Gruppen um (Rechnungen, Nachrichten)."""
        root_nodes = []
        current_msg = None
        current_inv = None

        def add_to_current(node):
            if current_inv: current_inv["children"].append(node)
            elif current_msg: current_msg["children"].append(node)
            else: root_nodes.append(node)

        # 1. Gruppierung nach Nachrichten (UNH) und Rechnungen (REC)
        for index, seg in enumerate(flat_data):
            name = seg.get("Segment")
            node = {"type": "segment", "title": f"[{index+1:03d}] {name}", "data": seg}

            if name == "UNH":
                ref = seg.get('Nachrichtenreferenznummer', 'Unbekannt')
                current_msg = {"type": "message", "title": f"📁 Nachricht (UNH): {ref}", "children": [node]}
                root_nodes.append(current_msg)
                current_inv = None
            elif name == "UNT":
                add_to_current(node)
                current_msg = None
                current_inv = None
            elif name == "REC":
                sammel = seg.get('Sammel_Rechnungsnummer', '')
                einzel = seg.get('Einzel_Rechnungsnummer', '')
                current_inv = {"type": "invoice", "title": f"📄 Rechnung (REC): {sammel} : {einzel}", "children": [node]}
                if current_msg: current_msg["children"].append(current_inv)
                else: root_nodes.append(current_inv)
            else:
                add_to_current(node)

        # 2. Gruppierung fortlaufend identischer Segmente (z.B. mehrere EHE)
        def group_consecutive(children_list):
            new_list = []
            i = 0
            while i < len(children_list):
                curr = children_list[i]
                if curr["type"] == "segment":
                    seg_name = curr["data"].get("Segment")
                    count = 1
                    # Zählen, wie viele identische Segmente folgen
                    while i + count < len(children_list) and children_list[i+count]["type"] == "segment" and children_list[i+count]["data"].get("Segment") == seg_name:
                        count += 1
                    
                    # Wenn mehr als 1 und kein Struktur-Segment, dann bündeln
                    if count > 1 and seg_name not in ["UNB", "UNZ", "UNH", "UNT", "REC", "INV"]:
                        group_node = {"type": "group", "title": f"📑 {count}x {seg_name}-Segmente", "children": children_list[i:i+count]}
                        new_list.append(group_node)
                        i += count
                        continue
                elif curr["type"] in ["message", "invoice"]:
                    curr["children"] = group_consecutive(curr["children"])
                
                new_list.append(curr)
                i += 1
            return new_list

        return group_consecutive(root_nodes)

    # ==========================================
    # LOGIK: SUCHE & FILTERUNG
    # ==========================================
    def perform_search(self):
        query = self.search_var.get().strip().lower()
        if not query:
            # Keine Suche: Normalen Baum anzeigen, kein Highlighting
            self.display_tree(self.full_hierarchy, expand_all=False, query="")
            return

        filtered_hierarchy = self.filter_hierarchy(self.full_hierarchy, query)
        # Gefilterten Baum anzeigen und den Suchbegriff zum Markieren übergeben
        self.display_tree(filtered_hierarchy, expand_all=True, query=query)

    def filter_hierarchy(self, nodes, query):
        """Gibt Knoten zurück, bei denen der Titel, die Feldbeschreibungen (Keys) oder die Werte matchen."""
        filtered = []
        for node in nodes:
            node_matches = False
            
            # 1. Prüfe den Titel des Knotens (z.B. "📁 Nachricht (UNH)", "📄 Rechnung (REC)", Segment-Namen)
            if query in node.get("title", "").lower():
                node_matches = True
                
            # 2. Wenn es ein Segment ist, durchsuche sowohl die Schlüssel (Beschreibungen) als auch die Werte
            if node["type"] == "segment" and "data" in node:
                for key, val in node["data"].items():
                    # Prüft, ob der Suchbegriff im Feldnamen (Key) Oder im Inhalt (Value) steht
                    if query in str(key).lower() or (val is not None and query in str(val).lower()):
                        node_matches = True
                        break
            
            # 3. Kinder rekursiv durchsuchen
            filtered_children = []
            if "children" in node:
                filtered_children = self.filter_hierarchy(node["children"], query)
            
            # Wenn der Knoten selbst matcht Oder Kinder gematcht haben:
            if node_matches or filtered_children:
                new_node = node.copy()
                if node_matches:
                    # Wenn der Ordner/Knoten selbst matcht (z.B. der Rechnungs-Ordner), 
                    # zeigen wir standardmäßig alle Unterelemente an, falls keine spezifischen Kinder gefiltert wurden.
                    if "children" in node and not filtered_children:
                        new_node["children"] = node["children"]
                    elif filtered_children:
                        new_node["children"] = filtered_children
                else:
                    # Wenn er nur wegen seiner Kinder matcht, übernehmen wir nur die gefilterten Kinder
                    new_node["children"] = filtered_children
                
                filtered.append(new_node)
                
        return filtered

    # ==========================================
    # LOGIK: ANZEIGE
    # ==========================================
    def display_tree(self, hierarchy_data, expand_all=False, query=""):
        # Alte Baumstruktur komplett löschen
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Tag für die Hervorhebung definieren (Ein sanftes Gelb/Pastell)
        # Hinweis: Das funktioniert am besten, wenn das 'clam'-Theme aktiv ist (wird im __main__ gesetzt)
        self.tree.tag_configure("highlight", background="#FFF3CD") 

        # Rekursive Funktion zum Einfügen der Knoten mit Treffer-Prüfung
        def insert_nodes(parent_id, nodes):
            for node in nodes:
                title = node["title"]
                # Prüfen, ob der Titel des Ordners/Segments den Suchbegriff enthält
                title_match = query and (query in title.lower())
                
                if node["type"] == "segment":
                    # Tag setzen, falls der Segment-Titel matcht
                    seg_tags = ("highlight",) if title_match else ()
                    seg_id = self.tree.insert(parent_id, "end", text=title, open=expand_all, tags=seg_tags)
                    
                    for key, value in node["data"].items():
                        if key == "Segment": continue
                        display_value = value if value is not None else ""
                        
                        # Prüfen, ob Feldname (Key) Oder Inhalt (Value) den Suchbegriff enthält
                        kv_match = query and (query in str(key).lower() or query in str(display_value).lower())
                        item_tags = ("highlight",) if kv_match else ()
                        
                        self.tree.insert(seg_id, "end", text=f"  ↳ {key}", values=(display_value,), tags=item_tags)
                else:
                    # Ordner (Message, Invoice, Group) einfügen
                    group_tags = ("highlight",) if title_match else ()
                    group_id = self.tree.insert(parent_id, "end", text=title, open=expand_all, tags=group_tags)
                    insert_nodes(group_id, node["children"])

        insert_nodes("", hierarchy_data)
        
    def flatten_data_for_table(self):
        """Wandelt die Baumstruktur in eine flache Tabellenform für CSV und Excel um."""
        rows = []
        def traverse(nodes, context=""):
            for node in nodes:
                if node["type"] == "segment":
                    seg_name = node["data"].get("Segment", "")
                    for k, v in node["data"].items():
                        if k == "Segment": continue
                        rows.append({
                            "Kontext": context,
                            "Segment": seg_name,
                            "Feld": k,
                            "Wert": v if v is not None else ""
                        })
                else:
                    new_context = f"{context} > {node['title']}" if context else node['title']
                    if "children" in node:
                        traverse(node["children"], new_context)
        traverse(self.full_hierarchy)
        return rows

    def export_data(self):
        """Öffnet den Speichern-Dialog und exportiert je nach gewählter Dateiendung."""
        if not hasattr(self, "full_hierarchy") or not self.full_hierarchy:
            messagebox.showwarning("Keine Daten", "Es sind keine Daten zum Exportieren vorhanden.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[
                ("Excel Datei", "*.xlsx"),
                ("CSV Datei", "*.csv"),
                ("JSON Datei", "*.json"),
                ("PDF Dokument", "*.pdf")
            ],
            title="Daten exportieren..."
        )
        if not filepath:
            return

        ext = os.path.splitext(filepath)[1].lower()

        try:
            if ext == ".json":
                import json
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.full_hierarchy, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("Erfolg", f"Daten erfolgreich als JSON gespeichert unter:\n{filepath}")

            elif ext == ".csv":
                import csv
                rows = self.flatten_data_for_table()
                with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                    if rows:
                        writer = csv.DictWriter(f, fieldnames=["Kontext", "Segment", "Feld", "Wert"], delimiter=';')
                        writer.writeheader()
                        writer.writerows(rows)
                messagebox.showinfo("Erfolg", f"Daten erfolgreich als CSV gespeichert unter:\n{filepath}")

            elif ext == ".xlsx":
                import pandas as pd
                rows = self.flatten_data_for_table()
                df = pd.DataFrame(rows)
                df.to_excel(filepath, index=False)
                messagebox.showinfo("Erfolg", f"Daten erfolgreich als Excel-Datei gespeichert unter:\n{filepath}")

            elif ext == ".pdf":
                self.generate_pdf(filepath)

        except Exception as e:
            messagebox.showerror("Export-Fehler", f"Die Datei konnte nicht exportiert werden:\n\n{e}")

    def generate_pdf(self, filepath):
        """Generiert das PDF-Dokument (wie zuvor implementiert)."""

        doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=15, textColor=colors.HexColor("#1A365D"))
        h2_style = ParagraphStyle('ReportH2', parent=styles['Heading2'], fontSize=12, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#2B6CB0"))

        story.append(Paragraph("EDIFACT Abrechnungsbericht (§ 302 SGB V)", title_style))
        story.append(Paragraph(f"Quelldatei: {os.path.basename(getattr(self, 'current_filepath', 'Unbekannt'))}", styles['Normal']))
        story.append(Spacer(1, 15))

        def process_nodes_for_pdf(nodes):
            for node in nodes:
                story.append(Paragraph(node["title"], h2_style))
                table_data = []
                def collect_segment_data(n):
                    if n["type"] == "segment":
                        for k, v in n["data"].items():
                            if k == "Segment": continue
                            table_data.append([str(k), str(v if v is not None else "")])
                    elif "children" in n:
                        for child in n["children"]:
                            collect_segment_data(child)

                if "children" in node:
                    for child in node["children"]:
                        collect_segment_data(child)

                if table_data:
                    t = Table(table_data, colWidths=[200, 335])
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
                        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#2D3748")),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                        ('FONTSIZE', (0,0), (-1,-1), 9),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                        ('TOPPADDING', (0,0), (-1,-1), 4),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0"))
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 10))

        process_nodes_for_pdf(self.full_hierarchy)
        doc.build(story)
        messagebox.showinfo("Erfolg", f"Das PDF wurde erfolgreich gespeichert unter:\n{filepath}")
        
    def export_to_pdf(self):
        """Generiert ein übersichtliches PDF aus den geparsten Daten."""
        if not hasattr(self, "full_hierarchy") or not self.full_hierarchy:
            messagebox.showwarning("Keine Daten", "Es sind keine Daten zum Exportieren vorhanden.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Dokument", "*.pdf")],
            title="PDF Bericht speichern unter..."
        )
        if not filepath:
            return

        try:
            doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            story = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=15,
                textColor=colors.HexColor("#1A365D")
            )
            
            h2_style = ParagraphStyle(
                'ReportH2',
                parent=styles['Heading2'],
                fontSize=12,
                spaceBefore=10,
                spaceAfter=5,
                textColor=colors.HexColor("#2B6CB0")
            )

            story.append(Paragraph("EDIFACT Abrechnungsbericht (§ 302 SGB V)", title_style))
            story.append(Paragraph(f"Quelldatei: {os.path.basename(getattr(self, 'current_filepath', 'Unbekannt'))}", styles['Normal']))
            story.append(Spacer(1, 15))

            # Rekursive Funktion, um die Hierarchie in Tabellenstrukturen für das PDF zu gießen
            def process_nodes_for_pdf(nodes):
                for node in nodes:
                    story.append(Paragraph(node["title"], h2_style))
                    
                    table_data = []
                    def collect_segment_data(n):
                        if n["type"] == "segment":
                            for k, v in n["data"].items():
                                if k == "Segment": continue
                                table_data.append([str(k), str(v if v is not None else "")])
                        elif "children" in n:
                            for child in n["children"]:
                                collect_segment_data(child)

                    # Kinder sammeln und in eine Tabelle schreiben
                    if "children" in node:
                        for child in node["children"]:
                            collect_segment_data(child)

                    if table_data:
                        t = Table(table_data, colWidths=[200, 335])
                        t.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#2D3748")),
                            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                            ('FONTSIZE', (0,0), (-1,-1), 9),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                            ('TOPPADDING', (0,0), (-1,-1), 4),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0"))
                        ]))
                        story.append(t)
                        story.append(Spacer(1, 10))

            process_nodes_for_pdf(self.full_hierarchy)
            
            doc.build(story)
            messagebox.showinfo("Erfolg", f"Das PDF wurde erfolgreich gespeichert unter:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Fehler beim PDF-Export", f"Das PDF konnte nicht erstellt werden:\n\n{e}")
            
    def expand_all_tree(self):
        """Klappt alle Ordner und Segmente im Baum rekursiv auf."""
        def set_open_state(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                set_open_state(child)
        
        for root_item in self.tree.get_children():
            set_open_state(root_item)

    def collapse_all_tree(self):
        """Klappt alle Ordner und Segmente im Baum rekursiv zu."""
        def set_close_state(item):
            self.tree.item(item, open=False)
            for child in self.tree.get_children(item):
                set_close_state(child)
        
        for root_item in self.tree.get_children():
            set_close_state(root_item)

# --- Startpunkt des Programms ---
if __name__ == "__main__":
    # Parser instanziieren
    my_parser = EdifactSLLAParser()
    
    # Tkinter Fenster erstellen
    root = tk.Tk()
    
    # Optional: Ein bisschen modernes Theming aktivieren
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
        
    # App starten
    app = EdifactViewerApp(root, my_parser)
    root.mainloop()