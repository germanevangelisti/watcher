# Definition of Done (DoD)

**Estándar del equipo** · Aplica a todas las historias de usuario salvo excepciones explícitas.

---

## ✅ Checklist de DoD

Para considerar una historia **terminada**, deben cumplirse **todos** los siguientes:

### Código
- [ ] El código compila sin errores
- [ ] Tipado estricto: sin `any` salvo excepciones justificadas con comentario `// FIXME:`
- [ ] Sin logs de debugging residuales
- [ ] Nombres de variables y funciones en inglés, documentación en español

### Testing
- [ ] Tests unitarios para la nueva funcionalidad
- [ ] Tests de borde: valores nulos, vacíos, negativos, casos límite
- [ ] Todos los tests existentes siguen pasando (sin regresiones)
- [ ] Cobertura razonable (caminos feliz + errores)

### Integración
- [ ] El código está wireado correctamente en el entry point
- [ ] Modo simulación/dry-run sigue funcionando
- [ ] Sin regresiones en funcionalidad existente

### Documentación
- [ ] `knowledgebase/current/status.md` actualizado
- [ ] Si hay nuevo concepto/arquitectura → ADR registrado
- [ ] APIs/eventos nuevos documentados

### Git
- [ ] Commits atómicos con mensajes convencionales (`feat:`, `fix:`, `test:`, `refactor:`)
- [ ] Archivos sensibles no se commitean (verificar `.gitignore`)

---

## ⚠️ Excepciones aceptables

| Excepción | Condición |
|---|---|
| Sin tests | Solo para spikes/experimentos en rama aparte (no mergear a `main`) |
| `any` en el código | Solo si es un hack temporal con ticket de seguimiento y `// FIXME:` |
| Sin documentación | Solo para refactors internos que no cambian comportamiento ni interfaz pública |

---

> *"Done means potentially shippable."*  
> Una historia terminada podría desplegarse hoy sin miedo. No dejamos cabos sueltos para "después".