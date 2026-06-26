// =============================================================================
// Watcher — Neo4j Schema Initialization
// =============================================================================
// Idempotent: all statements use IF NOT EXISTS.
// Execute once at startup via graph_driver.py:init_neo4j().
//
// Node labels:   Entidad, Boletin
// Relationship types:
//   MENCIONADO_EN, CONTRATA, DESIGNA, ADJUDICA, RECIBE_SUBSIDIO,
//   FIRMA, TRANSFIERE, AUTORIZA, APRUEBA, OTORGA, SANCIONA, APELA,
//   SE_RELACIONA_CON
// =============================================================================


// ---------------------------------------------------------------------------
// Constraints (enforce uniqueness + implicit index)
// ---------------------------------------------------------------------------

// Entidad: unique by normalized name (primary lookup key)
CREATE CONSTRAINT entidad_nombre_norm_unique IF NOT EXISTS
    FOR (e:Entidad) REQUIRE e.nombre_normalizado IS UNIQUE;

// Entidad: unique by PostgreSQL id (cross-DB join key)
CREATE CONSTRAINT entidad_pg_id_unique IF NOT EXISTS
    FOR (e:Entidad) REQUIRE e.pg_id IS UNIQUE;

// Boletin: unique by PostgreSQL id
CREATE CONSTRAINT boletin_pg_id_unique IF NOT EXISTS
    FOR (b:Boletin) REQUIRE b.pg_id IS UNIQUE;


// ---------------------------------------------------------------------------
// Indexes (performance for frequent filter/sort predicates)
// ---------------------------------------------------------------------------

// Filter by entity type (persona, organismo, empresa, contrato, monto)
CREATE INDEX entidad_tipo_idx IF NOT EXISTS
    FOR (e:Entidad) ON (e.tipo);

// Sort by mention count (graph overview, PageRank seed)
CREATE INDEX entidad_menciones_idx IF NOT EXISTS
    FOR (e:Entidad) ON (e.total_menciones);

// Date range queries on entities
CREATE INDEX entidad_primera_aparicion_idx IF NOT EXISTS
    FOR (e:Entidad) ON (e.primera_aparicion);

CREATE INDEX entidad_ultima_aparicion_idx IF NOT EXISTS
    FOR (e:Entidad) ON (e.ultima_aparicion);

// Boletin date for time-series queries
CREATE INDEX boletin_date_idx IF NOT EXISTS
    FOR (b:Boletin) ON (b.date);


// ---------------------------------------------------------------------------
// Full-text indexes (Neo4j 5+ native fulltext search)
// ---------------------------------------------------------------------------

// Search entities by display name or normalized name
CREATE FULLTEXT INDEX entidad_nombre_fulltext IF NOT EXISTS
    FOR (e:Entidad) ON EACH [e.nombre_display, e.nombre_normalizado];
