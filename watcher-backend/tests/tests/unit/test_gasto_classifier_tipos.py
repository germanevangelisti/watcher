"""Tests for the M8 axes of app/services/gasto_classifier.py.

Tres ejes, independientes a propósito:

- `etapa_gasto` — *cuándo* en el ciclo del gasto (llamado, adjudicación, pago).
- `tipo_gasto` — *por qué figura* se mueve el dinero (licitación, concurso de
  precios, compra directa, contratación, subsidio/transferencia).
- `objeto` — *qué* se compra o se hace (obra, bien, servicio, transferencia).

El tercero se separó después de que el PO etiquetara a mano y apareciera el
desacuerdo: un acto que dice "Licitación para la obra de drenaje" es las dos
cosas, y con un solo campo había que elegir.  Ninguna de las dos lecturas era un
error del clasificador; era una pregunta sin cerrar.

Run from watcher-backend/:
    .\\.venv\\Scripts\\python.exe -m pytest tests/tests/unit/test_gasto_classifier_tipos.py -v
"""

import pytest
from app.services.gasto_classifier import (
    ETAPA_ADJUDICACION,
    NIVEL_COMUNAL,
    NIVEL_DESCONOCIDO,
    NIVEL_MUNICIPAL,
    NIVEL_PROVINCIAL,
    NIVELES,
    OBJETO_BIEN,
    OBJETO_NO_APLICA,
    OBJETO_OBRA,
    OBJETO_OTRO,
    OBJETO_SERVICIO,
    OBJETO_TRANSFERENCIA,
    OBJETOS,
    TIPO_COMPRA_DIRECTA,
    TIPO_CONCURSO_PRECIOS,
    TIPO_CONTRATACION,
    TIPO_LICITACION,
    TIPO_NO_ES_GASTO,
    TIPO_OTRO,
    TIPO_SUBASTA_ELECTRONICA,
    TIPO_SUBSIDIO_TRANSFERENCIA,
    TIPOS_GASTO,
    classify_gasto,
    classify_objeto,
    municipio_de_organismo,
    texto_de_acto,
)

# ═══════════════════════════════════════════════════════════════════════════════
# tipo_gasto — la figura (procedimiento), no el objeto
# ═══════════════════════════════════════════════════════════════════════════════

CASOS_FIGURA = [
    # El objeto ya no compite acá: esta licitación de obra es `licitacion`.
    (
        {"tipo_acto": "licitacion", "fragmento": "LICITACION PUBLICA N 12/2026 - Obra de pavimento"},
        "4",
        TIPO_LICITACION,
    ),
    ({"tipo_acto": "otro", "descripcion": "Concurso de Precios N° 5/2026"}, "4", TIPO_CONCURSO_PRECIOS),
    # El boletín escribe "Concurso Privado de Precios" y no estaba contemplado.
    (
        {"tipo_acto": "otro", "descripcion": "ADJUDÍCASE el Concurso Privado de Precios No 03/2026"},
        "5",
        TIPO_CONCURSO_PRECIOS,
    ),
    (
        {"tipo_acto": "otro", "descripcion": "Compulsa Abreviada N° 31/2026 provisión de insumos"},
        "4",
        TIPO_CONCURSO_PRECIOS,
    ),
    # La subasta electrónica es su propia figura (Ley 10.155), no un concurso de
    # precios: el portal de compras la declara como tipo de proceso aparte.
    (
        {
            "tipo_acto": "licitacion",
            "fragmento": "EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA S.A.U. SUBASTA ELECTRONICA INVERSA No 1463",
        },
        "4",
        TIPO_SUBASTA_ELECTRONICA,
    ),
    (
        {"tipo_acto": "otro", "descripcion": "Compra Directa N° 12/2026 - adquisición de repuestos"},
        "4",
        TIPO_COMPRA_DIRECTA,
    ),
    ({"tipo_acto": "licitacion", "descripcion": "Llamado a Licitación Pública N° 44/2026"}, "4", TIPO_LICITACION),
    # La figura explícita gana sobre el `contrato|convenio` que todo pliego menciona.
    (
        {"tipo_acto": "licitacion", "fragmento": "LICITACION PUBLICA N 7/2026 - el contrato se regirá por el pliego"},
        "4",
        TIPO_LICITACION,
    ),
    (
        {"tipo_acto": "otro", "descripcion": "Apruébase el convenio de cooperación con el municipio"},
        "1",
        TIPO_CONTRATACION,
    ),
    (
        {"tipo_acto": "subsidio", "descripcion": "Subsidio para la obra de pavimento"},
        "4",
        TIPO_SUBSIDIO_TRANSFERENCIA,
    ),
    # Mueve plata, no tenía keyword de etapa y la puerta de gasto lo perdía.
    (
        {"tipo_acto": "otro", "descripcion": "OTÓRGUENSE un incentivo educativo, a la escuela primaria"},
        "5",
        TIPO_SUBSIDIO_TRANSFERENCIA,
    ),
    # Gasto con monto y sin figura reconocible: `otro`, nunca None.
    (
        {"tipo_acto": "otro", "descripcion": "Autorízase el pago de la suma de $1.000.000 a la firma X"},
        "1",
        TIPO_OTRO,
    ),
]


