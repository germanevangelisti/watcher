"""Calendar coverage of the provincial Boletín Oficial vs `boletines` (V.1.1).

Layer A only: did we ingest what was published?  This module does not look at
SIGAF, CGE cash execution, Neo4j or Chroma.

Source of truth for "published" is an HTTP probe of the canonical PDF URL
(`url_fetcher.build_url_cordoba_provincial`).  Weekdays are the *candidate*
grid that `sync_service` already uses (weekends skipped, holidays not);
a weekday without a PDF is a feriado/no-issue, not a lost bulletin.

The inventory must count what `sync` actually stored in `boletines`, not what
`ProvincialPipeline.extract()` would discover on disk.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from app.services.url_fetcher import build_url_cordoba_provincial

SECTIONS = (1, 2, 3, 4, 5)

COMPLETED_STATUSES = frozenset({"completed", "done", "ok"})
FAILED_STATUSES = frozenset({"failed", "error", "failed_download"})
PENDING_STATUSES = frozenset({"pending", "processing", "queued"})

_FILENAME_RE = re.compile(
    r"^(?P<ymd>\d{8})_(?P<section>\d)_Secc(?:\.pdf)?$",
    re.IGNORECASE,
)
_YMD_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
_ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

StatusBucket = Literal["completed", "failed", "pending", "other"]
ProbeMode = Literal["live", "cached", "weekdays_assumed"]

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
    "Accept-Language": "es-AR,es;q=0.9",
}


def parse_section(raw: Any) -> int | None:
    """Normalize `boletines.section` shapes to 1-5."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw if 1 <= raw <= 5 else None
    match = re.search(r"\d", str(raw))
    if not match:
        return None
    value = int(match.group())
    return value if 1 <= value <= 5 else None


