"""Vista global de vencimientos de todos los expedientes."""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

import database as db
from models import Vencimiento
from ui.dialogs import fecha_display
from ui.styles import COLOR_VENCIDO, COLOR_INMINENTE, COLOR_CUMPLIDO


class PanelVencimientosGlobales(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._venc_data: dict[str, dict] = {}
        self._build()

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=15, pady=(15, 5))
        ttk.Label(header, text="Vencimientos Globales", style="Title.TLabel").pack(side="left")

        # Filtro por estado + boton cambiar estado
        filtro_frame = ttk.Frame(self)
        filtro_frame.pack(fill="x", padx=15, pady=5)
        ttk.Label(filtro_frame, text="Filtrar estado:").pack(side="left", padx=(0, 5))
        self.filtro_estado = ttk.Combobox(
            filtro_frame, values=["", "pendiente", "cumplido", "vencido"],
            state="readonly", width=12)
        self.filtro_estado.set("")
        self.filtro_estado.pack(side="left")
        self.filtro_estado.bind("<<ComboboxSelected>>", lambda e: self.refrescar())

        ttk.Label(filtro_frame, text="   Cambiar a:").pack(side="left", padx=(20, 5))
        self.combo_nuevo_estado = ttk.Combobox(
            filtro_frame, values=["pendiente", "cumplido", "vencido"],
            state="readonly", width=12)
        self.combo_nuevo_estado.set("cumplido")
        self.combo_nuevo_estado.pack(side="left", padx=(0, 5))
        ttk.Button(filtro_frame, text="Aplicar", command=self._cambiar_estado).pack(side="left")

        # Tabla
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=15, pady=10)

        cols = ("fecha", "caratula", "descripcion", "estado")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("fecha", text="Fecha")
        self.tree.column("fecha", width=110, minwidth=80)
        self.tree.heading("caratula", text="Expediente (Caratula)")
        self.tree.column("caratula", width=250, minwidth=120)
        self.tree.heading("descripcion", text="Descripcion")
        self.tree.column("descripcion", width=300, minwidth=150)
        self.tree.heading("estado", text="Estado")
        self.tree.column("estado", width=100, minwidth=70)

        self.tree.tag_configure("vencido", foreground="white", background=COLOR_VENCIDO)
        self.tree.tag_configure("inminente", foreground="#000", background="#ffeaa7")
        self.tree.tag_configure("cumplido", foreground="white", background=COLOR_CUMPLIDO)
        self.tree.tag_configure("pendiente", foreground="#2c3e50")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Leyenda
        leyenda = ttk.Frame(self)
        leyenda.pack(fill="x", padx=15, pady=(0, 15))
        for color, texto in [(COLOR_VENCIDO, "Vencido"), ("#ffeaa7", "Proximo 5 dias"),
                              (COLOR_CUMPLIDO, "Cumplido")]:
            tk.Canvas(leyenda, width=14, height=14, bg=color, highlightthickness=0).pack(
                side="left", padx=(0, 3))
            ttk.Label(leyenda, text=texto).pack(side="left", padx=(0, 15))

    def _cambiar_estado(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleccionar", "Seleccione un vencimiento.", parent=self)
            return
        nuevo_estado = self.combo_nuevo_estado.get()
        if not nuevo_estado:
            return
        iid = sel[0]
        v_data = self._venc_data.get(iid)
        if not v_data:
            return
        venc = Vencimiento(id=v_data["id"], expediente_id=v_data["expediente_id"],
                           fecha=v_data["fecha"], descripcion=v_data["descripcion"],
                           estado=nuevo_estado)
        try:
            db.actualizar_vencimiento(venc)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cambiar el estado:\n{e}", parent=self)
            return
        self.refrescar()

    def refrescar(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._venc_data.clear()

        hoy = datetime.now().date()
        limite = hoy + timedelta(days=5)

        vencimientos = db.listar_vencimientos_globales(self.filtro_estado.get())
        for v in vencimientos:
            tag = "pendiente"
            if v["estado"] == "cumplido":
                tag = "cumplido"
            elif v["estado"] == "vencido":
                tag = "vencido"
            else:
                try:
                    fv = datetime.strptime(v["fecha"], "%Y-%m-%d").date()
                    if fv < hoy:
                        tag = "vencido"
                    elif fv <= limite:
                        tag = "inminente"
                except ValueError:
                    pass

            iid = str(v["id"])
            self._venc_data[iid] = v
            estado_display = "vencido" if tag == "vencido" else v["estado"]
            self.tree.insert("", "end", iid=iid, values=(
                fecha_display(v["fecha"]), v["expediente_caratula"], v["descripcion"], estado_display
            ), tags=(tag,))
