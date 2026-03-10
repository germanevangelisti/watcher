"""
Patrones de detección para Historical Intelligence Agent
Define los patrones sospechosos y reglas de análisis
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class PatternRule:
    """Regla de patrón sospechoso"""
    id: str
    nombre: str
    descripcion: str
    severidad: str  # ALTA, MEDIA, BAJA
    query_template: str
    threshold: Dict[str, Any]
    categoria: str
    cypher_template: str = ""  # Versión Cypher para Neo4j (fallback a query_template si vacío)


# Patrones predefinidos
PATRONES_SOSPECHOSOS = {
    "concentracion_contratos": PatternRule(
        id="concentracion_contratos",
        nombre="Concentración de Contratos",
        descripcion="Empresa recibe múltiples contratos en período corto",
        severidad="ALTA",
        query_template="""
            SELECT 
                ee.nombre_display as empresa,
                COUNT(*) as total_contratos,
                SUM(CAST(json_extract(re.metadata_extra, '$.monto') AS REAL)) as monto_total
            FROM entidades_extraidas ee
            JOIN relaciones_entidades re ON ee.id = re.entidad_destino_id
            WHERE ee.tipo = 'empresa'
            AND re.tipo_relacion IN ('contrata', 'adjudica')
            AND re.fecha_relacion >= date('now', '-{dias} days')
            GROUP BY ee.id
            HAVING COUNT(*) >= {min_contratos}
            ORDER BY total_contratos DESC
        """,
        threshold={"dias": 30, "min_contratos": 5},
        categoria="fiscal",
        cypher_template="""
            MATCH (emp:Entidad {tipo: 'empresa'})<-[r:CONTRATA|ADJUDICA]-()
            WHERE r.fecha >= date() - duration({days: $dias})
            WITH emp, count(r) AS total_contratos
            WHERE total_contratos >= $min_contratos
            RETURN emp.nombre_display AS empresa, total_contratos
            ORDER BY total_contratos DESC
        """
    ),

    "monto_anomalo": PatternRule(
        id="monto_anomalo",
        nombre="Monto Anómalamente Alto",
        descripcion="Monto supera significativamente el promedio histórico",
        severidad="ALTA",
        query_template="""
            WITH promedios AS (
                SELECT 
                    re.tipo_relacion,
                    AVG(CAST(json_extract(re.metadata_extra, '$.monto') AS REAL)) as promedio,
                    MAX(CAST(json_extract(re.metadata_extra, '$.monto') AS REAL)) as maximo
                FROM relaciones_entidades re
                WHERE json_extract(re.metadata_extra, '$.monto') IS NOT NULL
                AND re.fecha_relacion >= date('now', '-365 days')
                GROUP BY re.tipo_relacion
            )
            SELECT 
                re.id,
                re.tipo_relacion,
                CAST(json_extract(re.metadata_extra, '$.monto') AS REAL) as monto,
                p.promedio,
                (CAST(json_extract(re.metadata_extra, '$.monto') AS REAL) / p.promedio) as ratio
            FROM relaciones_entidades re
            JOIN promedios p ON re.tipo_relacion = p.tipo_relacion
            WHERE (CAST(json_extract(re.metadata_extra, '$.monto') AS REAL) / p.promedio) >= {ratio_threshold}
            AND re.fecha_relacion >= date('now', '-{dias_recientes} days')
            ORDER BY ratio DESC
        """,
        threshold={"ratio_threshold": 3.0, "dias_recientes": 90},
        categoria="fiscal",
        cypher_template="""
            MATCH ()-[r:CONTRATA|ADJUDICA]->()
            WHERE r.fecha >= date() - duration({days: 365})
            WITH type(r) AS tipo_rel, avg(toFloat(r.monto)) AS avg_monto
            WITH collect({tipo: tipo_rel, avg: avg_monto}) AS averages
            MATCH ()-[r2:CONTRATA|ADJUDICA]->()
            WHERE r2.fecha >= date() - duration({days: $dias_recientes})
            WITH r2, averages, [a IN averages WHERE a.tipo = type(r2) | a.avg][0] AS avg_for_type
            WHERE avg_for_type IS NOT NULL
              AND (toFloat(r2.monto) / avg_for_type) >= $ratio_threshold
            RETURN r2.pg_id AS relacion_id, type(r2) AS tipo,
                   toFloat(r2.monto) AS monto, avg_for_type AS promedio,
                   (toFloat(r2.monto) / avg_for_type) AS ratio
            ORDER BY ratio DESC
        """
    ),

    "designacion_contrato_rapido": PatternRule(
        id="designacion_contrato_rapido",
        nombre="Designación Seguida de Contrato",
        descripcion="Persona designada aparece en contrato en menos de 60 días",
        severidad="MEDIA",
        query_template="""
            WITH designaciones AS (
                SELECT 
                    re1.entidad_destino_id as persona_id,
                    ee.nombre_display as persona,
                    re1.fecha_relacion as fecha_designacion
                FROM relaciones_entidades re1
                JOIN entidades_extraidas ee ON re1.entidad_destino_id = ee.id
                WHERE re1.tipo_relacion = 'designa'
                AND ee.tipo = 'persona'
            ),
            contratos AS (
                SELECT DISTINCT
                    me.entidad_id as persona_id,
                    MIN(b.date) as fecha_primer_contrato
                FROM menciones_entidades me
                JOIN boletines b ON me.boletin_id = b.id
                WHERE me.fragmento LIKE '%contrat%' 
                   OR me.fragmento LIKE '%licitac%'
                   OR me.fragmento LIKE '%adjudica%'
                GROUP BY me.entidad_id
            )
            SELECT 
                d.persona,
                d.fecha_designacion,
                c.fecha_primer_contrato,
                julianday(c.fecha_primer_contrato) - julianday(d.fecha_designacion) as dias_diferencia
            FROM designaciones d
            JOIN contratos c ON d.persona_id = c.persona_id
            WHERE julianday(c.fecha_primer_contrato) - julianday(d.fecha_designacion) BETWEEN 0 AND {max_dias}
            ORDER BY dias_diferencia ASC
        """,
        threshold={"max_dias": 60},
        categoria="conflicto_interes",
        cypher_template="""
            MATCH ()-[d:DESIGNA]->(persona:Entidad {tipo: 'persona'})
            MATCH (persona)-[m:MENCIONADO_EN]->(b:Boletin)
            WHERE m.fragmento CONTAINS 'contrat'
               OR m.fragmento CONTAINS 'licitac'
               OR m.fragmento CONTAINS 'adjudica'
            WITH persona, d.fecha AS fecha_designacion, min(date(b.date)) AS fecha_contrato
            WHERE duration.between(fecha_designacion, fecha_contrato).days BETWEEN 0 AND $max_dias
            RETURN persona.nombre_display AS persona,
                   toString(fecha_designacion) AS fecha_designacion,
                   toString(fecha_contrato) AS fecha_primer_contrato,
                   duration.between(fecha_designacion, fecha_contrato).days AS dias_diferencia
            ORDER BY dias_diferencia ASC
        """
    ),

    "proveedor_unico": PatternRule(
        id="proveedor_unico",
        nombre="Proveedor Único Dominante",
        descripcion="Mismo proveedor gana la mayoría de contratos de un área",
        severidad="MEDIA",
        query_template="""
            WITH contratos_organismo AS (
                SELECT 
                    re.entidad_origen_id as organismo_id,
                    ee_org.nombre_display as organismo,
                    re.entidad_destino_id as empresa_id,
                    ee_emp.nombre_display as empresa,
                    COUNT(*) as contratos
                FROM relaciones_entidades re
                JOIN entidades_extraidas ee_org ON re.entidad_origen_id = ee_org.id
                JOIN entidades_extraidas ee_emp ON re.entidad_destino_id = ee_emp.id
                WHERE re.tipo_relacion IN ('contrata', 'adjudica')
                AND re.fecha_relacion >= date('now', '-{dias} days')
                AND ee_org.tipo = 'organismo'
                AND ee_emp.tipo = 'empresa'
                GROUP BY re.entidad_origen_id, re.entidad_destino_id
            ),
            totales AS (
                SELECT 
                    organismo_id,
                    SUM(contratos) as total_contratos
                FROM contratos_organismo
                GROUP BY organismo_id
            )
            SELECT 
                co.organismo,
                co.empresa,
                co.contratos,
                t.total_contratos,
                ROUND(100.0 * co.contratos / t.total_contratos, 2) as porcentaje
            FROM contratos_organismo co
            JOIN totales t ON co.organismo_id = t.organismo_id
            WHERE t.total_contratos >= {min_contratos_total}
            AND (100.0 * co.contratos / t.total_contratos) >= {porcentaje_threshold}
            ORDER BY porcentaje DESC
        """,
        threshold={"dias": 365, "min_contratos_total": 5, "porcentaje_threshold": 70.0},
        categoria="competencia",
        cypher_template="""
            MATCH (org:Entidad {tipo: 'organismo'})-[r:CONTRATA|ADJUDICA]->(emp:Entidad {tipo: 'empresa'})
            WHERE r.fecha >= date() - duration({days: $dias})
            WITH org, emp, count(r) AS contratos_pair
            WITH org, sum(contratos_pair) AS total_org,
                 collect({empresa: emp.nombre_display, contratos: contratos_pair}) AS por_empresa
            WHERE total_org >= $min_contratos_total
            UNWIND por_empresa AS pair
            WITH org.nombre_display AS organismo, pair.empresa AS empresa,
                 pair.contratos AS contratos, total_org,
                 round(100.0 * pair.contratos / total_org, 2) AS porcentaje
            WHERE porcentaje >= $porcentaje_threshold
            RETURN organismo, empresa, contratos, total_org, porcentaje
            ORDER BY porcentaje DESC
        """
    ),
    
    "fragmentacion_sospechosa": PatternRule(
        id="fragmentacion_sospechosa",
        nombre="Fragmentación de Contratos",
        descripcion="Múltiples contratos justo debajo del umbral de licitación",
        severidad="ALTA",
        query_template="""
            WITH contratos_empresa AS (
                SELECT 
                    ee.id as empresa_id,
                    ee.nombre_display as empresa,
                    re.fecha_relacion,
                    CAST(json_extract(re.metadata_extra, '$.monto') AS REAL) as monto
                FROM entidades_extraidas ee
                JOIN relaciones_entidades re ON ee.id = re.entidad_destino_id
                WHERE ee.tipo = 'empresa'
                AND re.tipo_relacion IN ('contrata', 'adjudica')
                AND json_extract(re.metadata_extra, '$.monto') IS NOT NULL
                AND CAST(json_extract(re.metadata_extra, '$.monto') AS REAL) < {umbral_licitacion}
                AND CAST(json_extract(re.metadata_extra, '$.monto') AS REAL) >= {umbral_licitacion} * 0.7
                AND re.fecha_relacion >= date('now', '-{dias_ventana} days')
            )
            SELECT 
                empresa,
                COUNT(*) as num_contratos,
                SUM(monto) as suma_total,
                MIN(monto) as monto_minimo,
                MAX(monto) as monto_maximo,
                AVG(monto) as monto_promedio
            FROM contratos_empresa
            GROUP BY empresa_id
            HAVING COUNT(*) >= {min_contratos}
            AND SUM(monto) >= {umbral_licitacion}
            ORDER BY num_contratos DESC, suma_total DESC
        """,
        threshold={
            "umbral_licitacion": 10000000,  # $10M
            "dias_ventana": 90,
            "min_contratos": 3
        },
        categoria="evasion",
        cypher_template="""
            MATCH (emp:Entidad {tipo: 'empresa'})<-[r:CONTRATA|ADJUDICA]-()
            WHERE r.fecha >= date() - duration({days: $dias_ventana})
              AND toFloat(r.monto) < $umbral_licitacion
              AND toFloat(r.monto) >= $umbral_licitacion * 0.7
            WITH emp, count(r) AS num_contratos, sum(toFloat(r.monto)) AS suma_total,
                 min(toFloat(r.monto)) AS monto_minimo, max(toFloat(r.monto)) AS monto_maximo
            WHERE num_contratos >= $min_contratos AND suma_total >= $umbral_licitacion
            RETURN emp.nombre_display AS empresa, num_contratos, suma_total, monto_minimo, monto_maximo
            ORDER BY num_contratos DESC, suma_total DESC
        """
    ),
    
    "recurrencia_temporal": PatternRule(
        id="recurrencia_temporal",
        nombre="Patrón Temporal Recurrente",
        descripcion="Empresa recibe contratos en fechas similares cada año",
        severidad="BAJA",
        query_template="""
            WITH contratos_temporales AS (
                SELECT 
                    ee.nombre_display as empresa,
                    strftime('%m', re.fecha_relacion) as mes,
                    strftime('%d', re.fecha_relacion) as dia,
                    strftime('%Y', re.fecha_relacion) as anio,
                    COUNT(*) as apariciones
                FROM entidades_extraidas ee
                JOIN relaciones_entidades re ON ee.id = re.entidad_destino_id
                WHERE ee.tipo = 'empresa'
                AND re.tipo_relacion IN ('contrata', 'adjudica')
                GROUP BY ee.id, mes, dia
                HAVING COUNT(*) >= {min_recurrencias}
            )
            SELECT 
                empresa,
                mes,
                dia,
                GROUP_CONCAT(anio) as anios,
                apariciones
            FROM contratos_temporales
            ORDER BY apariciones DESC, empresa
        """,
        threshold={"min_recurrencias": 2},
        categoria="patron_temporal",
        cypher_template="""
            MATCH (emp:Entidad {tipo: 'empresa'})<-[r:CONTRATA|ADJUDICA]-()
            WITH emp, r.fecha.month AS mes, r.fecha.day AS dia, r.fecha.year AS anio
            WITH emp, mes, dia, count(DISTINCT anio) AS apariciones, collect(DISTINCT toString(anio)) AS anios
            WHERE apariciones >= $min_recurrencias
            RETURN emp.nombre_display AS empresa, mes, dia, anios, apariciones
            ORDER BY apariciones DESC, empresa
        """
    ),
    
    "vinculo_cruzado": PatternRule(
        id="vinculo_cruzado",
        nombre="Vínculos Cruzados Complejos",
        descripcion="Red compleja de relaciones entre mismas entidades",
        severidad="MEDIA",
        query_template="""
            WITH relaciones_bidireccionales AS (
                SELECT DISTINCT
                    ee1.nombre_display as entidad1,
                    ee2.nombre_display as entidad2,
                    GROUP_CONCAT(DISTINCT re.tipo_relacion) as tipos_relacion,
                    COUNT(*) as num_relaciones
                FROM relaciones_entidades re
                JOIN entidades_extraidas ee1 ON re.entidad_origen_id = ee1.id
                JOIN entidades_extraidas ee2 ON re.entidad_destino_id = ee2.id
                WHERE re.fecha_relacion >= date('now', '-{dias} days')
                GROUP BY 
                    CASE WHEN ee1.id < ee2.id THEN ee1.id ELSE ee2.id END,
                    CASE WHEN ee1.id < ee2.id THEN ee2.id ELSE ee1.id END
                HAVING COUNT(DISTINCT re.tipo_relacion) >= {min_tipos_relacion}
            )
            SELECT * FROM relaciones_bidireccionales
            ORDER BY num_relaciones DESC
        """,
        threshold={"dias": 365, "min_tipos_relacion": 2},
        categoria="red_relaciones",
        cypher_template="""
            MATCH (e1:Entidad)-[r]-(e2:Entidad)
            WHERE r.fecha >= date() - duration({days: $dias})
              AND id(e1) < id(e2)
            WITH e1, e2, collect(DISTINCT type(r)) AS tipos_relacion, count(r) AS num_relaciones
            WHERE size(tipos_relacion) >= $min_tipos_relacion
            RETURN e1.nombre_display AS entidad1, e2.nombre_display AS entidad2,
                   tipos_relacion, num_relaciones
            ORDER BY num_relaciones DESC
        """
    )
}


def get_pattern(pattern_id: str) -> PatternRule:
    """Obtiene un patrón por ID"""
    return PATRONES_SOSPECHOSOS.get(pattern_id)


def get_patterns_by_severity(severidad: str) -> List[PatternRule]:
    """Obtiene patrones por severidad"""
    return [p for p in PATRONES_SOSPECHOSOS.values() if p.severidad == severidad]


def get_patterns_by_category(categoria: str) -> List[PatternRule]:
    """Obtiene patrones por categoría"""
    return [p for p in PATRONES_SOSPECHOSOS.values() if p.categoria == categoria]


def get_all_patterns() -> Dict[str, PatternRule]:
    """Obtiene todos los patrones"""
    return PATRONES_SOSPECHOSOS
