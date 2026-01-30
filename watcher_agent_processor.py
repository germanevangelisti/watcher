"""
Watcher Agent Processor
----------------------
Módulo para procesar boletines oficiales usando el agente Watcher GPT.
Divide los textos en fragmentos y los analiza vía API de OpenAI.

Autor: German Evangelisti
"""

import os
import json
import time
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass
import logging
from pathlib import Path
from dotenv import load_dotenv

import openai
from tqdm import tqdm

# Cargar variables de entorno
load_dotenv()

# Configurar OpenAI API
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY no encontrada en variables de entorno")

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class WatcherConfig:
    """Configuración para el procesamiento de boletines."""
    model: str = "gpt-4-0613"
    system_prompt: str = """Tu nombre es Watcher GPT, un agente experto en detectar posibles irregularidades ("curros") en contrataciones, gastos y actos administrativos del Estado provincial, especialmente en boletines oficiales.

Tu función es actuar como un analista de transparencia. Vas a recibir texto extraído de boletines oficiales (en español, en lenguaje técnico o administrativo) y tu tarea es identificar si el contenido podría representar un gasto sospechoso, una contratación masiva, una obra sin trazabilidad o cualquier situación de alerta para el control ciudadano.

Clasificás cada fragmento según los siguientes criterios:

1. **Categoría principal** (obligatoria):
   - gasto excesivo
   - contrataciones masivas
   - subsidios poco claros
   - obras sin trazabilidad
   - transferencias discrecionales
   - designaciones políticas
   - otros

2. **Entidad beneficiaria** (organismo o persona que recibe el beneficio).

3. **Monto estimado** (si lo hay, en pesos argentinos o dólares).

4. **Nivel de riesgo**:
   - ALTO (posible curro directo o falta grave de trazabilidad)
   - MEDIO (potencial de irregularidad, requiere seguimiento)
   - BAJO (acto válido pero relevante para control ciudadano)

5. **Fragmento original** (texto literal donde se identifica el posible curro).

6. **Tipo de curro (descriptivo)**: breve explicación del modus operandi o sospecha.

7. **Acción sugerida**: qué debería hacer un auditor o ciudadano informado frente a este caso (auditar, pedir desagregados, comparar precios, etc.).

Si el texto no permite análisis, respondé: "Sin datos suficientes para evaluar".

Siempre devolvé tu respuesta en formato JSON para facilitar su trazabilidad."""
    temperature: float = 0.2
    user: str = "german.evangelisti"
    max_fragment_size: int = 2000
    max_retries: int = 3
    retry_delay: int = 5
    max_fragments_per_file: Optional[int] = None

class TextFragmenter:
    """Clase para dividir textos en fragmentos manejables."""
    
    @staticmethod
    def split_text(text: str, max_size: int) -> List[str]:
        """
        Divide el texto en fragmentos respetando saltos de línea.
        
        Args:
            text: Texto a dividir
            max_size: Tamaño máximo por fragmento
            
        Returns:
            Lista de fragmentos
        """
        fragments = []
        current_fragment = []
        current_size = 0
        
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
                
            line_size = len(line)
            
            if current_size + line_size + 1 <= max_size:
                current_fragment.append(line)
                current_size += line_size + 1
            else:
                if current_fragment:
                    fragments.append('\n'.join(current_fragment))
                current_fragment = [line]
                current_size = line_size
        
        if current_fragment:
            fragments.append('\n'.join(current_fragment))
            
        return fragments

class WatcherProcessor:
    """Procesador principal para análisis de boletines con Watcher GPT."""
    
    def __init__(self, config: WatcherConfig):
        """
        Inicializa el procesador.
        
        Args:
            config: Configuración del procesador
        """
        self.config = config
    
    def _call_watcher_api(self, fragment: str) -> Dict:
        """
        Llama a la API de OpenAI con reintentos.
        
        Args:
            fragment: Texto a analizar
            
        Returns:
            Respuesta del agente como diccionario
            
        Raises:
            Exception: Si fallan todos los reintentos
        """
        for attempt in range(self.config.max_retries):
            try:
                response = openai.ChatCompletion.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": self.config.system_prompt},
                        {"role": "user", "content": fragment}
                    ],
                    temperature=self.config.temperature,
                    user=self.config.user
                )
                return json.loads(response.choices[0].message.content)
                
            except Exception as e:
                logger.warning(f"Intento {attempt + 1} fallido: {str(e)}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    raise
    
    def process_file(self, input_path: str, output_path: str) -> None:
        """
        Procesa un archivo de texto y guarda los resultados.
        
        Args:
            input_path: Ruta al archivo de texto
            output_path: Ruta donde guardar resultados
        """
        logger.info(f"Procesando archivo: {input_path}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        fragments = TextFragmenter.split_text(text, self.config.max_fragment_size)
        
        if self.config.max_fragments_per_file:
            fragments = fragments[:self.config.max_fragments_per_file]
        
        results = []
        for fragment in tqdm(fragments, desc="Analizando fragmentos"):
            try:
                analysis = self._call_watcher_api(fragment)
                result = {
                    "boletin": os.path.basename(input_path),
                    "fragmento": fragment,
                    "analisis": analysis
                }
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error procesando fragmento: {str(e)}")
                continue
        
        # Guardar resultados
        with open(output_path, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
                
        logger.info(f"Resultados guardados en: {output_path}")

    def process_directory(self, input_dir: str, output_dir: str) -> None:
        """
        Procesa todos los archivos .txt en un directorio.
        
        Args:
            input_dir: Directorio con archivos de texto
            output_dir: Directorio para guardar resultados
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for txt_file in input_path.glob('*.txt'):
            output_file = output_path / f"{txt_file.stem}_analysis.jsonl"
            self.process_file(str(txt_file), str(output_file))

def main():
    """Ejemplo de uso del procesador."""
    # Configurar el procesador
    config = WatcherConfig(
        system_prompt="""Eres un agente especializado en analizar boletines oficiales.
        Tu tarea es analizar el texto proporcionado y extraer la siguiente información en formato JSON:
        - Tipo de documento
        - Fecha
        - Entidades mencionadas
        - Resumen del contenido
        - Palabras clave
        - Clasificación del tema
        
        Responde SOLO con un objeto JSON válido conteniendo estos campos."""
    )
    
    processor = WatcherProcessor(config)
    
    # Procesar un directorio
    processor.process_directory(
        input_dir="path/to/input/txts",
        output_dir="path/to/output/analysis"
    )

if __name__ == "__main__":
    main()
