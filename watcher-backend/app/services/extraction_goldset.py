"""Score a hand-labeled extraction gold set against `analisis` (V.1.2).

Gold rows are the source of truth for acto / monto / organismo / numero_acto /
etapa.  The extractor is not allowed to redefine those fields.  Precision is
only reported for filenames whose gold set is marked `complete_gasto` (every
public-spending acto in that PDF was labeled).  S2/S3 control rows exist to
check that remates and sociedades are not classified as gasto público.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from app.services.presupuesto_matching import _normalize, resolve_numero_acto


def normalize_numero(raw: str | None) -> str | None:
    resolved = resolve_numero_acto(raw, raw)
    if resolved:
        return _normalize(resolved).replace(" ", "")
    if not raw:
        return None
    compact = _normalize(raw).replace(" ", "")
    return compact or None


def relative_monto_error(predicted: float | None, gold: float | None) -> float | None:
    if predicted is None or gold is None or gold == 0:
        return None
    return abs(predicted - gold) / abs(gold)


@dataclass
class GoldAct:
    filename: str
    gold_id: str
    tipo_acto: str | None = None
    numero_acto: str | None = None
    organismo: str | None = None
    monto: float | None = None
    etapa: str | None = None
    is_gasto_publico: bool | None = None
    complete_gasto: bool = False
    notes: str = ""

    @property
    def numero_norm(self) -> str | None:
        return normalize_numero(self.numero_acto)


@dataclass
class ExtractedAct:
    analisis_id: int
    filename: str
    section: str | None = None
    tipo_acto: str | None = None
    numero_acto: str | None = None
    organismo: str | None = None
    monto: float | None = None
    etapa: str | None = None
    is_gasto_publico: bool | None = None
    descripcion: str | None = None

    @property
    def numero_norm(self) -> str | None:
        return normalize_numero(self.numero_acto)


@dataclass
class GoldMatch:
    gold: GoldAct
    extracted: ExtractedAct | None
    method: str
    monto_error: float | None = None


@dataclass
class GoldMetrics:
    gold_n: int
    matched: int
    recall: float
    precision: float | None
    monto_mae_rel: float | None
    s4_with_numero: int
    s4_n: int
    s4_numero_pct: float | None
    gasto_false_positives: int
    matches: list[GoldMatch] = field(default_factory=list)
    unmatched_gold: list[GoldAct] = field(default_factory=list)

    def to_markdown(self) -> str:
        prec = "n/a" if self.precision is None else f"{self.precision:.1%}"
        mae = "n/a" if self.monto_mae_rel is None else f"{self.monto_mae_rel:.1%}"
        s4 = "n/a" if self.s4_numero_pct is None else f"{self.s4_numero_pct:.1%}"
        lines = [
            "# Gold set de extracción — V.1.2",
            "",
            "| Métrica | Valor |",
            "|---|---:|",
            f"| Actos gold | {self.gold_n} |",
            f"| Matcheados contra `analisis` | {self.matched} |",
            f"| Recall (gold recuperados) | {self.recall:.1%} |",
            f"| Precisión (PDFs `complete_gasto`) | {prec} |",
            f"| Error relativo medio de monto (matcheados) | {mae} |",
            f"| S4 gold con `numero_acto` extraído | {self.s4_with_numero}/{self.s4_n} ({s4}) |",
            f"| Gold `is_gasto_publico=false` clasificados como gasto | "
            f"{self.gasto_false_positives} |",
            "",
            "## Matches",
            "",
            "| gold_id | filename | método | numero gold | numero extraído | "
            "monto error |",
            "|---|---|---|---|---|---:|",
        ]
        for item in self.matches:
            err = "" if item.monto_error is None else f"{item.monto_error:.1%}"
            ext_num = item.extracted.numero_acto if item.extracted else ""
            lines.append(
                f"| {item.gold.gold_id} | {item.gold.filename} | {item.method} | "
                f"{item.gold.numero_acto or ''} | {ext_num} | {err} |"
            )
        lines.extend(["", "## Gold sin match", ""])
        if not self.unmatched_gold:
            lines.append("_Ninguno._")
        else:
            for gold in self.unmatched_gold:
                lines.append(
                    f"- `{gold.gold_id}` {gold.filename} "
                    f"{gold.numero_acto or ''} {gold.organismo or ''}"
                )
        lines.append("")
        return "\n".join(lines)


def _parse_bool(raw: str | None) -> bool | None:
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw).strip().lower() in {"1", "true", "yes", "si", "sí"}


def _parse_float(raw: str | None) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(str(raw).strip().replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def load_gold_csv(path) -> list[GoldAct]:
    rows: list[GoldAct] = []
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                GoldAct(
                    filename=row["filename"].strip(),
                    gold_id=row["gold_id"].strip(),
                    tipo_acto=(row.get("tipo_acto") or "").strip() or None,
                    numero_acto=(row.get("numero_acto") or "").strip() or None,
                    organismo=(row.get("organismo") or "").strip() or None,
                    monto=_parse_float(row.get("monto")),
                    etapa=(row.get("etapa") or "").strip() or None,
                    is_gasto_publico=_parse_bool(row.get("is_gasto_publico")),
                    complete_gasto=bool(_parse_bool(row.get("complete_gasto"))),
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return rows


# numero_acto collisions (same digits, different pliego) are rejected above this.
NUMERO_MONTO_MAX_REL_ERR = 0.10
# organismo+monto fallback only accepts near-exact amounts.
ORG_MONTO_MAX_REL_ERR = 0.02


def _numero_hit(gold: GoldAct, extracted: ExtractedAct) -> bool:
    g = gold.numero_norm
    e = extracted.numero_norm
    if not g or not e:
        return False
    if g == e:
        return True
    return g in e or e in g


def _numero_conflict(gold: GoldAct, extracted: ExtractedAct) -> bool:
    """True when both sides have a number and they are not the same acto."""
    if not gold.numero_norm or not extracted.numero_norm:
        return False
    return not _numero_hit(gold, extracted)


def _organismo_hit(gold: GoldAct, extracted: ExtractedAct) -> bool:
    if not gold.organismo or not extracted.organismo:
        return False
    g = _normalize(gold.organismo)
    e = _normalize(extracted.organismo)
    if not g or not e:
        return False
    return g in e or e in g or _token_overlap(g, e) >= 0.5


def _token_overlap(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def match_one(gold: GoldAct, candidates: list[ExtractedAct]) -> GoldMatch:
    same_file = [c for c in candidates if c.filename == gold.filename]
    pool = same_file or candidates

    numbered: list[tuple[float, ExtractedAct]] = []
    for cand in pool:
        if not _numero_hit(gold, cand):
            continue
        err = relative_monto_error(cand.monto, gold.monto)
        if gold.monto is not None and cand.monto is not None and (err is None or err > NUMERO_MONTO_MAX_REL_ERR):
            continue
        numbered.append((0.0 if err is None else err, cand))
    if numbered:
        numbered.sort(key=lambda item: item[0])
        best = numbered[0][1]
        return GoldMatch(
            gold, best, "numero_acto",
            relative_monto_error(best.monto, gold.monto),
        )

    scored: list[tuple[float, ExtractedAct]] = []
    for cand in pool:
        if _numero_conflict(gold, cand):
            continue
        if not _organismo_hit(gold, cand):
            continue
        err = relative_monto_error(cand.monto, gold.monto)
        if err is None or err > ORG_MONTO_MAX_REL_ERR:
            continue
        scored.append((err, cand))
    if scored:
        scored.sort(key=lambda item: item[0])
        best = scored[0][1]
        return GoldMatch(
            gold, best, "organismo+monto",
            relative_monto_error(best.monto, gold.monto),
        )
    return GoldMatch(gold, None, "unmatched", None)


def evaluate_goldset(
    gold_acts: Iterable[GoldAct],
    extracted: Iterable[ExtractedAct],
) -> GoldMetrics:
    gold_list = list(gold_acts)
    extracted_list = list(extracted)
    matches = [match_one(gold, extracted_list) for gold in gold_list]
    hit = [m for m in matches if m.extracted is not None]
    unmatched = [m.gold for m in matches if m.extracted is None]

    complete_files = {g.filename for g in gold_list if g.complete_gasto}
    if complete_files:
        predicted_gasto = [
            e for e in extracted_list
            if e.filename in complete_files and e.is_gasto_publico
        ]
        matched_ids = {m.extracted.analisis_id for m in hit if m.extracted}
        tp = sum(1 for e in predicted_gasto if e.analisis_id in matched_ids)
        precision = (tp / len(predicted_gasto)) if predicted_gasto else None
    else:
        precision = None

    monto_errs = [m.monto_error for m in hit if m.monto_error is not None]
    s4_gold = [g for g in gold_list if "_4_Secc" in g.filename]
    s4_with_num = 0
    for gold in s4_gold:
        match = next(m for m in matches if m.gold.gold_id == gold.gold_id)
        if match.extracted and match.extracted.numero_norm:
            s4_with_num += 1

    false_gasto = 0
    for match in matches:
        if match.gold.is_gasto_publico is False and match.extracted is not None and match.extracted.is_gasto_publico:
            false_gasto += 1

    recall = len(hit) / len(gold_list) if gold_list else 0.0
    return GoldMetrics(
        gold_n=len(gold_list),
        matched=len(hit),
        recall=recall,
        precision=precision,
        monto_mae_rel=(sum(monto_errs) / len(monto_errs)) if monto_errs else None,
        s4_with_numero=s4_with_num,
        s4_n=len(s4_gold),
        s4_numero_pct=(s4_with_num / len(s4_gold)) if s4_gold else None,
        gasto_false_positives=false_gasto,
        matches=matches,
        unmatched_gold=unmatched,
    )


def extracted_from_db_row(row: Any, filename: str, section: str | None = None) -> ExtractedAct:
    mapping = dict(row) if not isinstance(row, ExtractedAct) else None
    if mapping is None:
        return row
    gasto = mapping.get("is_gasto_publico")
    if gasto is not None:
        gasto = bool(gasto)
    return ExtractedAct(
        analisis_id=int(mapping["id"]),
        filename=filename,
        section=section,
        tipo_acto=mapping.get("tipo_acto"),
        numero_acto=mapping.get("numero_acto"),
        organismo=mapping.get("organismo"),
        monto=mapping.get("monto_numerico"),
        etapa=mapping.get("etapa_gasto"),
        is_gasto_publico=gasto,
        descripcion=mapping.get("descripcion"),
    )