class TestFigura:
    @pytest.mark.parametrize("acto,section,esperado", CASOS_FIGURA)
    def test_figura(self, acto, section, esperado):
        assert classify_gasto(acto, section=section).tipo_gasto == esperado

    @pytest.mark.parametrize("acto,section,esperado", CASOS_FIGURA)
    def test_figura_en_el_enum(self, acto, section, esperado):
        assert esperado in TIPOS_GASTO

    def test_incentivo_entra_al_gasto_publico(self):
        """La falta que el juez y las etiquetas del PO marcaron al mismo tiempo."""
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "OTÓRGUENSE un incentivo educativo"}, section="5"
        )
        assert result.is_gasto_publico is True

    def test_adjudicacion_no_es_figura_sino_etapa(self):
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Adjudícase la Licitación Pública N° 9/2026"}, section="4"
        )
        assert result.etapa_gasto == ETAPA_ADJUDICACION
        assert result.tipo_gasto == TIPO_LICITACION


# ═══════════════════════════════════════════════════════════════════════════════
# objeto — qué se compra o se hace
# ═══════════════════════════════════════════════════════════════════════════════

CASOS_OBJETO = [
    (
        {"tipo_acto": "licitacion", "fragmento": "LICITACION PUBLICA N 12/2026 - Obra de pavimento"},
        OBJETO_OBRA,
    ),
    # "limpieza" pelado matcheaba una compra de insumos como servicio de limpieza.
    (
        {"tipo_acto": "licitacion", "descripcion": "ADQUISICIÓN DE ELEMENTOS DE LIMPIEZA CON DESTINO A LOGÍSTICA"},
        OBJETO_BIEN,
    ),
    (
        {"tipo_acto": "otro", "descripcion": "Contrátase el servicio de limpieza de dependencias"},
        OBJETO_SERVICIO,
    ),
    ({"tipo_acto": "subsidio", "descripcion": "Subsidio no reintegrable a bomberos"}, OBJETO_TRANSFERENCIA),
    # Una obra de mantenimiento se compra como obra.
    ({"tipo_acto": "licitacion", "descripcion": "Obra de mantenimiento del edificio escolar"}, OBJETO_OBRA),
    # "mano de obra" es un componente del precio, no una obra.
    (
        {"tipo_acto": "licitacion", "fragmento": "LICITACION PUBLICA N 3/2026 - el precio incluye mano de obra"},
        OBJETO_OTRO,
    ),
    ({"tipo_acto": "licitacion", "descripcion": "Licitación pública para el servicio de vigilancia"}, OBJETO_SERVICIO),
    ({"tipo_acto": "otro", "descripcion": "Remate de un inmueble"}, OBJETO_NO_APLICA),
]


