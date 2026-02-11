"""
Parser Inteligente de Actos Administrativos
Extrae y clasifica actos administrativos con impacto fiscal desde boletines oficiales

Autor: Watcher Fiscal Agent
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ActoAdministrativo:
    """Representa un acto administrativo extraído"""
    tipo_acto: str  # DECRETO, RESOLUCIÓN, LICITACIÓN, DESIGNACIÓN, SUBSIDIO
    numero: Optional[str]
    fecha: Optional[datetime]
    organismo: str
    beneficiario: Optional[str]
    monto: Optional[float]
    partida: Optional[str]
    descripcion: str
    keywords: List[str]
    nivel_riesgo: str  # ALTO, MEDIO, BAJO
    fragmento_original: str
    boletin_id: Optional[int]
    pagina: Optional[int]
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para DB"""
        return {
            'tipo_acto': self.tipo_acto,
            'numero': self.numero,
            'fecha': self.fecha,
            'organismo': self.organismo,
            'beneficiario': self.beneficiario,
            'monto': self.monto,
            'partida': self.partida,
            'descripcion': self.descripcion,
            'keywords': ','.join(self.keywords),
            'nivel_riesgo': self.nivel_riesgo,
            'fragmento_original': self.fragmento_original,
            'boletin_id': self.boletin_id,
            'pagina': self.pagina
        }


