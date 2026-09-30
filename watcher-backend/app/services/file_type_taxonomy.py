"""Taxonomía de **tipos de archivo** del inventario de transparencia.

Eje **primario** de "Documentos por tipo" (decisión PO 2026-09-28): el tipo de
archivo (`expected_format` en `required_documents.json`), con la categoría legal
(`document_type`) como mapping secundario.

**Extensible**: agregar una entrada acá y usar el formato en el config alcanza —
el overview publica esta tabla, así que la UI toma la etiqueta y el orden de un
solo lugar en vez de adivinar el nombre del formato.
"""

# El orden del dict ES el orden de presentación (pdf → csv → xlsx).
FILE_TYPE_LABELS: dict[str, str] = {
    "pdf": "PDF",
    "csv": "CSV",
    "xlsx": "XLSX",
}

# Formato que no está en el config (no debería pasar: `expected_format` es
# NOT NULL). No inventa una entrada en la taxonomía: declara la ausencia.
UNKNOWN_FILE_TYPE = "sin_formato"

_FILE_TYPE_POSITION = {key: index for index, key in enumerate(FILE_TYPE_LABELS)}


def is_known_file_type(file_type: str) -> bool:
    return file_type in FILE_TYPE_LABELS


def file_type_label(file_type: str) -> str:
    return FILE_TYPE_LABELS.get(file_type, file_type.upper())


def file_type_order(file_type: str) -> tuple[int, int, str]:
    """Clave de orden: primero la taxonomía (en su orden), después lo desconocido."""
    if file_type in _FILE_TYPE_POSITION:
        return (0, _FILE_TYPE_POSITION[file_type], "")
    return (1, 0, file_type)


def file_type_taxonomy() -> list[dict[str, str]]:
    """La taxonomía como lista ordenada, para publicarla en el overview."""
    return [{"key": key, "label": label} for key, label in FILE_TYPE_LABELS.items()]