class TestObjeto:
    @pytest.mark.parametrize("acto,esperado", CASOS_OBJETO)
    def test_objeto(self, acto, esperado):
        assert classify_gasto(acto, section="4").objeto == esperado

    @pytest.mark.parametrize("acto,esperado", CASOS_OBJETO)
    def test_objeto_en_el_enum(self, acto, esperado):
        assert esperado in OBJETOS

    def test_los_dos_ejes_conviven(self):
        """El caso que motivó el tercer eje: una licitación de obra."""
        result = classify_gasto(
            {
                "tipo_acto": "licitacion",
                "fragmento": "Licitación para la implementación de equipos para la obra de drenaje pluvial",
            },
            section="4",
        )
        assert result.tipo_gasto == TIPO_LICITACION
        assert result.objeto == OBJETO_OBRA

    def test_no_es_gasto_no_tiene_objeto(self):
        for acto, section in (
            ({"tipo_acto": "otro", "descripcion": "Remate judicial de un inmueble"}, "2"),
            ({"tipo_acto": "otro", "descripcion": "Aumento de capital social a $50.000.000"}, "3"),
            ({"tipo_acto": "decreto", "descripcion": "Compensación de partidas presupuestarias"}, "1"),
            ({"tipo_acto": "designacion", "descripcion": "Desígnase director"}, "1"),
        ):
            result = classify_gasto(acto, section=section)
            assert result.tipo_gasto == TIPO_NO_ES_GASTO
            assert result.objeto == OBJETO_NO_APLICA

    def test_otro_y_no_es_gasto_llevan_motivo(self):
        """La invariante de M8: lo no clasificable se explica, no se descarta."""
        for acto, section in (
            ({"tipo_acto": "otro", "descripcion": "Autorízase el pago de $1.000.000"}, "1"),
            ({"tipo_acto": "otro", "descripcion": "Remate de bienes"}, "2"),
        ):
            result = classify_gasto(acto, section=section)
            assert result.tipo_gasto_motivo
            assert result.as_analisis_fields()["gasto_motivo"]


# ═══════════════════════════════════════════════════════════════════════════════
# objeto — WCL1: racionamiento/alimentos y objetos recurrentes del portal
# ═══════════════════════════════════════════════════════════════════════════════

# El clasificador de objeto dejaba 93 de las 153 compras 2026 de MuniCompras en
# `otro`, y la compra 12387 ("servicio de racionamiento en cocido") entre ellas.
# Estos casos salen de filas **reales** del corpus, no de ejemplos inventados.

