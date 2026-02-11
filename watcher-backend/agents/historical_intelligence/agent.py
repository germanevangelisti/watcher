"""
Historical Intelligence Agent - Análisis de documentos en contexto histórico

Este agente busca entidades en el historial, construye timelines,
detecta patrones sospechosos y genera alertas basadas en análisis temporal
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta

from sqlalchemy import text, select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    EntidadExtraida, MencionEntidad, RelacionEntidad, 
    Boletin, AlertasGestion
)
from .patterns import PATRONES_SOSPECHOSOS, PatternRule, get_pattern, get_all_patterns

logger = logging.getLogger(__name__)


class HistoricalIntelligenceAgent:
    """
    Agente de inteligencia histórica
    
    Analiza documentos considerando el contexto histórico de las entidades mencionadas.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.agent_type = "HISTORICAL_INTELLIGENCE"
        self.name = "Historical Intelligence Agent"
    
    async def execute(self, workflow: Any, task: Any) -> Dict[str, Any]:
        """
        Ejecuta una tarea del agente
        
        Args:
            workflow: Estado del workflow (puede ser None)
            task: Definición de la tarea con tipo y parámetros
            
        Returns:
            Resultado de la ejecución
        """
        task_type = task.task_type if hasattr(task, 'task_type') else task.get('task_type')
        params = task.parameters if hasattr(task, 'parameters') else task.get('parameters', {})
        
        logger.info(f"Ejecutando tarea: {task_type}")
        
        # Obtener DB del workflow o crear nueva sesión
        db = None
        if workflow and hasattr(workflow, 'db'):
            db = workflow.db
        
        if task_type == "entity_timeline":
            return await self.build_entity_timeline(params.get('entity_id'), db)
        
        elif task_type == "entity_relationships":
            return await self.get_entity_relationships(params.get('entity_id'), db)
        
        elif task_type == "detect_patterns":
            pattern_ids = params.get('pattern_ids')
            return await self.detect_patterns(pattern_ids, db)
        
        elif task_type == "analyze_entity_history":
            return await self.analyze_entity_history(
                params.get('entity_name'),
                params.get('entity_type'),
                db
            )
        
        elif task_type == "detect_anomalies":
            return await self.detect_anomalies(
                params.get('days_back', 90),
                db
            )
        
        else:
            return {
                "success": False,
                "error": f"Tipo de tarea desconocido: {task_type}"
            }
    
    async def build_entity_timeline(
        self, 
        entity_id: int, 
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Construye timeline de apariciones de una entidad
        
        Args:
            entity_id: ID de la entidad
            db: Sesión de base de datos
            
        Returns:
            Timeline con eventos ordenados cronológicamente
        """
        if not db:
            from app.db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                return await self._build_timeline_internal(entity_id, db)
        else:
            return await self._build_timeline_internal(entity_id, db)
    
    async def _build_timeline_internal(
        self,
        entity_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Implementación interna del timeline"""
        
        # Obtener entidad
        entity_result = await db.execute(
            select(EntidadExtraida).where(EntidadExtraida.id == entity_id)
        )
        entity = entity_result.scalar_one_or_none()
        
        if not entity:
            return {"success": False, "error": "Entidad no encontrada"}
        
        # Obtener menciones con fechas
        menciones_query = await db.execute(
            select(MencionEntidad, Boletin)
            .join(Boletin, MencionEntidad.boletin_id == Boletin.id)
            .where(MencionEntidad.entidad_id == entity_id)
            .order_by(Boletin.date.asc())
        )
        
        menciones = menciones_query.all()
        
        # Construir eventos del timeline
        events = []
        for mencion, boletin in menciones:
            fecha = datetime.strptime(boletin.date, '%Y%m%d').date()
            events.append({
                "fecha": fecha.isoformat(),
                "tipo": "mencion",
                "boletin_id": boletin.id,
                "boletin": boletin.filename,
                "contexto": mencion.fragmento[:200],
                "seccion": boletin.section
            })
        
        # Obtener relaciones donde participa
        relaciones_query = await db.execute(
            select(RelacionEntidad, Boletin)
            .join(Boletin, RelacionEntidad.boletin_id == Boletin.id)
            .where(
                or_(
                    RelacionEntidad.entidad_origen_id == entity_id,
                    RelacionEntidad.entidad_destino_id == entity_id
                )
            )
            .order_by(RelacionEntidad.fecha_relacion.asc())
        )
        
        relaciones = relaciones_query.all()
        
        for relacion, boletin in relaciones:
            events.append({
                "fecha": relacion.fecha_relacion.isoformat(),
                "tipo": "relacion",
                "relacion_tipo": relacion.tipo_relacion,
                "boletin_id": boletin.id,
                "contexto": relacion.contexto[:200] if relacion.contexto else "",
                "es_origen": relacion.entidad_origen_id == entity_id
            })
        
        # Ordenar eventos cronológicamente
        events.sort(key=lambda x: x['fecha'])
        
        return {
            "success": True,
            "entity": {
                "id": entity.id,
                "tipo": entity.tipo,
                "nombre": entity.nombre_display,
                "primera_aparicion": entity.primera_aparicion.isoformat() if entity.primera_aparicion else None,
                "ultima_aparicion": entity.ultima_aparicion.isoformat() if entity.ultima_aparicion else None,
                "total_menciones": entity.total_menciones
            },
            "timeline": events,
            "total_events": len(events)
        }
    
    async def get_entity_relationships(
        self,
        entity_id: int,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Obtiene grafo de relaciones de una entidad
        
        Returns:
            Nodos y edges para visualización de red
        """
        if not db:
            from app.db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                return await self._get_relationships_internal(entity_id, db)
        else:
            return await self._get_relationships_internal(entity_id, db)
    
    async def _get_relationships_internal(
        self,
        entity_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Implementación interna de relaciones"""
        
        # Obtener entidad principal
        entity_result = await db.execute(
            select(EntidadExtraida).where(EntidadExtraida.id == entity_id)
        )
        entity = entity_result.scalar_one_or_none()
        
        if not entity:
            return {"success": False, "error": "Entidad no encontrada"}
        
        # Obtener relaciones
        query = await db.execute(
            select(
                RelacionEntidad,
                EntidadExtraida.alias('origen'),
                EntidadExtraida.alias('destino')
            )
            .join(EntidadExtraida.alias('origen'), RelacionEntidad.entidad_origen_id == EntidadExtraida.id)
            .join(EntidadExtraida.alias('destino'), RelacionEntidad.entidad_destino_id == EntidadExtraida.id)
            .where(
                or_(
                    RelacionEntidad.entidad_origen_id == entity_id,
                    RelacionEntidad.entidad_destino_id == entity_id
                )
            )
        )
        
        relaciones = query.all()
        
        # Construir grafo
        nodes = {entity_id: {
            "id": entity_id,
            "label": entity.nombre_display,
            "type": entity.tipo,
            "is_main": True
        }}
        
        edges = []
        
        for rel, origen, destino in relaciones:
            # Agregar nodos si no existen
            if origen.id not in nodes:
                nodes[origen.id] = {
                    "id": origen.id,
                    "label": origen.nombre_display,
                    "type": origen.tipo
                }
            
            if destino.id not in nodes:
                nodes[destino.id] = {
                    "id": destino.id,
                    "label": destino.nombre_display,
                    "type": destino.tipo
                }
            
            # Agregar edge
            edges.append({
                "from": origen.id,
                "to": destino.id,
                "type": rel.tipo_relacion,
                "fecha": rel.fecha_relacion.isoformat(),
                "confianza": rel.confianza
            })
        
        return {
            "success": True,
            "entity": {
                "id": entity.id,
                "nombre": entity.nombre_display,
                "tipo": entity.tipo
            },
            "graph": {
                "nodes": list(nodes.values()),
                "edges": edges
            },
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges)
            }
        }
    
    async def detect_patterns(
        self,
        pattern_ids: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Detecta patrones sospechosos en los datos
        
        Args:
            pattern_ids: IDs de patrones específicos (None = todos)
            db: Sesión de base de datos
            
        Returns:
            Patrones detectados con detalles
        """
        if not db:
            from app.db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                return await self._detect_patterns_internal(pattern_ids, db)
        else:
            return await self._detect_patterns_internal(pattern_ids, db)
    
    async def _detect_patterns_internal(
        self,
        pattern_ids: Optional[List[str]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Implementación interna de detección de patrones"""
        
        # Seleccionar patrones a ejecutar
        if pattern_ids:
            patterns = {pid: PATRONES_SOSPECHOSOS[pid] for pid in pattern_ids if pid in PATRONES_SOSPECHOSOS}
        else:
            patterns = PATRONES_SOSPECHOSOS
        
        results = []
        
        for pattern_id, pattern in patterns.items():
            try:
                # Formatear query con thresholds
                query_sql = pattern.query_template.format(**pattern.threshold)
                
                # Ejecutar query
                result = await db.execute(text(query_sql))
                rows = result.fetchall()
                
                if rows:
                    results.append({
                        "pattern_id": pattern_id,
                        "nombre": pattern.nombre,
                        "descripcion": pattern.descripcion,
                        "severidad": pattern.severidad,
                        "categoria": pattern.categoria,
                        "detecciones": len(rows),
                        "casos": [
                            {col: val for col, val in zip(result.keys(), row)}
                            for row in rows[:10]  # Limitar a 10 casos
                        ]
                    })
            
            except Exception as e:
                logger.error(f"Error ejecutando patrón {pattern_id}: {e}")
                results.append({
                    "pattern_id": pattern_id,
                    "nombre": pattern.nombre,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "patterns_analyzed": len(patterns),
            "patterns_detected": len([r for r in results if 'detecciones' in r and r['detecciones'] > 0]),
            "results": results
        }
    
    async def analyze_entity_history(
        self,
        entity_name: str,
        entity_type: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Analiza historial completo de una entidad por nombre
        
        Returns:
            Análisis comprehensivo con timeline, relaciones y patrones
        """
        if not db:
            from app.db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                return await self._analyze_history_internal(entity_name, entity_type, db)
        else:
            return await self._analyze_history_internal(entity_name, entity_type, db)
    
    async def _analyze_history_internal(
        self,
        entity_name: str,
        entity_type: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Implementación interna de análisis de historial"""
        
        # Buscar entidad
        from app.services.entity_service import get_entity_service
        service = get_entity_service()
        
        normalized = service.normalize_entity(entity_name, entity_type)
        
        entity_result = await db.execute(
            select(EntidadExtraida).where(
                EntidadExtraida.nombre_normalizado == normalized
            )
        )
        entity = entity_result.scalar_one_or_none()
        
        if not entity:
            return {
                "success": False,
                "error": f"Entidad '{entity_name}' no encontrada"
            }
        
        # Obtener timeline
        timeline_result = await self._build_timeline_internal(entity.id, db)
        
        # Obtener relaciones
        relationships_result = await self._get_relationships_internal(entity.id, db)
        
        return {
            "success": True,
            "entity": {
                "id": entity.id,
                "nombre": entity.nombre_display,
                "tipo": entity.tipo,
                "primera_aparicion": entity.primera_aparicion.isoformat() if entity.primera_aparicion else None,
                "ultima_aparicion": entity.ultima_aparicion.isoformat() if entity.ultima_aparicion else None,
                "total_menciones": entity.total_menciones
            },
            "timeline": timeline_result.get('timeline', []),
            "relationships": relationships_result.get('graph', {}),
            "stats": {
                "total_events": timeline_result.get('total_events', 0),
                "total_relationships": len(relationships_result.get('graph', {}).get('edges', []))
            }
        }
    
    async def detect_anomalies(
        self,
        days_back: int = 90,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Detecta anomalías en período reciente
        
        Args:
            days_back: Días hacia atrás para analizar
            db: Sesión de base de datos
            
        Returns:
            Anomalías detectadas con severidad
        """
        # Ejecutar patrones de severidad ALTA
        high_severity_patterns = [pid for pid, p in PATRONES_SOSPECHOSOS.items() if p.severidad == "ALTA"]
        
        return await self.detect_patterns(high_severity_patterns, db)
