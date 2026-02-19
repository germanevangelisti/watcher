"""
Extractor de Contexto desde PDFs Presupuestarios
Procesa Ley de Presupuesto y Mensaje de Elevación para extraer keywords y prioridades

Autor: Watcher Fiscal Agent
"""

import pdfplumber
import json
import re
from pathlib import Path
from collections import Counter
from typing import Dict, List

# Rutas
BASE_DIR = Path(__file__).parent.parent.parent.parent
PDF_DIR = BASE_DIR / "watcher-doc" / "data"
OUTPUT_DIR = BASE_DIR / "watcher-doc"

# PDFs a procesar
LEY_PRESUPUESTO = PDF_DIR / "Ley-de-Presupuesto-L-11014.pdf"
MENSAJE_ELEVACION = PDF_DIR / "Mensaje-de-Elevacion_Presupuesto-2025.pdf"

# Keywords ignoradas (stopwords en español)
STOPWORDS = set([
    'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se', 'no', 'haber',
    'por', 'con', 'su', 'para', 'como', 'estar', 'tener', 'le', 'lo', 'todo',
    'pero', 'más', 'hacer', 'o', 'poder', 'decir', 'este', 'ir', 'otro', 'ese',
    'si', 'me', 'ya', 'ver', 'porque', 'dar', 'cuando', 'él', 'muy', 'sin', 'vez',
    'mucho', 'saber', 'qué', 'sobre', 'mi', 'alguno', 'mismo', 'yo', 'también',
    'hasta', 'año', 'dos', 'querer', 'entre', 'así', 'primero', 'desde', 'grande',
    'eso', 'ni', 'nos', 'llegar', 'pasar', 'tiempo', 'ella', 'sí', 'día', 'uno',
    'bien', 'poco', 'deber', 'entonces', 'poner', 'cosa', 'tanto', 'hombre', 'parecer',
    'nuestro', 'tan', 'donde', 'ahora', 'parte', 'después', 'vida', 'quedar', 'siempre',
    'creer', 'hablar', 'llevar', 'dejar', 'nada', 'cada', 'seguir', 'menos', 'nuevo',
    'encontrar', 'algo', 'solo', 'decir', 'casa', 'aunque', 'pues', 'ante', 'bajo',
    'artículo', 'artículos', 'articulo', 'articulos', 'ley', 'leyes', 'los', 'las',
    'del', 'al', 'ante', 'mediante', 'según', 'durante'
])


def extract_text_from_pdf(pdf_path: Path, max_pages: int = None) -> str:
    """Extrae texto completo de un PDF"""
    print(f"\n📖 Extrayendo texto de: {pdf_path.name}")
    
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        pages_to_process = min(max_pages, total_pages) if max_pages else total_pages
        
        print(f"   Total páginas: {total_pages}, procesando: {pages_to_process}")
        
        for i, page in enumerate(pdf.pages[:pages_to_process], 1):
            try:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
                if i % 10 == 0:
                    print(f"   ✓ Páginas procesadas: {i}/{pages_to_process}", end='\r')
            except Exception as e:
                print(f"\n   ⚠ Error en página {i}: {e}")
                continue
        
        print(f"\n   ✓ Extraídos {len(text)} caracteres")
    
    return text


def extract_keywords(text: str, min_freq: int = 3, min_length: int = 5) -> List[tuple]:
    """Extrae keywords por frecuencia"""
    # Limpiar y normalizar texto
    text = text.upper()
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Extraer palabras
    words = text.split()
    
    # Filtrar stopwords y palabras cortas
    words = [
        word for word in words 
        if len(word) >= min_length and word.lower() not in STOPWORDS
    ]
    
    # Contar frecuencias
    counter = Counter(words)
    
    # Retornar top keywords
    return counter.most_common(100)


