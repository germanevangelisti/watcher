"""
Servicio de Procesamiento de Menciones en Boletines
Procesa boletines para extraer y almacenar menciones jurisdiccionales.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import Boletin, MencionJurisdiccional
from app.services.mencion_extractor import get_mencion_extractor
from pathlib import Path

logger = logging.getLogger(__name__)


class MencionProcessor:
    """
    Procesador de menciones en boletines.
    
    Extrae menciones jurisdiccionales del contenido de boletines
    y las almacena en la base de datos.
    """
    
    def __init__(self):
        """Inicializa el procesador."""
        self.extractor = get_mencion_extractor()
        self.stats = {
            "boletines_procesados": 0,
            "menciones_encontradas": 0,
            "menciones_guardadas": 0,
            "errores": 0
        }
    
    async def procesar_boletin(
        self,
        boletin: Boletin,
        db: AsyncSession,
        forzar: bool = False
    ) -> Dict:
        """
        Procesa un boletín individual para extraer menciones.
        
        Args:
            boletin: Boletín a procesar
            db: Sesión de base de datos
            forzar: Si True, procesa aunque ya tenga menciones
            
        Returns:
            Diccionario con resultados del procesamiento
        """
        try:
            # Verificar si ya fue procesado
            if not forzar:
                query = select(MencionJurisdiccional).where(
                    MencionJurisdiccional.boletin_id == boletin.id
                )
                result = await db.execute(query)
                menciones_existentes = result.scalars().all()
                
                if menciones_existentes:
                    logger.info(
                        f"Boletín {boletin.id} ya tiene {len(menciones_existentes)} menciones. "
                        "Usar forzar=True para reprocesar."
                    )
                    return {
                        "boletin_id": boletin.id,
                        "ya_procesado": True,
                        "menciones_existentes": len(menciones_existentes)
                    }
            
            # Cargar jurisdicciones si no están cargadas
            if not self.extractor.jurisdicciones_cache:
                await self.extractor.load_jurisdicciones(db)
            
            # Obtener contenido del boletín
            contenido = await self._obtener_contenido_boletin(boletin)
            
            if not contenido:
                logger.warning(f"No se pudo obtener contenido del boletín {boletin.id}")
                return {
                    "boletin_id": boletin.id,
                    "error": "No se pudo leer el contenido"
                }
            
            # Extraer menciones
            menciones = self.extractor.extraer_menciones(contenido)
            
            # Si forzar, eliminar menciones existentes
            if forzar:
                await db.execute(
                    select(MencionJurisdiccional).where(
                        MencionJurisdiccional.boletin_id == boletin.id
                    ).delete()
                )
            
            # Guardar menciones en la base de datos
            menciones_guardadas = 0
            for mencion in menciones:
                nueva_mencion = MencionJurisdiccional(
                    boletin_id=boletin.id,
                    jurisdiccion_id=mencion["jurisdiccion_id"],
                    tipo_mencion=mencion["tipo_mencion"],
                    fragmento_texto=mencion["fragmento_texto"][:500],  # Limitar longitud
                    extra_data={
                        "posicion": mencion["posicion"],
                        "variante_encontrada": mencion["variante_encontrada"],
                        "fecha_extraccion": datetime.now().isoformat()
                    }
                )
                db.add(nueva_mencion)
                menciones_guardadas += 1
            
            await db.commit()
            
            self.stats["boletines_procesados"] += 1
            self.stats["menciones_encontradas"] += len(menciones)
            self.stats["menciones_guardadas"] += menciones_guardadas
            
            # Generar resumen
            resumen = self.extractor.generar_resumen_menciones(menciones)
            
            logger.info(
                f"Boletín {boletin.id}: {menciones_guardadas} menciones guardadas"
            )
            
            return {
                "boletin_id": boletin.id,
                "menciones_encontradas": len(menciones),
                "menciones_guardadas": menciones_guardadas,
                "resumen": resumen
            }
            
        except Exception as e:
            self.stats["errores"] += 1
            logger.error(f"Error procesando boletín {boletin.id}: {e}", exc_info=True)
            return {
                "boletin_id": boletin.id,
                "error": str(e)
            }
    
    async def _obtener_contenido_boletin(self, boletin: Boletin) -> Optional[str]:
        """
        Obtiene el contenido de texto de un boletín.
        
        Args:
            boletin: Boletín del cual obtener contenido
            
        Returns:
            Contenido de texto o None si no se puede leer
        """
        try:
            # Buscar PDF en varios posibles directorios
            pdf_path = Path(boletin.filename)
            
            posibles_paths = [
                pdf_path,
                Path(f"/Users/germanevangelisti/watcher-agent/boletines") / pdf_path.name,
            ]
            
            # Si tenemos la fecha, agregar path con estructura de directorios
            if boletin.date:
                if isinstance(boletin.date, str):
                    # Parsear fecha si es string (formato YYYY-MM-DD)
                    try:
                        from datetime import datetime as dt
                        date_obj = dt.fromisoformat(boletin.date.split()[0]).date()
                        posibles_paths.append(
                            Path(f"/Users/germanevangelisti/watcher-agent/boletines") / str(date_obj.year) / f"{date_obj.month:02d}" / pdf_path.name
                        )
                    except:
                        pass
                else:
                    posibles_paths.append(
                        Path(f"/Users/germanevangelisti/watcher-agent/boletines") / str(boletin.date.year) / f"{boletin.date.month:02d}" / pdf_path.name
                    )
            
            pdf_encontrado = None
            for path in posibles_paths:
                if path.exists():
                    pdf_encontrado = path
                    break
            
            if not pdf_encontrado:
                logger.warning(
                    f"No se encontró archivo PDF para boletín {boletin.id}: {boletin.filename}"
                )
                return None
            
            # Extraer texto del PDF usando el registry
            logger.info(f"Extrayendo texto de {pdf_encontrado}")
            from app.services.extractors import ExtractorRegistry
            
            resultado = await ExtractorRegistry.extract(pdf_encontrado)
            
            if not resultado.success or not resultado.full_text.strip():
                logger.warning(f"PDF vacío o sin texto: {pdf_encontrado}")
                return None
            
            return resultado.full_text
            
        except Exception as e:
            logger.error(f"Error leyendo contenido del boletín {boletin.id}: {e}")
            return None
    
    async def procesar_lote(
        self,
        limite: int,
        db: AsyncSession,
        forzar: bool = False,
        filtro_fecha_desde: Optional[datetime] = None,
        filtro_fecha_hasta: Optional[datetime] = None
    ) -> Dict:
        """
        Procesa un lote de boletines para extraer menciones.
        
        Args:
            limite: Número máximo de boletines a procesar
            db: Sesión de base de datos
            forzar: Si True, reprocesa boletines ya procesados
            filtro_fecha_desde: Filtrar boletines desde esta fecha
            filtro_fecha_hasta: Filtrar boletines hasta esta fecha
            
        Returns:
            Diccionario con estadísticas del procesamiento
        """
        # Reset stats
        self.stats = {
            "boletines_procesados": 0,
            "menciones_encontradas": 0,
            "menciones_guardadas": 0,
            "errores": 0
        }
        
        try:
            # Cargar jurisdicciones una vez
            await self.extractor.load_jurisdicciones(db)
            
            # Construir query
            query = select(Boletin).where(
                Boletin.jurisdiccion_id == 1  # Solo boletines provinciales
            )
            
            # Aplicar filtros de fecha
            if filtro_fecha_desde:
                query = query.where(Boletin.date >= filtro_fecha_desde)
            if filtro_fecha_hasta:
                query = query.where(Boletin.date <= filtro_fecha_hasta)
            
            # Ordenar por fecha descendente
            query = query.order_by(Boletin.date.desc()).limit(limite)
            
            result = await db.execute(query)
            boletines = result.scalars().all()
            
            logger.info(f"Procesando {len(boletines)} boletines...")
            
            resultados = []
            for boletin in boletines:
                resultado = await self.procesar_boletin(boletin, db, forzar)
                resultados.append(resultado)
            
            return {
                "total_boletines": len(boletines),
                "stats": self.stats,
                "resultados": resultados
            }
            
        except Exception as e:
            logger.error(f"Error en procesamiento de lote: {e}", exc_info=True)
            return {
                "error": str(e),
                "stats": self.stats
            }
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas del procesamiento actual."""
        return self.stats.copy()


# Singleton global
_processor_instance: Optional[MencionProcessor] = None


def get_mencion_processor() -> MencionProcessor:
    """Obtiene la instancia global del procesador de menciones."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = MencionProcessor()
    return _processor_instance
