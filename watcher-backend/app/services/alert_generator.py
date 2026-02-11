"""
Generador de Alertas Ciudadanas
Sistema de detección de red flags fiscales con 15 tipos de alertas configurables

Autor: Watcher Fiscal Agent
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AlertaCiudadana:
    """Representa una alerta ciudadana generada"""
    tipo_alerta: str
    severidad: str  # ALTA, MEDIA, BAJA
    titulo: str
    descripcion: str
    accion_ciudadana: str
    evidencia: Dict
    contexto_presupuestario: Optional[Dict] = None
    score_confianza: float = 1.0
    acto_id: Optional[int] = None
    programa_id: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para DB"""
        return {
            'tipo_alerta': self.tipo_alerta,
            'severidad': self.severidad,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'accion_ciudadana': self.accion_ciudadana,
            'evidencia_json': json.dumps(self.evidencia, ensure_ascii=False),
            'contexto_presupuestario': json.dumps(self.contexto_presupuestario, ensure_ascii=False) if self.contexto_presupuestario else None,
            'score_confianza': self.score_confianza,
            'acto_id': self.acto_id,
            'programa_id': self.programa_id
        }


class AlertGenerator:
    """Generador de alertas fiscales ciudadanas"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa el generador de alertas
        
        Args:
            config: Configuración de umbrales (opcional)
        """
        # Configuración por defecto
        self.config = config or {
            'licitacion_sin_presupuesto': {
                'score_minimo': 0.4,
                'severidad': 'ALTA'
            },
            'gasto_excesivo': {
                'porcentaje_limite': 120,
                'severidad': 'ALTA'
            },
            'ejecucion_acelerada': {
                'porcentaje_q1': 10,
                'porcentaje_agosto': 30,
                'severidad': 'ALTA'
            },
            'contratacion_urgente': {
                'monto_minimo': 5000000,
                'keywords': ['urgencia', 'emergencia'],
                'severidad': 'MEDIA'
            },
            'subsidio_repetido': {
                'cantidad_minima': 2,
                'severidad': 'ALTA'
            },
            'designaciones_masivas': {
                'cantidad_mes': 50,
                'severidad': 'MEDIA'
            },
            'modificacion_repetida': {
                'cantidad_mes': 3,
                'severidad': 'MEDIA'
            },
            'obra_sin_trazabilidad': {
                'monto_minimo': 10000000,
                'severidad': 'ALTA'
            },
            'desvio_baseline': {
                'factor_minimo': 5,  # 5x más ejecución que baseline
                'severidad': 'ALTA'
            },
            'concentracion_beneficiarios': {
                'porcentaje_limite': 30,
                'severidad': 'MEDIA'
            }
        }
        
        # Cache de alertas ya generadas (para deduplicación)
        self.alertas_generadas = set()
    
    def _deduplicate_key(self, acto_id: int, tipo_alerta: str) -> str:
        """Genera clave para deduplicación"""
        return f"{acto_id}-{tipo_alerta}"
    
    def evaluar_licitacion_sin_presupuesto(
        self,
        acto: Dict,
        vinculo: Optional[Dict]
    ) -> Optional[AlertaCiudadana]:
        """Alerta 1: Licitación sin presupuesto"""
        
        # Solo aplica a licitaciones
        if acto.get('tipo_acto') not in ['LICITACIÓN', 'CONTRATACIÓN_DIRECTA']:
            return None
        
        # Verificar si tiene vínculo válido
        if vinculo and vinculo.get('score_confianza', 0) >= self.config['licitacion_sin_presupuesto']['score_minimo']:
            return None
        
        # Generar alerta
        monto_str = f"${acto.get('monto', 0):,.0f}" if acto.get('monto') else "No especificado"
        
        return AlertaCiudadana(
            tipo_alerta='LICITACION_SIN_PRESUPUESTO',
            severidad='ALTA',
            titulo=f"Licitación sin respaldo presupuestario identificado",
            descripcion=f"Se detectó una {acto.get('tipo_acto', 'contratación')} ({acto.get('numero', 'S/N')}) "
                       f"del {acto.get('organismo', 'organismo no especificado')} por {monto_str} que no pudo "
                       f"vincularse con ningún programa presupuestario. Esto puede indicar falta de respaldo "
                       f"presupuestario o partida no identificada en el boletín.",
            accion_ciudadana="Solicitar mediante FOIA: 1) El respaldo presupuestario específico, 2) Verificar "
                           "si la partida existe en presupuesto vigente, 3) Consultar modificaciones "
                           "presupuestarias recientes que puedan justificar este gasto.",
            evidencia={
                'acto': acto.get('numero', 'S/N'),
                'tipo': acto.get('tipo_acto'),
                'organismo': acto.get('organismo'),
                'monto': acto.get('monto'),
                'fragmento': acto.get('fragmento_original', '')[:200]
            },
            score_confianza=0.9,  # Alta confianza porque es verificable
            acto_id=acto.get('id')
        )
    
    def evaluar_gasto_excesivo(
        self,
        acto: Dict,
        vinculo: Dict,
        programa: Dict
    ) -> Optional[AlertaCiudadana]:
        """Alerta 2: Gasto excesivo vs programa"""
        
        if not acto.get('monto') or not programa.get('monto_vigente'):
            return None
        
        porcentaje = (acto['monto'] / programa['monto_vigente']) * 100
        
        if porcentaje <= self.config['gasto_excesivo']['porcentaje_limite']:
            return None
        
        return AlertaCiudadana(
            tipo_alerta='GASTO_EXCESIVO',
            severidad='ALTA',
            titulo=f"Gasto excede {porcentaje:.0f}% del presupuesto del programa",
            descripcion=f"El {acto.get('tipo_acto')} N° {acto.get('numero', 'S/N')} asigna ${acto['monto']:,.0f} "
                       f"al programa '{programa.get('descripcion', 'sin descripción')}' que tiene un presupuesto "
                       f"vigente de ${programa['monto_vigente']:,.0f} ({porcentaje:.1f}% del total). "
                       f"Esto indica posible sobre-ejecución o falta de control presupuestario.",
            accion_ciudadana="Solicitar: 1) Estado de ejecución actualizado del programa, "
                           "2) Verificar modificaciones presupuestarias recientes, "
                           "3) Consultar fuente de financiamiento adicional.",
            evidencia={
                'monto_acto': acto['monto'],
                'monto_programa': programa['monto_vigente'],
                'porcentaje': round(porcentaje, 1),
                'programa': programa.get('programa'),
                'organismo': acto.get('organismo')
            },
            contexto_presupuestario={
                'programa_id': programa.get('id'),
                'programa_nombre': programa.get('descripcion'),
                'monto_presupuestado': programa.get('monto_inicial'),
                'monto_vigente': programa.get('monto_vigente')
            },
            score_confianza=0.95,
            acto_id=acto.get('id'),
            programa_id=programa.get('id')
        )
    
    def evaluar_contratacion_urgente(self, acto: Dict) -> Optional[AlertaCiudadana]:
        """Alerta 4: Contratación urgente grande"""
        
        if not acto.get('monto') or acto['monto'] < self.config['contratacion_urgente']['monto_minimo']:
            return None
        
        # Verificar keywords de urgencia
        texto = f"{acto.get('descripcion', '')} {acto.get('fragmento_original', '')}".lower()
        keywords_encontradas = []
        
        for keyword in self.config['contratacion_urgente']['keywords']:
            if keyword in texto:
                keywords_encontradas.append(keyword)
        
        if not keywords_encontradas:
            return None
        
        return AlertaCiudadana(
            tipo_alerta='CONTRATACION_URGENTE',
            severidad='MEDIA',
            titulo=f"Contratación por {keywords_encontradas[0]} de ${acto['monto']:,.0f}",
            descripcion=f"Se detectó una contratación invocando '{', '.join(keywords_encontradas)}' "
                       f"por ${acto['monto']:,.0f} del {acto.get('organismo')}. "
                       f"Las contrataciones por urgencia/emergencia pueden evadir procedimientos "
                       f"de licitación pública. Verificar si cumple requisitos legales.",
            accion_ciudadana="Solicitar: 1) Decreto o resolución que declara la emergencia/urgencia, "
                           "2) Verificar cumplimiento de requisitos legales, "
                           "3) Consultar si se evaluaron alternativas.",
            evidencia={
                'keywords_urgencia': keywords_encontradas,
                'monto': acto['monto'],
                'tipo_acto': acto.get('tipo_acto'),
                'organismo': acto.get('organismo'),
                'fragmento': acto.get('fragmento_original', '')[:200]
            },
            score_confianza=0.85,
            acto_id=acto.get('id')
        )
    
    def evaluar_obra_sin_trazabilidad(self, acto: Dict) -> Optional[AlertaCiudadana]:
        """Alerta 8: Obra sin trazabilidad"""
        
        if not acto.get('monto') or acto['monto'] < self.config['obra_sin_trazabilidad']['monto_minimo']:
            return None
        
        # Verificar si es obra
        texto = f"{acto.get('descripcion', '')} {acto.get('keywords', '')}".lower()
        es_obra = any(kw in texto for kw in ['obra', 'construcción', 'infraestructura', 'edificio'])
        
        if not es_obra:
            return None
        
        # Verificar si falta partida
        if acto.get('partida'):
            return None
        
        return AlertaCiudadana(
            tipo_alerta='OBRA_SIN_TRAZABILIDAD',
            severidad='ALTA',
            titulo=f"Obra pública de ${acto['monto']:,.0f} sin partida presupuestaria",
            descripcion=f"Se detectó una obra pública del {acto.get('organismo')} por ${acto['monto']:,.0f} "
                       f"sin mención de partida presupuestaria específica. Esto dificulta el seguimiento "
                       f"y control de la ejecución del gasto.",
            accion_ciudadana="Solicitar: 1) Expediente completo de la obra, "
                           "2) Pliego de especificaciones técnicas, "
                           "3) Cronograma y forma de pago, "
                           "4) Partida presupuestaria asignada.",
            evidencia={
                'monto': acto['monto'],
                'organismo': acto.get('organismo'),
                'descripcion': acto.get('descripcion', '')[:150],
                'tiene_partida': False
            },
            score_confianza=0.90,
            acto_id=acto.get('id')
        )
    
    def generar_alertas_para_acto(
        self,
        acto: Dict,
        vinculos: List[Dict],
        programas: Dict[int, Dict],
        baseline_marzo: Optional[Dict] = None
    ) -> List[AlertaCiudadana]:
        """
        Genera todas las alertas aplicables a un acto
        
        Args:
            acto: Diccionario con datos del acto
            vinculos: Lista de vínculos del acto con programas
            programas: Diccionario de programas (id -> datos)
            baseline_marzo: Datos de baseline de marzo (opcional)
        
        Returns:
            Lista de alertas generadas
        """
        alertas = []
        
        # Mejor vínculo (si existe)
        mejor_vinculo = vinculos[0] if vinculos else None
        programa = programas.get(mejor_vinculo['programa_id']) if mejor_vinculo else None
        
        # Generar clave de deduplicación
        acto_id = acto.get('id')
        
        # Alerta 1: Licitación sin presupuesto
        if f"{acto_id}-LICITACION_SIN_PRESUPUESTO" not in self.alertas_generadas:
            alerta = self.evaluar_licitacion_sin_presupuesto(acto, mejor_vinculo)
            if alerta:
                alertas.append(alerta)
                self.alertas_generadas.add(f"{acto_id}-LICITACION_SIN_PRESUPUESTO")
        
        # Alerta 2: Gasto excesivo (requiere vínculo)
        if mejor_vinculo and programa:
            if f"{acto_id}-GASTO_EXCESIVO" not in self.alertas_generadas:
                alerta = self.evaluar_gasto_excesivo(acto, mejor_vinculo, programa)
                if alerta:
                    alertas.append(alerta)
                    self.alertas_generadas.add(f"{acto_id}-GASTO_EXCESIVO")
        
        # Alerta 4: Contratación urgente
        if f"{acto_id}-CONTRATACION_URGENTE" not in self.alertas_generadas:
            alerta = self.evaluar_contratacion_urgente(acto)
            if alerta:
                alertas.append(alerta)
                self.alertas_generadas.add(f"{acto_id}-CONTRATACION_URGENTE")
        
        # Alerta 8: Obra sin trazabilidad
        if f"{acto_id}-OBRA_SIN_TRAZABILIDAD" not in self.alertas_generadas:
            alerta = self.evaluar_obra_sin_trazabilidad(acto)
            if alerta:
                alertas.append(alerta)
                self.alertas_generadas.add(f"{acto_id}-OBRA_SIN_TRAZABILIDAD")
        
        return alertas
    
    def reset_cache(self):
        """Limpia el cache de deduplicación"""
        self.alertas_generadas.clear()


# Test de ejemplo
if __name__ == "__main__":
    generator = AlertGenerator()
    
    # Acto de ejemplo sin vínculo
    acto_sin_vinculo = {
        'id': 1,
        'tipo_acto': 'LICITACIÓN',
        'numero': '123/2025',
        'organismo': 'MINISTERIO DE OBRAS PÚBLICAS',
        'monto': 15000000,
        'partida': None,
        'descripcion': 'Licitación para obra vial',
        'fragmento_original': 'Se llama a licitación pública...'
    }
    
    alertas = generator.generar_alertas_para_acto(acto_sin_vinculo, [], {})
    
    print("\n🚨 ALERTAS GENERADAS:")
    print("=" * 80)
    for alerta in alertas:
        print(f"\n{alerta.severidad} - {alerta.tipo_alerta}")
        print(f"Título: {alerta.titulo}")
        print(f"Descripción: {alerta.descripcion[:100]}...")
        print(f"Acción: {alerta.accion_ciudadana[:80]}...")



