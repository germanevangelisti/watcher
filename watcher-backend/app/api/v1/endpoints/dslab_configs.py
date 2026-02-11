"""
🧪 DS Lab - Endpoints para configuraciones y versiones de modelos
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional

from app.db.sync_session import get_sync_db
from app.db.models import AnalysisConfig, AnalysisExecution
from app.schemas.dslab import (
    AnalysisConfigCreate,
    AnalysisConfigUpdate,
    AnalysisConfigResponse
)

router = APIRouter()


@router.post("/configs", response_model=AnalysisConfigResponse, status_code=201)
async def create_config(
    config: AnalysisConfigCreate,
    db: Session = Depends(get_sync_db)
):
    """
    Crear una nueva configuración de análisis
    """
    # Verificar si ya existe esta versión
    existing = db.query(AnalysisConfig).filter(
        AnalysisConfig.config_name == config.config_name,
        AnalysisConfig.version == config.version
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Configuración {config.config_name} v{config.version} ya existe"
        )
    
    # Crear configuración
    db_config = AnalysisConfig(**config.dict())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return db_config


@router.get("/configs", response_model=List[AnalysisConfigResponse])
async def list_configs(
    active_only: bool = False,
    config_name: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_sync_db)
):
    """
    Listar configuraciones
    """
    query = db.query(AnalysisConfig)
    
    if active_only:
        query = query.filter(AnalysisConfig.is_active == True)
    
    if config_name:
        query = query.filter(AnalysisConfig.config_name == config_name)
    
    configs = query.order_by(
        desc(AnalysisConfig.created_at)
    ).offset(skip).limit(limit).all()
    
    return configs


@router.get("/configs/{config_id}", response_model=AnalysisConfigResponse)
async def get_config(
    config_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Obtener una configuración por ID
    """
    config = db.query(AnalysisConfig).filter(
        AnalysisConfig.id == config_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    
    return config


@router.put("/configs/{config_id}", response_model=AnalysisConfigResponse)
async def update_config(
    config_id: int,
    update_data: AnalysisConfigUpdate,
    db: Session = Depends(get_sync_db)
):
    """
    Actualizar una configuración
    """
    config = db.query(AnalysisConfig).filter(
        AnalysisConfig.id == config_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    
    # Actualizar campos
    update_dict = update_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(config, key, value)
    
    db.commit()
    db.refresh(config)
    
    return config


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: int,
    force: bool = False,
    db: Session = Depends(get_sync_db)
):
    """
    Eliminar una configuración
    """
    config = db.query(AnalysisConfig).filter(
        AnalysisConfig.id == config_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    
    # Verificar si tiene ejecuciones asociadas
    executions_count = db.query(AnalysisExecution).filter(
        AnalysisExecution.config_id == config_id
    ).count()
    
    if executions_count > 0 and not force:
        raise HTTPException(
            status_code=409,
            detail=f"Configuración tiene {executions_count} ejecuciones asociadas. Use force=true para eliminar de todos modos."
        )
    
    db.delete(config)
    db.commit()
    
    return {
        "message": "Configuración eliminada",
        "config_id": config_id,
        "executions_affected": executions_count
    }


@router.post("/configs/{config_id}/activate", response_model=AnalysisConfigResponse)
async def activate_config(
    config_id: int,
    deactivate_others: bool = True,
    db: Session = Depends(get_sync_db)
):
    """
    Activar una configuración (y opcionalmente desactivar las demás del mismo nombre)
    """
    config = db.query(AnalysisConfig).filter(
        AnalysisConfig.id == config_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    
    # Si se especifica, desactivar otras configs con el mismo nombre
    if deactivate_others:
        db.query(AnalysisConfig).filter(
            AnalysisConfig.config_name == config.config_name,
            AnalysisConfig.id != config_id
        ).update({"is_active": False})
    
    # Activar esta config
    config.is_active = True
    db.commit()
    db.refresh(config)
    
    return config


@router.get("/configs/{config_id}/executions")
async def get_config_executions(
    config_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Obtener todas las ejecuciones que usaron esta configuración
    """
    config = db.query(AnalysisConfig).filter(
        AnalysisConfig.id == config_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    
    executions = db.query(AnalysisExecution).filter(
        AnalysisExecution.config_id == config_id
    ).order_by(desc(AnalysisExecution.started_at)).all()
    
    return {
        "config": config,
        "total_executions": len(executions),
        "executions": [
            {
                "id": e.id,
                "execution_name": e.execution_name,
                "status": e.status,
                "total_documents": e.total_documents,
                "processed_documents": e.processed_documents,
                "failed_documents": e.failed_documents,
                "started_at": e.started_at,
                "completed_at": e.completed_at
            }
            for e in executions
        ]
    }


@router.get("/configs/names/list")
async def list_config_names(
    db: Session = Depends(get_sync_db)
):
    """
    Listar todos los nombres únicos de configuraciones
    """
    config_names = db.query(AnalysisConfig.config_name).distinct().all()
    
    result = []
    for (name,) in config_names:
        versions = db.query(AnalysisConfig).filter(
            AnalysisConfig.config_name == name
        ).order_by(desc(AnalysisConfig.created_at)).all()
        
        active_version = next((v for v in versions if v.is_active), None)
        
        result.append({
            "config_name": name,
            "total_versions": len(versions),
            "active_version": active_version.version if active_version else None,
            "latest_version": versions[0].version if versions else None,
            "created_at": versions[0].created_at if versions else None
        })
    
    return result


@router.post("/configs/{config_id}/clone", response_model=AnalysisConfigResponse)
async def clone_config(
    config_id: int,
    new_version: str,
    description: Optional[str] = None,
    db: Session = Depends(get_sync_db)
):
    """
    Clonar una configuración existente con una nueva versión
    """
    config = db.query(AnalysisConfig).filter(
        AnalysisConfig.id == config_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    
    # Verificar que la nueva versión no exista
    existing = db.query(AnalysisConfig).filter(
        AnalysisConfig.config_name == config.config_name,
        AnalysisConfig.version == new_version
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Versión {new_version} ya existe para {config.config_name}"
        )
    
    # Crear nueva configuración clonando la existente
    new_config = AnalysisConfig(
        config_name=config.config_name,
        version=new_version,
        description=description or f"Clonado de v{config.version}",
        parameters=config.parameters,
        model_version=config.model_version,
        model_weights_path=config.model_weights_path,
        created_by=config.created_by,
        is_active=False  # Nueva versión comienza desactivada
    )
    
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return new_config