def extract_priority_topics(text: str) -> Dict[str, List[str]]:
    """Extrae tópicos prioritarios basados en keywords clave"""
    text_upper = text.upper()
    
    # Diccionario de temas con sus keywords asociadas
    topics = {
        'salud': ['HOSPITAL', 'MÉDICO', 'MEDICINA', 'VACUNA', 'TRATAMIENTO', 
                  'PACIENTE', 'SANITARIO', 'CLÍNICA', 'SALUD'],
        'educacion': ['ESCUELA', 'DOCENTE', 'ALUMNO', 'EDUCATIVO', 'ENSEÑANZA',
                      'MAESTRO', 'UNIVERSIDAD', 'ESTUDIANTE', 'EDUCACIÓN'],
        'infraestructura': ['OBRA', 'CONSTRUCCIÓN', 'VIAL', 'RUTA', 'CAMINO',
                            'PAVIMENTO', 'INFRAESTRUCTURA', 'EDIFICIO'],
        'seguridad': ['POLICÍA', 'SEGURIDAD', 'PREVENCIÓN', 'EMERGENCIA',
                     'BOMBERO', 'PROTECCIÓN', 'VIGILANCIA'],
        'desarrollo_social': ['SOCIAL', 'COMUNIDAD', 'ASISTENCIA', 'SUBSIDIO',
                             'FAMILIA', 'POBREZA', 'INCLUSIÓN'],
        'economia': ['ECONÓMICO', 'FINANCIERO', 'PRESUPUESTO', 'FISCAL',
                    'TRIBUTARIO', 'IMPUESTO', 'RECAUDACIÓN'],
        'ambiente': ['AMBIENTE', 'AMBIENTAL', 'ECOLOGÍA', 'RESIDUO',
                    'AGUA', 'ENERGÍA', 'SOSTENIBLE', 'SUSTENTABLE'],
        'produccion': ['PRODUCCIÓN', 'INDUSTRIA', 'AGRÍCOLA', 'GANADERO',
                      'COMERCIO', 'EXPORTACIÓN', 'TECNOLOGÍA']
    }
    
    # Buscar menciones de cada tema
    topic_keywords = {}
    for topic, keywords in topics.items():
        found_keywords = []
        for keyword in keywords:
            count = text_upper.count(keyword)
            if count > 0:
                found_keywords.append(f"{keyword.lower()} ({count})")
        
        if found_keywords:
            topic_keywords[topic] = found_keywords
    
    return topic_keywords


def generate_semantic_vocabulary(keywords_ley: List[tuple], keywords_mensaje: List[tuple], topics: Dict) -> Dict:
    """Genera vocabulario semántico fiscal"""
    print("\n📝 Generando vocabulario semántico...")
    
    # Combinar keywords de ambos documentos
    all_keywords = set()
    for word, _ in keywords_ley[:50]:
        all_keywords.add(word.lower())
    for word, _ in keywords_mensaje[:50]:
        all_keywords.add(word.lower())
    
    # Vocabulario base con sinónimos
    vocab = {
        'licitacion': ['contratación', 'adjudicación', 'concurso', 'llamado', 'puja'],
        'decreto': ['resolución', 'disposición', 'acto administrativo', 'norma'],
        'subsidio': ['asistencia', 'ayuda económica', 'transferencia', 'aporte'],
        'obra': ['construcción', 'infraestructura', 'proyecto', 'edificación'],
        'programa': ['plan', 'proyecto', 'iniciativa', 'política pública'],
        'presupuesto': ['crédito', 'partida', 'asignación', 'recursos'],
        'ministerio': ['jurisdicción', 'cartera', 'organismo', 'secretaría'],
        'empleado': ['agente', 'funcionario', 'personal', 'trabajador'],
        'gasto': ['erogación', 'egreso', 'desembolso', 'inversión'],
        'ingreso': ['recurso', 'recaudación', 'renta', 'tributo']
    }
    
    # Agregar keywords por tema
    for topic, keywords in topics.items():
        # Extraer solo las palabras (sin counts)
        words = [kw.split(' (')[0] for kw in keywords]
        vocab[topic] = words[:10]  # Top 10 por tema
    
    # Agregar keywords generales
    vocab['keywords_generales'] = list(all_keywords)[:100]
    
    print(f"   ✓ Vocabulario generado con {len(vocab)} categorías")
    return vocab


def extract_priorities_summary(text: str, max_length: int = 2000) -> str:
    """Extrae resumen de prioridades del Mensaje de Elevación"""
    # Buscar sección de prioridades (típicamente en primeras páginas)
    text_lines = text.split('\n')
    
    # Buscar palabras clave de secciones importantes
    priority_keywords = ['PRIORITARIO', 'OBJETIVO', 'META', 'PRIORIDAD', 'ESTRATÉG']
    
    priority_lines = []
    for i, line in enumerate(text_lines[:200]):  # Primeras 200 líneas
        line_upper = line.upper()
        if any(kw in line_upper for kw in priority_keywords):
            # Agregar contexto (3 líneas antes y 5 después)
            start = max(0, i - 3)
            end = min(len(text_lines), i + 6)
            priority_lines.extend(text_lines[start:end])
    
    summary = '\n'.join(priority_lines)[:max_length]
    return summary if summary else text[:max_length]


