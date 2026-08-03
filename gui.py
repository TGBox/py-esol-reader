import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

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
        # --- Oberer Bereich: Buttons und Suche ---
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X)

        # Dateiauswahl
        self.btn_open = ttk.Button(top_frame, text="EDIFACT Datei öffnen...", command=self.load_file)
        self.btn_open.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_filename = ttk.Label(top_frame, text="Keine Datei ausgewählt", foreground="gray")
        self.lbl_filename.pack(side=tk.LEFT)

        # Suchfeld
        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=tk.RIGHT)
        
        ttk.Label(search_frame, text="Suchen:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        # Sobald sich der Text im Suchfeld ändert, wird die Suche ausgelöst
        self.search_var.trace_add("write", lambda *args: self.perform_search())
        self.entry_search = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.entry_search.pack(side=tk.LEFT)

        # --- Hauptbereich: Treeview ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

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
        if not filepath: return

        self.lbl_filename.config(text=os.path.basename(filepath), foreground="black")
        self.search_var.set("") # Suche zurücksetzen beim Neuladen

        try:
            # 1. Daten parsen
            flat_data = self.parser.parse_file(filepath)
            # 2. Daten hierarchisch strukturieren
            self.full_hierarchy = self.build_hierarchy(flat_data)
            # 3. Struktur anzeigen
            self.display_tree(self.full_hierarchy)
        except Exception as e:
            messagebox.showerror("Fehler beim Lesen", f"Die Datei konnte nicht verarbeitet werden:\n\n{e}")

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
            # Keine Suche: Kompletten Baum anzeigen
            self.display_tree(self.full_hierarchy, expand_all=False)
            return

        filtered_hierarchy = self.filter_hierarchy(self.full_hierarchy, query)
        # Bei Suchtreffern klappen wir den Baum automatisch auf
        self.display_tree(filtered_hierarchy, expand_all=True)

    def filter_hierarchy(self, nodes, query):
        """Gibt nur die Knoten zurück, die den Suchbegriff enthalten (oder deren Kinder)."""
        filtered = []
        for node in nodes:
            if node["type"] == "segment":
                # Prüfe, ob einer der Werte im Segment den Suchbegriff enthält
                match = any(query in str(v).lower() for v in node["data"].values() if v is not None)
                # Alternativ auch den Segment-Namen durchsuchen
                if query in node["data"].get("Segment", "").lower():
                    match = True
                    
                if match:
                    filtered.append(node)
            else:
                # Es ist ein Ordner (Message, Invoice, Group) -> Kinder durchsuchen
                filtered_children = self.filter_hierarchy(node["children"], query)
                if filtered_children:
                    new_node = node.copy()
                    new_node["children"] = filtered_children
                    filtered.append(new_node)
        return filtered

    # ==========================================
    # LOGIK: ANZEIGE
    # ==========================================
    def display_tree(self, hierarchy_data, expand_all=False):
        # Alte Baumstruktur komplett löschen
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Rekursive Funktion zum Einfügen der Knoten
        def insert_nodes(parent_id, nodes):
            for node in nodes:
                if node["type"] == "segment":
                    # Ein normales Segment eintragen
                    seg_id = self.tree.insert(parent_id, "end", text=node["title"], open=expand_all)
                    for key, value in node["data"].items():
                        if key == "Segment": continue
                        display_value = value if value is not None else ""
                        self.tree.insert(seg_id, "end", text=f"  ↳ {key}", values=(display_value,))
                else:
                    # Ein Ordner (Nachricht, Rechnung, EHE-Gruppe)
                    group_id = self.tree.insert(parent_id, "end", text=node["title"], open=expand_all)
                    insert_nodes(group_id, node["children"])

        insert_nodes("", hierarchy_data)

# --- (Der if __name__ == "__main__": Block bleibt wie vorher) ---


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