CASOS_OBJETO_WCL1 = [
    # ── Comida servida (12387, 8178, 8196) ─────────────────────────────────────
    (
        {"tipo_acto": "licitacion", "descripcion": "SERVICIO DE RACIONAMIENTO EN COCIDO"},
        OBJETO_SERVICIO,
    ),
    (
        {
            "tipo_acto": "licitacion",
            "descripcion": (
                "CONTRATACION DE SERVICIO DE RACIONAMIENTO EN COCIDO PARA AGENTES QUE "
                "PRESTAN SERVICIOS EN DEPARTAMENTO CAPITAL Y ASPIRANTES"
            ),
        },
        OBJETO_SERVICIO,
    ),
    ({"tipo_acto": "licitacion", "descripcion": "Servicio de viandas para el personal"}, OBJETO_SERVICIO),
    ({"tipo_acto": "licitacion", "descripcion": "Provisión de refrigerio para la jornada"}, OBJETO_SERVICIO),
    ({"tipo_acto": "licitacion", "descripcion": "Servicio de alimentación para escuelas"}, OBJETO_SERVICIO),
    ({"tipo_acto": "licitacion", "descripcion": "Servicio de coffee break"}, OBJETO_SERVICIO),
    # El alimento puede ser un medicamento: "parenteral" no es comida servida.
    (
        {"tipo_acto": "licitacion", "descripcion": "BOLSAS DE ALIMENTACION PARENTERAL MAGISTRAL"},
        OBJETO_BIEN,
    ),
    # ── Obra sin decir "obra" ──────────────────────────────────────────────────
    (
        {
            "tipo_acto": "licitacion",
            "descripcion": "SERVICIO DE REPARACIÓN EDILICIA - ESCUELA MUNICIPAL SAUL TABORDA",
        },
        OBJETO_OBRA,
    ),
    (
        {"tipo_acto": "licitacion", "descripcion": "REACONDICIONAMIENTO EDILICIO EN DISTRITO CRUZ DEL EJE"},
        OBJETO_OBRA,
    ),
    (
        {
            "tipo_acto": "licitacion",
            "descripcion": (
                "REPARACIÓN, REFUNCIONALIZACIÓN Y PUESTA EN VALOR DE LA INFRAESTRUCTURA EXISTENTE"
            ),
        },
        OBJETO_OBRA,
    ),
    (
        {
            "tipo_acto": "licitacion",
            "descripcion": (
                "MEJORAMIENTO DEL SISTEMA DE ALUMBRADO PÚBLICO E INSTALACION DE LUMINARIAS LED"
            ),
        },
        OBJETO_OBRA,
    ),
    (
        {"tipo_acto": "licitacion", "descripcion": "VEREDA PERIMETRAL ESCUELA MUNICIPAL"},
        OBJETO_OBRA,
    ),
    (
        {"tipo_acto": "licitacion", "descripcion": "DEMARCACIÓN VIAL HORIZONTAL EN LA CIUDAD"},
        OBJETO_OBRA,
    ),
    # ── Bienes que el portal nombra por su especie ─────────────────────────────
    ({"tipo_acto": "licitacion", "descripcion": "INDUMENTARIA Y CALZADO DE TRABAJO"}, OBJETO_BIEN),
    ({"tipo_acto": "licitacion", "descripcion": "INSUMOS ODONTOLÓGICOS"}, OBJETO_BIEN),
    (
        {"tipo_acto": "licitacion", "descripcion": "MEDICAMENTOS Y RELACIONADOS - ANTIBIÓTICOS"},
        OBJETO_BIEN,
    ),
    ({"tipo_acto": "licitacion", "descripcion": "BOMBAS SUMERGIBLES Y ELECTROBOMBA"}, OBJETO_BIEN),
    ({"tipo_acto": "licitacion", "descripcion": "UN (1) VEHICULO UTILITARIO"}, OBJETO_BIEN),
    # ── Servicios que el título nombra con la fórmula "servicio de X" ─────────
    (
        {
            "tipo_acto": "licitacion",
            "descripcion": "SERVICIO DE DISTRIBUCIÓN DOMICILIARIA DE CORRESPONDENCIA",
        },
        OBJETO_SERVICIO,
    ),
    (
        {"tipo_acto": "licitacion", "descripcion": "SERVICIO INTEGRAL DE CONTROL DE PLAGAS"},
        OBJETO_SERVICIO,
    ),
    # El servicio gana sobre el bien que menciona: es una póliza, no un vehículo.
    (
        {
            "tipo_acto": "licitacion",
            "descripcion": (
                "SERVICIO DE COBERTURA DE SEGURO PARA LOS VEHICULOS OFICIALES DEL ENTE"
            ),
        },
        OBJETO_SERVICIO,
    ),
    (
        {
            "tipo_acto": "licitacion",
            "descripcion": (
                "CONTRATACION DEL SERVICIO DE MANO DE OBRA PARA ALBAÑILERIA, PINTURERIA Y HERRERIA"
            ),
        },
        OBJETO_SERVICIO,
    ),
    # ── Negativos: la fórmula no siempre nombra un servicio ───────────────────
    # La deuda no se compra.
    (
        {"tipo_acto": "licitacion", "descripcion": "Servicio de la deuda pública 2026"},
        OBJETO_OTRO,
    ),
    # "Servicio de provisión de bienes" es una compra de bienes.
    (
        {
            "tipo_acto": "licitacion",
            "descripcion": "SERVICIO DE PROVISION DE REACTIVOS, CONTROLES Y CALIBRADORES",
        },
        OBJETO_BIEN,
    ),
]


class TestObjetoAmpliado:
    @pytest.mark.parametrize("acto,esperado", CASOS_OBJETO_WCL1)
    def test_objeto(self, acto, esperado):
        assert classify_gasto(acto, section="4").objeto == esperado

    @pytest.mark.parametrize("acto,esperado", CASOS_OBJETO_WCL1)
    def test_objeto_en_el_enum(self, acto, esperado):
        assert esperado in OBJETOS

    def test_servicio_generico_solo_mira_el_titulo(self):
        """Una mención en el cuerpo no convierte una compra en servicio.

        Medido: el fragmento de la compra 6541 trae el objeto de un acto vecino
        ("SERVICIO DE PREPARACIÓN DE COMIDAS") y convertía en servicio una
        adquisición de transformadores.
        """
        result = classify_gasto(
            {
                "tipo_acto": "licitacion",
                "descripcion": "ADQUISICION TRANSFORMADOR DE POTENCIA 13,2/34,65KV",
                "fragmento": "OBJETO: SERVICIO DE PREPARACION DE COMIDAS Y COMEDOR PARA EL PERSONAL",
            },
            section="4",
        )
        assert result.objeto == OBJETO_BIEN

    def test_mano_de_obra_no_es_obra(self):
        """Sigue sin ser obra aunque el texto traiga "reparación" cerca."""
        result = classify_gasto(
            {"tipo_acto": "licitacion", "descripcion": "el precio incluye mano de obra"},
            section="4",
        )
        assert result.objeto == OBJETO_OTRO

    def test_clasifica_el_texto_del_portal_sin_tipo_de_acto(self):
        """El portal conoce la figura y sólo pide el otro eje."""
        assert classify_objeto("subasta_electronica", "SERVICIO DE RACIONAMIENTO EN COCIDO") == (
            OBJETO_SERVICIO
        )
        assert classify_objeto("concurso_precios", "INSUMOS ODONTOLOGICOS") == OBJETO_BIEN

    def test_texto_de_acto_arma_el_mismo_haystack(self):
        assert "pavimento" in texto_de_acto({"fragmento": "Obra de pavimento"}).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# nivel
