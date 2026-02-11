"""
Parser de Archivos Excel de Ejecución Presupuestaria - Multi-Período
Procesa archivos Excel de ejecución presupuestaria de múltiples períodos (Marzo, Junio 2025)
Soporta formatos con COMPROMISO/DEVENGADO/PAGADO y formatos legacy.

Autor: Watcher Fiscal Agent
Fecha: Noviembre 2025
Versión: 2.0 - Soporte multi-período
"""

import pandas as pd
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime
import sys

# Rutas base
BASE_DIR = Path(__file__).parent.parent.parent.parent
OUTPUT_DIR = BASE_DIR / "watcher-doc"

# Directorios de datos por período
DATA_DIRS = {
    'marzo': BASE_DIR / "watcher-doc" / "data" / "Datos Abiertos - Ejecución Presupuestaria Marzo 2025",
    'junio': BASE_DIR / "watcher-doc" / "data" / "ejecucion_presupuestaria" / "junio-25"
}

# Patrones de archivos por período
FILE_PATTERNS = {
    'marzo': [
        "Gastos Administración Central - Acumulado Marzo 2025.xlsx",
        "Gastos EMAEE - Acumulado Marzo 2025.xlsx",
        "Recursos Administración Central -Acumulado Marzo 2025.xlsx",
        "Recursos EMAEE - Acumulado Marzo 2025.xlsx"
    ],
    'junio': [
        "Gastos Administración Central - Acumulado Junio 2025.xlsx",
        "Gastos EMAEE - Acumulado Junio 2025.xlsx",
        "Recursos Administración Central -Acumulado Junio 2025.xlsx",
        "Recursos EMAEE - Acumulado Junio 2025.xlsx"
    ]
}


class OrganismoNormalizer:
    """Normaliza nombres de organismos para matching consistente"""
    
    def __init__(self):
        self.mapping = {}
        self.keywords_ministerios = [
            "ministerio", "secretaría", "secretaria", "dirección", "direccion",
            "subsecretaría", "subsecretaria", "agencia", "ente", "tribunal"
        ]
    
    def normalize(self, organismo: str) -> str:
        """Normaliza nombre de organismo"""
        if not organismo or not isinstance(organismo, str):
            return "DESCONOCIDO"
        
        # Convertir a mayúsculas y limpiar
        org = organismo.strip().upper()
        
        # Remover caracteres especiales
        org = re.sub(r'[^\w\s\-]', '', org)
        
        # Normalizar espacios
        org = re.sub(r'\s+', ' ', org)
        
        # Abreviaturas comunes
        replacements = {
            'MIN ': 'MINISTERIO ',
            'MIN.': 'MINISTERIO',
            'SEC ': 'SECRETARIA ',
            'SEC.': 'SECRETARIA',
            'DIR ': 'DIRECCION ',
            'DIR.': 'DIRECCION',
            'GRAL': 'GENERAL',
            'GRAL.': 'GENERAL',
            'ADM': 'ADMINISTRACION',
            'PROV': 'PROVINCIAL'
        }
        
        for old, new in replacements.items():
            org = org.replace(old, new)
        
        # Guardar en mapping
        if organismo not in self.mapping:
            self.mapping[organismo] = org
        
        return org
    
    def extract_keywords(self, organismo: str) -> List[str]:
        """Extrae keywords del nombre del organismo"""
        org = self.normalize(organismo)
        keywords = []
        
        # Keywords específicos por tipo de organismo
        keyword_map = {
            "SALUD": ["hospital", "médico", "medicina", "vacuna", "tratamiento", "paciente"],
            "EDUCACION": ["escuela", "docente", "alumno", "educativo", "enseñanza"],
            "OBRAS": ["obra", "infraestructura", "construcción", "vial", "ruta"],
            "SEGURIDAD": ["policía", "seguridad", "prevención", "emergencia"],
            "DESARROLLO": ["social", "comunidad", "asistencia", "subsidio"],
            "FINANZAS": ["presupuesto", "contable", "financiero", "económico"],
            "JUSTICIA": ["tribunal", "justicia", "judicial", "legal"]
        }
        
        for key, words in keyword_map.items():
            if key in org:
                keywords.extend(words)
        
        # Agregar palabras significativas del nombre
        palabras = org.split()
        keywords.extend([p for p in palabras if len(p) > 4 and p not in ['MINISTERIO', 'SECRETARIA', 'DIRECCION']])
        
        return list(set(keywords))


