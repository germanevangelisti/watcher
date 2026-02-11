

# GPT-PORTAL — Watcher Governance Lab

## Propósito
Este documento fija **las anclas legales** (normas y obligaciones) que Watcher debe observar y auditar, y traduce esas obligaciones en **requisitos verificables** (checks) para guiar la planificación, el refactor y el diseño del motor de compliance.

**Idea central:** Watcher no “inventa” qué mirar: lo deriva de obligaciones explícitas de publicación/entrega de información pública y de transparencia fiscal. Esto convierte a Watcher en un sistema auditable y defendible.

---

## 1) Anclas legales del proyecto

### 1.1 Ley 25.917 (Régimen Federal de Responsabilidad Fiscal) — Art. 7 (Transparencia fiscal)
**Qué aporta a Watcher:** define el **dataset mínimo legal** que debe estar publicado en la web para Nación/Provincias/CABA y, por adhesión, para Córdoba.

**Obligaciones publicables (núcleo auditable):**
- **Presupuesto anual** (aprobado; si no, prorrogado hasta aprobación).
- **Presupuesto plurianual** (proyecciones) luego de su presentación legislativa.
- **Cuenta Anual de Inversión**.
- Con **rezago de 1 trimestre**, publicación **trimestral** de:
  - Ejecución presupuestaria (base **devengado** y base **caja**).
  - Gasto (base devengado) por **Finalidad y Función**.
  - **Stock de deuda pública** (incluida **deuda flotante**).
  - Programas multilaterales de financiamiento.
  - Pago de servicios de deuda, con detalle de **tipo de acreedor** (según corresponda).
- Información de **empleo público** con cortes al **30/6** y **31/12** (rezago 1 trimestre), con categorías (planta/contratados/equivalentes).

**Notas para diseño:**
- La norma exige **publicación en página web**. No impone explícitamente CSV/JSON/API, pero Watcher puede priorizar formatos reutilizables como “mejor práctica”.

---

### 1.2 Córdoba — Ley Provincial 10.471 (adhesión)
**Qué aporta a Watcher:** funciona como **ancla local** para exigir el paquete de responsabilidad fiscal/transparencia.

**Uso en Watcher:**
- Si un check federal (25.917 art. 7) falla en Córdoba, Watcher reporta “base legal” combinada:
  - **Ley 25.917 art. 7** + **Ley 10.471**.

---

### 1.3 Nación — Ley 27.275 (Acceso a la Información Pública)
**Qué aporta a Watcher:** marco general de **acceso** y **transparencia activa** para el Estado nacional (y como benchmark de buenas prácticas).

**Uso en Watcher:**
- Define el concepto de **transparencia activa** (publicación proactiva) y el derecho de solicitar información.
- Es útil como referencia para estandarizar “qué debería publicarse” aun cuando el foco operativo sea Córdoba.

---

### 1.4 Nación — Decreto 780/2024 (reglamentación/modificación de la Ley 27.275)
**Qué aporta a Watcher:** reglas operativas y límites (importante para anticipar **excusas** y **negativas**).

Puntos clave (impacto directo en un módulo AIP/requests o en análisis de cumplimiento):
- **Definiciones/alcance**: acota “información pública” y “documento” en ciertos supuestos.
- **Exclusiones**: deliberaciones preparatorias, papeles de trabajo y examen preliminar pueden invocarse como no públicos.
- **Requisitos formales** para solicitudes (identificación de persona humana/jurídica).
- **Excepciones** y reservas: reglas específicas (p.ej. criterios para clasificada, secretos comerciales, protección de investigaciones/denunciantes, etc.).
- **Respuesta por link**: si la info ya está publicada en un sitio oficial, se considera satisfecha la solicitud con remitir el enlace.

**Uso en Watcher:**
- Clasificar y tipificar negativas: `EXC_780_WORKING_PAPERS`, `EXC_SECURITY_INVESTIGATION`, etc.
- Si Watcher integra un “observatorio AIP”, registrar si responden con links válidos o links rotos/no descargables.

---

## 2) Traducción a requisitos verificables (Compliance Checks)

### 2.1 Principio de diseño
Cada obligación legal se modela como un **check** con:
- `legal_basis`: norma + artículo/sección.
- `expected`: frecuencia, rezago, tipo de periodo.
- `discovery`: cómo encontrar evidencia (catálogo, crawl, search).
- `extract`: cómo extraer (HTML table, PDF meta/text, descargas).
- `validate`: validadores (periodo, rezago, keywords, campos, accesibilidad).
- `evidence`: URLs, snapshots, hash de assets.

