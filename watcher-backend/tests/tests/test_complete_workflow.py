"""
Test completo del flujo de procesamiento de boletines
Valida extracción → procesamiento → análisis para una fecha específica
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "watcher-monolith" / "backend"))

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Analisis, Boletin
from app.services.pdf_service import PDFProcessor
from app.services.processing_logger import processing_logger
from sqlalchemy import func, select


class WorkflowValidator:
    """Validador del flujo completo de procesamiento"""

    def __init__(self, test_date: str = "20250101"):
        """
        Args:
            test_date: Fecha a testear en formato YYYYMMDD
        """
        self.test_date = test_date
        self.year = test_date[:4]
        self.month = test_date[4:6]
        self.day = test_date[6:8]
        self.session_id = f"test_{test_date}_{int(datetime.now().timestamp())}"

        self.pdf_processor = PDFProcessor()
        self.results = {
            "test_date": f"{self.day}/{self.month}/{self.year}",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "stages": {
                "1_discovery": {"status": "pending", "data": {}},
                "2_extraction": {"status": "pending", "data": {}},
                "3_validation": {"status": "pending", "data": {}},
                "4_analysis": {"status": "pending", "data": {}},
                "5_results": {"status": "pending", "data": {}}
            },
            "errors": [],
            "warnings": [],
            "summary": {}
        }

    async def run_complete_test(self) -> dict:
        """Ejecuta el test completo del workflow"""
        print("\n" + "="*80)
        print(f"🧪 INICIANDO TEST COMPLETO - {self.test_date}")
        print(f"📅 Fecha: {self.day}/{self.month}/{self.year}")
        print(f"🔑 Session ID: {self.session_id}")
        print("="*80 + "\n")

        processing_logger.start_session(self.session_id, f"Test Completo - {self.day}/{self.month}/{self.year}")

        try:
            # ETAPA 1: Descubrimiento de boletines
            await self._stage_1_discovery()

            # ETAPA 2: Extracción de contenido
            await self._stage_2_extraction()

            # ETAPA 3: Validación de extracción
            await self._stage_3_validation()

            # ETAPA 4: Análisis con agentes (opcional - comentar si no hay API key)
            # await self._stage_4_analysis()

            # ETAPA 5: Validación de resultados finales
            await self._stage_5_final_results()

            # Generar resumen
            self._generate_summary()

            processing_logger.end_session(self.session_id, success=len(self.results["errors"]) == 0)

        except Exception as e:
            self.results["errors"].append({
                "stage": "general",
                "error": str(e),
                "type": type(e).__name__
            })
            processing_logger.error(f"Error crítico en el test: {str(e)}", self.session_id)
            processing_logger.end_session(self.session_id, success=False)

        return self.results

    async def _stage_1_discovery(self):
        """ETAPA 1: Descubrir boletines para la fecha"""
        stage = "1_discovery"
        print(f"\n{'='*80}", flush=True)
        print("📋 ETAPA 1: DESCUBRIMIENTO DE BOLETINES", flush=True)
        print(f"{'='*80}", flush=True)

        processing_logger.info("Iniciando etapa 1: Descubrimiento", self.session_id)

        try:
            print("   → Conectando a la base de datos...", flush=True)
            async with AsyncSessionLocal() as db:
                print("   → Buscando boletines en la base de datos...", flush=True)
                # Buscar boletines de la fecha en la DB
                query = select(Boletin).where(Boletin.date == self.test_date)
                result = await db.execute(query)
                boletines_db = result.scalars().all()
                print(f"   ✓ Encontrados {len(boletines_db)} boletines en la base de datos", flush=True)

                # Buscar archivos físicos
                print(f"   → Buscando archivos PDF físicos en: {self.year}/{self.month}...", flush=True)
                boletines_dir = Path(settings.DATA_DIR) / "boletines" / self.year / self.month
                pdf_files = []

                if boletines_dir.exists():
                    print("   → Escaneando directorio...", flush=True)
                    # Buscar PDFs que coincidan con la fecha
                    for pdf_file in boletines_dir.glob("*.pdf"):
                        # Formato esperado: boletin_YYYYMMDD_N_Secc.pdf
                        if self.test_date in pdf_file.name:
                            pdf_files.append(pdf_file)
                    print(f"   ✓ Encontrados {len(pdf_files)} archivos PDF", flush=True)
                else:
                    print(f"   ⚠ Directorio no existe: {boletines_dir}", flush=True)

                self.results["stages"][stage]["status"] = "completed"
                self.results["stages"][stage]["data"] = {
                    "boletines_en_db": len(boletines_db),
                    "archivos_fisicos": len(pdf_files),
                    "boletines": [
                        {
                            "id": b.id,
                            "filename": b.filename,
                            "status": b.status,
                            "section": b.section
                        } for b in boletines_db
                    ]
                }

                # Validaciones
                if len(boletines_db) == 0:
                    self.results["errors"].append({
                        "stage": stage,
                        "error": "No se encontraron boletines en la base de datos para esta fecha",
                        "severity": "critical"
                    })
                    processing_logger.error("No hay boletines en la DB", self.session_id)
                    raise Exception("No hay boletines para testear")

                if len(pdf_files) == 0:
                    self.results["warnings"].append({
                        "stage": stage,
                        "warning": "No se encontraron archivos PDF físicos",
                        "severity": "high"
                    })
                    processing_logger.warning("No hay archivos PDF físicos", self.session_id)

                if len(boletines_db) != len(pdf_files):
                    self.results["warnings"].append({
                        "stage": stage,
                        "warning": f"Discrepancia: {len(boletines_db)} en DB vs {len(pdf_files)} archivos",
                        "severity": "medium"
                    })
                    processing_logger.warning("Discrepancia de archivos", self.session_id)

                print(f"\n✅ Boletines en DB: {len(boletines_db)}", flush=True)
                print(f"✅ Archivos físicos: {len(pdf_files)}", flush=True)
                print(f"{'='*80}\n", flush=True)
                processing_logger.success(f"Descubiertos {len(boletines_db)} boletines", self.session_id)

        except Exception as e:
            self.results["stages"][stage]["status"] = "failed"
            self.results["errors"].append({
                "stage": stage,
                "error": str(e),
                "type": type(e).__name__
            })
            processing_logger.error(f"Error en etapa 1: {str(e)}", self.session_id)
            raise

    async def _stage_2_extraction(self):
        """ETAPA 2: Extracción de contenido de PDFs"""
        stage = "2_extraction"
        print(f"\n{'='*80}", flush=True)
        print("📄 ETAPA 2: EXTRACCIÓN DE CONTENIDO", flush=True)
        print(f"{'='*80}", flush=True)

        processing_logger.info("Iniciando etapa 2: Extracción", self.session_id)

        try:
            print("   → Conectando a la base de datos...", flush=True)
            async with AsyncSessionLocal() as db:
                # Obtener boletines pendientes
                print("   → Buscando boletines pendientes de extracción...", flush=True)
                query = select(Boletin).where(
                    Boletin.date == self.test_date,
                    Boletin.status == "pending"
                )
                result = await db.execute(query)
                boletines_pending = result.scalars().all()
                print(f"   ✓ Encontrados {len(boletines_pending)} boletines pendientes\n", flush=True)

                extracted = 0
                failed = 0
                skipped = 0

                if len(boletines_pending) == 0:
                    print("   ℹ️  No hay boletines pendientes (ya fueron procesados)", flush=True)

                for idx, boletin in enumerate(boletines_pending, 1):
                    try:
                        print(f"   [{idx}/{len(boletines_pending)}] Extrayendo: {boletin.filename}...", end=" ", flush=True)

                        processing_logger.progress(
                            f"Extrayendo {boletin.filename}",
                            idx,
                            len(boletines_pending),
                            self.session_id
                        )

                        # Construir ruta al PDF
                        pdf_path = Path(settings.DATA_DIR) / "boletines" / self.year / self.month / boletin.filename

                        if not pdf_path.exists():
                            failed += 1
                            boletin.status = "failed"
                            boletin.error_message = f"PDF no encontrado: {pdf_path}"
                            print("❌ No encontrado", flush=True)
                            processing_logger.error(f"PDF no encontrado: {boletin.filename}", self.session_id)
                            continue

                        # Procesar PDF a texto
                        txt_path = await self.pdf_processor.process_pdf(pdf_path)

                        # Verificar que se generó contenido
                        if txt_path.exists():
                            txt_size = txt_path.stat().st_size
                            if txt_size > 0:
                                boletin.status = "processed"
                                boletin.error_message = None
                                extracted += 1
                                print(f"✅ OK ({txt_size:,} bytes)", flush=True)
                                processing_logger.success(f"Extraído: {boletin.filename} ({txt_size} bytes)", self.session_id)
                            else:
                                boletin.status = "failed"
                                boletin.error_message = "Archivo de texto vacío"
                                failed += 1
                                print("⚠️  Vacío", flush=True)
                                processing_logger.warning(f"Texto vacío: {boletin.filename}", self.session_id)
                        else:
                            boletin.status = "failed"
                            boletin.error_message = "No se generó archivo de texto"
                            failed += 1
                            print("❌ No generado", flush=True)
                            processing_logger.error(f"No se generó texto: {boletin.filename}", self.session_id)

                    except Exception as e:
                        boletin.status = "failed"
                        boletin.error_message = str(e)
                        failed += 1
                        print(f"❌ Error: {str(e)[:50]}", flush=True)
                        processing_logger.error(f"Error procesando {boletin.filename}: {str(e)}", self.session_id)

                print("\n   → Guardando cambios en la base de datos...", flush=True)
                await db.commit()
                print("   ✓ Cambios guardados", flush=True)

                # Contar boletines ya procesados previamente
                print("   → Calculando estadísticas...", flush=True)
                query_processed = select(func.count()).select_from(Boletin).where(
                    Boletin.date == self.test_date,
                    Boletin.status == "processed"
                )
                result_processed = await db.execute(query_processed)
                total_processed = result_processed.scalar()

                self.results["stages"][stage]["status"] = "completed" if failed == 0 else "completed_with_errors"
                self.results["stages"][stage]["data"] = {
                    "extracted_now": extracted,
                    "failed": failed,
                    "skipped": skipped,
                    "total_processed": total_processed,
                    "pending_before": len(boletines_pending)
                }

                print(f"\n✅ Extraídos ahora: {extracted}", flush=True)
                print(f"✅ Total procesados: {total_processed}", flush=True)
                print(f"❌ Fallidos: {failed}", flush=True)
                print(f"{'='*80}\n", flush=True)

                if failed > 0:
                    self.results["warnings"].append({
                        "stage": stage,
                        "warning": f"{failed} boletines fallaron en la extracción",
                        "severity": "high"
                    })

                processing_logger.success(f"Extracción completada: {extracted} exitosos, {failed} fallidos", self.session_id)

        except Exception as e:
            self.results["stages"][stage]["status"] = "failed"
            self.results["errors"].append({
                "stage": stage,
                "error": str(e),
                "type": type(e).__name__
            })
            processing_logger.error(f"Error en etapa 2: {str(e)}", self.session_id)
            raise

    async def _stage_3_validation(self):
        """ETAPA 3: Validación de extracción"""
        stage = "3_validation"
        print(f"\n{'='*80}", flush=True)
        print("✔️  ETAPA 3: VALIDACIÓN DE EXTRACCIÓN", flush=True)
        print(f"{'='*80}", flush=True)

        processing_logger.info("Iniciando etapa 3: Validación", self.session_id)

        try:
            print("   → Conectando a la base de datos...", flush=True)
            async with AsyncSessionLocal() as db:
                # Obtener todos los boletines de la fecha
                print("   → Obteniendo boletines procesados...", flush=True)
                query = select(Boletin).where(Boletin.date == self.test_date)
                result = await db.execute(query)
                boletines = result.scalars().all()
                print(f"   ✓ Encontrados {len(boletines)} boletines totales\n", flush=True)

                validations = {
                    "total": len(boletines),
                    "processed": 0,
                    "pending": 0,
                    "failed": 0,
                    "with_content": 0,
                    "empty_content": 0,
                    "missing_files": 0
                }

                print("   → Validando archivos de texto...", flush=True)
                for idx, boletin in enumerate(boletines, 1):
                    if idx % 5 == 0 or idx == len(boletines):
                        print(f"      Validados: {idx}/{len(boletines)}", end="\r", flush=True)

                    if boletin.status == "processed":
                        validations["processed"] += 1

                        # Verificar que existe el archivo de texto
                        txt_path = Path(settings.DATA_DIR) / "boletines" / self.year / self.month / boletin.filename.replace('.pdf', '.txt')

                        if txt_path.exists():
                            txt_size = txt_path.stat().st_size
                            if txt_size > 100:  # Mínimo 100 bytes
                                validations["with_content"] += 1
                            else:
                                validations["empty_content"] += 1
                                self.results["warnings"].append({
                                    "stage": stage,
                                    "warning": f"Contenido muy pequeño: {boletin.filename} ({txt_size} bytes)",
                                    "severity": "medium"
                                })
                        else:
                            validations["missing_files"] += 1
                            self.results["errors"].append({
                                "stage": stage,
                                "error": f"Archivo de texto no encontrado: {boletin.filename}",
                                "severity": "high"
                            })

                    elif boletin.status == "pending":
                        validations["pending"] += 1
                    elif boletin.status == "failed":
                        validations["failed"] += 1

                self.results["stages"][stage]["status"] = "completed"
                self.results["stages"][stage]["data"] = validations

                # Validaciones críticas
                if validations["processed"] == 0:
                    self.results["errors"].append({
                        "stage": stage,
                        "error": "No hay boletines procesados",
                        "severity": "critical"
                    })
                    processing_logger.error("No hay boletines procesados", self.session_id)

                print("   ✓ Validación completada\n", flush=True)

                success_rate = (validations["with_content"] / validations["total"] * 100) if validations["total"] > 0 else 0

                print(f"✅ Boletines procesados: {validations['processed']}/{validations['total']}", flush=True)
                print(f"✅ Con contenido válido: {validations['with_content']}", flush=True)
                print(f"⚠️  Contenido vacío: {validations['empty_content']}", flush=True)
                print(f"❌ Archivos faltantes: {validations['missing_files']}", flush=True)
                print(f"📊 Tasa de éxito: {success_rate:.1f}%", flush=True)
                print(f"{'='*80}\n", flush=True)

                processing_logger.success(f"Validación completada: {success_rate:.1f}% exitoso", self.session_id)

        except Exception as e:
            self.results["stages"][stage]["status"] = "failed"
            self.results["errors"].append({
                "stage": stage,
                "error": str(e),
                "type": type(e).__name__
            })
            processing_logger.error(f"Error en etapa 3: {str(e)}", self.session_id)
            raise

    async def _stage_4_analysis(self):
        """ETAPA 4: Análisis con agentes IA (opcional)"""
        stage = "4_analysis"
        print(f"\n{'='*80}")
        print("🤖 ETAPA 4: ANÁLISIS CON AGENTES IA")
        print(f"{'='*80}")

        processing_logger.info("Iniciando etapa 4: Análisis IA", self.session_id)

        # TODO: Implementar cuando esté listo el sistema de workflows
        self.results["stages"][stage]["status"] = "skipped"
        self.results["stages"][stage]["data"] = {
            "reason": "No implementado aún - requiere API key y workflows"
        }
        print("⏭️  Saltando análisis IA (no implementado en este test)")
        processing_logger.warning("Etapa 4 omitida", self.session_id)

    async def _stage_5_final_results(self):
        """ETAPA 5: Resultados finales y métricas"""
        stage = "5_results"
        print(f"\n{'='*80}", flush=True)
        print("📊 ETAPA 5: RESULTADOS FINALES", flush=True)
        print(f"{'='*80}", flush=True)

        processing_logger.info("Iniciando etapa 5: Resultados finales", self.session_id)

        try:
            print("   → Calculando estadísticas finales...", flush=True)
            async with AsyncSessionLocal() as db:
                # Estadísticas finales
                query_total = select(func.count()).select_from(Boletin).where(Boletin.date == self.test_date)
                result_total = await db.execute(query_total)
                total = result_total.scalar()

                query_processed = select(func.count()).select_from(Boletin).where(
                    Boletin.date == self.test_date,
                    Boletin.status == "processed"
                )
                result_processed = await db.execute(query_processed)
                processed = result_processed.scalar()

                query_failed = select(func.count()).select_from(Boletin).where(
                    Boletin.date == self.test_date,
                    Boletin.status == "failed"
                )
                result_failed = await db.execute(query_failed)
                failed = result_failed.scalar()

                # Análisis (si existen)
                query_analisis = select(func.count()).select_from(Analisis).join(Boletin).where(
                    Boletin.date == self.test_date
                )
                result_analisis = await db.execute(query_analisis)
                analisis_count = result_analisis.scalar()

                success_rate = (processed / total * 100) if total > 0 else 0
                print("   ✓ Estadísticas calculadas\n", flush=True)

                self.results["stages"][stage]["status"] = "completed"
                self.results["stages"][stage]["data"] = {
                    "total_boletines": total,
                    "procesados_exitosos": processed,
                    "fallidos": failed,
                    "analisis_generados": analisis_count,
                    "tasa_exito": round(success_rate, 2)
                }

                print(f"✅ Total de boletines: {total}", flush=True)
                print(f"✅ Procesados exitosamente: {processed}", flush=True)
                print(f"❌ Fallidos: {failed}", flush=True)
                print(f"📈 Análisis generados: {analisis_count}", flush=True)
                print(f"📊 Tasa de éxito: {success_rate:.1f}%", flush=True)
                print(f"{'='*80}\n", flush=True)

                processing_logger.success(f"Test completado: {success_rate:.1f}% exitoso", self.session_id)

        except Exception as e:
            self.results["stages"][stage]["status"] = "failed"
            self.results["errors"].append({
                "stage": stage,
                "error": str(e),
                "type": type(e).__name__
            })
            processing_logger.error(f"Error en etapa 5: {str(e)}", self.session_id)
            raise

    def _generate_summary(self):
        """Genera resumen del test"""
        errors_count = len(self.results["errors"])
        warnings_count = len(self.results["warnings"])

        stages_completed = sum(1 for s in self.results["stages"].values() if s["status"] in ["completed", "completed_with_errors"])
        stages_total = len(self.results["stages"])

        # Determinar estado general
        if errors_count == 0 and warnings_count == 0:
            overall_status = "✅ ÉXITO COMPLETO"
        elif errors_count == 0:
            overall_status = "⚠️  ÉXITO CON ADVERTENCIAS"
        else:
            overall_status = "❌ FALLIDO"

        self.results["summary"] = {
            "overall_status": overall_status,
            "stages_completed": f"{stages_completed}/{stages_total}",
            "errors": errors_count,
            "warnings": warnings_count,
            "test_passed": errors_count == 0
        }

        print(f"\n{'='*80}", flush=True)
        print("📋 RESUMEN FINAL", flush=True)
        print(f"{'='*80}", flush=True)
        print(f"Estado General: {overall_status}", flush=True)
        print(f"Etapas completadas: {stages_completed}/{stages_total}", flush=True)
        print(f"Errores: {errors_count}", flush=True)
        print(f"Advertencias: {warnings_count}", flush=True)
        print(f"Test pasado: {'✅ SÍ' if errors_count == 0 else '❌ NO'}", flush=True)
        print(f"{'='*80}\n", flush=True)


async def main():
    """Función principal del test"""
    import json

    # Fecha a testear (1 de enero de 2025)
    TEST_DATE = "20250101"

    validator = WorkflowValidator(test_date=TEST_DATE)
    results = await validator.run_complete_test()

    # Guardar resultados en JSON
    print("\n→ Guardando resultados...", flush=True)
    output_dir = Path(__file__).parent / "test_results"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"test_workflow_{TEST_DATE}_{int(datetime.now().timestamp())}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"✓ Resultados guardados en: {output_file}", flush=True)

    # Retornar código de salida
    return 0 if results["summary"]["test_passed"] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
