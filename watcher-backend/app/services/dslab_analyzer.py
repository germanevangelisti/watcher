"""
🧪 DS Lab Analyzer - Integración del análisis con persistencia
"""
import re
import time
from datetime import datetime
from typing import Any

try:
    import pdfplumber  # noqa: F401
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️  pdfplumber no disponible. Instalar con: pip install pdfplumber")


class DSLabAnalyzer:
    """Analizador de boletines con integración a BD"""

    def __init__(self, config_parameters: dict[str, Any]):
        """
        Inicializar analizador con parámetros de configuración
        
        Args:
            config_parameters: Parámetros de AnalysisConfig.parameters
        """
        self.config = config_parameters
        self.transparency_thresholds = config_parameters.get('transparency_thresholds', {})
        self.amount_thresholds = config_parameters.get('amount_thresholds', {})
        self.red_flag_rules = config_parameters.get('red_flag_rules', {})
        self.nlp_config = config_parameters.get('nlp_config', {})

    async def analyze_document(self, file_path: str) -> dict[str, Any]:
        """
        Analizar un documento completo
        
        Returns:
            Dict con:
            - transparency_score: float
            - risk_level: str
            - anomaly_score: float
            - extracted_entities: dict
            - red_flags: list
            - num_red_flags: int
            - ml_predictions: dict
            - extracted_text_sample: str
            - processing_time_seconds: float
        """
        start_time = time.time()

        try:
            # Extraer texto del PDF
            text, num_pages = await self._extract_text_from_pdf(file_path)

            if not text:
                return self._create_failed_result("No se pudo extraer texto del PDF")

            # Extraer entidades
            entities = self._extract_entities(text)

            # Calcular score de transparencia
            transparency_score = self._calculate_transparency_score(text, entities)

            # Detectar anomalías
            anomaly_score = self._calculate_anomaly_score(entities, text)

            # Determinar nivel de riesgo
            risk_level = self._determine_risk_level(transparency_score, anomaly_score)

            # Detectar red flags
            red_flags = self._detect_red_flags(text, entities, transparency_score)

            # Predicciones ML (placeholder por ahora)
            ml_predictions = self._run_ml_predictions(entities, transparency_score)

            # Texto de muestra
            text_sample = text[:5000] if len(text) > 5000 else text

            processing_time = time.time() - start_time

            return {
                "transparency_score": round(transparency_score, 2),
                "risk_level": risk_level,
                "anomaly_score": round(anomaly_score, 2),
                "extracted_entities": entities,
                "red_flags": red_flags,
                "num_red_flags": len(red_flags),
                "ml_predictions": ml_predictions,
                "extracted_text_sample": text_sample,
                "processing_time_seconds": round(processing_time, 2),
                "metadata": {
                    "num_pages": num_pages,
                    "text_length": len(text),
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            print(f"Error analizando {file_path}: {e}")
            return self._create_failed_result(str(e))

    async def _extract_text_from_pdf(self, file_path: str) -> tuple[str, int]:
        """Extraer texto completo de un PDF usando ExtractorRegistry"""
        try:
            from pathlib import Path

            from app.services.extractors import ExtractorRegistry

            result = await ExtractorRegistry.extract(Path(file_path))

            if not result.success:
                print(f"Error extrayendo PDF {file_path}: {result.error}")
                return ("", 0)

            return (result.full_text, result.stats.total_pages)

        except Exception as e:
            print(f"Error extrayendo PDF {file_path}: {e}")
            return ("", 0)

    def _extract_entities(self, text: str) -> dict[str, Any]:
        """
        Extraer entidades del texto (montos, beneficiarios, organismos)
        """
        entities = {
            "amounts": [],
            "beneficiaries": [],
            "organisms": [],
            "dates": [],
            "contracts": []
        }

        # Extraer montos
        if self.nlp_config.get('extract_amounts', True):
            amounts = self._extract_amounts(text)
            entities["amounts"] = amounts

        # Extraer beneficiarios
        if self.nlp_config.get('extract_beneficiaries', True):
            beneficiaries = self._extract_beneficiaries(text)
            entities["beneficiaries"] = beneficiaries

        # Extraer organismos
        if self.nlp_config.get('extract_organisms', True):
            organisms = self._extract_organisms(text)
            entities["organisms"] = organisms

        # Extraer fechas
        if self.nlp_config.get('extract_dates', True):
            dates = self._extract_dates(text)
            entities["dates"] = dates

        return entities

    def _extract_amounts(self, text: str) -> list[dict[str, Any]]:
        """Extraer montos del texto"""
        amounts = []
        patterns = self.nlp_config.get('amount_regex_patterns', [
            r'\$\s*[\d\.,]+',
            r'(?:pesos|ARS|PESOS)\s*[\d\.,]+',
            r'[\d\.,]+\s*(?:millones?|mil)'
        ])

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(0)
                numeric_value = self._parse_amount_to_number(amount_str)

                if numeric_value and numeric_value > 0:
                    amounts.append({
                        "raw_text": amount_str,
                        "numeric_value": numeric_value,
                        "position": match.start()
                    })

        # Ordenar por valor y eliminar duplicados cercanos
        amounts = sorted(amounts, key=lambda x: x['numeric_value'], reverse=True)
        return amounts[:20]  # Top 20 montos

    def _parse_amount_to_number(self, amount_str: str) -> float | None:
        """Convertir string de monto a número"""
        try:
            # Limpiar string
            clean = amount_str.replace('$', '').replace('pesos', '').replace('PESOS', '').replace('ARS', '')
            clean = clean.strip()

            # Manejar millones
            if 'millon' in clean.lower():
                num_part = re.search(r'[\d\.,]+', clean)
                if num_part:
                    value = float(num_part.group(0).replace('.', '').replace(',', '.'))
                    return value * 1000000

            # Manejar miles
            if 'mil' in clean.lower():
                num_part = re.search(r'[\d\.,]+', clean)
                if num_part:
                    value = float(num_part.group(0).replace('.', '').replace(',', '.'))
                    return value * 1000

            # Número directo
            clean = clean.replace('.', '').replace(',', '.')
            num_part = re.search(r'[\d\.]+', clean)
            if num_part:
                return float(num_part.group(0))

            return None
        except Exception:
            return None

    def _extract_beneficiaries(self, text: str) -> list[str]:
        """Extraer beneficiarios/empresas"""
        beneficiaries = []
        keywords = self.nlp_config.get('beneficiary_keywords', [
            'adjudicatario', 'beneficiario', 'contratista', 'proveedor', 'empresa'
        ])

        lines = text.split('\n')
        for i, line in enumerate(lines):
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    # Buscar nombre en la misma línea o siguiente
                    potential_names = self._extract_names_near(lines, i)
                    beneficiaries.extend(potential_names)

        # Eliminar duplicados y limpiar
        beneficiaries = list(set(beneficiaries))
        return beneficiaries[:30]  # Top 30

    def _extract_names_near(self, lines: list[str], index: int) -> list[str]:
        """Extraer nombres cerca de una línea"""
        names = []
        # Buscar en línea actual y 2 siguientes
        for i in range(index, min(index + 3, len(lines))):
            line = lines[i]
            # Pattern simple: palabras capitalizadas seguidas
            matches = re.findall(r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+', line)
            names.extend(matches)

        return names

    def _extract_organisms(self, text: str) -> list[str]:
        """Extraer organismos gubernamentales"""
        organisms = []
        common_organisms = [
            'Ministerio', 'Secretaría', 'Subsecretaría', 'Dirección',
            'Municipalidad', 'Gobierno', 'Legislatura', 'Tribunal'
        ]

        lines = text.split('\n')
        for line in lines:
            for org in common_organisms:
                if org in line:
                    organisms.append(line.strip())
                    break

        return list(set(organisms))[:20]

    def _extract_dates(self, text: str) -> list[str]:
        """Extraer fechas"""
        dates = []
        patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)

        return list(set(dates))[:10]

    def _calculate_transparency_score(self, text: str, entities: dict) -> float:
        """
        Calcular score de transparencia (0-100)
        Mayor score = mayor transparencia
        """
        score = 50.0  # Base

        # Puntos por tener montos identificados
        if entities.get('amounts'):
            score += 10
            if len(entities['amounts']) >= 5:
                score += 5

        # Puntos por identificar beneficiarios
        if entities.get('beneficiaries'):
            score += 15
            if len(entities['beneficiaries']) >= 3:
                score += 5

        # Puntos por identificar organismos
        if entities.get('organisms'):
            score += 10

        # Penalización por texto muy corto
        if len(text) < 1000:
            score -= 15

        # Penalización por falta de estructura
        if '\n' not in text or len(text.split('\n')) < 10:
            score -= 10

        # Bonus por fechas claras
        if entities.get('dates') and len(entities['dates']) >= 2:
            score += 5

        # Asegurar rango 0-100
        return max(0.0, min(100.0, score))

    def _calculate_anomaly_score(self, entities: dict, text: str) -> float:
        """
        Calcular score de anomalía (0-100)
        Mayor score = más anómalo
        """
        anomaly = 0.0

        # Montos sospechosos
        amounts = entities.get('amounts', [])
        for amount in amounts:
            value = amount['numeric_value']

            # Patrones sospechosos (999999, 9999, etc)
            if '999' in str(int(value)):
                anomaly += 15

            # Montos muy altos
            if value > self.amount_thresholds.get('very_high', 50000000):
                anomaly += 10

        # Falta de beneficiarios con montos altos
        if amounts and not entities.get('beneficiaries'):
            anomaly += 20

        # Texto muy repetitivo
        words = text.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                anomaly += 15

        return min(100.0, anomaly)

    def _determine_risk_level(self, transparency_score: float, anomaly_score: float) -> str:
        """Determinar nivel de riesgo"""
        thresholds = self.transparency_thresholds

        # Basado principalmente en transparency score
        if transparency_score < thresholds.get('high_risk', 30):
            return 'high'
        elif transparency_score < thresholds.get('medium_risk', 50) or anomaly_score > 60:
            return 'medium'
        else:
            return 'low'

    def _detect_red_flags(self, text: str, entities: dict, transparency_score: float) -> list[dict[str, Any]]:
        """Detectar red flags basadas en reglas"""
        red_flags = []

        # RED FLAG: HIGH_AMOUNT
        if self.red_flag_rules.get('HIGH_AMOUNT', {}).get('enabled', True):
            threshold = self.red_flag_rules['HIGH_AMOUNT'].get('threshold', 50000000)
            for amount in entities.get('amounts', []):
                if amount['numeric_value'] > threshold:
                    red_flags.append({
                        "type": "HIGH_AMOUNT",
                        "severity": "high",
                        "category": "amounts",
                        "title": f"Monto muy alto detectado: ${amount['numeric_value']:,.0f}",
                        "description": f"Se detectó un monto de ${amount['numeric_value']:,.0f} que supera el threshold de ${threshold:,.0f}",
                        "evidence": {
                            "amount": amount['numeric_value'],
                            "raw_text": amount['raw_text'],
                            "threshold": threshold
                        },
                        "confidence_score": 0.9
                    })

        # RED FLAG: MISSING_BENEFICIARY
        if self.red_flag_rules.get('MISSING_BENEFICIARY', {}).get('enabled', True):
            if entities.get('amounts') and not entities.get('beneficiaries'):
                red_flags.append({
                    "type": "MISSING_BENEFICIARY",
                    "severity": "medium",
                    "category": "transparency",
                    "title": "Falta identificación de beneficiario",
                    "description": "Se detectaron montos pero no se pudo identificar beneficiarios",
                    "evidence": {
                        "amounts_count": len(entities.get('amounts', [])),
                        "beneficiaries_found": 0
                    },
                    "confidence_score": 0.7
                })

        # RED FLAG: SUSPICIOUS_AMOUNT_PATTERN
        if self.red_flag_rules.get('SUSPICIOUS_AMOUNT_PATTERN', {}).get('enabled', True):
            patterns = self.red_flag_rules['SUSPICIOUS_AMOUNT_PATTERN'].get('patterns', ['999999', '9999'])
            for amount in entities.get('amounts', []):
                amount_str = str(int(amount['numeric_value']))
                for pattern in patterns:
                    if pattern in amount_str:
                        red_flags.append({
                            "type": "SUSPICIOUS_AMOUNT_PATTERN",
                            "severity": "medium",
                            "category": "patterns",
                            "title": f"Patrón sospechoso en monto: {pattern}",
                            "description": f"El monto ${amount['numeric_value']:,.0f} contiene el patrón sospechoso '{pattern}'",
                            "evidence": {
                                "amount": amount['numeric_value'],
                                "pattern": pattern,
                                "raw_text": amount['raw_text']
                            },
                            "confidence_score": 0.8
                        })

        # RED FLAG: LOW_TRANSPARENCY_SCORE
        if self.red_flag_rules.get('LOW_TRANSPARENCY_SCORE', {}).get('enabled', True):
            threshold = self.red_flag_rules['LOW_TRANSPARENCY_SCORE'].get('threshold', 30)
            if transparency_score < threshold:
                red_flags.append({
                    "type": "LOW_TRANSPARENCY_SCORE",
                    "severity": "high",
                    "category": "transparency",
                    "title": f"Score de transparencia muy bajo: {transparency_score:.1f}",
                    "description": f"El documento tiene un score de transparencia de {transparency_score:.1f}, por debajo del threshold de {threshold}",
                    "evidence": {
                        "transparency_score": transparency_score,
                        "threshold": threshold,
                        "missing_elements": self._identify_missing_transparency_elements(entities)
                    },
                    "confidence_score": 0.95
                })

        return red_flags

    def _identify_missing_transparency_elements(self, entities: dict) -> list[str]:
        """Identificar qué elementos faltan para transparencia"""
        missing = []

        if not entities.get('amounts'):
            missing.append("montos")
        if not entities.get('beneficiaries'):
            missing.append("beneficiarios")
        if not entities.get('organisms'):
            missing.append("organismos")
        if not entities.get('dates'):
            missing.append("fechas")

        return missing

    def _run_ml_predictions(self, entities: dict, transparency_score: float) -> dict[str, Any]:
        """
        Ejecutar predicciones de modelos ML
        Por ahora placeholder - aquí irían los modelos entrenados
        """
        return {
            "random_forest": {
                "risk_probability": 0.3 if transparency_score > 50 else 0.7,
                "confidence": 0.75
            },
            "isolation_forest": {
                "is_anomaly": transparency_score < 40,
                "anomaly_score": -0.5
            },
            "kmeans": {
                "cluster": 1 if transparency_score > 50 else 2,
                "distance_to_centroid": 1.5
            }
        }

    def _create_failed_result(self, error_message: str) -> dict[str, Any]:
        """Crear resultado para documentos que fallaron"""
        return {
            "transparency_score": 0.0,
            "risk_level": "unknown",
            "anomaly_score": 0.0,
            "extracted_entities": {},
            "red_flags": [{
                "type": "ANALYSIS_FAILED",
                "severity": "critical",
                "category": "system",
                "title": "Análisis falló",
                "description": error_message,
                "evidence": {"error": error_message},
                "confidence_score": 1.0
            }],
            "num_red_flags": 1,
            "ml_predictions": {},
            "extracted_text_sample": "",
            "processing_time_seconds": 0.0,
            "metadata": {
                "failed": True,
                "error": error_message
            }
        }