def parse_ymd(raw: Any) -> date | None:
    """Parse YYYYMMDD or YYYY-MM-DD into a date."""
    if raw is None:
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    text = str(raw).strip()
    match = _YMD_RE.match(text)
    if match:
        year, month, day = (int(p) for p in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    match = _ISO_RE.match(text)
    if match:
        year, month, day = (int(p) for p in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def filename_for(slot_date: date, section: int) -> str:
    return f"{slot_date:%Y%m%d}_{section}_Secc.pdf"


def parse_filename(filename: str | None) -> tuple[date, int] | None:
    """Parse `YYYYMMDD_N_Secc.pdf` as used by sync / the provincial scraper."""
    if not filename:
        return None
    stem = filename.rsplit("/", 1)[-1]
    match = _FILENAME_RE.match(stem)
    if not match:
        return None
    slot_date = parse_ymd(match.group("ymd"))
    section = int(match.group("section"))
    if slot_date is None or not 1 <= section <= 5:
        return None
    return slot_date, section


def classify_status(status: str | None) -> StatusBucket:
    raw = (status or "").strip().lower()
    if raw in COMPLETED_STATUSES:
        return "completed"
    if raw in FAILED_STATUSES:
        return "failed"
    if raw in PENDING_STATUSES:
        return "pending"
    return "other"


def weekday_dates(start: date, end: date) -> list[date]:
    """Inclusive weekday range — same rule as `SyncService.calculate_missing_dates`."""
    if end < start:
        return []
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def weekday_slots(start: date, end: date, sections: tuple[int, ...] = SECTIONS) -> list[tuple[date, int]]:
    return [(d, section) for d in weekday_dates(start, end) for section in sections]


def slot_url(slot_date: date, section: int) -> str:
    return build_url_cordoba_provincial(filename_for(slot_date, section))


@dataclass(frozen=True)
class Slot:
    date: date
    section: int

    @property
    def filename(self) -> str:
        return filename_for(self.date, self.section)

    @property
    def url(self) -> str:
        return slot_url(self.date, self.section)

    @property
    def key(self) -> tuple[str, int]:
        return self.date.isoformat(), self.section


@dataclass
class DbBoletin:
    id: int
    filename: str
    date: date | None
    section: int | None
    status: str
    fuente: str | None = None
    error_message: str | None = None

    @property
    def bucket(self) -> StatusBucket:
        return classify_status(self.status)

    @property
    def slot(self) -> Slot | None:
        parsed = parse_filename(self.filename)
        if parsed:
            return Slot(*parsed)
        if self.date is not None and self.section is not None:
            return Slot(self.date, self.section)
        return None


@dataclass
class ProbeResult:
    date: date
    section: int
    url: str
    published: bool
    http_status: int | None = None
    content_type: str | None = None
    error: str | None = None

    @property
    def slot(self) -> Slot:
        return Slot(self.date, self.section)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["date"] = self.date.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProbeResult:
        return cls(
            date=parse_ymd(payload["date"]) or date.fromisoformat(payload["date"]),
            section=int(payload["section"]),
            url=str(payload["url"]),
            published=bool(payload["published"]),
            http_status=payload.get("http_status"),
            content_type=payload.get("content_type"),
            error=payload.get("error"),
        )


@dataclass
class CoverageReport:
    start: date
    end: date
    probe_mode: ProbeMode
    weekday_days: int = 0
    weekday_slots: int = 0
    published_days: int = 0
    published_slots: int = 0
    db_total: int = 0
    db_completed: int = 0
    db_failed: int = 0
    db_pending: int = 0
    db_other: int = 0
    covered_slots: int = 0
    huecos: list[Slot] = field(default_factory=list)
    failed_rows: list[DbBoletin] = field(default_factory=list)
    pending_rows: list[DbBoletin] = field(default_factory=list)
    extra_in_db: list[DbBoletin] = field(default_factory=list)
    unpublished_weekdays: list[date] = field(default_factory=list)
    sections_present_by_day: dict[str, dict[str, int]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def pct_published_days_covered(self) -> float | None:
        """Share of published days where every published section is completed in DB."""
        if self.published_days == 0:
            return None
        complete = 0
        for day, counts in self.sections_present_by_day.items():
            if counts.get("published", 0) <= 0:
                continue
            if counts.get("covered", 0) == counts["published"]:
                complete += 1
        return round(100.0 * complete / self.published_days, 1)

    @property
    def pct_sections_present(self) -> float | None:
        if self.published_slots == 0:
            return None
        return round(100.0 * self.covered_slots / self.published_slots, 1)

    @property
    def pct_weekdays_with_any_db(self) -> float | None:
        if self.weekday_days == 0:
            return None
        present = sum(
            1
            for counts in self.sections_present_by_day.values()
            if counts.get("in_db", 0) > 0
        )
        return round(100.0 * present / self.weekday_days, 1)

    def to_markdown(self) -> str:
        pct_days = self.pct_published_days_covered
        pct_sec = self.pct_sections_present
        lines = [
            "# Inventario calendario vs DB — V.1.1",
            "",
            f"**Rango:** {self.start.isoformat()} → {self.end.isoformat()}",
            f"**Modo de publicación:** `{self.probe_mode}`",
            "",
            "Capa A: pipeline vs boletín. No es ejecución SIGAF/CGE.",
            "",
            "## Métricas",
            "",
            "| Métrica | Valor |",
            "|---|---:|",
            f"| Días hábiles (lun–vie, regla de sync) | {self.weekday_days} |",
            f"| Slots candidatos (día × S1–S5) | {self.weekday_slots} |",
            f"| Días con PDF publicado | {self.published_days} |",
            f"| Slots publicados | {self.published_slots} |",
            f"| Filas `boletines` en rango | {self.db_total} |",
            f"| `completed` | {self.db_completed} |",
            f"| `failed`/`error` | {self.db_failed} |",
            f"| `pending`/`processing` | {self.db_pending} |",
            f"| otro status | {self.db_other} |",
            f"| Slots publicados y `completed` en DB | {self.covered_slots} |",
            f"| % días publicados cubiertos (todas las secciones) | "
            f"{_fmt_pct(pct_days)} |",
            f"| % secciones publicadas presentes (`completed`) | "
            f"{_fmt_pct(pct_sec)} |",
            f"| Huecos (publicado, ausente en DB) | {len(self.huecos)} |",
            f"| Weekdays sin PDF (feriado / no salió) | "
            f"{len(self.unpublished_weekdays)} |",
            "",
        ]
        lines.extend(_md_day_table(self.sections_present_by_day))
        lines.extend(
            _md_slot_list(
                "Huecos — publicados y no están en `boletines`",
                self.huecos,
            )
        )
        lines.extend(_md_row_list("Failed / error", self.failed_rows))
        lines.extend(_md_row_list("Pending / processing", self.pending_rows))
        lines.extend(
            _md_row_list(
                "En DB pero no publicados (o no en el probe)",
                self.extra_in_db,
            )
        )
        if self.unpublished_weekdays:
            days = ", ".join(d.isoformat() for d in self.unpublished_weekdays)
            lines.extend(["## Weekdays sin PDF", "", days, ""])
        if self.notes:
            lines.extend(["## Notas", ""])
            lines.extend(f"- {note}" for note in self.notes)
            lines.append("")
        lines.extend(
            [
                "## Lectura",
                "",
                "- Feriado / no salió: weekday sin PDF (p.ej. Carnaval) no es hueco "
                "de pipeline. Carnaval 16–17 feb queda `failed` justificado; "
                "23–24 mar no tienen fila porque el BO no publicó.",
                "- Hueco: publicado en el BO y ausente en `boletines`.",
                "- `pending`: PDF registrado; la extracción LLM no cerró el slot.",
                "- Capa A solamente: no mezclar este inventario con CGE/SIGAF.",
                "",
            ]
        )
        return "\n".join(lines)


def _fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}%"


def _md_day_table(by_day: dict[str, dict[str, int]]) -> list[str]:
    if not by_day:
        return []
    lines = [
        "## Secciones por día",
        "",
        "| Fecha | Publicadas | En DB | Completed | Failed | Pending | Cubiertas |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for day in sorted(by_day):
        c = by_day[day]
        lines.append(
            f"| {day} | {c.get('published', 0)} | {c.get('in_db', 0)} | "
            f"{c.get('completed', 0)} | {c.get('failed', 0)} | "
            f"{c.get('pending', 0)} | {c.get('covered', 0)} |"
        )
    lines.append("")
    return lines


def _md_slot_list(title: str, slots: list[Slot]) -> list[str]:
    lines = [f"## {title}", ""]
    if not slots:
        lines.append("_Ninguno._")
        lines.append("")
        return lines
    lines.append("| Fecha | Sección | Filename |")
    lines.append("|---|---:|---|")
    for slot in slots:
        lines.append(f"| {slot.date.isoformat()} | S{slot.section} | {slot.filename} |")
    lines.append("")
    return lines


def _md_row_list(title: str, rows: list[DbBoletin]) -> list[str]:
    lines = [f"## {title}", ""]
    if not rows:
        lines.append("_Ninguno._")
        lines.append("")
        return lines
    lines.append("| id | Fecha | Sección | Status | Filename | Error |")
    lines.append("|---|---:|---:|---|---|---|")
    for row in rows:
        day = row.date.isoformat() if row.date else ""
        section = f"S{row.section}" if row.section else ""
        err = (row.error_message or "").replace("|", "/").replace("\n", " ")
        if len(err) > 80:
            err = err[:77] + "..."
        lines.append(
            f"| {row.id} | {day} | {section} | {row.status} | {row.filename} | {err} |"
        )
    lines.append("")
    return lines


def db_boletin_from_row(row: Any) -> DbBoletin:
    """Build a `DbBoletin` from a sqlite3.Row / mapping / sequence."""
    if isinstance(row, dict) or hasattr(row, "keys"):
        mapping = dict(row)
        filename = mapping.get("filename") or ""
        parsed = parse_filename(filename)
        slot_date = parse_ymd(mapping.get("date")) or (parsed[0] if parsed else None)
        section = parse_section(mapping.get("section")) or (parsed[1] if parsed else None)
        return DbBoletin(
            id=int(mapping.get("id") or 0),
            filename=filename,
            date=slot_date,
            section=section,
            status=str(mapping.get("status") or ""),
            fuente=mapping.get("fuente"),
            error_message=mapping.get("error_message"),
        )
    # sequence: id, filename, date, section, status, fuente, error_message
    filename = row[1] or ""
    parsed = parse_filename(filename)
    slot_date = parse_ymd(row[2]) or (parsed[0] if parsed else None)
    section = parse_section(row[3]) or (parsed[1] if parsed else None)
    return DbBoletin(
        id=int(row[0]),
        filename=filename,
        date=slot_date,
        section=section,
        status=str(row[4] or ""),
        fuente=row[5] if len(row) > 5 else None,
        error_message=row[6] if len(row) > 6 else None,
    )


def is_provincial_row(row: DbBoletin) -> bool:
    fuente = (row.fuente or "provincial").strip().lower()
    if fuente in {"", "provincial"}:
        return True
    # Filename of the provincial BO still counts even if fuente is messy.
    return parse_filename(row.filename) is not None and fuente not in {
        "municipal_capital",
        "municipal_otros",
    }


def diff_inventory(
    start: date,
    end: date,
    db_rows: list[DbBoletin],
    published: set[tuple[date, int]] | None = None,
    probe_mode: ProbeMode = "weekdays_assumed",
    notes: list[str] | None = None,
) -> CoverageReport:
    """Diff candidate/published slots against `boletines` rows.

    If `published` is None, every weekday×section is treated as published
    (`weekdays_assumed`).  Live/cached probes should pass the set of slots
    that actually returned a PDF.
    """
    candidates = weekday_slots(start, end)
    candidate_set = set(candidates)
    if published is None:
        published_set = candidate_set
        effective_mode: ProbeMode = "weekdays_assumed"
    else:
        published_set = {pair for pair in published if start <= pair[0] <= end}
        effective_mode = probe_mode

    in_range = [
        row
        for row in db_rows
        if is_provincial_row(row)
        and row.date is not None
        and start <= row.date <= end
        and row.section is not None
    ]

    by_slot: dict[tuple[date, int], list[DbBoletin]] = defaultdict(list)
    for row in in_range:
        assert row.date is not None and row.section is not None
        by_slot[(row.date, row.section)].append(row)

    report = CoverageReport(
        start=start,
        end=end,
        probe_mode=effective_mode,
        weekday_days=len(weekday_dates(start, end)),
        weekday_slots=len(candidates),
        published_slots=len(published_set),
        published_days=len({d for d, _ in published_set}),
        db_total=len(in_range),
        notes=list(notes or []),
    )

    for row in in_range:
        bucket = row.bucket
        if bucket == "completed":
            report.db_completed += 1
        elif bucket == "failed":
            report.db_failed += 1
            report.failed_rows.append(row)
        elif bucket == "pending":
            report.db_pending += 1
            report.pending_rows.append(row)
        else:
            report.db_other += 1

    day_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "published": 0,
            "in_db": 0,
            "completed": 0,
            "failed": 0,
            "pending": 0,
            "covered": 0,
        }
    )

    for day in weekday_dates(start, end):
        key = day.isoformat()
        _ = day_stats[key]  # ensure the weekday appears even with 0 published

    for slot_date, section in sorted(published_set):
        stats = day_stats[slot_date.isoformat()]
        stats["published"] += 1
        rows = by_slot.get((slot_date, section), [])
        if not rows:
            report.huecos.append(Slot(slot_date, section))
            continue
        stats["in_db"] += 1
        buckets = {row.bucket for row in rows}
        if "completed" in buckets:
            stats["completed"] += 1
            stats["covered"] += 1
            report.covered_slots += 1
        if "failed" in buckets and "completed" not in buckets:
            stats["failed"] += 1
        if "pending" in buckets and "completed" not in buckets:
            stats["pending"] += 1

    for (slot_date, section), rows in sorted(by_slot.items()):
        stats = day_stats[slot_date.isoformat()]
        if (slot_date, section) not in published_set:
            report.extra_in_db.extend(rows)
            stats["in_db"] += 1
            for row in rows:
                if row.bucket == "completed":
                    stats["completed"] += 1
                elif row.bucket == "failed":
                    stats["failed"] += 1
                elif row.bucket == "pending":
                    stats["pending"] += 1
        elif not any(r.bucket == "completed" for r in rows):
            # published + in DB but not completed still counts as in_db
            pass

    published_days = {d for d, _ in published_set}
    report.unpublished_weekdays = [
        d for d in weekday_dates(start, end) if d not in published_days
    ]
    report.sections_present_by_day = dict(day_stats)

    # Recompute in_db for published days so the table is not double-counting
    # extras.  The extra_in_db list is the audit trail; the per-day table
    # should reflect DB occupancy of that weekday regardless of probe.
    for day in weekday_dates(start, end):
        key = day.isoformat()
        in_db = sum(1 for section in SECTIONS if (day, section) in by_slot)
        day_stats[key]["in_db"] = in_db
        completed = sum(
            1
            for section in SECTIONS
            if any(r.bucket == "completed" for r in by_slot.get((day, section), []))
        )
        failed = sum(
            1
            for section in SECTIONS
            if any(r.bucket == "failed" for r in by_slot.get((day, section), []))
            and not any(r.bucket == "completed" for r in by_slot.get((day, section), []))
        )
        pending = sum(
            1
            for section in SECTIONS
            if any(r.bucket == "pending" for r in by_slot.get((day, section), []))
            and not any(r.bucket == "completed" for r in by_slot.get((day, section), []))
        )
        day_stats[key]["completed"] = completed
        day_stats[key]["failed"] = failed
        day_stats[key]["pending"] = pending
    report.sections_present_by_day = dict(day_stats)
    return report


def dump_probes(results: list[ProbeResult]) -> str:
    return json.dumps([item.to_dict() for item in results], indent=2, ensure_ascii=False)


def load_probes(raw: str | list[dict[str, Any]]) -> list[ProbeResult]:
    payload = json.loads(raw) if isinstance(raw, str) else raw
    return [ProbeResult.from_dict(item) for item in payload]


def published_set(results: list[ProbeResult]) -> set[tuple[date, int]]:
    return {(item.date, item.section) for item in results if item.published}


def _is_pdf_response(status_code: int, content_type: str | None, prefix: bytes) -> bool:
    if status_code != 200:
        return False
    ctype = (content_type or "").lower()
    if "pdf" in ctype:
        return True
    if "html" in ctype or "text/" in ctype or "json" in ctype:
        return False
    return prefix.startswith(b"%PDF")


async def probe_slot(
    client: httpx.AsyncClient,
    slot_date: date,
    section: int,
    timeout_s: float = 20.0,
) -> ProbeResult:
    """Stream a few bytes of the canonical PDF.  Do not persist the file."""
    url = slot_url(slot_date, section)
    parsed = urlparse(url)
    headers = {**_BROWSER_HEADERS, "Referer": f"{parsed.scheme}://{parsed.netloc}/"}
    try:
        async with client.stream("GET", url, headers=headers, timeout=timeout_s) as resp:
            prefix = b""
            async for chunk in resp.aiter_bytes():
                prefix += chunk
                if len(prefix) >= 8:
                    break
            await resp.aclose()
            ctype = resp.headers.get("content-type")
            return ProbeResult(
                date=slot_date,
                section=section,
                url=url,
                published=_is_pdf_response(resp.status_code, ctype, prefix),
                http_status=resp.status_code,
                content_type=ctype,
            )
    except httpx.HTTPError as exc:
        return ProbeResult(
            date=slot_date,
            section=section,
            url=url,
            published=False,
            error=str(exc),
        )


async def probe_slots(
    slots: list[tuple[date, int]],
    *,
    concurrency: int = 3,
    timeout_s: float = 20.0,
) -> list[ProbeResult]:
    """Probe canonical URLs.  Small concurrency to stay under CloudFront."""
    import asyncio

    semaphore = asyncio.Semaphore(concurrency)
    results: list[ProbeResult] = []

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_s) as client:

        async def _one(pair: tuple[date, int]) -> ProbeResult:
            async with semaphore:
                return await probe_slot(client, pair[0], pair[1], timeout_s=timeout_s)

        gathered = await asyncio.gather(*(_one(pair) for pair in slots))
        results.extend(gathered)
    return results
