"""
Parser de Mapas-por-Programas.pdf → presupuesto_base 2026

Extrae tablas del PDF de programas presupuestarios de la Provincia de Córdoba
(Ley N°11088) y carga los registros en presupuesto_base para ejercicio=2026.

Uso:
    cd watcher-backend
    python scripts/parse_pdf_presupuesto_2026.py [--dry-run] [--force]

Flags:
    --dry-run   Solo parsea el PDF y guarda JSON, sin tocar la DB
    --force     Elimina registros 2026 existentes antes de cargar
"""

import asyncio
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Any

# Backend on path for DB imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pdfplumber
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.db.models import PresupuestoBase

# Reuse OrganismoNormalizer from the Excel script
from scripts.parse_excel_presupuesto import OrganismoNormalizer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent.parent  # watcher/ monorepo root
PDF_PATH = BASE_DIR / "watcher-doc" / "data" / "2026" / "Mapas-por-Programas.pdf"
OUTPUT_JSON = BASE_DIR / "watcher-doc" / "data" / "2026" / "presupuesto_2026_parsed.json"
DATABASE_URL = "sqlite+aiosqlite:///./sqlite.db"  # run from watcher-backend/

FECHA_APROBACION = date(2026, 1, 1)   # Ley N°11088

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_normalizer = OrganismoNormalizer()


def _normalize_org(name: str) -> str:
    return _normalizer.normalize(name or "")


def _parse_monto(monto_str: Any) -> float:
    """Parse Argentine peso amount: '6.831.523.000' or '6.831.523,00' → float."""
    if not monto_str:
        return 0.0
    s = str(monto_str).strip()
    # Remove currency symbols and whitespace
    s = re.sub(r'[$\s]', '', s)
    if not s:
        return 0.0
    # "1.234.567,89"  → AR format (dot=thousands, comma=decimal)
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        # Only dots present → thousands separator, no decimal
        parts = s.split('.')
        if len(parts) > 1 and len(parts[-1]) == 3:
            s = s.replace('.', '')
        # else: single dot = decimal separator (unlikely for ARS budget)
    try:
        return float(s)
    except ValueError:
        return 0.0


def _normalize_fin_fun_det(raw: str) -> str:
    """'1 6 0' → '1.6.0'"""
    if not raw:
        return ""
    digits = re.findall(r'\d+', str(raw))
    return ".".join(digits) if digits else str(raw).strip()


def _clean_cell(val: Any) -> str:
    if val is None:
        return ""
    return re.sub(r'\s+', ' ', str(val)).strip()


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# PDF parser
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Column x-boundaries (determined empirically from word positions)
# Page is landscape ~862px wide.
# ---------------------------------------------------------------------------
_COL_BOUNDS = [
    ("codigo",              0,     93),
    ("denominacion",        93,    215),
    ("naturaleza",          215,   302),   # PROGRAMA at ~226, SUBPROGRAMA at ~218
    ("unidad_organizacion", 302,   417),   # content starts at ~303 in practice
    ("unidad_ejecutora",    417,   522),   # content starts at ~418 in practice
    ("servicio_admin",      522,   630),
    ("fin_fun_det",         630,   670),
    ("fuente",              670,   768),
    ("monto",               768,   9999),
]

_ROW_TOLERANCE_PX = 14  # words within this many px vertically → same logical row
_TABLE_TOP_MIN = 115     # ignore page header / column header rows above this


def _col_for_x(x0: float) -> str:
    for name, lo, hi in _COL_BOUNDS:
        if lo <= x0 < hi:
            return name
    return "other"


def _is_jurisdiction_header(text: str) -> bool:
    return bool(re.match(r'^\d+\.\d+\s*[-–]', text.strip()))


def _words_to_rows(words: List[Dict]) -> List[Dict[str, str]]:
    """
    Group words by approximate vertical position and assign to columns.
    Returns list of row-dicts keyed by column name.
    """
    # Filter to table area only (below column headers)
    data_words = [w for w in words if w["top"] >= _TABLE_TOP_MIN]
    if not data_words:
        return []

    # Sort by top then x0
    data_words.sort(key=lambda w: (w["top"], w["x0"]))

    # Group into logical rows using tolerance
    rows: List[List[Dict]] = []
    current_group: List[Dict] = []
    group_min_top: float = 0.0

    for word in data_words:
        if not current_group:
            current_group.append(word)
            group_min_top = word["top"]
        elif word["top"] - group_min_top <= _ROW_TOLERANCE_PX:
            current_group.append(word)
            if word["top"] < group_min_top:
                group_min_top = word["top"]
        else:
            rows.append(current_group)
            current_group = [word]
            group_min_top = word["top"]

    if current_group:
        rows.append(current_group)

    # Convert each word-group into a column-keyed dict
    result: List[Dict[str, str]] = []
    for word_group in rows:
        row_dict: Dict[str, List[str]] = {}
        for w in word_group:
            col = _col_for_x(w["x0"])
            if col not in row_dict:
                row_dict[col] = []
            row_dict[col].append(w["text"])
        result.append({col: " ".join(words_) for col, words_ in row_dict.items()})

    return result


