-- Migración: Sistema de Jurisdicciones
-- Fecha: 2026-02-03
-- Descripción: Agregar soporte para jerarquía jurisdiccional (Provincia > Municipalidades)

-- ============================================
-- 1. CREAR TABLA JURISDICCIONES
-- ============================================

CREATE TABLE IF NOT EXISTS jurisdicciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Información básica
    nombre VARCHAR(200) NOT NULL UNIQUE,
    tipo VARCHAR(50) NOT NULL,  -- provincia, capital, municipalidad, comuna
    
    -- Ubicación geográfica
    latitud REAL,
    longitud REAL,
    codigo_postal VARCHAR(10),
    departamento VARCHAR(100),
    
    -- Datos demográficos
    poblacion INTEGER,
    superficie_km2 REAL,
    
    -- Metadata
    extra_data TEXT,  -- JSON
    
    -- Timestamps
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jurisdiccion_nombre ON jurisdicciones(nombre);
CREATE INDEX idx_jurisdiccion_tipo ON jurisdicciones(tipo);


-- ============================================
-- 2. CREAR TABLA MENCIONES JURISDICCIONALES
-- ============================================

CREATE TABLE IF NOT EXISTS menciones_jurisdiccionales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Referencias
    boletin_id INTEGER NOT NULL REFERENCES boletines(id) ON DELETE CASCADE,
    jurisdiccion_id INTEGER NOT NULL REFERENCES jurisdicciones(id) ON DELETE CASCADE,
    
    -- Detalles de la mención
    tipo_mencion VARCHAR(50),  -- decreto, resolucion, licitacion, ordenanza
    seccion INTEGER,  -- Sección del boletín
    confianza REAL DEFAULT 1.0,  -- 0.0 a 1.0
    extracto TEXT,  -- Fragmento de texto
    
    -- Metadata
    extra_data TEXT,  -- JSON
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mencion_boletin ON menciones_jurisdiccionales(boletin_id);
CREATE INDEX idx_mencion_jurisdiccion ON menciones_jurisdiccionales(jurisdiccion_id);
CREATE INDEX idx_mencion_tipo ON menciones_jurisdiccionales(tipo_mencion);
CREATE INDEX idx_mencion_boletin_jurisdiccion ON menciones_jurisdiccionales(boletin_id, jurisdiccion_id);


-- ============================================
-- 3. ALTERAR TABLA BOLETINES
-- ============================================

-- Agregar columna fuente (tipo de boletín)
ALTER TABLE boletines ADD COLUMN fuente VARCHAR(50) DEFAULT 'provincial';

-- Agregar columna jurisdiccion_id (referencia)
ALTER TABLE boletines ADD COLUMN jurisdiccion_id INTEGER REFERENCES jurisdicciones(id);

-- Agregar columna seccion_nombre (nombre legible de sección)
ALTER TABLE boletines ADD COLUMN seccion_nombre VARCHAR(100);

CREATE INDEX idx_boletin_fuente ON boletines(fuente);
CREATE INDEX idx_boletin_jurisdiccion ON boletines(jurisdiccion_id);


-- ============================================
-- 4. SEED INICIAL - JURISDICCIONES PRINCIPALES
-- ============================================

-- Provincia de Córdoba
INSERT INTO jurisdicciones (nombre, tipo, latitud, longitud, departamento, poblacion) 
VALUES ('Provincia de Córdoba', 'provincia', -31.4201, -64.1888, NULL, 3978984);

-- Ciudad de Córdoba (Capital)
INSERT INTO jurisdicciones (nombre, tipo, latitud, longitud, codigo_postal, departamento, poblacion, extra_data)
VALUES (
    'Ciudad de Córdoba',
    'capital',
    -31.4201,
    -64.1888,
    '5000',
    'Capital',
    1329604,
    '{"url_boletin": "https://static01.cordoba.gob.ar/boe/boletines/", "intendente": null}'
);

-- Municipalidades principales (Top 20 por población)