def explore_excel_structure(file_path: Path) -> Dict:
    """Explora estructura de un archivo Excel"""
    print(f"\n{'='*80}")
    print(f"Explorando: {file_path.name}")
    print(f"{'='*80}")
    
    try:
        # Leer Excel
        df = pd.read_excel(file_path)
        
        result = {
            "archivo": file_path.name,
            "filas": len(df),
            "columnas": df.columns.tolist(),
            "tipos_datos": df.dtypes.astype(str).to_dict(),
            "primeras_filas": df.head(3).to_dict(orient='records'),
            "valores_nulos": df.isnull().sum().to_dict(),
            "columnas_numericas": df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        }
        
        print(f"✓ Filas: {result['filas']}")
        print(f"✓ Columnas ({len(result['columnas'])}): {result['columnas'][:5]}...")
        print(f"✓ Columnas numéricas: {result['columnas_numericas']}")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return {"error": str(e)}


def detect_file_format(df: pd.DataFrame) -> str:
    """Detecta el formato del archivo Excel (marzo legacy vs junio nuevo)"""
    columns_upper = [str(col).upper() for col in df.columns]
    
    # Junio 2025 tiene COMPROMISO, DEVENGADO, PAGADO
    if 'COMPROMISO' in columns_upper and 'DEVENGADO' in columns_upper and 'PAGADO' in columns_upper:
        return 'junio_2025'
    # Marzo 2025 tiene EJECUTADO o similar
    elif any(col in columns_upper for col in ['EJECUTADO', 'ACUMULADO']):
        return 'marzo_2025'
    else:
        return 'unknown'


