"""Panel de detalle de expediente con solapas internas."""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

import database as db
from models import Parte, PasoProcesal, Vencimiento, Honorario, Gasto
from ui.dialogs import FormDialog, confirmar, fecha_hoy, fecha_display
from ui.styles import COLOR_VENCIDO, COLOR_INMINENTE, COLOR_CUMPLIDO


class VentanaDetalleExpediente(tk.Toplevel):
    def __init__(self, parent, expediente_id: int, initial_tab: int = 0):
        super().__init__(parent)
        self.exp_id = expediente_id
        self.exp = db.obtener_expediente(expediente_id)
        if not self.exp:
            messagebox.showerror("Error", "Expediente no encontrado.", parent=parent)
            self.destroy()
            return

        self._parent_panel = parent
        self.title(f"Expediente: {self.exp.numero or self.exp.caratula}")
        self.geometry("950x650")
        self.minsize(800, 500)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()
        if initial_tab > 0:
            self.notebook.select(initial_tab)

    def _on_close(self):
        """Al cerrar, refresca la lista de expedientes del panel padre."""
        if hasattr(self._parent_panel, "refrescar"):
            self._parent_panel.refrescar()
        self.destroy()

    def _build(self):
        # Header con datos basicos
        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")
        titulo = f"{self.exp.numero} - {self.exp.caratula}" if self.exp.numero else self.exp.caratula
        ttk.Label(header, text=titulo, style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=f"Estado: {self.exp.estado.upper()}",
                  style="Subtitle.TLabel").pack(side="right")

        # Notebook con solapas
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._tab_datos()
        self._tab_partes()
        self._tab_pasos()
        self._tab_vencimientos()
        self._tab_honorarios()
        self._tab_gastos()

    # --- Solapa Datos ---
    def _tab_datos(self):
        frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(frame, text="Datos")

        ultimo_mov = db.obtener_ultimo_movimiento(self.exp_id)
        campos = [
            ("Numero", self.exp.numero),
            ("Caratula", self.exp.caratula),
            ("Fuero / Juzgado", self.exp.fuero_juzgado),
            ("Fecha de inicio", fecha_display(self.exp.fecha_inicio)),
            ("Tipo de proceso", self.exp.tipo_proceso),
            ("Estado", self.exp.estado),
            ("Ultimo movimiento", fecha_display(ultimo_mov) if ultimo_mov else "Sin movimientos"),
            ("Observaciones", self.exp.observaciones),
        ]
        for i, (label, valor) in enumerate(campos):
            ttk.Label(frame, text=f"{label}:", font=("Segoe UI", 10, "bold")).grid(
                row=i, column=0, sticky="nw", pady=4, padx=(0, 15))
            ttk.Label(frame, text=valor or "-", wraplength=600).grid(
                row=i, column=1, sticky="w", pady=4)

    # --- Solapa Partes ---
    def _tab_partes(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Partes")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(0, 5))
        ttk.Button(btn_frame, text="+ Agregar parte", command=self._nueva_parte).pack(side="left")
        ttk.Button(btn_frame, text="Editar", command=self._editar_parte).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Eliminar", command=self._eliminar_parte).pack(side="left")

        cols = ("nombre", "tipo", "dni_cuit", "domicilio", "telefono", "email")
        self.tree_partes = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        headers = {"nombre": 180, "tipo": 100, "dni_cuit": 110,
                   "domicilio": 200, "telefono": 110, "email": 160}
        for col, w in headers.items():
            self.tree_partes.heading(col, text=col.replace("_", " ").title())
            self.tree_partes.column(col, width=w, minwidth=50)

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree_partes.yview)
        self.tree_partes.configure(yscrollcommand=sb.set)
        self.tree_partes.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._refrescar_partes()

    def _refrescar_partes(self):
        for item in self.tree_partes.get_children():
            self.tree_partes.delete(item)
        for p in db.listar_partes(self.exp_id):
            self.tree_partes.insert("", "end", iid=str(p.id),
                                    values=(p.nombre, p.tipo, p.dni_cuit,
                                            p.domicilio, p.telefono, p.email))

    def _campos_parte(self):
        return [
            {"name": "nombre", "label": "Nombre completo", "required": True},
            {"name": "tipo", "label": "Tipo", "type": "combo",
             "options": ["actor", "demandado", "tercero", "perito", "testigo", "otro"]},
            {"name": "dni_cuit", "label": "DNI / CUIT"},
            {"name": "domicilio", "label": "Domicilio"},
            {"name": "telefono", "label": "Telefono"},
            {"name": "email", "label": "Email"},
        ]

    def _nueva_parte(self):
        dlg = FormDialog(self, "Nueva Parte", self._campos_parte())
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            try:
                db.crear_parte(Parte(expediente_id=self.exp_id, nombre=r["nombre"],
                                     tipo=r["tipo"], dni_cuit=r["dni_cuit"],
                                     domicilio=r["domicilio"], telefono=r["telefono"],
                                     email=r["email"]))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la parte:\n{e}", parent=self)
                return
            self._refrescar_partes()

    def _editar_parte(self):
        sel = self.tree_partes.selection()
        if not sel:
            messagebox.showinfo("Seleccionar", "Seleccione una parte.", parent=self)
            return
        parte_id = int(sel[0])
        partes = db.listar_partes(self.exp_id)
        parte = next((p for p in partes if p.id == parte_id), None)
        if not parte:
            return
        values = {"nombre": parte.nombre, "tipo": parte.tipo, "dni_cuit": parte.dni_cuit,
                  "domicilio": parte.domicilio, "telefono": parte.telefono, "email": parte.email}
        dlg = FormDialog(self, "Editar Parte", self._campos_parte(), values)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            parte.nombre = r["nombre"]
            parte.tipo = r["tipo"]
            parte.dni_cuit = r["dni_cuit"]
            parte.domicilio = r["domicilio"]
            parte.telefono = r["telefono"]
            parte.email = r["email"]
            try:
                db.actualizar_parte(parte)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar la parte:\n{e}", parent=self)
                return
            self._refrescar_partes()

    def _eliminar_parte(self):
        sel = self.tree_partes.selection()
        if not sel:
            return
        if confirmar(self, "Eliminar la parte seleccionada?"):
            try:
                db.eliminar_parte(int(sel[0]))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar la parte:\n{e}", parent=self)
                return
            self._refrescar_partes()

    # --- Solapa Pasos Procesales ---
    def _tab_pasos(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Pasos Procesales")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(0, 5))
        ttk.Button(btn_frame, text="+ Agregar paso", command=self._nuevo_paso).pack(side="left")
        ttk.Button(btn_frame, text="Editar", command=self._editar_paso).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Eliminar", command=self._eliminar_paso).pack(side="left")

        cols = ("fecha", "descripcion", "observaciones")
        self.tree_pasos = ttk.Treeview(frame, columns=cols, show="headings", height=12)
        self.tree_pasos.heading("fecha", text="Fecha")
        self.tree_pasos.column("fecha", width=100, minwidth=80)
        self.tree_pasos.heading("descripcion", text="Descripcion")
        self.tree_pasos.column("descripcion", width=350, minwidth=150)
        self.tree_pasos.heading("observaciones", text="Observaciones")
        self.tree_pasos.column("observaciones", width=300, minwidth=100)

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree_pasos.yview)
        self.tree_pasos.configure(yscrollcommand=sb.set)
        self.tree_pasos.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._refrescar_pasos()

    def _refrescar_pasos(self):
        for item in self.tree_pasos.get_children():
            self.tree_pasos.delete(item)
        for p in db.listar_pasos(self.exp_id):
            self.tree_pasos.insert("", "end", iid=str(p.id),
                                   values=(fecha_display(p.fecha), p.descripcion, p.observaciones))

    def _campos_paso(self):
        return [
            {"name": "fecha", "label": "Fecha (DD/MM/AAAA)", "required": True,
             "validate": "fecha", "default": fecha_hoy()},
            {"name": "descripcion", "label": "Descripcion", "required": True},
            {"name": "observaciones", "label": "Observaciones", "type": "text", "height": 8},
        ]

    def _nuevo_paso(self):
        dlg = FormDialog(self, "Nuevo Paso Procesal", self._campos_paso())
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            try:
                db.crear_paso(PasoProcesal(expediente_id=self.exp_id, fecha=r["fecha"],
                                           descripcion=r["descripcion"],
                                           observaciones=r["observaciones"]))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear el paso:\n{e}", parent=self)
                return
            self._refrescar_pasos()

    def _editar_paso(self):
        sel = self.tree_pasos.selection()
        if not sel:
            messagebox.showinfo("Seleccionar", "Seleccione un paso.", parent=self)
            return
        paso_id = int(sel[0])
        pasos = db.listar_pasos(self.exp_id)
        paso = next((p for p in pasos if p.id == paso_id), None)
        if not paso:
            return
        values = {"fecha": fecha_display(paso.fecha), "descripcion": paso.descripcion,
                  "observaciones": paso.observaciones}
        dlg = FormDialog(self, "Editar Paso Procesal", self._campos_paso(), values)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            paso.fecha = r["fecha"]
            paso.descripcion = r["descripcion"]
            paso.observaciones = r["observaciones"]
            try:
                db.actualizar_paso(paso)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el paso:\n{e}", parent=self)
                return
            self._refrescar_pasos()

    def _eliminar_paso(self):
        sel = self.tree_pasos.selection()
        if not sel:
            return
        if confirmar(self, "Eliminar el paso procesal seleccionado?"):
            try:
                db.eliminar_paso(int(sel[0]))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el paso:\n{e}", parent=self)
                return
            self._refrescar_pasos()

    # --- Solapa Vencimientos ---
    def _tab_vencimientos(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Vencimientos")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(0, 5))
        ttk.Button(btn_frame, text="+ Agregar vencimiento",
                   command=self._nuevo_vencimiento).pack(side="left")
        ttk.Button(btn_frame, text="Editar",
                   command=self._editar_vencimiento).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Eliminar",
                   command=self._eliminar_vencimiento).pack(side="left")

        cols = ("fecha", "descripcion", "estado")
        self.tree_venc = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        self.tree_venc.heading("fecha", text="Fecha")
        self.tree_venc.column("fecha", width=100)
        self.tree_venc.heading("descripcion", text="Descripcion")
        self.tree_venc.column("descripcion", width=400)
        self.tree_venc.heading("estado", text="Estado")
        self.tree_venc.column("estado", width=100)

        self.tree_venc.tag_configure("vencido", foreground=COLOR_VENCIDO)
        self.tree_venc.tag_configure("inminente", foreground=COLOR_INMINENTE)
        self.tree_venc.tag_configure("cumplido", foreground=COLOR_CUMPLIDO)

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree_venc.yview)
        self.tree_venc.configure(yscrollcommand=sb.set)
        self.tree_venc.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._refrescar_vencimientos()

    def _refrescar_vencimientos(self):
        for item in self.tree_venc.get_children():
            self.tree_venc.delete(item)
        hoy = datetime.now().date()
        limite = hoy + timedelta(days=5)
        for v in db.listar_vencimientos(self.exp_id):
            tag = ""
            if v.estado == "cumplido":
                tag = "cumplido"
            elif v.estado == "vencido":
                tag = "vencido"
            else:
                try:
                    fv = datetime.strptime(v.fecha, "%Y-%m-%d").date()
                    if fv < hoy:
                        tag = "vencido"
                    elif fv <= limite:
                        tag = "inminente"
                except ValueError:
                    pass
            estado_display = "vencido" if tag == "vencido" else v.estado
            self.tree_venc.insert("", "end", iid=str(v.id),
                                  values=(fecha_display(v.fecha), v.descripcion, estado_display), tags=(tag,))

    def _campos_vencimiento(self):
        return [
            {"name": "fecha", "label": "Fecha (DD/MM/AAAA)", "required": True,
             "validate": "fecha", "default": fecha_hoy()},
            {"name": "descripcion", "label": "Descripcion", "required": True},
            {"name": "estado", "label": "Estado", "type": "combo",
             "options": ["pendiente", "cumplido", "vencido"], "default": "pendiente"},
        ]

    def _nuevo_vencimiento(self):
        dlg = FormDialog(self, "Nuevo Vencimiento", self._campos_vencimiento())
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            try:
                db.crear_vencimiento(Vencimiento(expediente_id=self.exp_id, fecha=r["fecha"],
                                                 descripcion=r["descripcion"], estado=r["estado"]))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear el vencimiento:\n{e}", parent=self)
                return
            self._refrescar_vencimientos()

    def _editar_vencimiento(self):
        sel = self.tree_venc.selection()
        if not sel:
            messagebox.showinfo("Seleccionar", "Seleccione un vencimiento.", parent=self)
            return
        venc_id = int(sel[0])
        vencs = db.listar_vencimientos(self.exp_id)
        venc = next((v for v in vencs if v.id == venc_id), None)
        if not venc:
            return
        values = {"fecha": fecha_display(venc.fecha), "descripcion": venc.descripcion, "estado": venc.estado}
        dlg = FormDialog(self, "Editar Vencimiento", self._campos_vencimiento(), values)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            venc.fecha = r["fecha"]
            venc.descripcion = r["descripcion"]
            venc.estado = r["estado"]
            try:
                db.actualizar_vencimiento(venc)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el vencimiento:\n{e}", parent=self)
                return
            self._refrescar_vencimientos()

    def _eliminar_vencimiento(self):
        sel = self.tree_venc.selection()
        if not sel:
            return
        if confirmar(self, "Eliminar el vencimiento seleccionado?"):
            try:
                db.eliminar_vencimiento(int(sel[0]))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el vencimiento:\n{e}", parent=self)
                return
            self._refrescar_vencimientos()

    # --- Solapa Honorarios ---
    def _tab_honorarios(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Honorarios")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(0, 5))
        ttk.Button(btn_frame, text="+ Agregar honorario",
                   command=self._nuevo_honorario).pack(side="left")
        ttk.Button(btn_frame, text="Eliminar",
                   command=self._eliminar_honorario).pack(side="left", padx=5)

        cols = ("fecha", "monto", "moneda", "concepto", "forma_pago")
        self.tree_hon = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        self.tree_hon.heading("fecha", text="Fecha")
        self.tree_hon.column("fecha", width=100)
        self.tree_hon.heading("monto", text="Monto")
        self.tree_hon.column("monto", width=100, anchor="e")
        self.tree_hon.heading("moneda", text="Moneda")
        self.tree_hon.column("moneda", width=70)
        self.tree_hon.heading("concepto", text="Concepto")
        self.tree_hon.column("concepto", width=250)
        self.tree_hon.heading("forma_pago", text="Forma de pago")
        self.tree_hon.column("forma_pago", width=130)

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree_hon.yview)
        self.tree_hon.configure(yscrollcommand=sb.set)
        self.tree_hon.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.lbl_totales_hon = ttk.Label(frame, text="", style="Total.TLabel")
        self.lbl_totales_hon.pack(fill="x", pady=(8, 0))

        self._refrescar_honorarios()

    def _refrescar_honorarios(self):
        for item in self.tree_hon.get_children():
            self.tree_hon.delete(item)
        for h in db.listar_honorarios(self.exp_id):
            self.tree_hon.insert("", "end", iid=str(h.id),
                                 values=(fecha_display(h.fecha), f"{h.monto:,.2f}", h.moneda,
                                         h.concepto, h.forma_pago))
        totales = db.totales_honorarios(self.exp_id)
        partes = [f"{moneda}: {total:,.2f}" for moneda, total in sorted(totales.items())]
        self.lbl_totales_hon.config(text=("Totales:  " + "   |   ".join(partes)) if partes else "Sin honorarios registrados")

    def _nuevo_honorario(self):
        campos = [
            {"name": "fecha", "label": "Fecha (DD/MM/AAAA)", "required": True,
             "validate": "fecha", "default": fecha_hoy()},
            {"name": "monto", "label": "Monto", "required": True, "validate": "monto"},
            {"name": "moneda", "label": "Moneda", "type": "combo",
             "options": ["ARS", "USD"], "default": "ARS"},
            {"name": "concepto", "label": "Concepto"},
            {"name": "forma_pago", "label": "Forma de pago", "type": "combo",
             "options": ["efectivo", "transferencia", "cheque", "otro"]},
        ]
        dlg = FormDialog(self, "Nuevo Honorario", campos)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            try:
                db.crear_honorario(Honorario(
                    expediente_id=self.exp_id, fecha=r["fecha"],
                    monto=float(r["monto"]), moneda=r["moneda"],
                    concepto=r["concepto"], forma_pago=r["forma_pago"],
                ))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo registrar el honorario:\n{e}", parent=self)
                return
            self._refrescar_honorarios()

    def _eliminar_honorario(self):
        sel = self.tree_hon.selection()
        if not sel:
            return
        if confirmar(self, "Eliminar el honorario seleccionado?"):
            try:
                db.eliminar_honorario(int(sel[0]))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el honorario:\n{e}", parent=self)
                return
            self._refrescar_honorarios()

    # --- Solapa Gastos ---
    def _tab_gastos(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Gastos")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(0, 5))
        ttk.Button(btn_frame, text="+ Agregar gasto",
                   command=self._nuevo_gasto).pack(side="left")
        ttk.Button(btn_frame, text="Eliminar",
                   command=self._eliminar_gasto).pack(side="left", padx=5)

        cols = ("fecha", "monto", "moneda", "descripcion")
        self.tree_gastos = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        self.tree_gastos.heading("fecha", text="Fecha")
        self.tree_gastos.column("fecha", width=100)
        self.tree_gastos.heading("monto", text="Monto")
        self.tree_gastos.column("monto", width=100, anchor="e")
        self.tree_gastos.heading("moneda", text="Moneda")
        self.tree_gastos.column("moneda", width=70)
        self.tree_gastos.heading("descripcion", text="Descripcion")
        self.tree_gastos.column("descripcion", width=400)

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree_gastos.yview)
        self.tree_gastos.configure(yscrollcommand=sb.set)
        self.tree_gastos.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.lbl_totales_gastos = ttk.Label(frame, text="", style="Total.TLabel")
        self.lbl_totales_gastos.pack(fill="x", pady=(8, 0))

        self._refrescar_gastos()

    def _refrescar_gastos(self):
        for item in self.tree_gastos.get_children():
            self.tree_gastos.delete(item)
        for g in db.listar_gastos(self.exp_id):
            self.tree_gastos.insert("", "end", iid=str(g.id),
                                    values=(fecha_display(g.fecha), f"{g.monto:,.2f}", g.moneda,
                                            g.descripcion))
        totales = db.totales_gastos(self.exp_id)
        partes = [f"{moneda}: {total:,.2f}" for moneda, total in sorted(totales.items())]
        self.lbl_totales_gastos.config(
            text=("Saldo gastos:  " + "   |   ".join(partes)) if partes else "Sin gastos registrados")

    def _nuevo_gasto(self):
        campos = [
            {"name": "fecha", "label": "Fecha (DD/MM/AAAA)", "required": True,
             "validate": "fecha", "default": fecha_hoy()},
            {"name": "monto", "label": "Monto", "required": True, "validate": "monto"},
            {"name": "moneda", "label": "Moneda", "type": "combo",
             "options": ["ARS", "USD"], "default": "ARS"},
            {"name": "descripcion", "label": "Descripcion", "required": True},
        ]
        dlg = FormDialog(self, "Nuevo Gasto", campos)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            try:
                db.crear_gasto(Gasto(
                    expediente_id=self.exp_id, fecha=r["fecha"],
                    monto=float(r["monto"]), moneda=r["moneda"],
                    descripcion=r["descripcion"],
                ))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo registrar el gasto:\n{e}", parent=self)
                return
            self._refrescar_gastos()

    def _eliminar_gasto(self):
        sel = self.tree_gastos.selection()
        if not sel:
            return
        if confirmar(self, "Eliminar el gasto seleccionado?"):
            try:
                db.eliminar_gasto(int(sel[0]))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el gasto:\n{e}", parent=self)
                return
            self._refrescar_gastos()