class ActoAdministrativoParser:
    """Parser especializado en actos administrativos"""
    
    def __init__(self):
        # Patterns para tipos de actos
        self.tipo_patterns = {
            'DECRETO': [
                r'DECRETO\s+N[°º]?\s*(\d+/\d{4})',
                r'DECRETO\s+(\d+/\d{4})',
                r'DCTO\.?\s+N[°º]?\s*(\d+/\d{4})'
            ],
            'RESOLUCIÓN': [
                r'RESOLUCI[ÓO]N\s+N[°º]?\s*(\d+/\d{4})',
                r'RESOLUCI[ÓO]N\s+(\d+/\d{4})',
                r'RES\.?\s+N[°º]?\s*(\d+/\d{4})'
            ],
            'LICITACIÓN': [
                r'LICITACI[ÓO]N\s+P[ÚU]BLICA\s+N[°º]?\s*(\d+/\d{4})',
                r'LICITACI[ÓO]N\s+N[°º]?\s*(\d+)',
                r'LLAMADO\s+A\s+LICITACI[ÓO]N',
                r'CONCURSO\s+P[ÚU]BLICO\s+DE\s+PRECIOS'
            ],
            'DESIGNACIÓN': [
                r'DES[IÍ]GNASE',
                r'DES[IÍ]GNANSE',
                r'NOMBRAMIENTO\s+DE',
                r'CONTRATACI[ÓO]N\s+DE\s+PERSONAL'
            ],
            'SUBSIDIO': [
                r'SUBSIDIO',
                r'OT[ÓO]RGASE\s+SUBSIDIO',
                r'AYUDA\s+ECON[ÓO]MICA',
                r'APORTE\s+NO\s+REINTEGRABLE'
            ],
            'CONTRATACIÓN_DIRECTA': [
                r'CONTRATACI[ÓO]N\s+DIRECTA',
                r'ADQUISICI[ÓO]N\s+DIRECTA',
                r'SIN\s+LICITACI[ÓO]N'
            ],
            'MODIFICACIÓN_PRESUPUESTARIA': [
                r'MODIFICACI[ÓO]N\s+PRESUPUESTARIA',
                r'AMPLIACI[ÓO]N\s+DEL\s+PRESUPUESTO',
                r'REASIGNACI[ÓO]N\s+DE\s+PARTIDAS'
            ]
        }
        
        # Patterns para extracción de datos
        self.monto_patterns = [
            r'\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # $1.000.000,00
            r'PESOS\s+(\d{1,3}(?:\.\d{3})*)',  # PESOS 1.000.000
            r'SUMA\s+DE\s+\$?\s*(\d{1,3}(?:\.\d{3})*)',  # SUMA DE $1.000.000
            r'MONTO\s+DE\s+\$?\s*(\d{1,3}(?:\.\d{3})*)',  # MONTO DE $1.000.000
            r'POR\s+UN\s+IMPORTE\s+DE\s+\$?\s*(\d{1,3}(?:\.\d{3})*)'
        ]
        
        self.partida_patterns = [
            r'PARTIDA\s+(\d+\.?\d*\.?\d*\.?\d*)',
            r'PART\.?\s+(\d+\.?\d*\.?\d*\.?\d*)',
            r'INCISO\s+(\d+)',
            r'PROGRAMA\s+(\d+)'
        ]
        
        self.organismo_patterns = [
            r'MINISTERIO\s+DE\s+([^\n\.,;]+)',
            r'SECRETAR[ÍI]A\s+DE\s+([^\n\.,;]+)',
            r'DIRECCI[ÓO]N\s+GENERAL\s+DE\s+([^\n\.,;]+)',
            r'SUBSECRETAR[ÍI]A\s+DE\s+([^\n\.,;]+)',
            r'AGENCIA\s+([^\n\.,;]+)',
            r'TRIBUNAL\s+([^\n\.,;]+)'
        ]
        
        self.beneficiario_patterns = [
            r'A\s+FAVOR\s+DE\s+([^\n\.,;]+)',
            r'BENEFICIARIO:\s*([^\n\.,;]+)',
            r'ADJUDICATARIO:\s*([^\n\.,;]+)',
            r'CONTRATISTA:\s*([^\n\.,;]+)',
            r'PROVEEDOR:\s*([^\n\.,;]+)',
            r'(?:SR\.|SRA\.|SE[ÑN]OR|SE[ÑN]ORA)\s+([A-ZÁ-Ú\s\.]+)',
            r'EMPRESA\s+([A-ZÁ-Ú\s\.,]+)',
            r'COOPERATIVA\s+([A-ZÁ-Ú\s\.,]+)'
        ]
        
        # Keywords de riesgo
        self.risk_keywords = {
            'ALTO': [
                'urgencia', 'emergencia', 'excepción', 'sin licitación',
                'contratación directa', 'exclusivo', 'único proveedor',
                'decreto de necesidad', 'situación excepcional', 'sin concurso'
            ],
            'MEDIO': [
                'discrecional', 'renovación', 'prórroga', 'modificación',
                'ampliación', 'adicional', 'complementario', 'convenio marco',
                'adjudicación', 'designación'
            ],
            'BAJO': [
                'licitación pública', 'concurso', 'proceso regular',
                'marco legal', 'transparencia', 'registro público',
                'resolución', 'decreto', 'normativa'
            ]
        }
    
    def detectar_tipo_acto(self, texto: str) -> Tuple[str, Optional[str]]:
        """Detecta el tipo de acto y extrae su número"""
        texto_upper = texto.upper()
        
        for tipo, patterns in self.tipo_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, texto_upper)
                if match:
                    numero = match.group(1) if match.groups() else None
                    return tipo, numero
        
        return 'OTRO', None
    
    def extraer_monto(self, texto: str) -> Optional[float]:
        """Extrae monto del texto"""
        for pattern in self.monto_patterns:
            match = re.search(pattern, texto.upper())
            if match:
                monto_str = match.group(1)
                # Limpiar formato (remover puntos de miles, convertir coma a punto)
                monto_str = monto_str.replace('.', '').replace(',', '.')
                try:
                    return float(monto_str)
                except ValueError:
                    continue
        return None
    
    def extraer_partida(self, texto: str) -> Optional[str]:
        """Extrae partida presupuestaria"""
        texto_upper = texto.upper()
        for pattern in self.partida_patterns:
            match = re.search(pattern, texto_upper)
            if match:
                return match.group(1)
        return None
    
    def extraer_organismo(self, texto: str) -> str:
        """Extrae organismo emisor"""
        texto_upper = texto.upper()
        for pattern in self.organismo_patterns:
            match = re.search(pattern, texto_upper)
            if match:
                organismo = match.group(1).strip()
                # Limpiar caracteres extraños
                organismo = re.sub(r'\s+', ' ', organismo)
                return organismo[:100]  # Limitar longitud
        
        # Si no encuentra, retornar desconocido
        return "ORGANISMO NO ESPECIFICADO"
    
    def extraer_beneficiario(self, texto: str) -> Optional[str]:
        """Extrae beneficiario del acto"""
        texto_upper = texto.upper()
        for pattern in self.beneficiario_patterns:
            match = re.search(pattern, texto_upper)
            if match:
                beneficiario = match.group(1).strip()
                beneficiario = re.sub(r'\s+', ' ', beneficiario)
                return beneficiario[:150]
        return None
    
    def extraer_keywords(self, texto: str) -> List[str]:
        """Extrae keywords relevantes"""
        texto_upper = texto.upper()
        keywords = []
        
        # Lista de keywords a buscar
        keyword_list = [
            'OBRA', 'LICITACIÓN', 'SUBSIDIO', 'DESIGNACIÓN', 'CONTRATO',
            'ADJUDICACIÓN', 'HOSPITAL', 'ESCUELA', 'RUTA', 'CONSTRUCCIÓN',
            'SERVICIO', 'SUMINISTRO', 'MANTENIMIENTO', 'ADQUISICIÓN',
            'EMERGENCIA', 'URGENCIA', 'DIRECTA', 'PÚBLICA'
        ]
        
        for keyword in keyword_list:
            if keyword in texto_upper:
                keywords.append(keyword.lower())
        
        return list(set(keywords))  # Únicos
    
    def calcular_nivel_riesgo(self, tipo_acto: str, texto: str, monto: Optional[float]) -> str:
        """Calcula nivel de riesgo del acto"""
        texto_lower = texto.lower()
        
        # Contar keywords de cada nivel
        risk_scores = {'ALTO': 0, 'MEDIO': 0, 'BAJO': 0}
        
        for nivel, keywords in self.risk_keywords.items():
            for keyword in keywords:
                if keyword in texto_lower:
                    risk_scores[nivel] += 1
        
        # Factores adicionales de riesgo
        if monto and monto > 10000000:  # Más de 10 millones
            risk_scores['ALTO'] += 2
        
        if tipo_acto in ['CONTRATACIÓN_DIRECTA', 'SUBSIDIO']:
            risk_scores['MEDIO'] += 1
        
        if tipo_acto == 'LICITACIÓN':
            risk_scores['BAJO'] += 1
        
        # Determinar nivel final
        if risk_scores['ALTO'] > 0:
            return 'ALTO'
        elif risk_scores['MEDIO'] > risk_scores['BAJO']:
            return 'MEDIO'
        else:
            return 'BAJO'
    
    def parse_acto(self, texto: str, boletin_id: Optional[int] = None, pagina: Optional[int] = None) -> Optional[ActoAdministrativo]:
        """Parsea un fragmento de texto y extrae acto administrativo"""
        # Detectar tipo de acto
        tipo_acto, numero = self.detectar_tipo_acto(texto)
        
        # Si no es un acto reconocido, retornar None
        if tipo_acto == 'OTRO':
            return None
        
        # Extraer datos
        monto = self.extraer_monto(texto)
        partida = self.extraer_partida(texto)
        organismo = self.extraer_organismo(texto)
        beneficiario = self.extraer_beneficiario(texto)
        keywords = self.extraer_keywords(texto)
        nivel_riesgo = self.calcular_nivel_riesgo(tipo_acto, texto, monto)
        
        # Crear descripción resumida
        descripcion = texto[:200].strip() + "..." if len(texto) > 200 else texto.strip()
        
        # Crear acto
        acto = ActoAdministrativo(
            tipo_acto=tipo_acto,
            numero=numero,
            fecha=None,  # Se puede extraer del boletin
            organismo=organismo,
            beneficiario=beneficiario,
            monto=monto,
            partida=partida,
            descripcion=descripcion,
            keywords=keywords,
            nivel_riesgo=nivel_riesgo,
            fragmento_original=texto[:500],  # Guardar fragmento
            boletin_id=boletin_id,
            pagina=pagina
        )
        
        return acto
    
    def parse_boletin(self, texto: str, boletin_id: Optional[int] = None) -> List[ActoAdministrativo]:
        """Parsea un boletín completo y extrae todos los actos"""
        actos = []
        
        # Dividir en bloques por saltos de línea
        bloques = re.split(r'\n{2,}', texto)
        
        for i, bloque in enumerate(bloques):
            # Solo procesar bloques con contenido significativo
            if len(bloque) < 50:  # Muy corto, probablemente no es un acto
                continue
            
            acto = self.parse_acto(bloque, boletin_id=boletin_id, pagina=None)
            if acto:
                actos.append(acto)
        
        return actos


