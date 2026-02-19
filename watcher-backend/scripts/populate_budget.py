"""
Script para popular la base de datos con datos presupuestarios multi-período
Carga los datos extraídos de los Excel (Marzo, Junio) y genera comparaciones temporales

Autor: Watcher Fiscal Agent
Versión: 2.0 - Soporte multi-período
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Optional

# Agregar path para imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func, delete
from app.db.models import PresupuestoBase, MetricasGestion


# Rutas
BASE_DIR = Path(__file__).parent.parent.parent.parent
DATOS_DIR = BASE_DIR / "watcher-doc"
ML_DATASET_PATH = DATOS_DIR / "dataset_ml_presupuesto_2025.json"
COMPARISON_PATH = DATOS_DIR / "comparacion_marzo_junio_2025.json"


async def load_ml_dataset():
    """Carga dataset ML consolidado con datos de múltiples períodos"""
    print(f"📖 Cargando dataset ML desde: {ML_DATASET_PATH}")
    
    if not ML_DATASET_PATH.exists():
        print("⚠ Dataset ML no encontrado. Buscando archivos individuales...")
        return None
    
    with open(ML_DATASET_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ Metadata: {data['metadata']}")
    print(f"✓ Total programas: {len(data['programas'])}")
    print(f"✓ Períodos: {data['metadata'].get('periodos', [])}")
    
    return data


async def load_comparison_data():
    """Carga datos de comparación entre períodos"""
    print(f"📖 Cargando comparación desde: {COMPARISON_PATH}")
    
    if not COMPARISON_PATH.exists():
        print("⚠ Archivo de comparación no encontrado")
        return None
    
    with open(COMPARISON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ Programas comunes: {data.get('programas_comunes', 0)}")
    print(f"✓ Comparaciones: {len(data.get('comparaciones', []))}")
    
    return data


async def populate_presupuesto_base(session: AsyncSession, programas: List[Dict]) -> int:
    """Carga datos base de presupuesto"""
    print(f"\n{'='*80}")
    print("CARGANDO PRESUPUESTO BASE")
    print(f"{'='*80}")
    
    # Agrupar por key única para evitar duplicados (tomar el más reciente)
    unique_programas = {}
    for prog in programas:
        key = f"{prog['organismo']}-{prog['programa']}"
        # Preferir datos más recientes (junio sobre marzo)
        if key not in unique_programas or prog.get('periodo') == 'junio':
            unique_programas[key] = prog
    
    programas_cargados = 0
    programas_con_error = 0
    
    for prog in unique_programas.values():
        try:
            # Extraer código de programa
            programa_code = str(prog.get('programa', ''))
            subprograma_code = None
            if '-' in programa_code:
                parts = programa_code.split('-')
                programa_code = parts[0]
                subprograma_code = parts[1] if len(parts) > 1 else None
            
            # Crear registro
            presupuesto = PresupuestoBase(
                ejercicio=prog.get('ejercicio', 2025),
                organismo=prog.get('organismo', 'DESCONOCIDO'),
                programa=programa_code,
                subprograma=subprograma_code,
                partida_presupuestaria=prog.get('partida', ''),
                descripcion=prog.get('descripcion', '')[:500],  # Limitar longitud
                monto_inicial=prog.get('monto_presupuestado', 0.0),
                monto_vigente=prog.get('monto_presupuestado', 0.0),
                fecha_aprobacion=date(2025, 1, 1),
                fuente_financiamiento=prog.get('fuente', '')[:200],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session.add(presupuesto)
            programas_cargados += 1
            
            # Commit cada 100 registros
            if programas_cargados % 100 == 0:
                await session.commit()
                print(f"  ✓ Cargados: {programas_cargados}/{len(unique_programas)}", end='\r')
        
        except Exception as e:
            programas_con_error += 1
            if programas_con_error < 10:
                print(f"\n  ⚠ Error en programa: {e}")
            continue
    
    await session.commit()
    print(f"\n✓ Presupuesto base: {programas_cargados} registros")
    return programas_cargados


async def populate_metricas_gestion(session: AsyncSession, comparisons: List[Dict], programas: List[Dict]) -> int:
    """Carga métricas de gestión y comparaciones temporales"""
    print(f"\n{'='*80}")
    print("CARGANDO MÉTRICAS DE GESTIÓN")
    print(f"{'='*80}")
    
    # Limpiar métricas existentes
    await session.execute(delete(MetricasGestion))
    await session.commit()
    
    metricas_cargadas = 0
    
    # Agrupar programas por período
    programas_por_periodo = {}
    for prog in programas:
        periodo = prog.get('periodo', 'marzo')
        if periodo not in programas_por_periodo:
            programas_por_periodo[periodo] = []
        programas_por_periodo[periodo].append(prog)
    
    # Generar métricas por período y organismo
    for periodo, progs_periodo in programas_por_periodo.items():
        # Agrupar por organismo
        por_organismo = {}
        for prog in progs_periodo:
            org = prog.get('organismo', 'DESCONOCIDO')
            if org not in por_organismo:
                por_organismo[org] = []
            por_organismo[org].append(prog)
        
        # Crear métricas por organismo
        for organismo, progs in por_organismo.items():
            try:
                # Determinar fecha según período
                if periodo == 'marzo':
                    fecha_inicio = date(2025, 1, 1)
                    fecha_fin = date(2025, 3, 31)
                elif periodo == 'junio':
                    fecha_inicio = date(2025, 1, 1)
                    fecha_fin = date(2025, 6, 30)
                else:
                    fecha_inicio = date(2025, 1, 1)
                    fecha_fin = date(2025, 12, 31)
                
                # Calcular agregados
                presupuesto_vigente = sum(p.get('monto_presupuestado', 0) for p in progs)
                ejecutado = sum(p.get('monto_ejecutado', 0) for p in progs)
                porcentaje_ejecucion = (ejecutado / presupuesto_vigente * 100) if presupuesto_vigente > 0 else 0
                
                # Contar alertas
                total_ops = len(progs)
                ops_alto_riesgo = sum(1 for p in progs if p.get('alerta') == 'EJECUCION_ALTA')
                ops_medio_riesgo = sum(1 for p in progs if p.get('alerta') == 'EJECUCION_BAJA')
                
                metrica = MetricasGestion(
                    ejercicio=2025,
                    periodo='mensual' if periodo in ['marzo', 'junio'] else 'anual',
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    organismo=organismo,
                    programa=None,  # Agregado a nivel organismo
                    presupuesto_inicial=presupuesto_vigente,
                    presupuesto_vigente=presupuesto_vigente,
                    ejecutado_acumulado=ejecutado,
                    porcentaje_ejecucion=round(porcentaje_ejecucion, 2),
                    desvio_presupuestario=0.0,  # Se calculará con comparaciones
                    total_operaciones=total_ops,
                    operaciones_alto_riesgo=ops_alto_riesgo,
                    operaciones_medio_riesgo=ops_medio_riesgo,
                    monto_alto_riesgo=0.0,
                    porcentaje_riesgo=round((ops_alto_riesgo / total_ops * 100) if total_ops > 0 else 0, 2),
                    tiene_alertas=(ops_alto_riesgo + ops_medio_riesgo) > 0,
                    created_at=datetime.now()
                )
                
                session.add(metrica)
                metricas_cargadas += 1
                
                if metricas_cargadas % 50 == 0:
                    await session.commit()
                    print(f"  ✓ Métricas cargadas: {metricas_cargadas}", end='\r')
            
            except Exception as e:
                print(f"\n  ⚠ Error en métricas para {organismo}: {e}")
                continue
    
    # Agregar métricas de comparación marzo-junio
    if comparisons:
        print("\n  Agregando comparaciones temporales...")
        for comp in comparisons[:100]:  # Limitar para no saturar
            try:
                # Buscar métrica de junio para este organismo
                result = await session.execute(
                    select(MetricasGestion).where(
                        MetricasGestion.organismo == comp.get('organismo'),
                        MetricasGestion.fecha_fin == date(2025, 6, 30)
                    )
                )
                metrica = result.scalar_one_or_none()
                
                if metrica:
                    # Agregar variaciones
                    metrica.variacion_mes_anterior = comp.get('delta_ejecucion_pct', 0.0)
                    metrica.desvio_presupuestario = comp.get('velocidad_mensual', 0.0)
            
            except Exception:
                continue
    
    await session.commit()
    print(f"\n✓ Métricas de gestión: {metricas_cargadas} registros")
    return metricas_cargadas


async def populate_database(ml_data: dict, comparison_data: Optional[dict]):
    """Popular base de datos con programas y métricas"""
    # Crear engine async
    DATABASE_URL = "sqlite+aiosqlite:///./sqlite.db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print(f"\n{'='*80}")
        print("POPULANDO BASE DE DATOS - MULTI-PERÍODO")
        print(f"{'='*80}")
        
        # Verificar si ya hay datos
        result = await session.execute(select(func.count(PresupuestoBase.id)))
        existing_count = result.scalar()
        
        if existing_count > 0:
            print(f"⚠ Base de datos ya tiene {existing_count} registros en PresupuestoBase")
            response = input("¿Desea eliminar y recargar? (s/N): ").strip().lower()
            if response == 's':
                print("✓ Eliminando registros existentes...")
                await session.execute(delete(PresupuestoBase))
                await session.commit()
                print("✓ Registros existentes eliminados")
            else:
                print("⚠ Manteniendo registros existentes, solo actualizando métricas")
        
        # Cargar presupuesto base
        if existing_count == 0 or response == 's':
            programas_cargados = await populate_presupuesto_base(session, ml_data['programas'])
        else:
            programas_cargados = existing_count
        
        # Cargar métricas de gestión
        comparisons = comparison_data.get('comparaciones', []) if comparison_data else []
        metricas_cargadas = await populate_metricas_gestion(session, comparisons, ml_data['programas'])
        
        # Resumen final
        print(f"\n{'='*80}")
        print("RESUMEN DE CARGA")
        print(f"{'='*80}")
        print(f"✓ Programas en PresupuestoBase: {programas_cargados}")
        print(f"✓ Métricas de gestión: {metricas_cargadas}")
        
        # Verificar carga
        result = await session.execute(select(func.count(PresupuestoBase.id)))
        total_presupuesto = result.scalar()
        result = await session.execute(select(func.count(MetricasGestion.id)))
        total_metricas = result.scalar()
        
        print(f"\n{'='*80}")
        print("VERIFICACIÓN FINAL")
        print(f"{'='*80}")
        print(f"✓ Total registros PresupuestoBase: {total_presupuesto}")
        print(f"✓ Total registros MetricasGestion: {total_metricas}")
        
        # Top organismos
        result = await session.execute(
            select(
                PresupuestoBase.organismo,
                func.count(PresupuestoBase.id).label('count'),
                func.sum(PresupuestoBase.monto_vigente).label('total')
            ).group_by(PresupuestoBase.organismo)
            .order_by(func.sum(PresupuestoBase.monto_vigente).desc())
            .limit(10)
        )
        
        print(f"\n{'='*80}")
        print("TOP 10 ORGANISMOS POR PRESUPUESTO")
        print(f"{'='*80}")
        for organismo, count, total in result:
            print(f"  • {organismo[:50]:<50} ${total:>15,.0f} ({count} progs)")
        
        await engine.dispose()


async def main():
    """Función principal multi-período"""
    print(f"\n{'#'*80}")
    print("# CARGA DE PRESUPUESTO A BASE DE DATOS - MULTI-PERÍODO")
    print(f"{'#'*80}\n")
    
    try:
        # Cargar dataset ML consolidado
        ml_data = await load_ml_dataset()
        
        if not ml_data:
            print("\n❌ Error: No se encontró dataset ML")
            print("   Primero ejecute: python scripts/parse_excel_presupuesto.py")
            sys.exit(1)
        
        # Cargar comparaciones
        comparison_data = await load_comparison_data()
        
        # Popular DB
        await populate_database(ml_data, comparison_data)
        
        print(f"\n{'#'*80}")
        print("# ✅ CARGA COMPLETADA EXITOSAMENTE")
        print(f"{'#'*80}\n")
        print(f"✓ Datos de {len(ml_data['metadata'].get('periodos', []))} períodos cargados")
        print("✓ Base de datos lista para análisis temporal")
        print(f"\n{'#'*80}\n")
    
    except FileNotFoundError as e:
        print("\n❌ Error: Archivo no encontrado")
        print(f"   {e}")
        print("\n   Primero ejecute: python scripts/parse_excel_presupuesto.py")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

