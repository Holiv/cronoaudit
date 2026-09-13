#!/usr/bin/env python3
"""Create and edit an organisation profile without touching JSON by hand.

    python3 profile_tool.py init  [--out profile.json] [--organisation "..."]
    python3 profile_tool.py discover model.json            # candidates to fill the fields
    python3 profile_tool.py set profile.json key=value ...  # dotted keys: fields.discipline=DISCIPLINA
    python3 profile_tool.py show profile.json [model.json]  # with resolution against a file
    python3 profile_tool.py validate profile.json
    python3 profile_tool.py example                          # a filled example to copy

The interview that fills a profile is conversational and lives in the skill
itself; this tool is what that conversation writes with. Show candidates first,
then ask -- recognition beats recall.
"""
from __future__ import annotations

import argparse
import json
import sys

import custom_fields as cf_mod
import i18n
import profile as prof_mod


def parse_value(raw: str):
    low = raw.strip().lower()
    if low in ("null", "none", ""):
        return None
    if low in ("true", "false"):
        return low == "true"
    if raw.startswith("[") or raw.startswith("{"):
        return json.loads(raw)
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def set_path(d: dict, dotted: str, value):
    parts = dotted.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def cmd_init(a):
    prof = json.loads(json.dumps(prof_mod.DEFAULTS))
    if a.organisation:
        prof["organisation"] = a.organisation
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(prof, fh, indent=2, ensure_ascii=False)
    print(a.out)


def cmd_set(a):
    with open(a.profile, encoding="utf-8") as fh:
        prof = json.load(fh)
    for pair in a.pairs:
        if "=" not in pair:
            raise SystemExit(f"expected key=value, got {pair!r}")
        k, v = pair.split("=", 1)
        set_path(prof, k.strip(), parse_value(v))
    merged = prof_mod.deep_merge(prof_mod.DEFAULTS, prof)
    problems = prof_mod.validate(merged)
    if problems:
        raise SystemExit("Not saved. Problems:\n  - " + "\n  - ".join(problems))
    with open(a.profile, "w", encoding="utf-8") as fh:
        json.dump(prof, fh, indent=2, ensure_ascii=False)
    print(a.profile)


def cmd_show(a):
    prof = prof_mod.load(a.profile)
    print(json.dumps(prof, indent=2, ensure_ascii=False))
    if a.model:
        with open(a.model, encoding="utf-8") as fh:
            model = json.load(fh)
        resolved, missing = prof_mod.resolve_fields(model, prof)
        print("\nfields resolved against the file:")
        for role, row in resolved.items():
            print(f"  {role:<24} -> {row.get('alias') or row.get('field_name')} ({row['field_id']}), "
                  f"fill {row.get('fill_rate')}%")
        for m in missing:
            print(f"  NOT FOUND: {m}")
        g = prof.get("grouping")
        if g and g != "wbs" and not prof_mod.resolve_field(model, g):
            print(f"  NOT FOUND: grouping: {g}")


def cmd_validate(a):
    prof = prof_mod.load(a.profile)
    print("ok" if not prof_mod.validate(prof) else "problems")


def cmd_discover(a):
    with open(a.model, encoding="utf-8") as fh:
        model = json.load(fh)
    disc = model.get("custom_fields") or {}
    lang = a.lang or i18n.detect(model)["lang"]
    cands, sparse = cf_mod.interview_candidates(disc, a.min_fill)
    roles = ["discipline", "service", "section", "work_front", "justification", "quantity",
             "unit", "productivity", "regulator_code", "status_note"]
    print("role                     candidate (alias)            fill    distinct  sample")
    for role in roles:
        for it in (cands.get(role) or [])[:3]:
            print(f"{role:<24} {str(it['alias'] or it['field_name']):<28} {it['fill_rate']:>5.1f}%  "
                  f"{str(it['distinct']):>8}  {' | '.join(it['sample'][:3])[:40]}")
    for role, items in sparse.items():
        for it in items:
            print(f"{role:<24} {str(it['alias'] or it['field_name']):<28} {it['fill_rate']:>5.1f}%  "
                  f"{'':>8}  (barely filled: a finding, not a dimension)")
    print(f"\nlanguage detected: {lang}")


def cmd_example(a):
    print(json.dumps(prof_mod.example(), indent=2, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init"); s.add_argument("--out", default="profile.json"); s.add_argument("--organisation")
    s.set_defaults(fn=cmd_init)
    s = sub.add_parser("set"); s.add_argument("profile"); s.add_argument("pairs", nargs="+")
    s.set_defaults(fn=cmd_set)
    s = sub.add_parser("show"); s.add_argument("profile"); s.add_argument("model", nargs="?")
    s.set_defaults(fn=cmd_show)
    s = sub.add_parser("validate"); s.add_argument("profile"); s.set_defaults(fn=cmd_validate)
    s = sub.add_parser("discover"); s.add_argument("model"); s.add_argument("--min-fill", type=float, default=20.0)
    s.add_argument("--lang", choices=["en", "pt"]); s.set_defaults(fn=cmd_discover)
    s = sub.add_parser("example"); s.set_defaults(fn=cmd_example)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
