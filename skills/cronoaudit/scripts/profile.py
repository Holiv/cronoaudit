#!/usr/bin/env python3
"""The organisation profile: everything an organisation may declare instead of
having it coded.

Every key has a default that works with no profile at all, so the skill runs
ready-to-use; the profile only narrows. Nothing here is required. The transferable
idea is that an organisation's mapping is declared, not coded, so one codebase
serves organisations that keep their meaning in different places.

Field references accept a stable field id, an alias, or a field name; resolution
happens against the file at run time and a name that does not exist is reported,
never silently ignored.
"""
from __future__ import annotations

import json
import os

VERSION = 1

DEFAULTS = {
    "version": VERSION,
    "organisation": "",
    "lang": None,                   # None = follow the schedule's own language
    "ev_method": None,              # None = as declared in the file; "physical" | "percent"
    "baseline_slot": None,          # None = elected by coverage; "0".."10" to force
    "threshold_days": 30,           # E and C, working days of the activity's calendar
    "tolerance_days": 1,            # G
    "checks_optional": [],          # e.g. ["B", "F"] to promote standby checks to findings
    "grouping": "wbs",              # "wbs" or a custom field (alias, name or id)
    "fields": {                     # role -> custom field (alias, name or id), all optional
        "discipline": None, "service": None, "section": None, "work_front": None,
        "justification": None, "quantity": None, "unit": None,
        "productivity_contracted": None, "regulator_code": None,
    },
    "productivity": {"recent_days": 30, "thin_evidence_days": 10, "thin_evidence_share": 0.02},
    "rain": {"reserve_days_per_month": 4},
    "lookahead_weeks": [4, 8],
    "theme": {"accent": None, "crit": None, "warn": None, "good": None,
              "font_display": None, "font_sans": None, "font_mono": None, "logo_text": None},
    "template": None,               # a customised report template path
    "sections_hidden": [],          # e.g. ["v6", "v9"] to hide sections the organisation does not use
}

CHECK_CODES = {"A1", "A2", "H", "E", "C", "G", "B", "F", "P"}
EV_METHODS = {None, "physical", "percent"}


def deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path: str | None) -> dict:
    """Defaults, overlaid by the file when given. Missing file is an error; no
    path at all is the ready-to-use default."""
    if not path:
        return json.loads(json.dumps(DEFAULTS))
    if not os.path.exists(path):
        raise SystemExit(f"Profile not found: {path}")
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    prof = deep_merge(DEFAULTS, raw)
    problems = validate(prof)
    if problems:
        raise SystemExit("Profile problems:\n  - " + "\n  - ".join(problems))
    return prof


def validate(prof: dict) -> list:
    p = []
    if prof.get("ev_method") not in EV_METHODS:
        p.append(f"ev_method must be physical, percent or null, not {prof.get('ev_method')!r}")
    if prof.get("lang") not in (None, "en", "pt"):
        p.append(f"lang must be en, pt or null, not {prof.get('lang')!r}")
    bad = [c for c in prof.get("checks_optional") or [] if c not in CHECK_CODES]
    if bad:
        p.append(f"checks_optional has unknown codes: {bad}")
    if not isinstance(prof.get("threshold_days"), int) or prof["threshold_days"] < 1:
        p.append("threshold_days must be a positive integer of working days")
    slot = prof.get("baseline_slot")
    if slot is not None and str(slot) not in {str(i) for i in range(11)}:
        p.append("baseline_slot must be null or 0..10")
    w = prof.get("lookahead_weeks") or []
    if not w or any((not isinstance(x, int)) or x < 1 for x in w):
        p.append("lookahead_weeks must be a list of positive integers")
    return p


def resolve_field(model: dict, ref) -> dict | None:
    """A custom field by id, alias or name, against the file; None if absent."""
    if not ref:
        return None
    wanted = str(ref).strip().lower()
    for row in (model.get("custom_fields") or {}).get("fields", []):
        for key in ("field_id", "alias", "field_name"):
            v = row.get(key)
            if v and str(v).strip().lower() == wanted:
                return row
    return None


def resolve_fields(model: dict, prof: dict) -> tuple:
    """(resolved role -> field row, list of references not found in the file)."""
    resolved, missing = {}, []
    for role, ref in (prof.get("fields") or {}).items():
        if not ref:
            continue
        row = resolve_field(model, ref)
        if row:
            resolved[role] = row
        else:
            missing.append(f"{role}: {ref}")
    return resolved, missing


def example() -> dict:
    ex = json.loads(json.dumps(DEFAULTS))
    ex.update({
        "organisation": "Example Infrastructure Programme",
        "lang": None, "ev_method": None, "grouping": "DISCIPLINE",
        "fields": {**ex["fields"], "discipline": "DISCIPLINE", "section": "SECTION",
                   "justification": "JUSTIFICATION", "productivity_contracted": "CREW RATE"},
        "checks_optional": ["B"],
        "theme": {**ex["theme"], "accent": "#1B4D8F", "logo_text": "EIP"},
    })
    return ex
