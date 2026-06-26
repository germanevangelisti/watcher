-- Migration: add_sumarios_parseados
-- Agrega tabla para almacenar los sumarios parseados de boletines provinciales de Córdoba.
-- Scope: solo boletines con fuente=PROVINCIAL y jurisdiccion_id=1.

CREATE TABLE IF NOT EXISTS sumarios_parseados (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    boletin_id     INTEGER NOT NULL REFERENCES boletines(id) ON DELETE CASCADE,
    format_type    TEXT NOT NULL,   -- organismo_jerarquia | categorias_simples | categorias_judiciales | unknown
    confidence     REAL NOT NULL DEFAULT 0.0,
    pagina_sumario INTEGER,         -- Página estimada donde se encontró el bloque SUMARIO (1-indexed)
    entries_json   TEXT NOT NULL,   -- JSON array de SumarioEntry (serializado con dataclasses.asdict)
    raw_text       TEXT,            -- Texto crudo del bloque SUMARIO (para debugging y re-parse)
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(boletin_id)
);

CREATE INDEX IF NOT EXISTS idx_sumario_boletin  ON sumarios_parseados(boletin_id);
CREATE INDEX IF NOT EXISTS idx_sumario_format   ON sumarios_parseados(format_type);
CREATE INDEX IF NOT EXISTS idx_sumario_conf     ON sumarios_parseados(confidence);
