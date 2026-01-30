"""
Motor de Vinculación Semántica
Vincula actos administrativos con programas presupuestarios usando matching híbrido

Autor: Watcher Fiscal Agent
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class VinculoActoPresupuesto:
    """Representa un vínculo entre acto y programa presupuestario"""
    acto_id: int
    programa_id: int
    score_confianza: float  # 0.0 - 1.0
    metodo_matching: str  # partida, organismo, keywords, semantico
    detalles: Dict  # Información adicional del match
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para DB"""
        return {
            'acto_id': self.acto_id,
            'programa_id': self.programa_id,
            'score_confianza': self.score_confianza,
            'metodo_matching': self.metodo_matching,
            'detalles_json': json.dumps(self.detalles, ensure_ascii=False)
        }


class SemanticMatcher:
    """Motor de vinculación semántica entre actos y programas presupuestarios"""
    
    def __init__(self, vocabulario_path: Optional[Path] = None):
        """
        Inicializa el matcher
        
        Args:
            vocabulario_path: Ruta al vocabulario semántico fiscal
        """
        # Cargar vocabulario semántico si está disponible
        self.vocabulario = {}
        if vocabulario_path and vocabulario_path.exists():
            with open(vocabulario_path, 'r', encoding='utf-8') as f:
                self.vocabulario = json.load(f)
        
        # Normalización de organismos comunes
        self.organismo_aliases = {
            'ECONOMÍA': ['ECONOMIA', 'ECONÓMICO', 'ECONOMICO', 'HACIENDA', 'FINANZAS'],
            'SALUD': ['SANITARIO', 'HOSPITAL', 'MEDICO', 'MEDICINA'],
            'EDUCACIÓN': ['EDUCACION', 'EDUCATIVO', 'ENSEÑANZA', 'ESCUELA'],
            'OBRAS': ['INFRAESTRUCTURA', 'CONSTRUCCIÓN', 'CONSTRUCCION', 'VIAL'],
            'SEGURIDAD': ['POLICIA', 'POLICÍA', 'PROTECCIÓN', 'PROTECCION'],
            'DESARROLLO': ['SOCIAL', 'COMUNIDAD', 'ASISTENCIA'],
            'PRODUCCIÓN': ['PRODUCCION', 'INDUSTRIA', 'COMERCIO', 'AGRICULTURA'],
            'AMBIENTE': ['AMBIENTAL', 'ECOLOGÍA', 'ECOLOGIA', 'SOSTENIBLE']
        }
        
        # Pesos para scoring
        self.pesos = {
            'partida_exacta': 1.0,
            'partida_parcial': 0.85,
            'organismo_exacto': 0.85,
            'organismo_similar': 0.70,
            'keywords_fuertes': 0.65,
            'keywords_debiles': 0.45,
            'semantico': 0.50
        }
        
        # Umbral mínimo para considerar un match válido
        self.umbral_minimo = 0.4
    
    def normalizar_organismo(self, organismo: str) -> str:
        """Normaliza nombre de organismo"""
        if not organismo:
            return ""
        
        org = organismo.upper().strip()
        
        # Remover prefijos comunes
        for prefix in ['MINISTERIO DE', 'SECRETARIA DE', 'DIRECCION DE']:
            if org.startswith(prefix):
                org = org[len(prefix):].strip()
        
        # Remover números de código
        org = re.sub(r'^\d+\s*-\s*', '', org)
        
        return org
    
    def match_by_partida(self, acto_partida: str, programa_partida: str) -> Tuple[float, Dict]:
        """
        Match directo por partida presupuestaria
        
        Returns:
            (score, detalles)
        """
        if not acto_partida or not programa_partida:
            return 0.0, {}
        
        # Normalizar partidas
        acto_p = acto_partida.strip().replace(' ', '')
        prog_p = programa_partida.strip().replace(' ', '')
        
        # Match exacto
        if acto_p == prog_p:
            return self.pesos['partida_exacta'], {
                'tipo': 'partida_exacta',
                'acto_partida': acto_partida,
                'programa_partida': programa_partida
            }
        
        # Match parcial (primeros dígitos)
        if acto_p.startswith(prog_p) or prog_p.startswith(acto_p):
            return self.pesos['partida_parcial'], {
                'tipo': 'partida_parcial',
                'acto_partida': acto_partida,
                'programa_partida': programa_partida
            }
        
        return 0.0, {}
    
    def match_by_organismo(self, acto_organismo: str, programa_organismo: str) -> Tuple[float, Dict]:
        """
        Match por organismo emisor
        
        Returns:
            (score, detalles)
        """
        if not acto_organismo or not programa_organismo:
            return 0.0, {}
        
        # Normalizar
        acto_org = self.normalizar_organismo(acto_organismo)
        prog_org = self.normalizar_organismo(programa_organismo)
        
        # Match exacto (ignorando case)
        if acto_org == prog_org:
            return self.pesos['organismo_exacto'], {
                'tipo': 'organismo_exacto',
                'acto_organismo': acto_organismo,
                'programa_organismo': programa_organismo
            }
        
        # Match por contenido
        if acto_org in prog_org or prog_org in acto_org:
            return self.pesos['organismo_similar'], {
                'tipo': 'organismo_contenido',
                'acto_organismo': acto_organismo,
                'programa_organismo': programa_organismo
            }
        
        # Match por alias
        for categoria, aliases in self.organismo_aliases.items():
            acto_match = any(alias in acto_org for alias in aliases)
            prog_match = any(alias in prog_org for alias in aliases)
            if acto_match and prog_match:
                return self.pesos['organismo_similar'], {
                    'tipo': 'organismo_alias',
                    'categoria': categoria,
                    'acto_organismo': acto_organismo,
                    'programa_organismo': programa_organismo
                }
        
        return 0.0, {}
    
    def match_by_keywords(self, acto_keywords: List[str], programa_keywords: List[str]) -> Tuple[float, Dict]:
        """
        Match por keywords comunes
        
        Returns:
            (score, detalles)
        """
        if not acto_keywords or not programa_keywords:
            return 0.0, {}
        
        # Convertir a sets y normalizar
        acto_kw = set(kw.lower().strip() for kw in acto_keywords)
        prog_kw = set(kw.lower().strip() for kw in programa_keywords)
        
        # Calcular intersección
        comunes = acto_kw & prog_kw
        
        if not comunes:
            return 0.0, {}
        
        # Score basado en proporción de keywords comunes
        proporcion = len(comunes) / min(len(acto_kw), len(prog_kw))
        
        # Determinar si son keywords fuertes o débiles
        keywords_fuertes = {
            'hospital', 'escuela', 'ruta', 'obra', 'licitación',
            'construcción', 'servicio', 'suministro'
        }
        
        tiene_fuertes = bool(comunes & keywords_fuertes)
        
        if tiene_fuertes:
            score = self.pesos['keywords_fuertes'] * proporcion
        else:
            score = self.pesos['keywords_debiles'] * proporcion
        
        return score, {
            'tipo': 'keywords_comunes',
            'keywords_comunes': list(comunes),
            'cantidad': len(comunes),
            'proporcion': round(proporcion, 3)
        }
    
    def expandir_con_vocabulario(self, keywords: List[str]) -> List[str]:
        """Expande keywords usando vocabulario semántico"""
        if not self.vocabulario:
            return keywords
        
        expandidos = set(keywords)
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Buscar en vocabulario
            for tema, sinonimos in self.vocabulario.items():
                if keyword_lower in [s.lower() for s in sinonimos]:
                    expandidos.update([s.lower() for s in sinonimos[:5]])  # Top 5 sinónimos
        
        return list(expandidos)
    
    def calcular_match_completo(
        self,
        acto: Dict,
        programa: Dict,
        usar_vocabulario: bool = True
    ) -> Tuple[float, str, Dict]:
        """
        Calcula match completo entre acto y programa usando todos los métodos
        
        Args:
            acto: Diccionario con datos del acto
            programa: Diccionario con datos del programa
            usar_vocabulario: Si usar vocabulario para expandir keywords
        
        Returns:
            (score_final, metodo_principal, detalles_completos)
        """
        scores = []
        detalles_matches = []
        
        # 1. Match por partida (prioridad máxima)
        if acto.get('partida') and programa.get('partida'):
            score_partida, detalles = self.match_by_partida(
                acto['partida'],
                programa['partida']
            )
            if score_partida > 0:
                scores.append(score_partida)
                detalles_matches.append(detalles)
        
        # 2. Match por organismo
        if acto.get('organismo') and programa.get('organismo'):
            score_org, detalles = self.match_by_organismo(
                acto['organismo'],
                programa['organismo']
            )
            if score_org > 0:
                scores.append(score_org)
                detalles_matches.append(detalles)
        
        # 3. Match por keywords
        acto_kw = acto.get('keywords', [])
        if isinstance(acto_kw, str):
            acto_kw = [k.strip() for k in acto_kw.split(',')]
        
        programa_kw = programa.get('keywords', [])
        
        if usar_vocabulario and acto_kw:
            acto_kw = self.expandir_con_vocabulario(acto_kw)
        
        if acto_kw and programa_kw:
            score_kw, detalles = self.match_by_keywords(acto_kw, programa_kw)
            if score_kw > 0:
                scores.append(score_kw)
                detalles_matches.append(detalles)
        
        # Calcular score final (promedio ponderado)
        if not scores:
            return 0.0, 'sin_match', {}
        
        # El score más alto determina el método principal
        score_final = max(scores)
        idx_mejor = scores.index(score_final)
        metodo_principal = detalles_matches[idx_mejor].get('tipo', 'desconocido')
        
        # Detalles completos
        detalles_completos = {
            'score_final': round(score_final, 3),
            'scores_individuales': [round(s, 3) for s in scores],
            'matches': detalles_matches,
            'acto_id': acto.get('id'),
            'programa_id': programa.get('id')
        }
        
        return score_final, metodo_principal, detalles_completos
    
    def match_acto_con_programas(
        self,
        acto: Dict,
        programas: List[Dict],
        top_n: int = 3
    ) -> List[VinculoActoPresupuesto]:
        """
        Busca los mejores matches de un acto con lista de programas
        
        Args:
            acto: Diccionario con datos del acto
            programas: Lista de programas disponibles
            top_n: Cantidad de matches a retornar
        
        Returns:
            Lista de VinculoActoPresupuesto ordenados por score
        """
        vinculos = []
        
        for programa in programas:
            score, metodo, detalles = self.calcular_match_completo(acto, programa)
            
            # Solo considerar matches sobre el umbral
            if score >= self.umbral_minimo:
                vinculo = VinculoActoPresupuesto(
                    acto_id=acto.get('id', 0),
                    programa_id=programa.get('id', 0),
                    score_confianza=score,
                    metodo_matching=metodo,
                    detalles=detalles
                )
                vinculos.append(vinculo)
        
        # Ordenar por score descendente
        vinculos.sort(key=lambda v: v.score_confianza, reverse=True)
        
        return vinculos[:top_n]


