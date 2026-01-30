# Catálogo de Alertas Ciudadanas - Watcher Fiscal

**Versión:** 1.0.0  
**Fecha:** 6 de Noviembre 2025

---

## 📋 Tipos de Alertas Implementadas

### 1. LICITACIÓN SIN PRESUPUESTO
**Severidad:** ALTA  
**Condición:** Acto tipo "licitación" sin vínculo con programa (score < 0.4)

**Descripción:**  
Se detectó una licitación pública o contratación que no puede vincularse con ningún programa presupuestario existente, lo que indica posible falta de respaldo presupuestario o partida no identificada.

**Acción Ciudadana:**
- Solicitar mediante FOIA el respaldo presupuestario específico
- Verificar si la partida existe en presupuesto vigente
- Consultar modificaciones presupuestarias recientes

**Ejemplo:**
```
Licitación N° 123/2025 para obra vial por $50M sin programa identificado
```

---

### 2. GASTO EXCESIVO VS PROGRAMA
**Severidad:** ALTA  
**Condición:** Monto > 120% del monto programa vigente

**Descripción:**  
Un acto administrativo asigna un monto que excede significativamente el presupuesto aprobado para el programa, indicando posible sobre-ejecución o falta de control presupuestario.

**Acción Ciudadana:**
- Solicitar estado de ejecución actualizado del programa
- Verificar si hubo modificaciones presupuestarias
- Consultar fuente de financiamiento adicional

**Ejemplo:**
```
Decreto adjudica $60M a programa con presupuesto de $45M (133% de ejecución)
```

---

### 3. EJECUCIÓN ACELERADA
**Severidad:** ALTA  
**Condición:** Programa con <10% ejecutado en marzo + >30% en agosto

**Descripción:**  
Un programa que ejecutó muy poco en el primer trimestre muestra ejecución acelerada en agosto, lo que puede indicar concentración atípica de gastos o ejecución de emergencia.

**Acción Ciudadana:**
- Solicitar cronograma de ejecución original
- Verificar justificación de la aceleración
- Consultar si hubo modificación de metas

**Ejemplo:**
```
Programa ejecutó 5% en Q1 y 40% en agosto (concentración de 8x en 5 meses)
```

---

### 4. CONTRATACIÓN URGENTE GRANDE
**Severidad:** MEDIA  
**Condición:** Keywords "urgencia"/"emergencia" + monto >$5M

**Descripción:**  
Contratación invocando urgencia o emergencia por montos significativos, lo que puede indicar uso discrecional de excepciones a licitación pública.

**Acción Ciudadana:**
- Solicitar decreto o resolución que declara la emergencia
- Verificar si la situación cumple requisitos legales de urgencia
- Consultar si se evaluaron alternativas

**Ejemplo:**
```
Contratación directa por emergencia de $8M sin licitación
```

---

### 5. SUBSIDIO REPETIDO
**Severidad:** ALTA  
**Condición:** Mismo beneficiario >2 subsidios sin mención "aprobación rendición"

**Descripción:**  
Un beneficiario recibe múltiples subsidios sin que los boletines mencionen aprobación de rendición de cuentas de subsidios anteriores.

**Acción Ciudadana:**
- Solicitar rendiciones de cuenta de subsidios previos
- Verificar cumplimiento de objetivos anteriores
- Consultar normativa de otorgamiento de subsidios

**Ejemplo:**
```
Asociación X recibió 3 subsidios ($2M, $1.5M, $3M) sin mencionar rendiciones
```

---

### 6. DESIGNACIONES MASIVAS
**Severidad:** MEDIA  
**Condición:** Organismo >50 designaciones en agosto

**Descripción:**  
Un organismo designa cantidad inusualmente alta de personal en un mes, lo que puede indicar aumento no planificado de planta o contrataciones políticas.

**Acción Ciudadana:**
- Solicitar justificación de necesidad de personal
- Verificar si están en presupuesto de personal
- Consultar si hubo concursos públicos

**Ejemplo:**
```
Ministerio designó 75 agentes en agosto (vs promedio de 10/mes)
```

---

### 7. MODIFICACIÓN PRESUPUESTARIA REPETIDA
**Severidad:** MEDIA  
**Condición:** Mismo programa >3 modificaciones en mes

**Descripción:**  
Un programa muestra múltiples modificaciones presupuestarias en corto período, indicando posible falta de planificación o reasignaciones discrecionales.

**Acción Ciudadana:**
- Solicitar detalle de modificaciones y justificaciones
- Verificar coherencia con plan original
- Consultar impacto en metas del programa

**Ejemplo:**
```
Programa 456 tuvo 5 modificaciones en agosto (aumento y reasignación de partidas)
```

---

### 8. OBRA SIN TRAZABILIDAD
**Severidad:** ALTA  
**Condición:** Obra >$10M sin partida específica

**Descripción:**  
Obra pública por monto significativo sin mención de partida presupuestaria específica, dificultando seguimiento y control.

**Acción Ciudadana:**
- Solicitar expediente completo de la obra
- Verificar pliego de especificaciones técnicas
- Consultar cronograma y forma de pago

**Ejemplo:**
```
Obra "Construcción Hospital" por $25M sin indicar partida presupuestaria
```

---

### 9. DESVÍO VS BASELINE
**Severidad:** ALTA  
**Condición:** Programa ejecutó 5% marzo, 40% agosto

**Descripción:**  
Desvío significativo respecto al baseline de marzo, indicando cambio drástico en velocidad de ejecución comparado con primer trimestre.

