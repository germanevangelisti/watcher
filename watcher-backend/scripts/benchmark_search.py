"""
Benchmark de Búsqueda Semántica - Evaluación de Precisión

Este script evalúa la calidad de los resultados de búsqueda semántica
comparando diferentes modelos y métricas.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any
import time
import json
from datetime import datetime

# Agregar el directorio del backend al path
sys.path.insert(0, str(Path(__file__).parent.parent / "watcher-monolith" / "backend"))

from app.services.embedding_service import get_embedding_service


# Casos de prueba con ground truth
TEST_CASES = [
    {
        "query": "contrato",
        "expected_keywords": ["contrato", "licitación", "adjudicación", "obra"],
        "min_score": 0.3,
        "description": "Búsqueda genérica de contratos"
    },
    {
        "query": "contrato de construcción",
        "expected_keywords": ["construcción", "obra", "contrato", "edificio"],
        "min_score": 0.4,
        "description": "Contratos específicos de construcción"
    },
    {
        "query": "licitación pública obras públicas",
        "expected_keywords": ["licitación", "pública", "obra", "adjudicación"],
        "min_score": 0.45,
        "description": "Licitaciones de obras públicas"
    },
    {
        "query": "designación funcionario",
        "expected_keywords": ["designa", "nombra", "funcionario", "cargo"],
        "min_score": 0.4,
        "description": "Designaciones de personal"
    },
    {
        "query": "decreto presupuesto asignación fondos",
        "expected_keywords": ["presupuesto", "fondos", "asignación", "decreto"],
        "min_score": 0.4,
        "description": "Asignaciones presupuestarias"
    },
    {
        "query": "resolución aprobación",
        "expected_keywords": ["resolución", "aprueba", "autoriza"],
        "min_score": 0.35,
        "description": "Resoluciones administrativas"
    }
]


class SearchBenchmark:
    """Clase para ejecutar benchmarks de búsqueda"""
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.results = []
    
    async def run_test_case(self, test_case: Dict[str, Any], n_results: int = 10) -> Dict[str, Any]:
        """
        Ejecuta un caso de prueba y evalúa los resultados
        """
        query = test_case["query"]
        expected_keywords = test_case["expected_keywords"]
        min_score = test_case["min_score"]
        
        print(f"\n{'='*80}")
        print(f"Test: {test_case['description']}")
        print(f"Query: '{query}'")
        print(f"{'='*80}")
        
        # Ejecutar búsqueda
        start_time = time.time()
        results = await self.embedding_service.search(
            query=query,
            n_results=n_results
        )
        execution_time = (time.time() - start_time) * 1000  # ms
        
        # Evaluar resultados
        evaluation = {
            "query": query,
            "description": test_case["description"],
            "execution_time_ms": round(execution_time, 2),
            "total_results": len(results),
            "results_analysis": []
        }
        
        # Analizar cada resultado
        relevant_count = 0
        scores = []
        
        for idx, result in enumerate(results[:10], 1):  # Top 10
            document = result.get('document', '').lower()
            distance = result.get('distance', 2.0)
            score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
            scores.append(score)
            
            # Verificar si contiene keywords esperadas
            keywords_found = [kw for kw in expected_keywords if kw.lower() in document]
            is_relevant = len(keywords_found) >= 2  # Al menos 2 keywords
            
            if is_relevant:
                relevant_count += 1
            
            result_info = {
                "rank": idx,
                "score": round(score, 3),
                "distance": round(distance, 3),
                "keywords_found": keywords_found,
                "is_relevant": is_relevant,
                "filename": result.get('metadata', {}).get('filename', 'N/A'),
                "snippet": document[:150] + "..." if len(document) > 150 else document
            }
            
            evaluation["results_analysis"].append(result_info)
            
            # Imprimir resultado
            emoji = "✅" if is_relevant else "❌"
            print(f"{emoji} Rank {idx}: Score={score:.1%} | {len(keywords_found)}/{len(expected_keywords)} keywords | {result_info['filename']}")
            if keywords_found:
                print(f"   Keywords: {', '.join(keywords_found)}")
        
        # Calcular métricas
        precision_at_10 = relevant_count / min(10, len(results)) if results else 0
        avg_score = sum(scores) / len(scores) if scores else 0
        min_score_achieved = min(scores) if scores else 0
        max_score_achieved = max(scores) if scores else 0
        
        # Evaluar si pasó el umbral
        passed = avg_score >= min_score and precision_at_10 >= 0.5
        
        evaluation["metrics"] = {
            "precision_at_10": round(precision_at_10, 3),
            "avg_score": round(avg_score, 3),
            "min_score": round(min_score_achieved, 3),
            "max_score": round(max_score_achieved, 3),
            "relevant_count": relevant_count,
            "passed": passed,
            "threshold": min_score
        }
        
        # Imprimir resumen
        print("\n📊 Métricas:")
        print(f"   Precision@10: {precision_at_10:.1%}")
        print(f"   Score promedio: {avg_score:.1%}")
        print(f"   Resultados relevantes: {relevant_count}/10")
        print(f"   Tiempo de ejecución: {execution_time:.0f}ms")
        print("   ✅ PASÓ" if passed else "   ❌ NO PASÓ")
        
        return evaluation
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecuta todos los casos de prueba
        """
        print("\n" + "="*80)
        print("BENCHMARK DE BÚSQUEDA SEMÁNTICA - WATCHER AGENT")
        print("="*80)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total de tests: {len(TEST_CASES)}")
        print(f"Chunks indexados: {self.embedding_service.collection.count()}")
        print("="*80)
        
        results = []
        for test_case in TEST_CASES:
            result = await self.run_test_case(test_case)
            results.append(result)
            await asyncio.sleep(0.5)  # Pausa entre tests
        
        # Calcular métricas globales
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["metrics"]["passed"])
        avg_precision = sum(r["metrics"]["precision_at_10"] for r in results) / total_tests
        avg_score = sum(r["metrics"]["avg_score"] for r in results) / total_tests
        avg_time = sum(r["execution_time_ms"] for r in results) / total_tests
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "pass_rate": round(passed_tests / total_tests, 3),
            "avg_precision_at_10": round(avg_precision, 3),
            "avg_score": round(avg_score, 3),
            "avg_execution_time_ms": round(avg_time, 2),
            "results": results
        }
        
        # Imprimir resumen final
        print("\n" + "="*80)
        print("RESUMEN GENERAL")
        print("="*80)
        print(f"Tests ejecutados: {total_tests}")
        print(f"Tests aprobados: {passed_tests}/{total_tests} ({summary['pass_rate']:.1%})")
        print(f"Precision@10 promedio: {avg_precision:.1%}")
        print(f"Score promedio: {avg_score:.1%}")
        print(f"Tiempo promedio: {avg_time:.0f}ms")
        print("="*80)
        
        # Guardar resultados
        output_file = Path(__file__).parent / "benchmark_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados guardados en: {output_file}")
        
        return summary


async def main():
    """Función principal"""
    benchmark = SearchBenchmark()
    await benchmark.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