# Test de ejemplo
if __name__ == "__main__":
    matcher = SemanticMatcher()
    
    # Acto de ejemplo
    acto = {
        'id': 1,
        'organismo': 'MINISTERIO DE OBRAS PÚBLICAS',
        'partida': '1.2.3.4',
        'keywords': ['obra', 'construcción', 'ruta'],
        'monto': 15000000
    }
    
    # Programas de ejemplo
    programas = [
        {
            'id': 100,
            'organismo': 'MINISTERIO DE OBRAS PÚBLICAS',
            'partida': '1.2.3.4',
            'keywords': ['infraestructura', 'vial', 'obra'],
            'descripcion': 'Infraestructura Vial Provincial'
        },
        {
            'id': 200,
            'organismo': 'MINISTERIO DE SALUD',
            'partida': '2.1.5.6',
            'keywords': ['hospital', 'salud', 'medicina'],
            'descripcion': 'Hospitales Provinciales'
        },
        {
            'id': 300,
            'organismo': 'MINISTERIO DE INFRAESTRUCTURA Y SERVICIOS PÚBLICOS',
            'partida': '1.2.4.8',
            'keywords': ['obra', 'construcción', 'servicio'],
            'descripcion': 'Obras Públicas Generales'
        }
    ]
    
    # Buscar matches
    vinculos = matcher.match_acto_con_programas(acto, programas)
    
    print("\n🔗 VÍNCULOS ENCONTRADOS:")
    print("=" * 80)
    for i, vinculo in enumerate(vinculos, 1):
        print(f"\n{i}. MATCH (Score: {vinculo.score_confianza:.3f})")
        print(f"   Método: {vinculo.metodo_matching}")
        print(f"   Programa ID: {vinculo.programa_id}")
        print(f"   Detalles: {vinculo.detalles.get('matches', [])[0] if vinculo.detalles.get('matches') else 'N/A'}")



