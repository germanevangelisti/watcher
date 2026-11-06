# Fuentes del catálogo de jurisdicciones de Córdoba (WMA1)

`municipios_cordoba.json` y `watcher-frontend/public/geo/municipios-cordoba.geojson`
se generan con `scripts/build_municipios_cordoba.py`. **Bajados el 2026-11-06**; el
mapa no consulta ninguna API en tiempo de ejecución.

| Dato | Fuente | Detalle |
| --- | --- | --- |
| Nombre, tipo, departamento, código y población | **ReFeGLo** — Base de Registro Federal de Gobiernos Locales, Ministerio del Interior | Campo `población_censo_2022` (Censo 2022, INDEC). 427 gobiernos locales de Córdoba: 260 municipios y 167 comunas. CSV `;`, latin-1. `http://datos.mininterior.gob.ar/dataset/8431ab79-3f44-41ee-b72b-cdc645f68d1e` |
| Límites | **OpenStreetMap**, `boundary=administrative` + `admin_level=7` dentro de `rel(3592494)` (provincia de Córdoba), vía Overpass API | © OpenStreetMap contributors, ODbL 1.0. Simplificado con Douglas-Peucker (tolerancia 0,0015° ≈ 150 m). |

## Por qué OSM y no IGN/IDECOR

La historia proponía IGN (unidades de gobierno local), la API georef de
datos.gob.ar o IDECOR. Desde el entorno de la sesión:

- `ign.gob.ar` no respondió (timeout de conexión) ni por HTTP ni por HTTPS.
- `idecor.gob.ar` / `idecor.cba.gov.ar` no resolvieron o devolvieron 403.
- La API georef devuelve centroides, **no geometrías**.

OSM tiene exactamente las 427 jurisdicciones de Córdoba en `admin_level=7`
(municipios **y** comunas) y se puede citar con fecha de extracción. El archivo
generado queda versionado, así que el producto no depende de Overpass. Si en el
futuro se consigue el GeoJSON del IGN, se reemplaza el archivo y se actualiza
esta nota: el contrato del endpoint no cambia.

## Emparejamiento OSM → ReFeGLo

426 de las 426 relaciones emparejaron. La número 427 del catálogo
(**Leguizamón**, comuna de Presidente Roque Sáenz Peña, 35 hab.) no tiene polígono
en OSM: se dibuja como punto con sus coordenadas del catálogo.

Los nombres de OSM no son idénticos a los de ReFeGLo. Emparejamientos no exactos
(revisados uno por uno, por nombre, subconjunto de tokens o centroide a menos de
40 km):

- Prefijos: `Municipio de …`, `Comuna de …`, `icipalidad de …` (dato roto en OSM).
- `Miramar de Ansenuza` → `Miramar`; `Alcira` → `Alcira Gigena`; `Calmayo` →
  `Parque Calmayo`; `Corral de Bustos` → `Corral de Bustos - Ifflinger`;
  `Pedro E. Vivas` → `Pedro E. Vivas - Kilómetro 658`; `Santa Catalina` →
  `Santa Catalina - Holmberg`; `Santa Rosa de Río Primero` → `Villa Santa Rosa
  De Río Primero`; `Villa Cañada del Sauce` → `Cañada del Sauce`.
- `Negro Huasi` → `Las Cañadas` (Cruz del Eje): es el nombre que usa OSM; alias
  explícito en el script.
- `Saturninio` → `Saturnino María Laspiur`; `Huanchillas` → `Huanchilla`;
  `Lucio V. Mansilla` → `Lucio Victorio Mansilla`; `Riobamba` → `Río Bamba`;
  `Villa Quilinzo` → `Villa Quillinzo`.
- Nombres repetidos resueltos por cercanía: `Los Chañaritos (Río Segundo)` /
  `Los Chañaritos (Cruz del Eje-Ischilin)` y `Villa Sarmiento (San Alberto)` /
  `Villa Sarmiento (General Roca)`.

## Cómo regenerar

```bash
# refeglo: CSV de ReFeGLo (latin-1, ';'); osm: salida de Overpass con `out geom;`
python scripts/build_municipios_cordoba.py \
  --refeglo brgl.csv --osm geo7.json \
  --catalogo app/data/municipios_cordoba.json \
  --geojson ../watcher-frontend/public/geo/municipios-cordoba.geojson
```

La consulta de Overpass usada:

```
[out:json][timeout:300];
area(3603592494)->.a;
rel(area.a)["boundary"="administrative"]["admin_level"="7"];
out geom;
```
