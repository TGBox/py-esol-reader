import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

from esol_reader import EdifactSLLAParser

class EdifactViewerApp:
    def __init__(self, root, parser):
        self.root = root
        self.parser = parser
        
        self.root.title("EDIFACT SLLA Viewer - § 302 SGB V")
        self.root.geometry("900x600")
        
        # --- UI Layout ---
        self.setup_ui()

    def setup_ui(self):
        # Oberer Bereich: Buttons und Datei-Info
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X)

        self.btn_open = ttk.Button(top_frame, text="EDIFACT Datei öffnen...", command=self.load_file)
        self.btn_open.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_filename = ttk.Label(top_frame, text="Keine Datei ausgewählt", foreground="gray")
        self.lbl_filename.pack(side=tk.LEFT)

        # Hauptbereich: Treeview (Baumstruktur) für die Daten
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

        # Treeview erstellen
        columns = ("Wert",)
        self.tree = ttk.Treeview(main_frame, columns=columns, selectmode="browse")
        
        # Spalten formatieren
        self.tree.heading("#0", text="Segment / Feld", anchor=tk.W)
        self.tree.heading("Wert", text="Inhalt / Wert", anchor=tk.W)
        
        self.tree.column("#0", width=350, minwidth=200)
        self.tree.column("Wert", width=500, minwidth=200)

        # Scrollbars hinzufügen
        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Layout der Treeview und Scrollbars
        self.tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')
        
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

    def load_file(self):
        """Öffnet einen Dateidialog und lädt die ausgewählte Datei."""
        filepath = filedialog.askopenfilename(
            title="Abrechnungsdatei auswählen",
            filetypes=[("Alle Dateien", "*.*"), ("Textdateien", "*.txt"), ("EDI Dateien", "*.edi")]
        )
        
        if not filepath:
            return # Abgebrochen durch Nutzer

        # Dateinamen im Label aktualisieren
        self.lbl_filename.config(text=os.path.basename(filepath), foreground="black")

        # Daten parsen
        try:
            parsed_data = self.parser.parse_file(filepath)
            self.display_data(parsed_data)
        except Exception as e:
            messagebox.showerror("Fehler beim Lesen", f"Die Datei konnte nicht verarbeitet werden:\n\n{e}")

    def display_data(self, data):
        """Füllt die Treeview mit den geparsten Daten."""
        # Alte Einträge löschen
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Neue Daten eintragen
        for index, segment_dict in enumerate(data):
            # Segment-Name ermitteln (z.B. "REC", "INV")
            seg_name = segment_dict.get("Segment", "Unbekannt")
            
            # Hauptknoten für das Segment anlegen (z.B. "[01] Segment: INV")
            parent_text = f"[{index + 1:02d}] Segment: {seg_name}"
            
            # open=True sorgt dafür, dass die Basis-Segmente wie FKT, REC, INV direkt aufgeklappt sind
            # Bei sehr vielen EHE-Segmenten empfiehlt es sich vielleicht, open=False zu setzen.
            parent_id = self.tree.insert("", "end", text=parent_text, open=False)

            # Alle Felder dieses Segments als Unterknoten anhängen
            for key, value in segment_dict.items():
                if key == "Segment": 
                    continue # Haben wir schon im Parent-Knoten stehen
                
                # Leere Werte (None) als leeren String anzeigen
                display_value = value if value is not None else ""
                
                self.tree.insert(parent_id, "end", text=f"  {key}", values=(display_value,))


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