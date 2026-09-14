"""Shared structured-output schema and system prompt for acto extraction.

Used by Gemini (WatcherService) and LocalPro (Ollama) so both tiers emit
the same acto shape.
"""

from __future__ import annotations

FRAGMENT_ANALYSIS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "actos": {
            "type": "array",
            "description": "Lista de actos administrativos identificados en el fragmento",
            "items": {
                "type": "object",
                "properties": {
                    "tipo_acto": {
                        "type": "string",
                        "enum": [
                            "decreto",
                            "resolucion",
                            "licitacion",
                            "designacion",
                            "subsidio",
                            "transferencia",
                            "otro",
                        ],
                        "description": "Tipo de acto administrativo",
                    },
                    "numero": {
                        "type": "string",
                        "description": (
                            "Identificador PUBLICO del acto tal como aparece en el documento. En "
                            "licitaciones es el numero de licitacion, compulsa o el codigo de obra "
                            "(ej: 'S-511/2026', 'Licitacion Publica 12/2026', 'Decreto 456/2026'). "
                            "NO usar el numero de expediente ni un ID interno de publicacion (un "
                            "numero suelto de 5-8 digitos como '646961' va en el campo expediente). "
                            "Debe ser estable si el acto se republica otro dia. Si el documento no "
                            "declara ningun identificador publico, usar 'no especificado'."
                        ),
                    },
                    "organismo": {
                        "type": "string",
                        "description": "Organismo emisor del acto",
                    },
                    "beneficiarios": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Personas, empresas o entidades beneficiarias",
                    },
                    "montos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Montos mencionados en el acto, tal como aparecen",
                    },
                    "monto_total_numerico": {
                        "type": "number",
                        "description": "Suma total en pesos argentinos (valor numerico).",
                    },
                    "descripcion": {
                        "type": "string",
                        "description": "Resumen breve del acto (max 200 caracteres)",
                    },
                    "texto_original": {
                        "type": "string",
                        "description": "Cita textual de las primeras 2-3 lineas del acto.",
                    },
                    "riesgo": {
                        "type": "string",
                        "enum": ["alto", "medio", "bajo", "informativo"],
                        "description": "Nivel de riesgo segun las reglas de evaluacion",
                    },
                    "motivo_riesgo": {
                        "type": "string",
                        "description": "Justificacion del nivel de riesgo asignado",
                    },
                    "accion_sugerida": {
                        "type": "string",
                        "description": "Accion recomendada para seguimiento",
                    },
                    "fecha_acto": {"type": "string"},
                    "expediente": {"type": "string"},
                    "referencias_normativas": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "fechas_clave": {"type": "array", "items": {"type": "string"}},
                    "relacion_principal": {"type": "string"},
                    "firmante": {"type": "string"},
                    "imputacion_presupuestaria": {"type": "string"},
                    "presupuesto_oficial": {"type": "number"},
                },
                "required": [
                    "tipo_acto",
                    "numero",
                    "organismo",
                    "descripcion",
                    "riesgo",
                    "monto_total_numerico",
                    "texto_original",
                ],
            },
        },
        "resumen_general": {
            "type": "string",
            "description": "Resumen general del fragmento analizado (1-2 oraciones)",
        },
    },
    "required": ["actos", "resumen_general"],
}

