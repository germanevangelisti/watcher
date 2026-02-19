"""
Script para vincular actos administrativos con programas presupuestarios
Usa el semantic matcher para encontrar los mejores matches

Autor: Watcher Fiscal Agent
"""

import asyncio
import json
import sys
from pathlib import Path

# Agregar path para imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func, delete
from app.db.models import ActoAdministrativo, PresupuestoBase, VinculoActoPresupuesto
from app.services.semantic_matcher import SemanticMatcher


# Rutas
BASE_DIR = Path(__file__).parent.parent.parent.parent
VOCABULARIO_PATH = BASE_DIR / "watcher-doc" / "vocabulario_semantico_fiscal.json"


async def vincular_actos():
    """Vincula actos con programas presupuestarios"""
    
    # Crear engine async
    DATABASE_URL = "sqlite+aiosqlite:///./sqlite.db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Inicializar matcher
    matcher = SemanticMatcher(vocabulario_path=VOCABULARIO_PATH if VOCABULARIO_PATH.exists() else None)
    
    print(f"\n{'#'*80}")
    print("# VINCULACIÓN DE ACTOS CON PROGRAMAS PRESUPUESTARIOS")
    print(f"{'#'*80}\n")
    
    async with async_session() as session:
        # Verificar si ya hay vínculos
        result = await session.execute(select(func.count(VinculoActoPresupuesto.id)))
        existing = result.scalar()
        
        if existing > 0:
            print(f"⚠ Ya existen {existing} vínculos en la base de datos")
            print("✓ Eliminando para recargar...")
            await session.execute(delete(VinculoActoPresupuesto))
            await session.commit()
        
        # Obtener todos los actos
        result = await session.execute(select(ActoAdministrativo))
        actos = result.scalars().all()
        
        print(f"📄 Total actos: {len(actos)}")
        
        if len(actos) == 0:
            print("\n⚠ No hay actos para vincular")
            print("   Primero ejecute: python scripts/process_boletines_actos.py")
            return
        
        # Obtener todos los programas
        result = await session.execute(select(PresupuestoBase))
        programas_db = result.scalars().all()
        
        print(f"💼 Total programas: {len(programas_db)}")
        
        if len(programas_db) == 0:
            print("\n⚠ No hay programas presupuestarios")
            print("   Primero ejecute: python scripts/populate_budget.py")
            return
        
        # Convertir programas a diccionarios
        programas = []
        for prog in programas_db:
            prog_dict = {
                'id': prog.id,
                'organismo': prog.organismo,
                'partida': prog.partida_presupuestaria,
                'keywords': prog.fuente_financiamiento.split(',') if prog.fuente_financiamiento else [],
                'descripcion': prog.descripcion or ''
            }
            programas.append(prog_dict)
        
        # Vincular cada acto
        print(f"\n{'='*80}")
        print("PROCESANDO VINCULACIONES")
        print(f"{'='*80}")
        
        total_vinculos = 0
        actos_vinculados = 0
        actos_sin_vinculo = 0
        
        for i, acto in enumerate(actos, 1):
            # Convertir acto a diccionario
            acto_dict = {
                'id': acto.id,
                'organismo': acto.organismo,
                'partida': acto.partida,
                'keywords': acto.keywords.split(',') if acto.keywords else [],
                'monto': acto.monto
            }
            
            # Buscar matches (top 3)
            vinculos = matcher.match_acto_con_programas(acto_dict, programas, top_n=3)
            
            if vinculos:
                # Guardar vínculos en DB
                for vinculo in vinculos:
                    vinculo_db = VinculoActoPresupuesto(
                        acto_id=vinculo.acto_id,
                        programa_id=vinculo.programa_id,
                        score_confianza=vinculo.score_confianza,
                        metodo_matching=vinculo.metodo_matching,
                        detalles_json=json.dumps(vinculo.detalles, ensure_ascii=False)
                    )
                    session.add(vinculo_db)
                
                total_vinculos += len(vinculos)
                actos_vinculados += 1
                
                # Mostrar mejor match
                mejor = vinculos[0]
                print(f"✓ [{i}/{len(actos)}] Acto {acto.id} → Programa {mejor.programa_id} (score: {mejor.score_confianza:.3f}, {mejor.metodo_matching})")
            else:
                actos_sin_vinculo += 1
                print(f"  [{i}/{len(actos)}] Acto {acto.id}: sin vinculo válido")
            
            # Commit cada 10 actos
            if i % 10 == 0:
                await session.commit()
        
        # Commit final
        await session.commit()
        
        # Estadísticas finales
        print(f"\n{'='*80}")
        print("RESUMEN DE VINCULACIÓN")
        print(f"{'='*80}")
        print(f"✓ Total actos procesados: {len(actos)}")
        print(f"✓ Actos vinculados: {actos_vinculados} ({actos_vinculados/len(actos)*100:.1f}%)")
        print(f"✗ Actos sin vínculo: {actos_sin_vinculo} ({actos_sin_vinculo/len(actos)*100:.1f}%)")
        print(f"✓ Total vínculos creados: {total_vinculos}")
        print(f"✓ Promedio vínculos/acto: {total_vinculos/actos_vinculados if actos_vinculados > 0 else 0:.2f}")
        
        # Estadísticas por método
        result = await session.execute(
            select(
                VinculoActoPresupuesto.metodo_matching,
                func.count(VinculoActoPresupuesto.id).label('count')
            ).group_by(VinculoActoPresupuesto.metodo_matching).order_by(func.count(VinculoActoPresupuesto.id).desc())
        )
        
        print("\n📊 VÍNCULOS POR MÉTODO:")
        for metodo, count in result:
            print(f"   • {metodo:<30} {count:>4} vínculos")
        
        # Estadísticas por score
        result = await session.execute(
            select(VinculoActoPresupuesto).order_by(VinculoActoPresupuesto.score_confianza.desc()).limit(10)
        )
        top_vinculos = result.scalars().all()
        
        if top_vinculos:
            print("\n🏆 TOP 10 VÍNCULOS POR CONFIANZA:")
            for vinculo in top_vinculos:
                print(f"   • Acto {vinculo.acto_id} → Programa {vinculo.programa_id} (score: {vinculo.score_confianza:.3f}, {vinculo.metodo_matching})")
        
        # Distribución de scores
        result = await session.execute(select(VinculoActoPresupuesto.score_confianza))
        scores = [row[0] for row in result.all()]
        
        if scores:
            print("\n📈 DISTRIBUCIÓN DE SCORES:")
            print(f"   • Promedio: {sum(scores)/len(scores):.3f}")
            print(f"   • Mínimo: {min(scores):.3f}")
            print(f"   • Máximo: {max(scores):.3f}")
            print(f"   • > 0.8 (alto): {sum(1 for s in scores if s > 0.8)} ({sum(1 for s in scores if s > 0.8)/len(scores)*100:.1f}%)")
            print(f"   • 0.6-0.8 (medio): {sum(1 for s in scores if 0.6 <= s <= 0.8)} ({sum(1 for s in scores if 0.6 <= s <= 0.8)/len(scores)*100:.1f}%)")
            print(f"   • < 0.6 (bajo): {sum(1 for s in scores if s < 0.6)} ({sum(1 for s in scores if s < 0.6)/len(scores)*100:.1f}%)")
        
        await engine.dispose()
    
    print(f"\n{'#'*80}")
    print("# ✅ VINCULACIÓN COMPLETADA")
    print(f"{'#'*80}\n")


async def main():
    """Función principal"""
    try:
        await vincular_actos()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())



