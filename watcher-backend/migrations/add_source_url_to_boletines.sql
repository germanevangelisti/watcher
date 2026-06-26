-- Migration: add_source_url_to_boletines
-- Agrega URL de origen al boletín y pobla JurisdiccionSyncConfig para Córdoba Provincial.

ALTER TABLE boletines ADD COLUMN source_url TEXT;

CREATE INDEX IF NOT EXISTS idx_boletines_source_url ON boletines(source_url);

-- Seed: URL template para Boletín Oficial de la Provincia de Córdoba
-- URL real: https://boletinoficial.cba.gov.ar/wp-content/4p96humuzp/2026/03/4_Secc_060326.pdf
-- Template vars: {year}, {month}, {day}, {section}
-- Nota: date en URL es DDMMYY (distinto al filename YYYYMMDD)
INSERT OR IGNORE INTO jurisdiccion_sync_configs (
    jurisdiccion_id,
    source_url_template,
    scraper_type,
    sync_enabled,
    sync_frequency,
    sections_to_sync,
    extra_config,
    created_at,
    updated_at
) VALUES (
    1,
    'https://boletinoficial.cba.gov.ar/wp-content/4p96humuzp/{year}/{month}/{section}_Secc_{day}{month}{year_short}.pdf',
    'provincial',
    1,
    'daily',
    '["1", "2", "3", "4", "5"]',
    '{"slug": "4p96humuzp", "date_format": "DDMMYY", "sections": 5}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);
