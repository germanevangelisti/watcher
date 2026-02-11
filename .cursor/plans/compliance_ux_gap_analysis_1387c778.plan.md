---
name: Compliance UX Gap Analysis
overview: Analisis completo del estado actual de Watcher vs la vision del GPT-portal.MD, con foco en construir una UX dinamica, educativa y transparente que comunique al ciudadano que se busca, que se encontro y por que importa.
todos:
  - id: compliance-models
    content: Crear modelos ComplianceCheck, CheckResult y Evidence en backend + config/checks.json con los 5 checks del GPT-portal
    status: completed
  - id: compliance-engine
    content: Implementar ComplianceEngine service con Rules Engine que ejecute checks y produzca PASS/WARN/FAIL/UNKNOWN + scoring ponderado
    status: completed
  - id: compliance-api
    content: Crear endpoints /compliance/scorecard, /compliance/checks, /compliance/checks/{id}/evidence
    status: completed
  - id: scorecard-page
    content: Crear pagina frontend /compliance con scorecard visual tipo report-card, gauge de score, y red flags de compliance
    status: completed
  - id: legal-basis-ui
    content: Crear componentes LegalBasisCard, ComplianceExplainer, MethodologyPanel para contexto educativo
    status: completed
  - id: evidence-trail
    content: Implementar Evidence Store en backend y panel de evidencia en frontend (fuente -> snapshot -> validacion -> resultado)
    status: completed
  - id: onboarding
    content: Crear OnboardingWizard y mejorar modo Ciudadano con textos explicativos y tooltips educativos
    status: completed
  - id: dashboard-integration
    content: Integrar compliance scorecard resumido en RealDashboard e InsightsPanel, vincular alertas existentes a legal_basis
    status: completed
  - id: menciones-ui
    content: Completar UI de menciones jurisdiccionales (pagina /menciones, tabs en jurisdiccion y boletin)
    status: completed
  - id: source-catalog
    content: Implementar config/sources/cordoba_prov.json y Source Catalog service para centralizar fuentes oficiales
    status: completed
isProject: false
---

