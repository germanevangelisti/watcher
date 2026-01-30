"""
Script de migración para actualizar la base de datos con nuevas columnas y tablas
"""

import asyncio
import sqlite3
from pathlib import Path

async def migrate_database():
    """Migra la base de datos agregando nuevas columnas y tablas."""
    
    print("🔄 MIGRACIÓN DE BASE DE DATOS")
    print("=" * 40)
    
    db_path = Path("sqlite.db")
    
    if not db_path.exists():
        print("❌ Base de datos no encontrada")
        return
    
    print(f"📁 Base de datos: {db_path}")
    
    # Conectar a SQLite
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("\n📊 Verificando estructura actual...")
        
        # Verificar columnas existentes en tabla analisis
        cursor.execute("PRAGMA table_info(analisis)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"   Columnas en 'analisis': {columns}")
        
        # Agregar columna monto_numerico si no existe
        if 'monto_numerico' not in columns:
            print("   ➕ Agregando columna 'monto_numerico'...")
            cursor.execute("ALTER TABLE analisis ADD COLUMN monto_numerico REAL")
            print("   ✅ Columna 'monto_numerico' agregada")
        else:
            print("   ✅ Columna 'monto_numerico' ya existe")
        
        print("\n🏗️ Creando nuevas tablas...")
        
        # Crear tabla presupuesto_base
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS presupuesto_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ejercicio INTEGER NOT NULL,
                organismo TEXT NOT NULL,
                programa TEXT NOT NULL,
                subprograma TEXT,
                partida_presupuestaria TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                monto_inicial REAL NOT NULL,
                monto_vigente REAL NOT NULL,
                fecha_aprobacion DATE NOT NULL,
                meta_fisica TEXT,
                meta_numerica REAL,
                unidad_medida TEXT,
                cronograma_json TEXT,
                fuente_financiamiento TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ Tabla 'presupuesto_base' creada/verificada")
        
        # Crear índices para presupuesto_base
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_presupuesto_ejercicio_organismo 
            ON presupuesto_base(ejercicio, organismo)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_presupuesto_partida 
            ON presupuesto_base(partida_presupuestaria)
        """)
        
        # Crear tabla ejecucion_presupuestaria
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ejecucion_presupuestaria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boletin_id INTEGER REFERENCES boletines(id),
                presupuesto_base_id INTEGER REFERENCES presupuesto_base(id),
                fecha_boletin DATE NOT NULL,
                organismo TEXT NOT NULL,
                beneficiario TEXT NOT NULL,
                concepto TEXT NOT NULL,
                monto REAL NOT NULL,
                tipo_operacion TEXT NOT NULL,
                partida_presupuestaria TEXT,
                programa TEXT,
                subprograma TEXT,
                categoria_watcher TEXT,
                riesgo_watcher TEXT,
                monto_acumulado_mes REAL,
                monto_acumulado_trimestre REAL,
                monto_acumulado_anual REAL,
                es_modificacion_presupuestaria BOOLEAN DEFAULT 0,
                requiere_revision BOOLEAN DEFAULT 0,
                observaciones TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ Tabla 'ejecucion_presupuestaria' creada/verificada")
        
        # Crear índices para ejecucion_presupuestaria
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ejecucion_fecha_organismo 
            ON ejecucion_presupuestaria(fecha_boletin, organismo)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ejecucion_monto 
            ON ejecucion_presupuestaria(monto)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ejecucion_tipo 
            ON ejecucion_presupuestaria(tipo_operacion)
        """)
        
        # Crear tabla metricas_gestion
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metricas_gestion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ejercicio INTEGER NOT NULL,
                periodo TEXT NOT NULL,
                fecha_inicio DATE NOT NULL,
                fecha_fin DATE NOT NULL,
                organismo TEXT NOT NULL,
                programa TEXT,
                presupuesto_inicial REAL NOT NULL,
                presupuesto_vigente REAL NOT NULL,
                ejecutado_acumulado REAL NOT NULL,
                porcentaje_ejecucion REAL NOT NULL,
                desvio_presupuestario REAL NOT NULL,
                meta_fisica_planificada REAL,
                meta_fisica_ejecutada REAL,
                porcentaje_avance_fisico REAL,
                total_operaciones INTEGER NOT NULL,
                operaciones_alto_riesgo INTEGER NOT NULL,
                operaciones_medio_riesgo INTEGER NOT NULL,
                monto_alto_riesgo REAL NOT NULL,
                porcentaje_riesgo REAL NOT NULL,
                beneficiarios_unicos INTEGER NOT NULL,
                concentracion_beneficiarios REAL NOT NULL,
                tiene_alertas BOOLEAN DEFAULT 0,
                alertas_json TEXT,
                variacion_mes_anterior REAL,
                variacion_mismo_periodo_anio_anterior REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ Tabla 'metricas_gestion' creada/verificada")
        
        # Crear índices para metricas_gestion
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metricas_ejercicio_periodo 
            ON metricas_gestion(ejercicio, periodo)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metricas_organismo_fecha 
            ON metricas_gestion(organismo, fecha_fin)
        """)
        
        # Crear tabla alertas_gestion
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alertas_gestion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_alerta TEXT NOT NULL,
                nivel_severidad TEXT NOT NULL,
                organismo TEXT NOT NULL,
                programa TEXT,
                fecha_deteccion DATETIME DEFAULT CURRENT_TIMESTAMP,
                titulo TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                valor_detectado REAL,
                valor_esperado REAL,
                porcentaje_desvio REAL,
                boletin_id INTEGER REFERENCES boletines(id),
                ejecucion_id INTEGER REFERENCES ejecucion_presupuestaria(id),
                estado TEXT DEFAULT 'activa',
                fecha_revision DATETIME,
                observaciones_revision TEXT,
                acciones_sugeridas TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ Tabla 'alertas_gestion' creada/verificada")
        
        # Crear índices para alertas_gestion
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alertas_tipo_nivel 
            ON alertas_gestion(tipo_alerta, nivel_severidad)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alertas_estado_fecha 
            ON alertas_gestion(estado, fecha_deteccion)
        """)
        
        # Crear tabla procesamiento_batch
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procesamiento_batch (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT UNIQUE NOT NULL,
                fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
                fecha_fin DATETIME,
                directorio_origen TEXT NOT NULL,
                filtros_aplicados TEXT,
                total_archivos INTEGER NOT NULL,
                archivos_procesados INTEGER DEFAULT 0,
                archivos_fallidos INTEGER DEFAULT 0,
                total_ejecuciones_detectadas INTEGER DEFAULT 0,
                monto_total_procesado REAL DEFAULT 0.0,
                alertas_generadas INTEGER DEFAULT 0,
                estado TEXT DEFAULT 'iniciado',
                error_message TEXT,
                tiempo_procesamiento_segundos REAL,
                archivos_por_segundo REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ Tabla 'procesamiento_batch' creada/verificada")
        
        # Confirmar cambios
        conn.commit()
        
        print("\n📊 Verificando estructura final...")
        
        # Listar todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   Tablas disponibles: {tables}")
        
        # Verificar columnas de analisis
        cursor.execute("PRAGMA table_info(analisis)")
        analisis_columns = [row[1] for row in cursor.fetchall()]
        print(f"   Columnas en 'analisis': {analisis_columns}")
        
        print("\n✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 40)
        print("🎯 La base de datos está lista para el sistema batch optimizado")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_database())