def parse_excel_gastos(file_path: Path, normalizer: OrganismoNormalizer, periodo: str = 'marzo') -> List[Dict]:
    """Parsea archivo de gastos y extrae estructura presupuestaria con soporte multi-período"""
    print(f"\n📊 Parseando gastos: {file_path.name}")
    
    df = pd.read_excel(file_path)
    programas = []
    
    # Detectar formato del archivo
    file_format = detect_file_format(df)
    print(f"✓ Formato detectado: {file_format}")
    
    # Identificar columnas relevantes (nombres pueden variar)
    columnas_posibles = {
        'organismo': ['ORGANISMO', 'JURISDICCION', 'JURISDICCIÓN', 'ORG'],
        'programa': ['PROGRAMA', 'PROG', 'SUBPROGRAMA', 'SUBPROG'],
        'partida': ['PARTIDA', 'INCISO', 'PRINCIPAL', 'PARCIAL'],
        'descripcion': ['DESCRIPCION', 'DESCRIPCIÓN', 'DESC', 'DETALLE', 'CONCEPTO', 'FINALIDAD', 'FUNCION'],
        'presupuestado': ['PRESUPUESTADO', 'CREDITO', 'CRÉDITO', 'INICIAL', 'VIGENTE', 'PRESUPUESTO VIGENTE'],
        'ejecutado': ['EJECUTADO', 'DEVENGADO', 'PAGADO', 'ACUMULADO'],
        # Nuevas columnas para formato Junio 2025
        'compromiso': ['COMPROMISO'],
        'devengado': ['DEVENGADO'],
        'pagado': ['PAGADO'],
        'mes': ['MES'],
        'anio': ['AÑO', 'ANIO', 'ANO']
    }
    
    # Mapear columnas del Excel a nuestro schema
    col_map = {}
    for key, posibles in columnas_posibles.items():
        for col in df.columns:
            col_upper = str(col).upper()
            if any(p == col_upper or p in col_upper for p in posibles):
                col_map[key] = col
                break
    
    print(f"✓ Columnas mapeadas: {col_map}")
    
    # Procesar filas
    for idx, row in df.iterrows():
        try:
            # Extraer datos básicos
            organismo_raw = row.get(col_map.get('organismo', ''), '')
            organismo = normalizer.normalize(organismo_raw)
            
            if not organismo or organismo == "DESCONOCIDO":
                continue
            
            # Determinar período y año/mes
            if 'anio' in col_map and 'mes' in col_map:
                anio = int(row.get(col_map['anio'], 2025))
                mes = int(row.get(col_map['mes'], 3 if periodo == 'marzo' else 6))
            else:
                anio = 2025
                mes = 3 if periodo == 'marzo' else 6
            
            # Extraer monto presupuestado
            monto_presupuestado = float(row.get(col_map.get('presupuestado', ''), 0) or 0)
            
            # Extraer montos de ejecución según formato
            if file_format == 'junio_2025' and 'compromiso' in col_map:
                monto_compromiso = float(row.get(col_map['compromiso'], 0) or 0)
                monto_devengado = float(row.get(col_map['devengado'], 0) or 0)
                monto_pagado = float(row.get(col_map['pagado'], 0) or 0)
                # Usar devengado como principal indicador de ejecución
                monto_ejecutado = monto_devengado
            else:
                # Formato legacy (marzo)
                monto_ejecutado = float(row.get(col_map.get('ejecutado', ''), 0) or 0)
                monto_compromiso = None
                monto_devengado = monto_ejecutado
                monto_pagado = None
            
            programa = {
                'ejercicio': anio,
                'periodo': periodo,
                'mes': mes,
                'organismo_raw': organismo_raw,
                'organismo': organismo,
                'programa': str(row.get(col_map.get('programa', ''), '')),
                'partida': str(row.get(col_map.get('partida', ''), '')),
                'descripcion': str(row.get(col_map.get('descripcion', ''), ''))[:200],  # Limitar longitud
                'monto_presupuestado': monto_presupuestado,
                'monto_ejecutado': monto_ejecutado,
                'fuente': file_path.name,
                'keywords': normalizer.extract_keywords(organismo_raw),
                'formato': file_format
            }
            
            # Agregar etapas de ejecución si están disponibles (formato nuevo)
            if file_format == 'junio_2025':
                programa['monto_compromiso'] = monto_compromiso
                programa['monto_devengado'] = monto_devengado
                programa['monto_pagado'] = monto_pagado
                
                # Calcular ratios de pipeline de ejecución
                if monto_compromiso and monto_compromiso > 0:
                    programa['ratio_devengado_compromiso'] = round((monto_devengado / monto_compromiso) * 100, 2)
                    programa['ratio_pagado_compromiso'] = round((monto_pagado / monto_compromiso) * 100, 2) if monto_pagado else 0
                if monto_devengado and monto_devengado > 0:
                    programa['ratio_pagado_devengado'] = round((monto_pagado / monto_devengado) * 100, 2) if monto_pagado else 0
            
            # Calcular porcentaje ejecución
            if programa['monto_presupuestado'] > 0:
                programa['porcentaje_ejecucion'] = round(
                    (programa['monto_ejecutado'] / programa['monto_presupuestado']) * 100, 2
                )
            else:
                programa['porcentaje_ejecucion'] = 0.0
            
            # Detectar anomalías con lógica ajustada por período
            # Q1 (Marzo): >50% es alto, <5% es bajo
            # Q2 (Junio): >75% es alto, <15% es bajo (esperado mayor ejecución)
            if periodo == 'marzo':
                if programa['porcentaje_ejecucion'] > 50:
                    programa['alerta'] = 'EJECUCION_ALTA'
                elif programa['porcentaje_ejecucion'] < 5:
                    programa['alerta'] = 'EJECUCION_BAJA'
                else:
                    programa['alerta'] = None
            else:  # junio o posterior
                if programa['porcentaje_ejecucion'] > 75:
                    programa['alerta'] = 'EJECUCION_ALTA'
                elif programa['porcentaje_ejecucion'] < 15:
                    programa['alerta'] = 'EJECUCION_BAJA'
                else:
                    programa['alerta'] = None
            
            # Detectar anomalías de pipeline (solo para formato nuevo)
            if file_format == 'junio_2025' and monto_compromiso:
                if monto_compromiso > 0 and monto_pagado / monto_compromiso < 0.3:
                    programa['alerta_pipeline'] = 'PAGO_LENTO'
                elif monto_devengado > 0 and monto_pagado / monto_devengado < 0.5:
                    programa['alerta_pipeline'] = 'REZAGO_PAGO'
            
            programas.append(programa)
        
        except Exception as e:
            print(f"⚠ Error en fila {idx}: {e}")
            continue
    
    print(f"✓ Programas extraídos: {len(programas)}")
    return programas


