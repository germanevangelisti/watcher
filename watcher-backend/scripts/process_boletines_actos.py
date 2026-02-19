"""
Script para procesar boletines y extraer actos administrativos
Procesa los boletines de agosto 2025 y extrae actos con impacto fiscal

Autor: Watcher Fiscal Agent
"""

import asyncio
import sys
from pathlib import Path

# Agregar path para imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func
from app.db.models import Boletin, ActoAdministrativo
from app.services.acto_parser import ActoAdministrativoParser


# Rutas
BASE_DIR = Path(__file__).parent.parent
BOLETINES_PROCESADOS = BASE_DIR / "data" / "processed"


async def process_boletines(limit: int = None):
    """Procesa boletines y extrae actos administrativos"""
    
    # Crear engine async
    DATABASE_URL = "sqlite+aiosqlite:///./sqlite.db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Inicializar parser
    parser = ActoAdministrativoParser()
    
    print(f"\n{'#'*80}")
    print("# PROCESAMIENTO DE BOLETINES - EXTRACCIÓN DE ACTOS")
    print(f"{'#'*80}\n")
    
    async with async_session() as session:
        # Verificar si ya hay actos
        result = await session.execute(select(func.count(ActoAdministrativo.id)))
        existing = result.scalar()
        
        if existing > 0:
            print(f"⚠ Ya existen {existing} actos en la base de datos")
            print("✓ Eliminando para recargar...")
            await session.execute("DELETE FROM actos_administrativos")
            await session.commit()
        
        # Obtener boletines de la DB
        result = await session.execute(
            select(Boletin).where(Boletin.status == 'completed').limit(limit) if limit 
            else select(Boletin).where(Boletin.status == 'completed')
        )
        boletines = result.scalars().all()
        
        print(f"📄 Boletines a procesar: {len(boletines)}")
        
        if len(boletines) == 0:
            print("\n⚠ No hay boletines procesados en la base de datos")
            print("   Primero ejecute el procesamiento batch de PDFs")
            return
        
        total_actos = 0
        boletines_procesados = 0
        
        for i, boletin in enumerate(boletines, 1):
            # Buscar archivo de texto procesado
            txt_file = BOLETINES_PROCESADOS / f"{boletin.filename.replace('.pdf', '.txt')}"
            
            if not txt_file.exists():
                print(f"⚠ [{i}/{len(boletines)}] Archivo no encontrado: {txt_file.name}")
                continue
            
            # Leer contenido
            with open(txt_file, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Parsear actos
            actos = parser.parse_boletin(contenido, boletin_id=boletin.id)
            
            if actos:
                # Guardar en DB
                for acto in actos:
                    acto_db = ActoAdministrativo(**acto.to_dict())
                    session.add(acto_db)
                
                await session.commit()
                total_actos += len(actos)
                boletines_procesados += 1
                
                print(f"✓ [{i}/{len(boletines)}] {boletin.filename}: {len(actos)} actos extraídos")
            else:
                print(f"  [{i}/{len(boletines)}] {boletin.filename}: sin actos detectados")
        
        # Estadísticas finales
        print(f"\n{'='*80}")
        print("RESUMEN DE PROCESAMIENTO")
        print(f"{'='*80}")
        print(f"✓ Boletines procesados: {boletines_procesados}/{len(boletines)}")
        print(f"✓ Total actos extraídos: {total_actos}")
        
        if total_actos > 0:
            # Estadísticas por tipo
            result = await session.execute(
                select(
                    ActoAdministrativo.tipo_acto,
                    func.count(ActoAdministrativo.id).label('count')
                ).group_by(ActoAdministrativo.tipo_acto).order_by(func.count(ActoAdministrativo.id).desc())
            )
            
            print("\n📊 ACTOS POR TIPO:")
            for tipo, count in result:
                print(f"   • {tipo:<30} {count:>4} actos")
            
            # Estadísticas por riesgo
            result = await session.execute(
                select(
                    ActoAdministrativo.nivel_riesgo,
                    func.count(ActoAdministrativo.id).label('count')
                ).group_by(ActoAdministrativo.nivel_riesgo).order_by(func.count(ActoAdministrativo.id).desc())
            )
            
            print("\n📊 ACTOS POR NIVEL DE RIESGO:")
            for nivel, count in result:
                print(f"   • {nivel:<30} {count:>4} actos")
            
            # Actos con monto
            result = await session.execute(
                select(func.count(ActoAdministrativo.id)).where(ActoAdministrativo.monto.isnot(None))
            )
            count_con_monto = result.scalar()
            print(f"\n💰 ACTOS CON MONTO: {count_con_monto}/{total_actos}")
            
            # Top 10 actos por monto
            result = await session.execute(
                select(ActoAdministrativo).where(ActoAdministrativo.monto.isnot(None)).order_by(ActoAdministrativo.monto.desc()).limit(10)
            )
            top_actos = result.scalars().all()
            
            if top_actos:
                print("\n💎 TOP 10 ACTOS POR MONTO:")
                for acto in top_actos:
                    print(f"   • ${acto.monto:>15,.0f} - {acto.tipo_acto} - {acto.organismo[:50]}")
        
        await engine.dispose()
    
    print(f"\n{'#'*80}")
    print("# ✅ PROCESAMIENTO COMPLETADO")
    print(f"{'#'*80}\n")


async def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Procesar boletines y extraer actos administrativos')
    parser.add_argument('--limit', type=int, default=None, help='Limitar número de boletines a procesar')
    parser.add_argument('--test', action='store_true', help='Modo prueba (solo 5 boletines)')
    
    args = parser.parse_args()
    
    limit = 5 if args.test else args.limit
    
    if limit:
        print(f"ℹ️  Modo limitado: procesando {limit} boletines")
    
    try:
        await process_boletines(limit=limit)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())



