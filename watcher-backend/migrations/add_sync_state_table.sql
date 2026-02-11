-- Migración: Agregar tabla sync_state para sincronización automática
-- Fecha: 2026-02-03
-- Descripción: Tabla para gestionar el estado de sincronización automática de boletines

CREATE TABLE IF NOT EXISTS sync_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Estado de sincronización
    last_synced_date DATE,
    last_sync_timestamp DATETIME,
    next_scheduled_sync DATETIME,
    
    -- Estado actual
    status VARCHAR(20) DEFAULT 'idle',
    
    -- Estadísticas
    boletines_pending INTEGER DEFAULT 0,
    boletines_downloaded INTEGER DEFAULT 0,
    boletines_processed INTEGER DEFAULT 0,
    boletines_failed INTEGER DEFAULT 0,
    
    -- Configuración de scheduler
    auto_sync_enabled BOOLEAN DEFAULT 0,
    sync_frequency VARCHAR(20) DEFAULT 'daily',
    sync_hour INTEGER DEFAULT 6,
    
    -- Errores y logs
    error_message TEXT,
    current_operation VARCHAR(100),
    
    -- Timestamps
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insertar registro inicial
INSERT INTO sync_state (
    status,
    boletines_pending,
    boletines_downloaded,
    boletines_processed,
    boletines_failed,
    auto_sync_enabled,
    sync_frequency,
    sync_hour
) VALUES (
    'idle',
    0,
    0,
    0,
    0,
    0,
    'daily',
    6
);
