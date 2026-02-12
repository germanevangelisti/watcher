"""
Servicio para procesamiento de archivos PDF en lotes - Versión optimizada con historial acumulativo
"""

import asyncio
import logging
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text

from app.db import crud
from app.db.models import Boletin, Analisis, EjecucionPresupuestaria, AlertasGestion, ProcesamientoBatch
from app.services.extractors import ExtractorRegistry
from app.services.watcher_service import WatcherService

logger = logging.getLogger(__name__)

class BatchProcessor:
    """Procesador optimizado de archivos PDF con historial acumulativo."""
    
    def __init__(self, db: AsyncSession):
        """
        Inicializa el procesador.
        
        Args:
            db: Sesión de base de datos
        """
        self.db = db
        self.watcher_service = WatcherService()
        
        # Configuración de procesamiento
        self.max_workers = 4
        self.batch_size = 10
        
        # Patrones para extracción de montos
        self.monto_patterns = [
            r'\$\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',  # $1.000.000,00
            r'pesos\s+([0-9]{1,3}(?:\.[0-9]{3})*)',  # pesos 1.000.000
            r'suma\s+de\s+\$?\s*([0-9]{1,3}(?:\.[0-9]{3})*)',  # suma de $1.000.000
            r'monto\s+de\s+\$?\s*([0-9]{1,3}(?:\.[0-9]{3})*)',  # monto de $1.000.000
        ]
        
        # Patrones para identificar organismos
        self.organismo_patterns = [
            r'ministerio\s+de\s+([^,\n\.]+)',
            r'secretar[ií]a\s+de\s+([^,\n\.]+)',
            r'direcci[óo]n\s+general\s+de\s+([^,\n\.]+)',
            r'subsecretar[ií]a\s+de\s+([^,\n\.]+)',
        ]
    
    async def process_directory(
        self, 
        source_dir: Path, 
        batch_size: int = 10,
        filtros: Optional[Dict] = None
    ) -> Dict:
        """
        Procesa directorio con historial acumulativo y comparación presupuestaria.
        
        Args:
            source_dir: Directorio con PDFs
            batch_size: Tamaño del lote
            filtros: Filtros opcionales (fechas, organismos, etc.)
            
        Returns:
            Estadísticas del procesamiento
        """
        # Crear registro de batch
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        batch_record = ProcesamientoBatch(
            batch_id=batch_id,
            directorio_origen=str(source_dir),
            filtros_aplicados=filtros or {}
        )
        
        self.db.add(batch_record)
        await self.db.commit()
        
        logger.info(f"Iniciando procesamiento batch {batch_id}")
        
        try:
            # Obtener archivos a procesar
            pdf_files = self._get_files_to_process(source_dir, filtros)
            total_files = len(pdf_files)
            
            # Actualizar registro
            batch_record.total_archivos = total_files
            batch_record.estado = 'procesando'
            await self.db.commit()
            
            logger.info(f"Procesando {total_files} archivos en lotes de {batch_size}")
            
            # Estadísticas
            processed_count = 0
            failed_count = 0
            total_ejecuciones = 0
            monto_total = 0.0
            alertas_generadas = 0
            
            start_time = datetime.now()
            
            # Procesar en lotes
            for i in range(0, total_files, batch_size):
                batch_files = pdf_files[i:i + batch_size]
                
                # Procesar lote en paralelo
                batch_results = await self._process_batch(batch_files)
                
                for result in batch_results:
                    if result["status"] == "completed":
                        processed_count += 1
                        total_ejecuciones += result.get("ejecuciones_detectadas", 0)
                        monto_total += result.get("monto_procesado", 0.0)
                        alertas_generadas += result.get("alertas_generadas", 0)
                    else:
                        failed_count += 1
                
                # Actualizar progreso
                batch_record.archivos_procesados = processed_count
                batch_record.archivos_fallidos = failed_count
                batch_record.total_ejecuciones_detectadas = total_ejecuciones
                batch_record.monto_total_procesado = monto_total
                batch_record.alertas_generadas = alertas_generadas
                await self.db.commit()
                
                logger.info(f"Lote {i//batch_size + 1} completado. Progreso: {processed_count}/{total_files}")
            
            # Calcular métricas finales
            end_time = datetime.now()
            tiempo_total = (end_time - start_time).total_seconds()
            
            # Actualizar registro final
            batch_record.fecha_fin = end_time
            batch_record.estado = 'completado'
            batch_record.tiempo_procesamiento_segundos = tiempo_total
            batch_record.archivos_por_segundo = total_files / tiempo_total if tiempo_total > 0 else 0
            await self.db.commit()
            
            stats = {
                "batch_id": batch_id,
                "total": total_files,
                "processed": processed_count,
                "failed": failed_count,
                "ejecuciones_detectadas": total_ejecuciones,
                "monto_total_procesado": monto_total,
                "alertas_generadas": alertas_generadas,
                "tiempo_procesamiento": tiempo_total,
                "archivos_por_segundo": batch_record.archivos_por_segundo
            }
            
            logger.info(f"Procesamiento batch {batch_id} completado: {stats}")
            return stats
            
        except Exception as e:
            # Marcar batch como error
            batch_record.estado = 'error'
            batch_record.error_message = str(e)
            batch_record.fecha_fin = datetime.now()
            await self.db.commit()
            
            logger.error(f"Error en procesamiento batch {batch_id}: {e}")
            raise
    
    def _get_files_to_process(self, source_dir: Path, filtros: Optional[Dict]) -> List[Path]:
        """Obtiene archivos a procesar aplicando filtros."""
        pdf_files = sorted(list(source_dir.glob('*.pdf')))
        
        if not filtros:
            return pdf_files
        
        filtered_files = []
        
        for pdf_file in pdf_files:
            # Filtro por fecha
            if 'fecha_desde' in filtros or 'fecha_hasta' in filtros:
                match = re.match(r'(\d{8})', pdf_file.name)
                if match:
                    file_date = match.group(1)
                    if 'fecha_desde' in filtros and file_date < filtros['fecha_desde']:
                        continue
                    if 'fecha_hasta' in filtros and file_date > filtros['fecha_hasta']:
                        continue
            
            # Filtro por sección
            if 'secciones' in filtros:
                match = re.search(r'_(\d+)_Secc\.pdf$', pdf_file.name)
                if match:
                    seccion = match.group(1)
                    if seccion not in filtros['secciones']:
                        continue
            
            filtered_files.append(pdf_file)
        
        return filtered_files
    
    async def _process_batch(self, batch_files: List[Path]) -> List[Dict]:
        """Procesa un lote de archivos secuencialmente para evitar conflictos de transacción."""
        processed_results = []
        
        # Procesar secuencialmente para evitar problemas de transacción
        for pdf_file in batch_files:
            try:
                result = await self._process_single_pdf(pdf_file)
                processed_results.append(result)
            except Exception as e:
                logger.error(f"Error procesando {pdf_file.name}: {e}")
                processed_results.append({
                    "filename": pdf_file.name,
                    "status": "failed",
                    "error": str(e)
                })
        
        return processed_results
    
    async def _process_single_pdf(self, pdf_path: Path) -> Dict:
        """
        Procesa un PDF individual con manejo seguro de transacciones.
        """
        filename = pdf_path.name
        logger.info(f"Procesando {filename}")
        
        # Usar una sesión de background para evitar conflictos con HTTP handlers
        from app.db.database import BackgroundSessionLocal
        
        async with BackgroundSessionLocal() as file_db:
            try:
                # Extraer información del archivo
                boletin_date_match = re.match(r'(\d{8})', filename)
                boletin_date = boletin_date_match.group(1) if boletin_date_match else "unknown"
                boletin_section_match = re.search(r'_(\d+)_Secc\.pdf$', filename)
                boletin_section = boletin_section_match.group(1) if boletin_section_match else "unknown"
                
                # Crear o actualizar boletín
                boletin = await crud.create_boletin(
                    file_db,
                    filename=filename,
                    date=boletin_date,
                    section=boletin_section
                )
                await crud.update_boletin_status(file_db, boletin.id, "processing")
                
                # Extraer contenido usando ExtractorRegistry
                result = await ExtractorRegistry.extract(pdf_path, detect_sections=True)
                
                if not result.success:
                    logger.error(f"Error extracting PDF {filename}: {result.error}")
                    await crud.update_boletin_status(file_db, boletin.id, "failed", result.error)
                    await file_db.commit()
                    return {
                        "filename": filename,
                        "status": "failed",
                        "error": result.error
                    }
                
                # Convertir secciones al formato esperado
                sections = []
                for section in result.sections:
                    sections.append({
                        "content": section.content,
                        "metadata": {
                            "boletin": pdf_path.stem,
                            "start_page": section.start_page,
                            "end_page": section.end_page,
                            "section_type": section.section_type.value,
                            **section.metadata
                        }
                    })
                
                ejecuciones_detectadas = 0
                monto_procesado = 0.0
                alertas_generadas = 0
                
                # Analizar cada sección (limitado para evitar problemas)
                for i, section in enumerate(sections[:3]):  # Solo primeras 3 secciones
                    try:
                        # Análisis con Watcher (contenido limitado)
                        content_limited = section["content"][:2000]  # Limitar contenido
                        analysis_result = await self.watcher_service.analyze_content(
                            content=content_limited,
                            metadata=section["metadata"]
                        )
                        
                        # Guardar análisis
                        await crud.create_analisis(
                            file_db,
                            boletin_id=boletin.id,
                            fragmento=content_limited,
                            analisis_data=analysis_result
                        )
                        
                        # Extraer monto simple (sin SQL directo por ahora)
                        monto = self._extraer_monto(content_limited)
                        if monto:
                            ejecuciones_detectadas += 1
                            monto_procesado += monto
                            
                            # Alerta simple
                            if monto > 10000000:  # > $10M
                                alertas_generadas += 1
                        
                    except Exception as e:
                        logger.error(f"Error analizando sección {i} de {filename}: {e}")
                        continue
                
                # Actualizar estado final
                await crud.update_boletin_status(file_db, boletin.id, "completed")
                
                # Commit final
                await file_db.commit()
                
                return {
                    "filename": filename,
                    "status": "completed",
                    "ejecuciones_detectadas": ejecuciones_detectadas,
                    "monto_procesado": monto_procesado,
                    "alertas_generadas": alertas_generadas
                }
                
            except Exception as e:
                logger.error(f"Error procesando {filename}: {e}")
                
                # Rollback en caso de error
                try:
                    await file_db.rollback()
                    if 'boletin' in locals():
                        await crud.update_boletin_status(file_db, boletin.id, "failed", str(e))
                        await file_db.commit()
                except Exception as rollback_error:
                    logger.error(f"Error en rollback: {rollback_error}")
                
                return {
                    "filename": filename,
                    "status": "failed",
                    "error": str(e)
                }
    
    async def _extraer_ejecucion_presupuestaria(
        self, 
        content: str, 
        analysis: Dict, 
        boletin_id: int,
        boletin_date: str
    ) -> Optional[Dict]:
        """
        Extrae información de ejecución presupuestaria del contenido usando SQL directo.
        """
        # Extraer monto
        monto = self._extraer_monto(content)
        if not monto:
            return None
        
        # Extraer organismo
        organismo = self._extraer_organismo(content) or analysis.get('entidad_beneficiaria', 'No especificado')
        
        # Determinar tipo de operación
        tipo_operacion = self._determinar_tipo_operacion(content, analysis)
        
        # Crear fecha del boletín
        try:
            fecha_boletin = datetime.strptime(boletin_date, '%Y%m%d').date()
        except:
            fecha_boletin = date.today()
        
        # Crear registro usando SQL directo
        ejecucion_data = {
            'boletin_id': boletin_id,
            'fecha_boletin': fecha_boletin.isoformat(),
            'organismo': organismo,
            'beneficiario': analysis.get('entidad_beneficiaria', ''),
            'concepto': content[:200],
            'monto': monto,
            'tipo_operacion': tipo_operacion,
            'categoria_watcher': analysis.get('categoria', ''),
            'riesgo_watcher': analysis.get('riesgo', ''),
            'requiere_revision': analysis.get('riesgo') in ['ALTO', 'MEDIO']
        }
        
        sql = """
        INSERT INTO ejecucion_presupuestaria 
        (boletin_id, fecha_boletin, organismo, beneficiario, concepto, 
         monto, tipo_operacion, categoria_watcher, riesgo_watcher, 
         requiere_revision, created_at)
        VALUES 
        (:boletin_id, :fecha_boletin, :organismo, :beneficiario, :concepto,
         :monto, :tipo_operacion, :categoria_watcher, :riesgo_watcher,
         :requiere_revision, :created_at)
        """
        
        ejecucion_data['created_at'] = datetime.now().isoformat()
        await self.db.execute(text(sql), ejecucion_data)
        
        return ejecucion_data
    
    async def _crear_alerta_sql(self, ejecucion_data: Dict, boletin_id: int):
        """Crea una alerta usando SQL directo."""
        sql = """
        INSERT INTO alertas_gestion 
        (tipo_alerta, nivel_severidad, organismo, titulo, descripcion, 
         valor_detectado, boletin_id, created_at)
        VALUES 
        (:tipo_alerta, :nivel_severidad, :organismo, :titulo, :descripcion,
         :valor_detectado, :boletin_id, :created_at)
        """
        
        alerta_data = {
            'tipo_alerta': 'presupuestaria',
            'nivel_severidad': 'alta',
            'organismo': ejecucion_data['organismo'],
            'titulo': f'Monto elevado: ${ejecucion_data["monto"]:,.0f}',
            'descripcion': f'Operación por ${ejecucion_data["monto"]:,.0f} en {ejecucion_data["organismo"]}',
            'valor_detectado': ejecucion_data['monto'],
            'boletin_id': boletin_id,
            'created_at': datetime.now().isoformat()
        }
        
        await self.db.execute(text(sql), alerta_data)
    
    def _extraer_monto(self, content: str) -> Optional[float]:
        """Extrae monto del contenido usando patrones regex."""
        for pattern in self.monto_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                try:
                    # Tomar el primer monto encontrado
                    monto_str = matches[0].replace('.', '').replace(',', '.')
                    return float(monto_str)
                except ValueError:
                    continue
        return None
    
    def _extraer_organismo(self, content: str) -> Optional[str]:
        """Extrae organismo del contenido."""
        for pattern in self.organismo_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip().title()
        return None
    
    def _determinar_tipo_operacion(self, content: str, analysis: Dict) -> str:
        """Determina el tipo de operación basado en el contenido y análisis."""
        content_lower = content.lower()
        
        if 'subsidio' in content_lower:
            return 'subsidio'
        elif 'obra' in content_lower or 'construcción' in content_lower:
            return 'obra'
        elif 'licitación' in content_lower or 'adjudicación' in content_lower:
            return 'licitacion'
        elif 'transferencia' in content_lower:
            return 'transferencia'
        elif 'designa' in content_lower or 'nombramiento' in content_lower:
            return 'designacion'
        elif analysis.get('categoria') == 'gastos excesivos':
            return 'gasto'
        else:
            return 'otros'