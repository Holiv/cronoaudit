#!/usr/bin/env python3
"""Discover which custom fields a schedule actually uses, and what is in them.

An organisation keeps its own meaning in custom fields: discipline, work front,
contractor, justification, quantity, regulator code. That mapping is the
organisation's asset and cannot be guessed from a schema. But it can be
*discovered* -- and asking someone "which field holds the discipline?" is a much
worse question than showing them the five fields that are populated, with a sample
of their values, and asking which is which.

Two rules this module follows, both learned the hard way:

* **Key on the stable identifier, never on the field name.** Field names arrive
  translated by the installed language: the same field reads `Text1` or `Texto1`,
  `Flag20` or `Sinalizador20`. Code that matches on the name breaks on the next
  file from a differently-localised machine.
* **Infer the type from the values, not from the name.** Same reason, and it also
  catches a field whose name says one thing and whose content says another.
"""
from __future__ import annotations

import re
from collections import Counter

NS = {"p": "http://schemas.microsoft.com/project"}

# Alias keywords that suggest a role, in both languages. Suggestions only: the
# report says "candidate", never "is". A wrong confident guess about which field
# holds the discipline is worse than no guess, because nobody re-checks it.
ROLE_HINTS = {
    "discipline": ["disciplina", "discipline", "especialidade", "trade"],
    "work_front": ["frente", "front", "trecho", "lote", "segment", "section"],
    "chainage": ["km", "estaca", "chainage", "station", "progressiva"],
    "contractor": ["contratada", "contractor", "empreiteira", "subcontract", "fornecedor"],
    "contract": ["contrato", "contract", "pedido", "order"],
    "phase": ["fase", "phase", "etapa", "pre-obra", "pré-obra", "stage"],
    "justification": ["justificativa", "justification", "motivo", "reason", "cause", "causa"],
    "status_note": ["situacao", "situação", "status", "situation"],
    "quantity": ["qtde", "quantidade", "quantity", "qty"],
    "unit": ["und", "unidade", "unit", "uom"],
    "regulator_code": ["per", "pep", "wbs code", "codigo", "código", "regulator"],
    "planned_percent": ["prev", "previsto", "planned", "plan %"],
    "productivity": ["prod", "produtividade", "productivity", "rendimento"],
}

# The value type a role should have. A field called "Status Date" matches the word
# "status" but holds a date, and ranking it above the real status field would put a
# timestamp where a category belongs.
ROLE_TYPES = {
    "discipline": {"text"}, "work_front": {"text"}, "contractor": {"text"},
    "contract": {"text"}, "phase": {"text"}, "justification": {"text"},
    "status_note": {"text"}, "unit": {"text"}, "regulator_code": {"text", "number"},
    "chainage": {"number"}, "quantity": {"number"}, "planned_percent": {"number"},
    "productivity": {"number"},
}

# Roles worth reporting even when barely populated, because emptiness is the
# finding. A justification field blank on 96% of activities is not a field to
# ignore -- it is a contract-compliance finding waiting to be written down.
EMPTINESS_MATTERS = {"justification", "status_note", "planned_percent"}