def consolidate_programas(all_programas: List[Dict], periodo: str = 'marzo') -> Dict:
    """Consolida programas de múltiples archivos con soporte multi-período"""
    print(f"\n📦 Consolidando {len(all_programas)} programas del período {periodo}...")
    
    # Agrupar por organismo
    by_organismo = defaultdict(list)
    by_programa_id = defaultdict(list)
    by_periodo = defaultdict(list)
    
    for prog in all_programas:
        by_organismo[prog['organismo']].append(prog)
        key = f"{prog['organismo']}-{prog['programa']}"
        by_programa_id[key].append(prog)
        by_periodo[prog.get('periodo', 'marzo')].append(prog)
    
    # Estadísticas
    stats = {
        'total_programas': len(all_programas),
        'organismos_unicos': len(by_organismo),
        'programas_unicos': len(by_programa_id),
        'periodos': list(by_periodo.keys()),
        'top_organismos_presupuesto': [],
        'top_organismos_ejecucion': [],
        'programas_alerta_alta': 0,
        'programas_alerta_baja': 0,
        'programas_alerta_pipeline': 0
    }
    
    # Top organismos por presupuesto
    org_totals = {}
    for org, progs in by_organismo.items():
        total_pres = sum(p['monto_presupuestado'] for p in progs)
        total_ejec = sum(p['monto_ejecutado'] for p in progs)
        org_totals[org] = {
            'presupuestado': total_pres,
            'ejecutado': total_ejec,
            'porcentaje': round((total_ejec / total_pres * 100) if total_pres > 0 else 0, 2),
            'num_programas': len(progs)
        }
    
    # Ordenar por presupuesto
    top_pres = sorted(org_totals.items(), key=lambda x: x[1]['presupuestado'], reverse=True)[:10]
    stats['top_organismos_presupuesto'] = [
        {'organismo': org, **data} for org, data in top_pres
    ]
    
    # Ordenar por ejecución
    top_ejec = sorted(org_totals.items(), key=lambda x: x[1]['ejecutado'], reverse=True)[:10]
    stats['top_organismos_ejecucion'] = [
        {'organismo': org, **data} for org, data in top_ejec
    ]
    
    # Contar alertas
    stats['programas_alerta_alta'] = sum(1 for p in all_programas if p.get('alerta') == 'EJECUCION_ALTA')
    stats['programas_alerta_baja'] = sum(1 for p in all_programas if p.get('alerta') == 'EJECUCION_BAJA')
    stats['programas_alerta_pipeline'] = sum(1 for p in all_programas if p.get('alerta_pipeline'))
    
    return {
        'stats': stats,
        'by_organismo': {k: v for k, v in by_organismo.items()},
        'by_programa_id': {k: v for k, v in by_programa_id.items()},
        'by_periodo': {k: v for k, v in by_periodo.items()},
        'organismos_totals': org_totals
    }