# ═══════════════════════════════════════════════════════════════════════════════

class TestNivel:
    def test_seccion_municipal(self):
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Ordenanza tarifaria"}, section="5"
        )
        assert result.nivel == NIVEL_MUNICIPAL

    def test_comuna_gana_sobre_municipio(self):
        result = classify_gasto(
            {
                "tipo_acto": "otro",
                "descripcion": "Llamado a licitación",
                "organismo": "COMUNA DE LOS REARTES",
            },
            section="5",
        )
        assert result.nivel == NIVEL_COMUNAL

    def test_provincial_por_defecto_en_seccion_de_gasto(self):
        result = classify_gasto(
            {"tipo_acto": "licitacion", "descripcion": "Licitación pública"}, section="4"
        )
        assert result.nivel == NIVEL_PROVINCIAL

    def test_judicial_sin_senal_de_nivel_no_se_inventa(self):
        """Un edicto sin organismo es `desconocido`, no `provincial`."""
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Cítase y emplázase"}, section="2"
        )
        assert result.nivel == NIVEL_DESCONOCIDO

    def test_nivel_siempre_en_el_enum(self):
        for acto, section in (
            ({"tipo_acto": "licitacion", "descripcion": "Licitación"}, "4"),
            ({"tipo_acto": "otro", "descripcion": "Ordenanza"}, "5"),
            ({"tipo_acto": "otro", "descripcion": "Cítase y emplázase"}, "2"),
        ):
            assert classify_gasto(acto, section=section).nivel in NIVELES

    def test_edicto_municipal_en_seccion_judicial_es_de_los_dos_ejes(self):
        """Los ejes son independientes: municipal acá, fuera_presupuesto allá."""
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Edicto de la Municipalidad de Carrilobo"}, section="2"
        )
        assert result.nivel == NIVEL_MUNICIPAL
        assert result.jurisdiccion == "fuera_presupuesto"
        assert result.tipo_gasto == TIPO_NO_ES_GASTO


# ═══════════════════════════════════════════════════════════════════════════════
# municipio
# ═══════════════════════════════════════════════════════════════════════════════

class TestMunicipio:
    @pytest.mark.parametrize(
        "organismo,esperado",
        [
            ("MUNICIPALIDAD DE CARRILOBO", "Carrilobo"),
            ("Municipalidad de San Francisco", "San Francisco"),
            ("COMUNA DE LOS REARTES", "Los Reartes"),
            ("Intendente Municipal de Río Ceballos", "Río Ceballos"),
            ("Concejo Deliberante de Villa María", "Villa María"),
        ],
    )
    def test_extrae_el_nombre(self, organismo, esperado):
        assert municipio_de_organismo(organismo) == esperado

    @pytest.mark.parametrize(
        "organismo",
        [None, "", "ACIF", "MINISTERIO DE DESARROLLO SOCIAL", "EPEC S.A.U."],
    )
    def test_sin_senal_devuelve_none(self, organismo):
        assert municipio_de_organismo(organismo) is None

    def test_llega_al_resultado_de_clasificacion(self):
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Licitación", "organismo": "MUNICIPALIDAD DE CARRILOBO"},
            section="5",
        )
        assert result.municipio == "Carrilobo"
        assert result.as_analisis_fields()["municipio"] == "Carrilobo"
