# Gestion de Expedientes

Aplicacion de escritorio en Python + Tkinter para administrar expedientes juridicos con persistencia local en SQLite.

## Que permite hacer

- Crear, editar y eliminar expedientes.
- Buscar y filtrar expedientes por numero, caratula, estado y juzgado.
- Ver el detalle completo de cada expediente.
- Gestionar partes asociadas.
- Registrar pasos procesales.
- Registrar vencimientos y consultar una vista global.
- Registrar honorarios y gastos por expediente.
- Mantener los datos en una base SQLite local (`expedientes.db`).

## Tecnologias

- Python
- Tkinter / ttk
- SQLite

## Estructura del proyecto

```text
gestion_expedientes_v01/
|-- main.py
|-- database.py
|-- models.py
|-- expedientes.db
|-- ui/
|   |-- app.py
|   |-- expedientes.py
|   |-- detalle_expediente.py
|   |-- vencimientos.py
|   |-- dialogs.py
|   `-- styles.py
```

## Requisitos

- Python 3.10 o superior

## Como ejecutar

1. Abrir una terminal en la carpeta del proyecto.
2. Ejecutar:

```bash
python main.py
```

La base de datos se crea automaticamente si no existe.

## Base de datos

El proyecto usa un archivo SQLite local:

```text
expedientes.db
```

Tablas principales:

- `expedientes`
- `partes`
- `pasos_procesales`
- `vencimientos`
- `honorarios`
- `gastos`

## Notas

- La aplicacion esta pensada para uso local.
- No requiere servidor ni instalacion de dependencias externas.
- En Windows incluye ajuste de DPI para mejorar la visualizacion en pantallas de alta resolucion.

## Posibles mejoras futuras

- Exportacion de reportes.
- Backups automaticos de la base.
- Recordatorios o alertas de vencimientos.
- Edicion de honorarios y gastos.
- Empaquetado a ejecutable para distribucion.
