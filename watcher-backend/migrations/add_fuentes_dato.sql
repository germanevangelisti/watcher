-- Migration: add_fuentes_dato
-- Tabla de fuentes de datos por jurisdicción (boletines, presupuesto, ejecución).
-- Separada de JurisdiccionSyncConfig (que es config operativa del sync de boletines).

CREATE TABLE IF NOT EXISTS fuentes_dato (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jurisdiccion_id INTEGER NOT NULL REFERENCES jurisdicciones(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,          -- "boletin_diario" | "presupuesto_anual" | "ejecucion_trimestral"
    nombre TEXT NOT NULL,        -- Display name legible
    url_template TEXT,           -- URL directa o template con {year}, {month}, {day}, {section}
    activa INTEGER DEFAULT 1,
    descripcion TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(jurisdiccion_id, tipo)
);

CREATE INDEX IF NOT EXISTS idx_fuentes_dato_jurisdiccion ON fuentes_dato(jurisdiccion_id);
CREATE INDEX IF NOT EXISTS idx_fuentes_dato_tipo ON fuentes_dato(tipo);

-- Seed: Boletín Oficial de la Provincia de Córdoba (slug estable, verificado >1 año)
INSERT OR IGNORE INTO fuentes_dato (jurisdiccion_id, tipo, nombre, url_template, activa, descripcion)
VALUES (
    1,
    'boletin_diario',
    'Boletín Oficial de la Provincia de Córdoba',
    'https://boletinoficial.cba.gov.ar/wp-content/4p96humuzp/{year}/{month}/{section}_Secc_{day}{month}{year_short}.pdf',
    1,
    'Publicación diaria (días hábiles). 5 secciones: Designaciones, Compras, Subsidios, Obras, Notificaciones.'
);