_NUM = re.compile(r"^-?\d+([.,]\d+)?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_BOOL = {"0", "1", "true", "false", "sim", "nao", "não", "yes", "no"}


def _text(node, tag):
    if node is None:
        return None
    el = node.find(f"p:{tag}", NS)
    return el.text.strip() if el is not None and el.text else None


def infer_type(values: list) -> str:
    """The type the content actually is, regardless of what the field is called."""
    if not values:
        return "empty"
    sample = values[:400]
    if all(v.lower() in _BOOL for v in sample):
        return "flag"
    if all(_DATE.match(v) for v in sample):
        return "date"
    if all(_NUM.match(v) for v in sample):
        return "number"
    return "text"


def suggest_role(alias: str, field_name: str) -> list:
    """Candidate roles for a field, from its alias. Ranked, never asserted."""
    hay = f"{alias or ''} {field_name or ''}".lower()
    hits = []
    for role, words in ROLE_HINTS.items():
        for w in words:
            if w in hay:
                # A longer match is a stronger signal than a two-letter one.
                hits.append((len(w), role))
                break
    hits.sort(reverse=True)
    return [role for _, role in hits]


def discover(root, tasks_el=None) -> dict:
    """Definitions plus what is actually in them, per stable field identifier."""
    definitions = {}
    for el in root.findall("p:ExtendedAttributes/p:ExtendedAttribute", NS):
        fid = _text(el, "FieldID")
        if not fid:
            continue
        lookup = el.find("p:ValueList", NS)
        definitions[fid] = {
            "field_id": fid,
            # Localised display name. Kept for the human, never matched on.
            "field_name": _text(el, "FieldName"),
            "alias": _text(el, "Alias"),
            "has_value_list": lookup is not None and len(lookup) > 0,
        }

    populated = Counter()
    populated_leaves = Counter()
    samples: dict[str, list] = {}
    distinct: dict[str, set] = {}

    for task in root.findall("p:Tasks/p:Task", NS):
        is_leaf = _text(task, "Summary") != "1"
        for ea in task.findall("p:ExtendedAttribute", NS):
            fid = _text(ea, "FieldID")
            value = _text(ea, "Value")
            if not fid or value is None or value == "":
                continue
            populated[fid] += 1
            if is_leaf:
                populated_leaves[fid] += 1
            bucket = samples.setdefault(fid, [])
            if len(bucket) < 400:
                bucket.append(value)
            seen = distinct.setdefault(fid, set())
            if len(seen) < 500:
                seen.add(value)

    total_leaves = sum(
        1 for t in root.findall("p:Tasks/p:Task", NS) if _text(t, "Summary") != "1"
    )

    rows = []
    for fid in set(list(definitions) + list(populated)):
        d = definitions.get(fid, {"field_id": fid, "field_name": None, "alias": None,
                                  "has_value_list": False})
        vals = samples.get(fid, [])
        seen = distinct.get(fid, set())
        n_leaves = populated_leaves.get(fid, 0)
        common = Counter(vals).most_common(6)
        rows.append({
            **d,
            "declared": fid in definitions,
            "populated": populated.get(fid, 0),
            "populated_leaves": n_leaves,
            "fill_rate": round(n_leaves / total_leaves * 100, 1) if total_leaves else 0.0,
            "distinct": len(seen) if len(seen) < 500 else "500+",
            "type": infer_type(vals),
            # A small closed set groups well; free text does not.
            "closed_set": len(seen) <= 40 and len(seen) > 0,
            "sample": [v[:60] for v, _ in common],
            "suggested_roles": suggest_role(d.get("alias"), d.get("field_name")),
        })

    rows.sort(key=lambda r: (-r["populated_leaves"], str(r["field_name"])))
    return {
        "total_leaves": total_leaves,
        "declared": len(definitions),
        "populated": sum(1 for r in rows if r["populated"]),
        "fields": rows,
    }


def interview_candidates(discovery: dict, min_fill: float = 20.0) -> tuple:
    """The fields worth asking about, grouped by the role they might serve.

    Returns (candidates, sparse). Ordered so an interview can put the strongest
    candidate first and let the person confirm or correct it, rather than recall
    which field holds what. Recognition is reliable; recall is not.
    """
    def entry(row):
        return {
            "field_id": row["field_id"],
            "field_name": row["field_name"],
            "alias": row["alias"],
            "fill_rate": row["fill_rate"],
            "distinct": row["distinct"],
            "closed_set": row["closed_set"],
            "type": row["type"],
            "sample": row["sample"][:4],
        }

    out: dict[str, list] = {}
    sparse: dict[str, list] = {}
    for row in discovery["fields"]:
        if not row["populated"]:
            continue
        roles = row["suggested_roles"] or ["unclassified"]
        for role in roles:
            if row["fill_rate"] >= min_fill:
                out.setdefault(role, []).append(entry(row))
            elif role in EMPTINESS_MATTERS:
                # Not a candidate to configure: a finding to report.
                sparse.setdefault(role, []).append(entry(row))

    for bucket in (out, sparse):
        for role in bucket:
            expected = ROLE_TYPES.get(role)
            bucket[role].sort(key=lambda r: (
                # A field whose content type does not suit the role goes last, however
                # well its name matches.
                bool(expected) and r["type"] not in expected,
                not r["closed_set"],
                -r["fill_rate"],
            ))
    return out, sparse
