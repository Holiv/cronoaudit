#!/usr/bin/env python3
"""Show which custom fields a schedule uses, so a profile can be built from evidence.

    python3 discover_fields.py model.json
    python3 discover_fields.py model.json --json candidates.json

Run this before customising anything. Asking "which field holds the discipline?"
makes someone recall a convention; showing them the populated fields with a sample
of their values makes them recognise one. Recognition is reliable, recall is not.

Field names are shown for the human but never matched on: they arrive translated by
the installed language, so the stable field id is the key. Types are inferred from
the values rather than the names, for the same reason.
"""
from __future__ import annotations

import argparse
import json
import sys

import custom_fields as cf_mod
import i18n

TEXT = {
    "en": {
        "title": "Custom fields in use",
        "declared": "declared in the file",
        "populated": "carrying values",
        "leaves": "leaf activities",
        "hdr": ("Field", "Alias", "Type", "Fill", "Distinct", "Set", "Sample"),
        "candidates": "Candidates by role, strongest first",
        "none": "No custom field is populated on more than a fifth of the activities.",
        "closed": "closed",
        "free": "free",
        "footer": [
            "A closed set with a high fill rate is a good grouping field.",
            "Free text with hundreds of distinct values is a note, not a dimension.",
            "Nothing here is a decision: confirm each one before a profile relies on it.",
        ],
        "undeclared": "populated but not declared in the file's own field list",
        "sparse_title": "Barely populated, and that is the finding",
        "sparse_note": "These fields exist and are almost empty. Do not configure them as "
                       "dimensions; report the emptiness.",
        "sparse_tail": "filled on almost nothing",
    },
    "pt": {
        "title": "Campos personalizados em uso",
        "declared": "declarados no arquivo",
        "populated": "com valores",
        "leaves": "atividades folha",
        "hdr": ("Campo", "Apelido", "Tipo", "Preench.", "Distintos", "Conjunto", "Amostra"),
        "candidates": "Candidatos por papel, o mais forte primeiro",
        "none": "Nenhum campo personalizado está preenchido em mais de um quinto das atividades.",
        "closed": "fechado",
        "free": "livre",
        "footer": [
            "Conjunto fechado com preenchimento alto é um bom campo de agrupamento.",
            "Texto livre com centenas de valores distintos é uma nota, não uma dimensão.",
            "Nada aqui é decisão: confirme cada um antes de um perfil depender dele.",
        ],
        "undeclared": "preenchido mas não declarado na lista de campos do arquivo",
        "sparse_title": "Quase sem preenchimento, e é isso que é o achado",
        "sparse_note": "Estes campos existem e estão quase vazios. Não configure como "
                       "dimensão; reporte o vazio.",
        "sparse_tail": "preenchido em quase nada",
    },
}


def render(discovery: dict, candidates: dict, sparse: dict, lang: str) -> str:
    T = TEXT.get(lang, TEXT["en"])
    lines = [
        f"{T['title']}: {discovery['declared']} {T['declared']}, "
        f"{discovery['populated']} {T['populated']}, "
        f"{discovery['total_leaves']} {T['leaves']}",
        "",
    ]
    hdr = T["hdr"]
    lines.append(
        f"  {hdr[0]:<16}{hdr[1]:<26}{hdr[2]:<8}{hdr[3]:>7}  {hdr[4]:>9}  {hdr[5]:<10}{hdr[6]}"
    )
    lines.append("  " + "-" * 104)
    for r in discovery["fields"]:
        if not r["populated"]:
            continue
        name = (r["field_name"] or r["field_id"])[:15]
        alias = (r["alias"] or ("? " + T["undeclared"][:20]))[:25]
        st = T["closed"] if r["closed_set"] else T["free"]
        sample = " | ".join(r["sample"][:3])[:44]
        lines.append(
            f"  {name:<16}{alias:<26}{r['type']:<8}{r['fill_rate']:>6.1f}%  "
            f"{str(r['distinct']):>9}  {st:<10}{sample}"
        )

    lines += ["", T["candidates"], ""]
    if not candidates:
        lines.append(f"  {T['none']}")
    for role, items in sorted(candidates.items()):
        if role == "unclassified":
            continue
        lines.append(f"  {role}")
        for it in items[:3]:
            st = T["closed"] if it["closed_set"] else T["free"]
            lines.append(
                f"      {str(it['alias'] or it['field_name']):<26}"
                f"{it['fill_rate']:>6.1f}%  {str(it['distinct']):>6} {st:<8}"
                f"{' | '.join(it['sample'][:3])[:40]}"
            )
    if sparse:
        lines += ["", T["sparse_title"], "", f"  {T['sparse_note']}", ""]
        for role, items in sorted(sparse.items()):
            for it in items:
                lines.append(
                    f"  {role:<16}{str(it['alias'] or it['field_name']):<26}"
                    f"{it['fill_rate']:>6.1f}%   {T['sparse_tail']}"
                )
    lines += [""] + [f"  {line}" for line in T["footer"]]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("model", help="JSON produced by parse_mspdi.py")
    ap.add_argument("--json", help="write the candidates here, for a profile to build on")
    ap.add_argument("--min-fill", type=float, default=20.0,
                    help="ignore fields populated on less than this share of activities")
    ap.add_argument("--lang", choices=["en", "pt"])
    args = ap.parse_args()

    with open(args.model, encoding="utf-8") as fh:
        model = json.load(fh)
    discovery = model.get("custom_fields")
    if not discovery:
        raise SystemExit(
            "This model has no custom_fields block. Re-run parse_mspdi.py to produce one."
        )
    lang = args.lang or i18n.detect(model)["lang"]
    candidates, sparse = cf_mod.interview_candidates(discovery, args.min_fill)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"lang": lang, "candidates": candidates, "sparse": sparse,
                       "fields": discovery["fields"]}, fh, indent=2, ensure_ascii=False)
        print(f"candidates -> {args.json}", file=sys.stderr)
    print(render(discovery, candidates, sparse, lang))


if __name__ == "__main__":
    main()