def parse_pdf(pdf_path: Path) -> List[Dict]:
    """
    Extract budget program records from Mapas-por-Programas.pdf using
    word-position based column reconstruction (pdfplumber extract_tables
    merges all cells into column 0 for this PDF).

    Returns a list of dicts ready to be loaded into presupuesto_base.
    """
    records: List[Dict] = []
    current_jurisdiccion: str = ""
    current_programa: str = ""
    current_unidad_org: str = ""
    current_unidad_ejec: str = ""

    with pdfplumber.open(pdf_path) as pdf:
        print(f"  PDF: {len(pdf.pages)} páginas")

        for page_num, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(keep_blank_chars=False)

            # Detect jurisdiction header from words above the table area
            header_words = [w for w in words if w["top"] < _TABLE_TOP_MIN]
            header_text = " ".join(w["text"] for w in header_words)
            m = re.search(r'(\d+\.\d+\s*[-–].+)', header_text)
            if m:
                current_jurisdiccion = m.group(1).strip()

            rows = _words_to_rows(words)

            for row in rows:
                denominacion = row.get("denominacion", "").strip()
                nat_raw = row.get("naturaleza", "").strip().upper()
                # Normalise naturaleza — column may pick up spillover text
                if "SUBPROGRAMA" in nat_raw:
                    naturaleza = "SUBPROGRAMA"
                elif "ACTIVIDADES" in nat_raw or "CENTRALES" in nat_raw:
                    naturaleza = "ACTIVIDADES CENTRALES"
                elif "PROGRAMA" in nat_raw:
                    naturaleza = "PROGRAMA"
                else:
                    naturaleza = nat_raw
                monto_raw = row.get("monto", "")
                codigo = row.get("codigo", "").strip()

                # Skip total rows and rows with no meaningful content
                if not denominacion:
                    continue
                denominacion_lc = denominacion.lower()
                if denominacion_lc.startswith("total") or denominacion_lc.startswith("código"):
                    continue

                monto = _parse_monto(monto_raw) if monto_raw else 0.0

                # Update context for PROGRAMA / ACTIVIDADES CENTRALES rows
                unidad_org = row.get("unidad_organizacion", "").strip()
                unidad_ejec = row.get("unidad_ejecutora", "").strip()

                if naturaleza in ("PROGRAMA", "ACTIVIDADES CENTRALES") and codigo:
                    current_programa = (
                        f"{codigo} - {denominacion}" if codigo else denominacion
                    )
                    if unidad_org:
                        current_unidad_org = unidad_org
                    if unidad_ejec:
                        current_unidad_ejec = unidad_ejec

                # For SUBPROGRAMA, inherit parent context if cells are empty
                effective_unidad_org = unidad_org or current_unidad_org
                effective_unidad_ejec = unidad_ejec or current_unidad_ejec
                organismo_raw = effective_unidad_ejec or effective_unidad_org or current_jurisdiccion
                organismo = _normalize_org(organismo_raw)

                # Skip rows with neither monto nor known naturaleza (likely header fragments)
                if not naturaleza and monto == 0:
                    continue

                records.append({
                    "ejercicio": 2026,
                    "organismo": organismo,
                    "organismo_raw": organismo_raw,
                    "programa": current_programa,
                    "subprograma": denominacion if naturaleza == "SUBPROGRAMA" else None,
                    "partida_presupuestaria": _normalize_fin_fun_det(row.get("fin_fun_det", "")),
                    "descripcion": f"[{effective_unidad_org or current_jurisdiccion}] {denominacion}"[:500],
                    "monto_inicial": monto,
                    "monto_vigente": monto,
                    "fuente_financiamiento": row.get("fuente", "") or None,
                    "naturaleza": naturaleza,
                    "jurisdiccion": current_jurisdiccion,
                    "page": page_num,
                })

    return records


# ---------------------------------------------------------------------------
# DB loader
# ---------------------------------------------------------------------------

