#!/bin/bash
# 🚀 Script rápido para reorganizar boletines

echo "🗂️  REORGANIZACIÓN RÁPIDA DE BOLETINES"
echo "====================================="

BOLETINES_DIR="/Users/germanevangelisti/watcher-agent/boletines"

cd "$BOLETINES_DIR" || exit 1

# Contar archivos sueltos
LOOSE_FILES=$(find . -maxdepth 1 -name "*.pdf" | wc -l)
echo "📊 Archivos sueltos encontrados: $LOOSE_FILES"

if [ "$LOOSE_FILES" -eq 0 ]; then
    echo "✅ No hay archivos para reorganizar"
    exit 0
fi

# Crear estructura (ya con formato 01, 02, etc.)
echo ""
echo "📁 Creando estructura de directorios..."
for year in 2024 2025 2026; do
    for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
        mkdir -p "$year/$month"
    done
done
echo "✅ Estructura creada con formato 01, 02, 03, etc."

# Mover archivos
echo ""
echo "🚚 Moviendo archivos a estructura organizada..."

for pdf in *.pdf; do
    if [ -f "$pdf" ]; then
        # Extraer año y mes del nombre (YYYYMMDD_N_Secc.pdf)
        YEAR=$(echo "$pdf" | cut -c1-4)
        MONTH=$(echo "$pdf" | cut -c5-6)
        
        # Verificar que sean válidos
        if [[ "$YEAR" =~ ^[0-9]{4}$ ]] && [[ "$MONTH" =~ ^[0-9]{2}$ ]]; then
            DEST_DIR="$YEAR/$MONTH"
            
            # Crear directorio si no existe
            mkdir -p "$DEST_DIR"
            
            # Verificar si ya existe en destino
            if [ -f "$DEST_DIR/$pdf" ]; then
                echo "⏭️  Ya existe: $DEST_DIR/$pdf"
            else
                mv "$pdf" "$DEST_DIR/"
                echo "✅ Movido: $pdf → $DEST_DIR/"
            fi
        else
            echo "⚠️ Formato inválido: $pdf"
        fi
    fi
done

# Resumen
echo ""
echo "📊 RESUMEN DE ORGANIZACIÓN:"
echo "========================="
for YEAR in {2024..2026}; do
    if [ -d "$YEAR" ]; then
        YEAR_COUNT=$(find "$YEAR" -name "*.pdf" | wc -l)
        if [ "$YEAR_COUNT" -gt 0 ]; then
            echo ""
            echo "📅 $YEAR: $YEAR_COUNT archivos"
            for MONTH in $(ls "$YEAR" 2>/dev/null); do
                MONTH_COUNT=$(find "$YEAR/$MONTH" -name "*.pdf" | wc -l)
                if [ "$MONTH_COUNT" -gt 0 ]; then
                    echo "  📆 $MONTH: $MONTH_COUNT archivos"
                fi
            done
        fi
    fi
done

echo ""
echo "✅ REORGANIZACIÓN COMPLETADA"
echo ""
echo "Estructura final:"
tree -L 2 "$BOLETINES_DIR" 2>/dev/null || find "$BOLETINES_DIR" -type d -maxdepth 2

echo ""
echo "💡 Próximos pasos:"
echo "  1. Verificar archivos con: ls -lR boletines/"
echo "  2. Ejecutar análisis con DS Lab"
echo "  3. Usar la UI para visualizar resultados"