def generate_reports(consolidated: Dict, all_programas: List[Dict], normalizer: OrganismoNormalizer, periodo: str = 'marzo'):
    """Genera reportes de análisis multi-período"""
    stats = consolidated['stats']
    periodos_str = ', '.join(stats.get('periodos', [periodo]))
    
    print(f"\n{'='*80}")
    print(f"📊 RESUMEN EJECUTIVO - PRESUPUESTO 2025 ({periodos_str.upper()})")
    print(f"{'='*80}")
    print(f"✓ Total de programas procesados: {stats['total_programas']}")
    print(f"✓ Organismos únicos: {stats['organismos_unicos']}")
    print(f"✓ Programas únicos: {stats['programas_unicos']}")
    print(f"✓ Períodos procesados: {periodos_str}")
    print(f"⚠ Alertas ejecución alta: {stats['programas_alerta_alta']}")
    print(f"⚠ Alertas ejecución baja: {stats['programas_alerta_baja']}")
    if stats.get('programas_alerta_pipeline', 0) > 0:
        print(f"⚠ Alertas pipeline (pago lento): {stats['programas_alerta_pipeline']}")
    
    print(f"\n{'='*80}")
    print(f"💰 TOP 10 ORGANISMOS POR PRESUPUESTO")
    print(f"{'='*80}")
    for i, org_data in enumerate(stats['top_organismos_presupuesto'], 1):
        print(f"{i:2d}. {org_data['organismo'][:60]:<60} ${org_data['presupuestado']:>15,.0f}")
        print(f"    Ejecutado: ${org_data['ejecutado']:>15,.0f} ({org_data['porcentaje']:>5.1f}%)")
    
    # Guardar archivos JSON
    output_files = {}
    
    # 1. Presupuesto estructurado por período
    presupuesto_estructurado = {
        'metadata': {
            'ejercicio': 2025,
            'periodos': stats.get('periodos', [periodo]),
            'fecha_generacion': datetime.now().isoformat(),
            'total_programas': stats['total_programas'],
            'organismos': stats['organismos_unicos']
        },
        'programas': all_programas
    }
    
    output_path = OUTPUT_DIR / f"presupuesto_estructurado_2025_{periodo}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(presupuesto_estructurado, f, ensure_ascii=False, indent=2)
    output_files['presupuesto_estructurado'] = str(output_path)
    print(f"\n✓ Guardado: {output_path}")
    
    # 2. Ejecución por período
    ejecucion = {
        'metadata': {
            'periodos': stats.get('periodos', [periodo]),
            'fecha_generacion': datetime.now().isoformat()
        },
        'por_organismo': consolidated['organismos_totals'],
        'alertas': {
            'ejecucion_alta': [p for p in all_programas if p.get('alerta') == 'EJECUCION_ALTA'],
            'ejecucion_baja': [p for p in all_programas if p.get('alerta') == 'EJECUCION_BAJA'],
            'pipeline': [p for p in all_programas if p.get('alerta_pipeline')]
        }
    }
    
    output_path = OUTPUT_DIR / f"ejecucion_{periodo}_2025.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ejecucion, f, ensure_ascii=False, indent=2)
    output_files['ejecucion'] = str(output_path)
    print(f"✓ Guardado: {output_path}")
    
    # 3. Organismos normalizados
    organismos_norm = {
        'mapping': normalizer.mapping,
        'keywords_por_organismo': {
            org: normalizer.extract_keywords(org)
            for org in set(p['organismo_raw'] for p in all_programas)
        }
    }
    
    output_path = OUTPUT_DIR / "organismos_normalizados.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(organismos_norm, f, ensure_ascii=False, indent=2)
    output_files['organismos'] = str(output_path)
    print(f"✓ Guardado: {output_path}")
    
    return output_files