async def load_into_db(records: List[Dict], engine: Any, force: bool = False) -> int:
    """Load parsed records into presupuesto_base. Returns count loaded."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check existing 2026 records
        result = await session.execute(
            select(func.count(PresupuestoBase.id)).where(PresupuestoBase.ejercicio == 2026)
        )
        existing = result.scalar() or 0

        if existing > 0:
            if force:
                print(f"  Eliminando {existing} registros existentes de ejercicio 2026...")
                await session.execute(
                    delete(PresupuestoBase).where(PresupuestoBase.ejercicio == 2026)
                )
                await session.commit()
            else:
                print(f"  ⚠ Ya existen {existing} registros para 2026. Usa --force para reemplazar.")
                return 0

        # Deduplicate by (organismo, programa, subprograma) — keep last seen
        seen: Dict[str, Dict] = {}
        for rec in records:
            key = f"{rec['organismo']}|{rec['programa']}|{rec.get('subprograma') or ''}"
            seen[key] = rec

        loaded = 0
        for rec in seen.values():
            try:
                presupuesto = PresupuestoBase(
                    ejercicio=rec["ejercicio"],
                    organismo=rec["organismo"],
                    programa=rec["programa"] or "",
                    subprograma=rec.get("subprograma"),
                    partida_presupuestaria=rec["partida_presupuestaria"] or "",
                    descripcion=rec["descripcion"],
                    monto_inicial=rec["monto_inicial"],
                    monto_vigente=rec["monto_vigente"],
                    fecha_aprobacion=FECHA_APROBACION,
                    fuente_financiamiento=rec.get("fuente_financiamiento"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(presupuesto)
                loaded += 1

                if loaded % 100 == 0:
                    await session.commit()
                    print(f"  → {loaded}/{len(seen)} cargados", end="\r")

            except Exception as e:
                print(f"\n  ⚠ Error cargando registro: {e}")
                continue

        await session.commit()
        print(f"  → {loaded} registros cargados          ")

    return loaded


# ---------------------------------------------------------------------------
# Verification query
# ---------------------------------------------------------------------------

async def verify(n_loaded: int, engine: Any) -> None:
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            select(
                func.count(PresupuestoBase.id),
                func.sum(PresupuestoBase.monto_vigente),
            ).where(PresupuestoBase.ejercicio == 2026)
        )
        count, total = result.one()

        print(f"\n{'='*60}")
        print("VERIFICACIÓN presupuesto_base (ejercicio=2026)")
        print(f"{'='*60}")
        print(f"  Registros:    {count:,}")
        print(f"  Total ARS:    {(total or 0):>20,.0f}")
        print("  (Ley 11088 aprueba ~11.4T ARS de gasto total)")

        # Top 10 organismos
        result = await session.execute(
            select(
                PresupuestoBase.organismo,
                func.count(PresupuestoBase.id).label("n"),
                func.sum(PresupuestoBase.monto_vigente).label("total"),
            )
            .where(PresupuestoBase.ejercicio == 2026)
            .group_by(PresupuestoBase.organismo)
            .order_by(func.sum(PresupuestoBase.monto_vigente).desc())
            .limit(10)
        )
        print("\n  Top 10 organismos:")
        for org, n, tot in result:
            print(f"    {org[:45]:<45} ${(tot or 0):>15,.0f}  ({n} prog)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    print(f"\n{'#'*60}")
    print("# PARSE PDF PRESUPUESTO 2026 → presupuesto_base")
    print(f"{'#'*60}\n")

    if not PDF_PATH.exists():
        print(f"❌ PDF no encontrado: {PDF_PATH}")
        sys.exit(1)

    # Step 1: Parse PDF
    print(f"[1/3] Parseando {PDF_PATH.name} ...")
    records = parse_pdf(PDF_PATH)
    print(f"  → {len(records)} filas extraídas del PDF")

    if not records:
        print("❌ No se extrajeron registros. Revisar estructura del PDF.")
        sys.exit(1)

    # Step 2: Save intermediate JSON
    print(f"[2/3] Guardando JSON intermedio → {OUTPUT_JSON.name} ...")
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, default=str)
    print(f"  → {OUTPUT_JSON}")

    if dry_run:
        print("\n⚠ --dry-run: se omite la carga en DB.")
        _print_sample(records)
        return

    # Step 3: Load into DB (single engine shared with verify)
    print("[3/3] Cargando en presupuesto_base (ejercicio=2026) ...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        n_loaded = await load_into_db(records, engine, force=force)

        if n_loaded > 0:
            await verify(n_loaded, engine)
            print(f"\n✅ COMPLETADO: {n_loaded} registros en presupuesto_base\n")
        else:
            print("\n⚠ No se cargaron registros nuevos.\n")
    finally:
        await engine.dispose()


def _print_sample(records: List[Dict]) -> None:
    print("\nMuestra de primeros 5 registros:")
    for r in records[:5]:
        print(f"  organismo:   {r['organismo']}")
        print(f"  programa:    {r['programa']}")
        print(f"  subprograma: {r.get('subprograma')}")
        print(f"  partida:     {r['partida_presupuestaria']}")
        print(f"  monto:       {r['monto_inicial']:,.0f}")
        print(f"  fuente:      {r.get('fuente_financiamiento')}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
