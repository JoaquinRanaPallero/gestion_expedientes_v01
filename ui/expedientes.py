"""Panel de lista y gestion de expedientes."""

import tkinter as tk
from tkinter import ttk, messagebox

import database as db
from models import Expediente
from ui.dialogs import FormDialog, confirmar, fecha_hoy, fecha_display
from ui.detalle_expediente import VentanaDetalleExpediente


def _campos_expediente():
    """Genera los campos cada vez para que fecha_hoy() sea actual."""
    return [
        {"name": "numero", "label": "Numero"},
        {"name": "caratula", "label": "Caratula", "required": True},
        {"name": "fuero_juzgado", "label": "Fuero / Juzgado"},
        {"name": "fecha_inicio", "label": "Fecha inicio (DD/MM/AAAA)", "validate": "fecha",
         "default": fecha_hoy()},
        {"name": "tipo_proceso", "label": "Tipo de proceso"},
        {"name": "estado", "label": "Estado", "type": "combo",
         "options": ["activo", "archivado", "cerrado"], "default": "activo"},
        {"name": "observaciones", "label": "Observaciones", "type": "text"},
    ]


class PanelExpedientes(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        # Titulo
        header = ttk.Frame(self)
        header.pack(fill="x", padx=15, pady=(15, 5))
        ttk.Label(header, text="Expedientes", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="+ Nuevo expediente", command=self._nuevo,
                   style="Primary.TButton").pack(side="right")

        # Filtros
        filtros = ttk.Frame(self)
        filtros.pack(fill="x", padx=15, pady=5)

        ttk.Label(filtros, text="Buscar:").pack(side="left", padx=(0, 5))
        self.filtro_numero = ttk.Entry(filtros, width=15)
        self.filtro_numero.pack(side="left", padx=2)
        self.filtro_numero.insert(0, "")
        self.filtro_numero.bind("<KeyRelease>", lambda e: self.refrescar())

        ttk.Label(filtros, text="Caratula:").pack(side="left", padx=(10, 5))
        self.filtro_caratula = ttk.Entry(filtros, width=20)
        self.filtro_caratula.pack(side="left", padx=2)
        self.filtro_caratula.bind("<KeyRelease>", lambda e: self.refrescar())

        ttk.Label(filtros, text="Estado:").pack(side="left", padx=(10, 5))
        self.filtro_estado = ttk.Combobox(filtros, values=["", "activo", "archivado", "cerrado"],
                                          state="readonly", width=12)
        self.filtro_estado.set("")
        self.filtro_estado.pack(side="left", padx=2)
        self.filtro_estado.bind("<<ComboboxSelected>>", lambda e: self.refrescar())

        ttk.Label(filtros, text="Juzgado:").pack(side="left", padx=(10, 5))
        self.filtro_juzgado = ttk.Entry(filtros, width=15)
        self.filtro_juzgado.pack(side="left", padx=2)
        self.filtro_juzgado.bind("<KeyRelease>", lambda e: self.refrescar())

        # Tabla
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=15, pady=10)

        cols = ("numero", "caratula", "fuero_juzgado", "fecha_inicio", "tipo_proceso", "estado", "ultimo_mov")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        headers = {
            "numero": ("Numero", 120),
            "caratula": ("Caratula", 250),
            "fuero_juzgado": ("Fuero / Juzgado", 180),
            "fecha_inicio": ("Fecha Inicio", 100),
            "tipo_proceso": ("Tipo Proceso", 120),
            "estado": ("Estado", 80),
            "ultimo_mov": ("Ultimo Mov.", 110),
        }
        self._sort_col = ""
        self._sort_reverse = False
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text,
                              command=lambda c=col: self._ordenar_por(c))
            self.tree.column(col, width=width, minwidth=60)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self._ver_detalle_pasos())

        # Botones inferiores
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        ttk.Button(btn_frame, text="Ver detalle", command=self._ver_detalle).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Editar", command=self._editar).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Eliminar", command=self._eliminar,
                   style="Danger.TButton").pack(side="left", padx=2)

    def refrescar(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        expedientes = db.listar_expedientes(
            filtro_numero=self.filtro_numero.get().strip(),
            filtro_caratula=self.filtro_caratula.get().strip(),
            filtro_estado=self.filtro_estado.get(),
            filtro_juzgado=self.filtro_juzgado.get().strip(),
        )
        ultimos = db.obtener_ultimos_movimientos()
        for exp in expedientes:
            ultimo = fecha_display(ultimos.get(exp.id, "")) or "-"
            self.tree.insert("", "end", iid=str(exp.id), values=(
                exp.numero, exp.caratula, exp.fuero_juzgado,
                fecha_display(exp.fecha_inicio), exp.tipo_proceso, exp.estado, ultimo,
            ))

    def _ordenar_por(self, col: str):
        """Ordena el Treeview al clickear en el header de una columna."""
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        items = [(self.tree.set(iid, col), iid) for iid in self.tree.get_children()]

        # Para columnas de fecha (DD/MM/AAAA) convertir a AAAA-MM-DD para ordenar bien
        fecha_cols = {"fecha_inicio", "ultimo_mov"}
        if col in fecha_cols:
            def fecha_key(val: str) -> str:
                if not val or val == "-":
                    return "0000-00-00"
                try:
                    parts = val.split("/")
                    return f"{parts[2]}-{parts[1]}-{parts[0]}"
                except (IndexError, ValueError):
                    return val
            items.sort(key=lambda t: fecha_key(t[0]), reverse=self._sort_reverse)
        else:
            items.sort(key=lambda t: t[0].lower(), reverse=self._sort_reverse)

        for idx, (_, iid) in enumerate(items):
            self.tree.move(iid, "", idx)

        # Indicador visual en el header
        arrow = " ▼" if self._sort_reverse else " ▲"
        headers = {
            "numero": "Numero", "caratula": "Caratula",
            "fuero_juzgado": "Fuero / Juzgado", "fecha_inicio": "Fecha Inicio",
            "tipo_proceso": "Tipo Proceso", "estado": "Estado",
            "ultimo_mov": "Ultimo Mov.",
        }
        for c, text in headers.items():
            self.tree.heading(c, text=text + (arrow if c == col else ""))

    def _get_selected_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleccionar", "Seleccione un expediente.", parent=self)
            return None
        return int(sel[0])

    def _nuevo(self):
        dlg = FormDialog(self, "Nuevo Expediente", _campos_expediente())
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            numero = r["numero"]
            if numero and db.numero_existe(numero):
                messagebox.showwarning("Numero duplicado",
                                       f"Ya existe un expediente con numero '{numero}'.\n"
                                       "Se guardara el expediente sin numero.",
                                       parent=self)
                numero = ""
            exp = Expediente(
                numero=numero, caratula=r["caratula"],
                fuero_juzgado=r["fuero_juzgado"], fecha_inicio=r["fecha_inicio"],
                tipo_proceso=r["tipo_proceso"], estado=r["estado"],
                observaciones=r["observaciones"],
            )
            try:
                db.crear_expediente(exp)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear el expediente:\n{e}", parent=self)
                return
            self.refrescar()

    def _editar(self):
        exp_id = self._get_selected_id()
        if exp_id is None:
            return
        exp = db.obtener_expediente(exp_id)
        if not exp:
            return

        values = {
            "numero": exp.numero, "caratula": exp.caratula,
            "fuero_juzgado": exp.fuero_juzgado, "fecha_inicio": fecha_display(exp.fecha_inicio),
            "tipo_proceso": exp.tipo_proceso, "estado": exp.estado,
            "observaciones": exp.observaciones,
        }
        dlg = FormDialog(self, "Editar Expediente", _campos_expediente(), values)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            numero = r["numero"]
            if numero and db.numero_existe(numero, excluir_id=exp_id):
                messagebox.showwarning("Numero duplicado",
                                       f"Ya existe otro expediente con numero '{numero}'.\n"
                                       "Se guardara el expediente sin numero.",
                                       parent=self)
                numero = ""
            exp.numero = numero
            exp.caratula = r["caratula"]
            exp.fuero_juzgado = r["fuero_juzgado"]
            exp.fecha_inicio = r["fecha_inicio"]
            exp.tipo_proceso = r["tipo_proceso"]
            exp.estado = r["estado"]
            exp.observaciones = r["observaciones"]
            try:
                db.actualizar_expediente(exp)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el expediente:\n{e}", parent=self)
                return
            self.refrescar()

    def _eliminar(self):
        exp_id = self._get_selected_id()
        if exp_id is None:
            return
        exp = db.obtener_expediente(exp_id)
        if exp and confirmar(self, f"Eliminar expediente '{exp.numero or exp.caratula}'?\n"
                                    "Se eliminaran todas las partes, pasos, vencimientos, "
                                    "honorarios y gastos asociados."):
            try:
                db.eliminar_expediente(exp_id)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el expediente:\n{e}", parent=self)
                return
            self.refrescar()

    def _ver_detalle(self):
        exp_id = self._get_selected_id()
        if exp_id is None:
            return
        VentanaDetalleExpediente(self, exp_id)

    def _ver_detalle_pasos(self):
        exp_id = self._get_selected_id()
        if exp_id is None:
            return
        VentanaDetalleExpediente(self, exp_id, initial_tab=2)
