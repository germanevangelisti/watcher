-- Migration: Knowledge Graph - Entidades y Relaciones
-- Date: 2026-02-05
-- Description: Agrega tablas para el grafo de conocimiento de entidades extraídas y sus relaciones

-- =============================================================================
-- TABLA: entidades_extraidas
-- =============================================================================

CREATE TABLE IF NOT EXISTS entidades_extraidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo VARCHAR(50) NOT NULL,
    nombre_normalizado VARCHAR(255) NOT NULL UNIQUE,
    nombre_display VARCHAR(255) NOT NULL,
    variantes TEXT,  -- JSON array
    primera_aparicion DATE,
    ultima_aparicion DATE,
    total_menciones INTEGER DEFAULT 0,
    metadata_extra TEXT,  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entidad_tipo ON entidades_extraidas(tipo);
CREATE INDEX IF NOT EXISTS idx_entidad_nombre_normalizado ON entidades_extraidas(nombre_normalizado);
CREATE INDEX IF NOT EXISTS idx_entidad_tipo_nombre ON entidades_extraidas(tipo, nombre_normalizado);

-- =============================================================================
-- TABLA: menciones_entidades
-- =============================================================================

CREATE TABLE IF NOT EXISTS menciones_entidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entidad_id INTEGER NOT NULL,
    boletin_id INTEGER NOT NULL,
    fragmento TEXT NOT NULL,
    pagina INTEGER,
    confianza REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (entidad_id) REFERENCES entidades_extraidas(id) ON DELETE CASCADE,
    FOREIGN KEY (boletin_id) REFERENCES boletines(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mencion_entidad ON menciones_entidades(entidad_id);
CREATE INDEX IF NOT EXISTS idx_mencion_boletin ON menciones_entidades(boletin_id);
CREATE INDEX IF NOT EXISTS idx_mencion_entidad_boletin ON menciones_entidades(entidad_id, boletin_id);
CREATE INDEX IF NOT EXISTS idx_mencion_created ON menciones_entidades(created_at);

-- =============================================================================
-- TABLA: relaciones_entidades
-- =============================================================================

CREATE TABLE IF NOT EXISTS relaciones_entidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entidad_origen_id INTEGER NOT NULL,
    entidad_destino_id INTEGER NOT NULL,
    tipo_relacion VARCHAR(100) NOT NULL,
    boletin_id INTEGER NOT NULL,
    fecha_relacion DATE NOT NULL,
    contexto TEXT,
    confianza REAL DEFAULT 1.0,
    metadata_extra TEXT,  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (entidad_origen_id) REFERENCES entidades_extraidas(id) ON DELETE CASCADE,
    FOREIGN KEY (entidad_destino_id) REFERENCES entidades_extraidas(id) ON DELETE CASCADE,
    FOREIGN KEY (boletin_id) REFERENCES boletines(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_relacion_origen ON relaciones_entidades(entidad_origen_id);
CREATE INDEX IF NOT EXISTS idx_relacion_destino ON relaciones_entidades(entidad_destino_id);
CREATE INDEX IF NOT EXISTS idx_relacion_origen_destino ON relaciones_entidades(entidad_origen_id, entidad_destino_id);
CREATE INDEX IF NOT EXISTS idx_relacion_tipo ON relaciones_entidades(tipo_relacion);
CREATE INDEX IF NOT EXISTS idx_relacion_fecha ON relaciones_entidades(fecha_relacion);
CREATE INDEX IF NOT EXISTS idx_relacion_tipo_fecha ON relaciones_entidades(tipo_relacion, fecha_relacion);
CREATE INDEX IF NOT EXISTS idx_relacion_boletin ON relaciones_entidades(boletin_id);

-- =============================================================================
-- COMENTARIOS EXPLICATIVOS
-- =============================================================================

-- Tipos de entidades soportados:
--   - persona: Personas físicas (funcionarios, beneficiarios, firmantes)
--   - organismo: Ministerios, secretarías, direcciones
--   - empresa: Empresas privadas, constructoras, proveedores
--   - contrato: Licitaciones, contratos, expedientes
--   - monto: Montos específicos mencionados

-- Tipos de relaciones soportados:
--   - contrata: Organismo contrata Empresa
--   - designa: Organismo designa Persona
--   - recibe_subsidio: Persona/Empresa recibe subsidio de Organismo
--   - firma: Persona firma Contrato
--   - adjudica: Organismo adjudica Contrato a Empresa
--   - transfiere: Organismo transfiere fondos a otro Organismo

-- Uso de confianza (0.0 - 1.0):
--   - 1.0: Extracción con patrón exacto (ej: "MINISTERIO DE X")
--   - 0.8: Extracción con variante conocida
--   - 0.6: Extracción con inferencia contextual
--   - 0.4: Extracción ambigua que requiere validación