# Ejemplo de uso
if __name__ == "__main__":
    parser = ActoAdministrativoParser()
    
    # Texto de ejemplo
    texto_ejemplo = """
    DECRETO N° 1234/2025
    
    MINISTERIO DE OBRAS PÚBLICAS
    
    ARTÍCULO 1°.- Apruébase la contratación directa por un monto de $15.000.000,00
    (PESOS QUINCE MILLONES) a favor de la empresa CONSTRUCTORA XYZ S.A. para la 
    realización de obras de emergencia en la Ruta Provincial 19, con cargo a la 
    Partida 1.2.3.4.5.
    
    ARTÍCULO 2°.- La presente contratación se realiza en virtud de la situación de
    urgencia declarada por Resolución 567/2025.
    """
    
    acto = parser.parse_acto(texto_ejemplo)
    
    if acto:
        print("Acto extraído:")
        print(f"  Tipo: {acto.tipo_acto}")
        print(f"  Número: {acto.numero}")
        print(f"  Organismo: {acto.organismo}")
        print(f"  Monto: ${acto.monto:,.2f}" if acto.monto else "  Monto: No especificado")
        print(f"  Partida: {acto.partida}")
        print(f"  Beneficiario: {acto.beneficiario}")
        print(f"  Riesgo: {acto.nivel_riesgo}")
        print(f"  Keywords: {', '.join(acto.keywords)}")