**Acción Ciudadana:**
- Solicitar explicación del cambio en ritmo de ejecución
- Verificar si hubo modificación de cronograma
- Consultar si se mantienen metas originales

**Ejemplo:**
```
Programa con 5% ejecutado en Q1 alcanzó 45% en agosto (desvío de 8x)
```

---

### 10. CONCENTRACIÓN DE BENEFICIARIOS
**Severidad:** MEDIA  
**Condición:** 1 beneficiario >30% del presupuesto programa

**Descripción:**  
Un solo beneficiario concentra porcentaje significativo del presupuesto de un programa, lo que puede indicar falta de competencia o direccionamiento.

**Acción Ciudadana:**
- Solicitar listado completo de beneficiarios del programa
- Verificar si hubo proceso competitivo
- Consultar criterios de asignación

**Ejemplo:**
```
Empresa ABC recibió $15M de los $40M del programa (37.5% concentración)
```

---

### 11. SIN LICITACIÓN RECURRENTE
**Severidad:** MEDIA  
**Condición:** Mismo beneficiario >2 contrataciones directas en 3 meses

**Descripción:**  
Un proveedor recibe múltiples contrataciones directas en corto período, evitando sistemáticamente licitación pública.

**Acción Ciudadana:**
- Solicitar justificación de cada contratación directa
- Verificar si los montos son fraccionados para evadir licitación
- Consultar precios de referencia

**Ejemplo:**
```
Proveedor XYZ: 4 contrataciones directas ($3M, $2.5M, $4M, $1M) en 3 meses
```

---

### 12. PAGO SIN DECRETO/RESOLUCIÓN
**Severidad:** ALTA  
**Condición:** Monto >$1M sin número de acto administrativo

**Descripción:**  
Pago o transferencia significativa sin mención de decreto o resolución que lo respalde, indicando posible falta de respaldo legal.

**Acción Ciudadana:**
- Solicitar decreto o resolución que autoriza el gasto
- Verificar competencia del funcionario autorizante
- Consultar si está en plan anual de contrataciones

**Ejemplo:**
```
Transferencia de $3M sin mencionar decreto o resolución autorizante
```

---

### 13. VENCIMIENTO DE PLAZOS
**Severidad:** MEDIA  
**Condición:** Prórroga de contrato >2 veces mismo beneficiario

**Descripción:**  
Contrato prorrogado múltiples veces al mismo proveedor, indicando posible continuidad sin nueva licitación.

**Acción Ciudadana:**
- Solicitar contrato original y prórrogas
- Verificar si monto acumulado excede umbral de licitación
- Consultar evaluación de desempeño

**Ejemplo:**
```
Contrato de limpieza prorrogado 3 veces (acumulado $8M en 2 años)
```

---

### 14. ADJUDICACIÓN A ÚNICO OFERENTE
**Severidad:** MEDIA  
**Condición:** Licitación con 1 solo oferente + monto >$2M

**Descripción:**  
Licitación con un solo oferente por monto significativo, indicando posible falta de competencia o pliegos restrictivos.

**Acción Ciudadana:**
- Solicitar pliego de bases y condiciones
- Verificar requisitos técnicos no sean restrictivos
- Consultar si hubo difusión adecuada

**Ejemplo:**
```
Licitación por $5M adjudicada a único oferente (sin competencia)
```

---

### 15. GASTO SIN META IDENTIFICABLE
**Severidad:** MEDIA  
**Condición:** Programa sin descripción clara de meta + ejecución >$10M

**Descripción:**  
Programa ejecuta montos significativos sin que sea claro cuál es el objetivo o meta a cumplir, dificultando evaluación de resultados.

**Acción Ciudadana:**
- Solicitar plan operativo anual del programa
- Verificar metas físicas y financieras
- Consultar indicadores de gestión

**Ejemplo:**
```
Programa "Desarrollo Comunitario" ejecutó $15M sin metas cuantificables
```

---

## 📊 Configuración de Umbrales

Los umbrales son configurables en `/watcher-doc/reglas_vinculacion.yaml`:

```yaml
alertas:
  licitacion_sin_presupuesto:
    score_minimo: 0.4
    severidad: ALTA
    
  gasto_excesivo:
    porcentaje_limite: 120
    severidad: ALTA
    
  ejecucion_acelerada:
    porcentaje_q1: 10
    porcentaje_agosto: 30
    severidad: ALTA
    
  contratacion_urgente:
    monto_minimo: 5000000
    keywords: ["urgencia", "emergencia"]
    severidad: MEDIA
    
  designaciones_masivas:
    cantidad_mes: 50
    severidad: MEDIA
    
  modificacion_repetida:
    cantidad_mes: 3
    severidad: MEDIA
```

---

## 🎯 Uso del Sistema de Alertas

### Generar Alertas para Actos Existentes
```python
from app.services.alert_generator import AlertGenerator

generator = AlertGenerator()
alertas = await generator.generar_alertas_actos()
```

### Filtrar por Severidad
```python
alertas_altas = await generator.filtrar_por_severidad("ALTA")
```

### Exportar Reporte
```python
from app.services.report_generator import CitizenReportGenerator

report_gen = CitizenReportGenerator()
report_gen.generate_alert_report(alertas, formato="pdf")
```

---

## 📈 Métricas de Alertas

- **Precisión Objetivo:** <10% falsos positivos
- **Cobertura:** 100% de casos ALTO detectados
- **Tiempo Respuesta:** <1 segundo por alerta
- **Deduplicación:** Automática por acto_id + tipo_alerta

---

**Mantenido por:** Watcher Fiscal Team  
**Última Actualización:** 6 de Noviembre 2025  
**Próxima Revisión:** Milestone 2