def process_period(periodo: str, normalizer: OrganismoNormalizer) -> Tuple[List[Dict], Dict]:
    """Procesa un período específico (marzo o junio)"""
    print(f"\n{'='*80}")
    print(f"PROCESANDO PERÍODO: {periodo.upper()}")
    print(f"{'='*80}")
    
    data_dir = DATA_DIRS.get(periodo)
    file_patterns = FILE_PATTERNS.get(periodo)
    
    if not data_dir or not data_dir.exists():
        print(f"⚠ Directorio no encontrado para {periodo}: {data_dir}")
        return [], {}
    
    if not file_patterns:
        print(f"⚠ No hay patrones de archivo definidos para {periodo}")
        return [], {}
    
    # 1. Verificar archivos
    print(f"\n📁 Verificando archivos Excel de {periodo}...")
    files_found = []
    for filename in file_patterns:
        file_path = data_dir / filename
        if not file_path.exists():
            print(f"✗ No encontrado: {filename}")
        else:
            print(f"✓ Encontrado: {filename}")
            files_found.append(file_path)
    
    if not files_found:
        print(f"\n❌ Error: No se encontraron archivos para {periodo}")
        return [], {}
    
    # 2. Explorar estructura (solo primer archivo)
    print(f"\n{'='*80}")
    print(f"FASE 1: EXPLORACIÓN DE ESTRUCTURA ({periodo.upper()})")
    print(f"{'='*80}")
    
    explore_excel_structure(files_found[0])
    
    # 3. Parsear datos
    print(f"\n{'='*80}")
    print(f"FASE 2: EXTRACCIÓN DE DATOS ({periodo.upper()})")
    print(f"{'='*80}")
    
    all_programas = []
    for file_path in files_found:
        if 'Gastos' in file_path.name:  # Solo procesar archivos de gastos
            programas = parse_excel_gastos(file_path, normalizer, periodo=periodo)
            all_programas.extend(programas)
    
    # 4. Consolidar y analizar
    print(f"\n{'='*80}")
    print(f"FASE 3: CONSOLIDACIÓN Y ANÁLISIS ({periodo.upper()})")
    print(f"{'='*80}")
    
    consolidated = consolidate_programas(all_programas, periodo=periodo)
    
    return all_programas, consolidated


def compare_periods(marzo_data: List[Dict], junio_data: List[Dict]) -> Dict:
    """Compara datos entre períodos y genera métricas comparativas"""
    print(f"\n{'='*80}")
    print(f"ANÁLISIS COMPARATIVO: MARZO vs JUNIO")
    print(f"{'='*80}")
    
    # Crear diccionario de programas por key para matching
    marzo_by_key = {}
    for prog in marzo_data:
        key = f"{prog['organismo']}-{prog['programa']}"
        marzo_by_key[key] = prog
    
    junio_by_key = {}
    for prog in junio_data:
        key = f"{prog['organismo']}-{prog['programa']}"
        junio_by_key[key] = prog
    
    # Identificar programas comunes y únicos
    keys_marzo = set(marzo_by_key.keys())
    keys_junio = set(junio_by_key.keys())
    keys_common = keys_marzo & keys_junio
    keys_only_marzo = keys_marzo - keys_junio
    keys_only_junio = keys_junio - keys_marzo
    
    print(f"\n📊 Programas comunes: {len(keys_common)}")
    print(f"📊 Solo en marzo: {len(keys_only_marzo)}")
    print(f"📊 Solo en junio: {len(keys_only_junio)}")
    
    # Calcular métricas comparativas
    comparisons = []
    for key in keys_common:
        prog_marzo = marzo_by_key[key]
        prog_junio = junio_by_key[key]
        
        # Calcular variación en ejecución
        ejec_marzo = prog_marzo.get('monto_ejecutado', 0)
        ejec_junio = prog_junio.get('monto_ejecutado', 0)
        delta_ejecucion = ejec_junio - ejec_marzo
        delta_ejecucion_pct = ((delta_ejecucion / ejec_marzo) * 100) if ejec_marzo > 0 else 0
        
        # Velocidad de ejecución (promedio mensual)
        velocidad_ejecucion = delta_ejecucion / 3  # 3 meses entre marzo y junio
        
        comparison = {
            'key': key,
            'organismo': prog_marzo['organismo'],
            'programa': prog_marzo['programa'],
            'presupuesto': prog_marzo.get('monto_presupuestado', 0),
            'ejecucion_marzo': ejec_marzo,
            'ejecucion_junio': ejec_junio,
            'delta_ejecucion': delta_ejecucion,
            'delta_ejecucion_pct': round(delta_ejecucion_pct, 2),
            'velocidad_mensual': round(velocidad_ejecucion, 2),
            'porcentaje_marzo': prog_marzo.get('porcentaje_ejecucion', 0),
            'porcentaje_junio': prog_junio.get('porcentaje_ejecucion', 0),
            'aceleracion': 'acelerado' if delta_ejecucion_pct > 50 else 'desacelerado' if delta_ejecucion_pct < 10 else 'estable'
        }
        comparisons.append(comparison)
    
    # Top 10 programas con mayor aceleración
    top_aceleracion = sorted(comparisons, key=lambda x: x['delta_ejecucion_pct'], reverse=True)[:10]
    print(f"\n🚀 TOP 10 PROGRAMAS CON MAYOR ACELERACIÓN:")
    for i, comp in enumerate(top_aceleracion, 1):
        print(f"{i:2d}. {comp['organismo'][:50]:<50} Δ{comp['delta_ejecucion_pct']:>6.1f}%")
    
    # Top 10 programas con desaceleración
    top_desaceleracion = sorted(comparisons, key=lambda x: x['delta_ejecucion_pct'])[:10]
    print(f"\n⚠ TOP 10 PROGRAMAS CON DESACELERACIÓN/MENOR CRECIMIENTO:")
    for i, comp in enumerate(top_desaceleracion, 1):
        print(f"{i:2d}. {comp['organismo'][:50]:<50} Δ{comp['delta_ejecucion_pct']:>6.1f}%")
    
    return {
        'programas_comunes': len(keys_common),
        'solo_marzo': len(keys_only_marzo),
        'solo_junio': len(keys_only_junio),
        'comparaciones': comparisons,
        'top_aceleracion': top_aceleracion,
        'top_desaceleracion': top_desaceleracion
    }


