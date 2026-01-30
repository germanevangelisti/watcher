
-- Migración para agregar red flags a Watcher Monolith
-- Ejecutar en: /watcher-monolith/backend/sqlite.db

-- Tabla para almacenar red flags
CREATE TABLE IF NOT EXISTS red_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flag_id VARCHAR(255) UNIQUE NOT NULL,
    document_id VARCHAR(255) NOT NULL,
    flag_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICO', 'ALTO', 'MEDIO', 'INFORMATIVO')),
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    description TEXT NOT NULL,
    evidence TEXT, -- JSON array
    recommendation TEXT,
    transparency_score REAL,
    risk_factors TEXT, -- JSON object
    metadata TEXT, -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimización
CREATE INDEX IF NOT EXISTS idx_red_flags_document_id ON red_flags(document_id);
CREATE INDEX IF NOT EXISTS idx_red_flags_severity ON red_flags(severity);
CREATE INDEX IF NOT EXISTS idx_red_flags_flag_type ON red_flags(flag_type);
CREATE INDEX IF NOT EXISTS idx_red_flags_created_at ON red_flags(created_at);

-- Tabla para coordenadas visuales en PDFs
CREATE TABLE IF NOT EXISTS pdf_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    red_flag_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    coordinates TEXT NOT NULL, -- JSON con x, y, width, height
    highlighted_text TEXT,
    context_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (red_flag_id) REFERENCES red_flags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pdf_evidence_red_flag_id ON pdf_evidence(red_flag_id);
CREATE INDEX IF NOT EXISTS idx_pdf_evidence_page ON pdf_evidence(page_number);

-- Vista para consultas optimizadas
CREATE VIEW IF NOT EXISTS red_flags_summary AS
SELECT 
    document_id,
    COUNT(*) as total_flags,
    SUM(CASE WHEN severity = 'CRITICO' THEN 1 ELSE 0 END) as critical_flags,
    SUM(CASE WHEN severity = 'ALTO' THEN 1 ELSE 0 END) as high_flags,
    SUM(CASE WHEN severity = 'MEDIO' THEN 1 ELSE 0 END) as medium_flags,
    SUM(CASE WHEN severity = 'INFORMATIVO' THEN 1 ELSE 0 END) as info_flags,
    AVG(confidence) as avg_confidence,
    MIN(transparency_score) as min_transparency,
    MAX(created_at) as last_analysis
FROM red_flags 
GROUP BY document_id;

-- Trigger para actualizar updated_at
CREATE TRIGGER IF NOT EXISTS update_red_flags_timestamp 
    AFTER UPDATE ON red_flags
BEGIN
    UPDATE red_flags SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