INSERT INTO jurisdicciones (nombre, tipo, latitud, longitud, codigo_postal, departamento, poblacion) VALUES
('Villa María', 'municipalidad', -32.4072, -63.2401, '5900', 'General San Martín', 79971),
('Río Cuarto', 'municipalidad', -33.1237, -64.3499, '5800', 'Río Cuarto', 157010),
('San Francisco', 'municipalidad', -31.4277, -62.0832, '2400', 'San Justo', 61750),
('Villa Carlos Paz', 'municipalidad', -31.4241, -64.4978, '5152', 'Punilla', 69451),
('Alta Gracia', 'municipalidad', -31.6536, -64.4297, '5186', 'Santa María', 43200),
('Río Tercero', 'municipalidad', -32.1733, -64.1119, '5850', 'Tercero Arriba', 46200),
('Bell Ville', 'municipalidad', -32.6264, -62.6886, '2550', 'Unión', 34439),
('Villa Dolores', 'municipalidad', -31.9453, -65.1897, '5870', 'San Javier', 32290),
('Jesús María', 'municipalidad', -30.9804, -64.0930, '5220', 'Colón', 31719),
('Río Segundo', 'municipalidad', -31.6520, -63.9115, '5960', 'Río Segundo', 19148),
('Villa Allende', 'municipalidad', -31.2951, -64.2951, '5105', 'Colón', 28597),
('Cosquín', 'municipalidad', -31.2450, -64.4662, '5143', 'Punilla', 19840),
('Laboulaye', 'municipalidad', -34.1265, -63.3889, '6120', 'Presidente Roque Sáenz Peña', 20534),
('Deán Funes', 'municipalidad', -30.4198, -64.3499, '5200', 'Ischilín', 21133),
('La Falda', 'municipalidad', -31.0875, -64.4874, '5172', 'Punilla', 15827),
('Cruz del Eje', 'municipalidad', -30.7258, -64.8100, '5280', 'Cruz del Eje', 30534),
('Marcos Juárez', 'municipalidad', -32.6977, -62.1061, '2580', 'Marcos Juárez', 26967),
('Villa del Rosario', 'municipalidad', -31.5567, -63.5364, '5963', 'Río Segundo', 14750),
('Arroyito', 'municipalidad', -31.4219, -63.0513, '2434', 'San Justo', 19266),
('Río Ceballos', 'municipalidad', -31.1654, -64.3226, '5111', 'Colón', 20421);

-- Comunas representativas

INSERT INTO jurisdicciones (nombre, tipo, latitud, longitud, codigo_postal, departamento, poblacion) VALUES
('Los Reartes', 'comuna', -31.9167, -64.5833, '5189', 'Calamuchita', 1523),
('Villa Cura Brochero', 'comuna', -31.7333, -65.0333, '5891', 'San Alberto', 5500),
('Capilla del Monte', 'comuna', -30.8575, -64.5250, '5184', 'Punilla', 10328),
('La Cumbrecita', 'comuna', -31.8667, -64.7833, '5194', 'Calamuchita', 500);


-- ============================================
-- 5. ACTUALIZAR BOLETINES EXISTENTES
-- ============================================

-- Asignar fuente 'provincial' a todos los boletines existentes
UPDATE boletines SET fuente = 'provincial' WHERE fuente IS NULL;

-- Asignar jurisdiccion_id = Provincia de Córdoba a todos los boletines provinciales
UPDATE boletines 
SET jurisdiccion_id = (SELECT id FROM jurisdicciones WHERE nombre = 'Provincia de Córdoba' LIMIT 1)
WHERE fuente = 'provincial';

-- Asignar nombres legibles a las secciones
UPDATE boletines SET seccion_nombre = 'Legislación y Normativas' WHERE section = '1';
UPDATE boletines SET seccion_nombre = 'Judiciales' WHERE section = '2';
UPDATE boletines SET seccion_nombre = 'Sociedades y Asambleas' WHERE section = '3';
UPDATE boletines SET seccion_nombre = 'Licitaciones y Contrataciones' WHERE section = '4';
UPDATE boletines SET seccion_nombre = 'Normativas Municipales' WHERE section = '5';


-- ============================================
-- VERIFICACIÓN
-- ============================================

-- Contar jurisdicciones por tipo
SELECT tipo, COUNT(*) as cantidad
FROM jurisdicciones
GROUP BY tipo;

-- Verificar boletines actualizados
SELECT fuente, COUNT(*) as cantidad
FROM boletines
GROUP BY fuente;

-- Fin de migración