def main():
    """Función principal con soporte multi-período"""
    print(f"\n{'#'*80}")
    print(f"# PARSER DE PRESUPUESTO PROVINCIAL - CÓRDOBA 2025 (MULTI-PERÍODO)")
    print(f"{'#'*80}")
    
    # Inicializar normalizer compartido
    normalizer = OrganismoNormalizer()
    
    # Procesar ambos períodos
    marzo_programas, marzo_consolidated = process_period('marzo', normalizer)
    junio_programas, junio_consolidated = process_period('junio', normalizer)
    
    # Generar reportes por período
    if marzo_programas:
        print(f"\n{'='*80}")
        print(f"GENERANDO REPORTES: MARZO 2025")
        print(f"{'='*80}")
        marzo_files = generate_reports(marzo_consolidated, marzo_programas, normalizer, periodo='marzo')
    
    if junio_programas:
        print(f"\n{'='*80}")
        print(f"GENERANDO REPORTES: JUNIO 2025")
        print(f"{'='*80}")
        junio_files = generate_reports(junio_consolidated, junio_programas, normalizer, periodo='junio')
    
    # Análisis comparativo si tenemos ambos períodos
    if marzo_programas and junio_programas:
        comparison_data = compare_periods(marzo_programas, junio_programas)
        
        # Guardar análisis comparativo
        output_path = OUTPUT_DIR / "comparacion_marzo_junio_2025.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(comparison_data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Guardado análisis comparativo: {output_path}")
        
        # Generar dataset consolidado para modelos ML
        all_programas_ml = marzo_programas + junio_programas
        ml_dataset = {
            'metadata': {
                'total_registros': len(all_programas_ml),
                'periodos': ['marzo', 'junio'],
                'fecha_generacion': datetime.now().isoformat()
            },
            'programas': all_programas_ml,
            'comparaciones': comparison_data['comparaciones']
        }
        
        output_path = OUTPUT_DIR / "dataset_ml_presupuesto_2025.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ml_dataset, f, ensure_ascii=False, indent=2)
        print(f"✓ Guardado dataset ML: {output_path}")
    
    # Resumen final
    print(f"\n{'#'*80}")
    print(f"# ✅ PROCESAMIENTO COMPLETADO")
    print(f"{'#'*80}")
    print(f"\n📊 RESUMEN GENERAL:")
    if marzo_programas:
        print(f"  • Marzo 2025: {len(marzo_programas)} programas")
    if junio_programas:
        print(f"  • Junio 2025: {len(junio_programas)} programas")
    if marzo_programas and junio_programas:
        print(f"  • Comparación: {comparison_data['programas_comunes']} programas comunes")
    print(f"\n{'#'*80}\n")


if __name__ == "__main__":
    main()