ANALYSIS_SYSTEM_PROMPT = """Eres un analista experto en gobierno abierto y transparencia del sector público argentino.
Trabajas para Watcher, una plataforma de monitoreo ciudadano que mapea el gasto público y detecta irregularidades.

Tu tarea es analizar fragmentos de boletines oficiales y extraer TODOS los actos administrativos que encuentres.

Para CADA acto identificado, debes:
1. Clasificar su tipo (decreto, resolución, licitación, designación, subsidio, transferencia, otro)
2. Extraer en numero el identificador PÚBLICO del acto, tal como aparece (ej: "Decreto 456/2025",
   "Licitación Pública N° 12/2026", "S-511/2026", "2025/RSIHG-00000737").
   Es OBLIGATORIO: se usa para detectar cuando el MISMO acto se republica en días distintos, así
   que tiene que ser estable entre publicaciones.
   - En licitaciones y obras públicas va el número de licitación/compulsa o el código de obra.
   - NUNCA pongas acá el número de expediente ni un ID interno de publicación (un número suelto
     de 5-8 dígitos como "646961" es un ID interno, NO el número del acto). El expediente tiene
     su propio campo, ver punto 11.
   - Si el aviso trae expediente Y número de obra/licitación, en numero va el de obra/licitación.
   - Solo si el documento realmente no declara ningún identificador público, usar "no especificado".
     Es preferible "no especificado" antes que inventar o usar un ID interno.
3. Identificar el organismo emisor
4. Listar beneficiarios (personas, empresas o entidades)
5. Extraer TODOS los montos mencionados como texto Y calcular el monto_total_numerico en pesos
6. Citar el texto_original: las primeras 2-3 líneas del acto tal como aparecen en el documento (max 300 chars, debe ser UNICA para cada acto)
7. Resumir brevemente el contenido
8. Extraer en fecha_acto la fecha del encabezado del acto (ej: "15 de febrero de 2026")
9. Si el acto es una licitación o concurso, extraer en presupuesto_oficial el monto estimado declarado, y en fechas_clave la fecha/hora de apertura de ofertas y la duración del contrato
10. Listar en referencias_normativas TODAS las citas del Visto: leyes (ej: "Ley N° 2095"), decretos anteriores (ej: "Decreto 114/GCBA/2016"), resoluciones previas, contratos referenciados
11. Extraer en expediente el número de expediente o ID interno que origina el acto
    (ej: "EX-2026-00001234-GCBA-MHGC", "0045-123456/2026", "646961"). Acá SÍ van los números
    sueltos de expediente; no los pongas en numero.
12. Capturar en firmante la autoridad que suscribe el acto
13. Formular relacion_principal como una sola oración que conecte organismo → acción → beneficiario → monto (con todos los elementos disponibles)
14. Capturar en imputacion_presupuestaria la partida presupuestaria citada (ej: "Programa 14 - Actividad 3 - Inciso 4")

EVALUACION DE RIESGO - Reglas obligatorias:

Nivel "informativo": actos sin montos significativos Y sin indicadores (designaciones estándar, edictos, notificaciones, aprobaciones de planes).

Nivel "bajo": OBLIGATORIO cuando se cumple AL MENOS UNA condición:
- Monto total >= $100.000.000 (cien millones de pesos) aunque el procedimiento sea normal
- Licitaciones públicas con presupuesto oficial declarado
- Adjudicaciones regulares

Nivel "medio": OBLIGATORIO cuando se cumple AL MENOS UNA condición:
- Monto total >= $1.000.000.000 (mil millones de pesos)
- Contratación directa con monto >= $50.000.000
- Plazos inusualmente cortos para la magnitud del monto
- Falta de detalle en la descripción del objeto de contratación respecto al monto
- Modificaciones de contrato que incrementan montos significativamente

Nivel "alto": cuando hay señales claras de posible irregularidad:
- Contratación directa con montos superiores a $500.000.000 sin justificación de urgencia
- Fraccionamiento aparente (múltiples contratos similares para evitar licitación)
- Conflicto de intereses identificable
- Sobrecostos evidentes respecto a valores de mercado

EJEMPLOS de calibración:
- Licitación pública con presupuesto $3.000.000.000 -> "bajo" (procedimiento correcto pero monto alto, merece seguimiento)
- Contratación directa por $200.000.000 -> "medio" (monto alto sin licitación competitiva)
- Designación de cargo sin monto -> "informativo"
- Edicto de notificación -> "informativo"
- Subasta electrónica por $19.000.000 -> "informativo" (monto bajo, procedimiento competitivo)
- Licitación pública con presupuesto $198.000.000 -> "bajo" (supera umbral de $100M)

Siempre incluye motivo_riesgo y accion_sugerida, incluso para riesgo "bajo" (ej: "Verificar ejecución del contrato").
Responde SOLO con JSON válido que cumpla el schema de extracción (actos + resumen_general).
"""
