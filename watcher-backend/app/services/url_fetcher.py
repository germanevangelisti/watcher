"""
URL Fetcher para boletines oficiales.

Construye la URL canónica de un boletín a partir de su filename y la config
de sincronización de la jurisdicción, luego descarga el PDF a un archivo
temporal para que el extractor normal lo procese.

Opción A: URL-first sin almacenamiento de PDFs en disco.
El PDF se descarga a un tempfile, se extrae el texto, y el tempfile se elimina.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Construcción de URL
# ---------------------------------------------------------------------------

def build_url_cordoba_provincial(filename: str) -> str:
    """
    Construye la URL del Boletín Oficial de la Provincia de Córdoba.

    Filename DB:  20260306_4_Secc.pdf  (YYYYMMDD_section_Secc.pdf)
    URL resultante: https://boletinoficial.cba.gov.ar/wp-content/4p96humuzp/2026/03/4_Secc_060326.pdf

    El date en la URL usa formato DDMMYY (invertido respecto al filename).
    El slug 4p96humuzp es estable (verificado desde hace >1 año).
    """
    stem = filename.replace(".pdf", "")
    parts = stem.split("_")  # ["20260306", "4", "Secc"]

    date_str = parts[0]      # "20260306"
    section = parts[1]       # "4"

    year = date_str[:4]      # "2026"
    month = date_str[4:6]    # "03"
    day = date_str[6:8]      # "06"
    year_short = year[2:]    # "26"

    # URL date: DDMMYY
    url_date = f"{day}{month}{year_short}"  # "060326"

    return (
        f"https://boletinoficial.cba.gov.ar/wp-content/4p96humuzp"
        f"/{year}/{month}/{section}_Secc_{url_date}.pdf"
    )


def build_url_from_template(template: str, filename: str) -> str:
    """
    Construye URL a partir del template almacenado en JurisdiccionSyncConfig.

    Template example:
      https://boletinoficial.cba.gov.ar/wp-content/4p96humuzp/{year}/{month}/{section}_Secc_{day}{month}{year_short}.pdf

    Variables disponibles: {year}, {month}, {day}, {section}, {year_short}
    """
    stem = filename.replace(".pdf", "")
    parts = stem.split("_")

    date_str = parts[0]
    section = parts[1]

    year = date_str[:4]
    month = date_str[4:6]
    day = date_str[6:8]
    year_short = year[2:]

    return template.format(
        year=year,
        month=month,
        day=day,
        section=section,
        year_short=year_short,
    )


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
    "Accept-Language": "es-AR,es;q=0.9",
}


async def fetch_pdf_to_tempfile(url: str, timeout_s: int = 30) -> Path:
    """
    Descarga un PDF desde una URL y lo guarda en un archivo temporal.

    Incluye headers de navegador: algunos servidores (ej. WordPress de Córdoba)
    rechazan requests sin User-Agent con 403.

    Returns:
        Path al tempfile (el llamador es responsable de borrarlo con .unlink()).

    Raises:
        httpx.HTTPError: si la descarga falla.
        ValueError: si la respuesta no es un PDF.
    """
    logger.info("Descargando PDF desde %s", url)

    # Referer: raíz del dominio para evitar bloqueos de hotlink
    from urllib.parse import urlparse
    parsed = urlparse(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    headers = {**_BROWSER_HEADERS, "Referer": referer}

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_s) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type and not url.endswith(".pdf"):
            raise ValueError(
                f"Respuesta inesperada (content-type={content_type!r}) para URL: {url}"
            )

        # Escribir a tempfile con sufijo .pdf para que los extractores lo reconozcan
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(response.content)
        tmp.close()

        size_kb = len(response.content) // 1024
        logger.info("PDF descargado (%d KB) → %s", size_kb, tmp.name)
        return Path(tmp.name)


async def fetch_and_extract_text(
    url: str,
    extractor_method: str = "pdfplumber",
    timeout_s: int = 30,
) -> str:
    """
    Descarga un PDF desde URL, extrae el texto y elimina el tempfile.

    Este es el entry point principal para Opción A.
    El PDF nunca se guarda de forma permanente en disco.

    Returns:
        Texto completo extraído del PDF.
    """
    tmp_path: Optional[Path] = None
    try:
        tmp_path = await fetch_pdf_to_tempfile(url, timeout_s=timeout_s)

        from app.services.extractors.registry import ExtractorRegistry
        content = await ExtractorRegistry.extract(tmp_path, method=extractor_method)

        if not content.success:
            raise RuntimeError(f"Extracción fallida para {url}: {content.error}")

        return content.full_text

    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
            logger.debug("Tempfile eliminado: %s", tmp_path)