def main():
    """Función principal"""
    print(f"\n{'#'*80}")
    print("# EXTRACTOR DE CONTEXTO PRESUPUESTARIO")
    print(f"{'#'*80}")
    
    # 1. Extraer texto de Ley de Presupuesto
    print(f"\n{'='*80}")
    print("FASE 1: LEY DE PRESUPUESTO")
    print(f"{'='*80}")
    
    if not LEY_PRESUPUESTO.exists():
        print(f"✗ No encontrado: {LEY_PRESUPUESTO}")
        return
    
    texto_ley = extract_text_from_pdf(LEY_PRESUPUESTO)
    keywords_ley = extract_keywords(texto_ley)
    
    print("\n📊 Top 10 Keywords Ley de Presupuesto:")
    for word, count in keywords_ley[:10]:
        print(f"   • {word:<30} {count:>4} menciones")
    
    # 2. Extraer texto de Mensaje de Elevación
    print(f"\n{'='*80}")
    print("FASE 2: MENSAJE DE ELEVACIÓN")
    print(f"{'='*80}")
    
    if not MENSAJE_ELEVACION.exists():
        print(f"✗ No encontrado: {MENSAJE_ELEVACION}")
        return
    
    texto_mensaje = extract_text_from_pdf(MENSAJE_ELEVACION, max_pages=30)
    keywords_mensaje = extract_keywords(texto_mensaje)
    
    print("\n📊 Top 10 Keywords Mensaje de Elevación:")
    for word, count in keywords_mensaje[:10]:
        print(f"   • {word:<30} {count:>4} menciones")
    
    # 3. Extraer tópicos prioritarios
    print(f"\n{'='*80}")
    print("FASE 3: ANÁLISIS DE PRIORIDADES")
    print(f"{'='*80}")
    
    topics = extract_priority_topics(texto_mensaje)
    
    print("\n📍 Tópicos Identificados:")
    for topic, keywords in sorted(topics.items()):
        print(f"   • {topic}: {len(keywords)} keywords")
        print(f"     {', '.join(keywords[:5])}")
    
    # 4. Generar vocabulario semántico
    vocab = generate_semantic_vocabulary(keywords_ley, keywords_mensaje, topics)
    
    # 5. Extraer resumen de prioridades
    priorities_summary = extract_priorities_summary(texto_mensaje)
    
    # 6. Guardar outputs
    print(f"\n{'='*80}")
    print("GUARDANDO ARCHIVOS")
    print(f"{'='*80}")
    
    # Vocabulario semántico
    vocab_path = OUTPUT_DIR / "vocabulario_semantico_fiscal.json"
    with open(vocab_path, 'w', encoding='utf-8') as f:
        json.dump(vocab, f, ensure_ascii=False, indent=2)
    print(f"✓ Guardado: {vocab_path}")
    
    # Metas presupuestarias
    metas_path = OUTPUT_DIR / "metas_presupuestarias_2025.json"
    metas = {
        'keywords_ley': [{'word': w, 'count': c} for w, c in keywords_ley[:50]],
        'keywords_mensaje': [{'word': w, 'count': c} for w, c in keywords_mensaje[:50]],
        'topics': topics
    }
    with open(metas_path, 'w', encoding='utf-8') as f:
        json.dump(metas, f, ensure_ascii=False, indent=2)
    print(f"✓ Guardado: {metas_path}")
    
    # Prioridades gubernamentales
    priorities_path = OUTPUT_DIR / "prioridades_gubernamentales.txt"
    with open(priorities_path, 'w', encoding='utf-8') as f:
        f.write(priorities_summary)
    print(f"✓ Guardado: {priorities_path}")
    
    print(f"\n{'#'*80}")
    print("# ✅ EXTRACCIÓN COMPLETADA")
    print(f"{'#'*80}\n")


if __name__ == "__main__":
    main()