### 2.2 Checks prioritarios (Córdoba Provincia)
**Nivel CRITICAL (núcleo):**
1) **Presupuesto anual publicado**.
2) **Ejecución trimestral** con **devengado y caja** y **rezago 1 trimestre**.
3) **Deuda**: stock + **deuda flotante** con rezago.

**Nivel HIGH:**
4) **Servicios de deuda** con **tipo de acreedor**.

**Nivel MEDIUM:**
5) **Empleo público**: cortes **30/6** y **31/12** con rezago.

---

## 3) Scorecard y alertas (Watcher outputs)

### 3.1 Estados
- `PASS`: cumple.
- `WARN`: cumple parcialmente (p.ej. existe ejecución pero falta base caja).
- `FAIL`: incumplimiento.
- `UNKNOWN`: sin evidencia concluyente.

### 3.2 Scoring
- `score = Σ(weight_i * value_i) / Σ(weight_i)`
- Valores: `PASS=1`, `WARN=0.5`, `FAIL=0`.

### 3.3 Red flags automáticas
- `RF_EXEC_GAPS`: faltan ≥ 2 trimestres de ejecución.
- `RF_DEBT_OPAQUE`: deuda sin flotante o sin tipo de acreedor en servicios.
- `RF_HEADCOUNT_MISSING`: empleo público sin cortes 30/6 o 31/12.
- `RF_BUDGET_NOT_PUBLIC`: presupuesto anual no accesible.

---

## 4) Implicancias para refactor (nuevo enfoque)

### 4.1 Arquitectura lógica recomendada (módulos)
1) **Source Catalog** (por jurisdicción y tema): URLs oficiales, patrones allow/deny.
2) **Discovery Engine**: encuentra candidatos (assets/tablas/links).
3) **Extraction Pipeline**: normaliza artefactos:
   - HTML→Tabla→CSV
   - PDF→Meta/Text (+ OCR si escaneado)
   - Descargas (ZIP/PDF/XLSX)
4) **Normalization Layer**:
   - Normaliza periodos (`YYYY-Qn`, `YYYY-MM`, `cutoff_date`)
   - Mapea nomenclaturas (devengado/pagado/caja)
5) **Rules Engine** (checks): ejecuta validadores y produce status.
6) **Evidence Store**: snapshots + hashes + artefactos procesados.
7) **Scoring & Alerts**: score por tema/jurisdicción + red flags.
8) **Reporting UI/API**: dashboard y endpoints.

### 4.2 Refactor orientado a “compliance-first”
- Extraer lógica ad-hoc del scraper a un motor declarativo de checks.
- Separar “descubrimiento” de “validación”: un portal puede cambiar UI sin romper la regla.
- Tratar “periodos” como entidad de primera clase (evitar lógica hardcodeada).
- Hacer que cada check sea reproducible por evidencia (hash + snapshot + dataset).

---

## 5) Configuración sugerida (para el repo)

### 5.1 Archivos
- `config/checks.schema.json` — validación del config.
- `config/checks.json` — checks declarativos (Ley 25.917 + adhesión + observatorio 780/2024 si aplica).
- `config/sources/cordoba_prov.json` — catálogo de fuentes.

### 5.2 Estructura de resultado
Cada ejecución produce:
- `check_result`: status, score, evidencia, metadata extraída, reason, remediation.

---

## 6) Roadmap mínimo para adoptar el enfoque
1) Implementar `Source Catalog` + `Discovery` (solo Córdoba).
2) Implementar `Extraction` para:
   - HTML tables (Transparencia CBA)
   - PDF downloads (Presupuesto/Deuda/Empleo)
3) Implementar `Rules Engine` con 3 checks CRITICAL.
4) Persistencia de evidencia (hash+snapshot).
5) Score + red flags.
6) Expandir a checks HIGH/MEDIUM.
7) (Opcional) Observatorio AIP con tipificación de negativas (Decreto 780/2024).

---

## 7) Convenciones (naming)
- Checks: `RF_25917_<TOPIC>_<DETAIL>`
- Red flags: `RF_<CATEGORY>_<ISSUE>`
- Excepciones AIP: `EXC_780_<REASON>`

---

## 8) Qué NO hace Watcher (para acotar alcance)
- No asume que “si no está en CSV está mal”: lo marca como “formato no reutilizable” (mejor práctica), salvo obligación explícita.
- No reemplaza auditoría jurídica: produce evidencia y señales.