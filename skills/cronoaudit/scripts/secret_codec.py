#!/usr/bin/env python3
"""Secret mode, the codec: what an agent reads instead of the schedule. EXPERIMENTAL.

The engine runs on the real data, unchanged. This module only rewrites its OUTPUT
(the JSON sidecars and the payload embedded in the HTML report) so that an agent
reading it sees codes instead of what identifies the works, and so that the coded
output decodes back to the engine's own output exactly. That last property is the
validity criterion: findings computed on the real data, read in code, decoded on
this machine. A codec that did not round-trip would make the agent's analysis
apply to something else.

What becomes a code and what stays legible is a product decision, written down in
LEGIBILITY below and nowhere else.

    names (tasks, resources, calendars, holidays, custom-field aliases and values,
    project header fields, notes, file name)    ->  T·3fa91c  (one token per text)
    money                                       ->  times a secret factor k
    dates                                       ->  D+0412    (days from a secret origin)

Dates are shifted, never scaled: a scaled date would scale every duration and every
delay with it, which is the very failure this skill hunts.

Every coded shape carries the shape it came from, so decoding never guesses:

    2026-10-30            D+0412        an ISO day (alone, or inside a sentence)
    2026-10-30T17:00:00   D+0412T17:00:00   the time of day is not coded
    30/10/2026            d+0412        the same day, in the report's display form
    2026-10               M+0013        a month, counted in months from the origin's
    2026  (a year)        Y+0001        years from the origin's year
    1.234.567 (money in a sentence)   ¤8.543.210   the mark says "coded money"

Stdlib only, Windows and macOS.
"""
from __future__ import annotations

import hashlib
import hmac
import math
import re
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# The boundary. One place, on purpose: what an agent may read is decided here.
# TODO(per-company): let the organisation profile narrow or widen this list (for
# example a company whose WBS codes carry the contract number, or one that wants
# resource units coded too). Until then the default below is the only boundary.
# ---------------------------------------------------------------------------
LEGIBILITY = {
    # XML elements whose text stays legible although it contains letters. Everything
    # else with letters in the file becomes a token (fail-safe: an element nobody
    # thought of is coded, not leaked).
    "legible_tags": frozenset({
        "WBS", "OutlineNumber",            # how a planner finds a row; kept by decision
        "MaterialLabel",                   # units (m³, t, km): needed to read a rate
        "CurrencySymbol", "CurrencyCode",  # the money is coded; the unit is not
        "FieldName",                       # Text1, Number3: the tool's own field names
    }),
    # Keys of the engine's JSON whose numbers are money and are multiplied by k.
    # Every ratio built from them (SPI, CPI, percentages, weights) stays legible,
    # because k cancels out of a ratio.
    "money_keys": frozenset({
        "bac", "budget", "budget_at_completion", "baseline_cost", "cost",
        "planned", "earned", "earned_alt", "planned_cum", "earned_cum", "earned_alt_cum",
        "planned_to_date", "earned_to_date", "earned_alt_to_date", "earned_phased_after_status",
        "sv", "sv_cum", "earned_computed", "earned_file", "difference",
        "ahead_of_baseline_value", "planned_earning", "projected_earning_at_practised_rate",
        "remaining_total", "in_reserve", "remaining",
        "bcws", "bcwp", "acwp", "fixed_cost", "actual_cost", "remaining_cost",
        # residual terms of the cycle (0.7.2)
        "bac_before", "bac_after", "bac_delta", "inserted_cost", "removed_cost", "changed_cost",
        "earned_erased", "baseline_cost_before", "baseline_cost_after", "ev",
        # percent complete against physical percent (0.8)
        "value_at_stake",
    }),
    # Withheld from the coded layer altogether, and restored from the vault on the
    # way back. The rain-reserve share per month repeats every twelve month-codes
    # and so tells the season, hence the hemisphere and the calendar month, even
    # with every month coded. The aggregate shares stay; the monthly series does not.
    "withheld": (("forecast", "rain_exposure", "months"),),
    "legible": "durations, percentages and percentage points, counts, SPI/CPI/TSPI and "
               "every other ratio, task IDs and UIDs, WBS codes, units of quantity, "
               "quantities and rates, the currency symbol",
}

# Category letters, in priority order: a text that is both a task name and a
# calendar name gets one token, the first category's.
CATEGORIES = {
    "P": "project header", "F": "file name", "T": "task name", "R": "resource",
    "C": "calendar", "H": "calendar exception (holiday)", "A": "custom-field alias",
    "V": "custom-field value", "N": "note or other free text", "O": "organisation profile",
}
_TAG_CATEGORY = {
    "Title": "P", "Subject": "P", "Company": "P", "Author": "P", "Manager": "P",
    "Category": "P", "Keywords": "P", "Comments": "P", "LastAuthor": "P",
    "Alias": "A", "Value": "V", "Description": "V",
    "Initials": "R", "Group": "R", "Code": "R", "EmailAddress": "R", "NTAccount": "R",
    "Notes": "N", "Hyperlink": "N", "HyperlinkAddress": "N", "HyperlinkSubAddress": "N",
    "Contact": "N",
}
_NAME_BY_PARENT = {"Project": "P", "Task": "T", "Resource": "R", "Calendar": "C",
                   "Exception": "H", "WeekDay": "H"}

TOKEN_SEP = "·"            # U+00B7: in every Windows code page a console uses
WIDTH = 6                  # hex digits; 16.7 million per category, collisions resolved
MONEY_MARK = "¤"

# A token, strictly: one capital, the separator, exactly WIDTH lowercase hex digits,
# and no word character on either side, so no token can sit inside another.
def _token_re(width: int) -> re.Pattern:
    return re.compile(r"(?<![\w" + TOKEN_SEP + r"])([A-Z])" + TOKEN_SEP + r"([0-9a-f]{%d})(?![0-9A-Za-z])" % width)


def _lenient_token_re(width: int) -> re.Pattern:
    # What an agent may have done to a token when writing prose: a dot or a hyphen
    # instead of the middle dot. Only for the agent's own text, never for the
    # engine's output, where the strict form is the only one produced.
    return re.compile(r"(?<![\w" + TOKEN_SEP + r"])([A-Z])[" + TOKEN_SEP + r".\-_]([0-9a-f]{%d})(?![0-9A-Za-z])" % width)


# The coded date shapes. The look-behind keeps a code from starting inside a word
# or a token.
_CODE_DAY = re.compile(r"(?<![\w" + TOKEN_SEP + r"+\-])([Dd])([+-])(\d{4,6})(?!\d)")
_CODE_MONTH = re.compile(r"(?<![\w" + TOKEN_SEP + r"+\-])M([+-])(\d{4,6})(?!\d)")
_CODE_YEAR = re.compile(r"(?<![\w" + TOKEN_SEP + r"+\-])Y([+-])(\d{4,6})(?!\d)")
_CODE_YEAR_WHOLE = re.compile(r"Y([+-])(\d{4,6})")
_CODE_MONEY = re.compile(re.escape(MONEY_MARK) + r"\s?(-?\d[\d.,]*\d|-?\d)")

# The real date shapes the engine writes.
_ISO_DAY = re.compile(r"(?<![\w" + TOKEN_SEP + r"])(\d{4})-(\d{2})-(\d{2})(?!\d)")
_DMY = re.compile(r"(?<![\w" + TOKEN_SEP + r"/])(\d{2})/(\d{2})/(\d{4})(?![\d/])")
_PERIOD = re.compile(r"(?<![\w" + TOKEN_SEP + r"\-])(\d{4})-(\d{2})(?![\d\-])")
# A bare year is coded only where the engine writes one as a label, "2026: ...";
# a free-standing 2026 in a sentence is as likely to be a count.
_YEAR_LABEL = re.compile(r"(?<![\w" + TOKEN_SEP + r"])((?:19|20|21)\d\d)(?=:(?!\d))")

# Anything in the real output that already looks like a code would be decoded into
# something it never was. Such a file is refused, not coded.
CODE_LIKE = re.compile(
    r"[A-Z]" + TOKEN_SEP + r"[0-9a-f]{4,}"
    r"|(?<![\w])[DdMY][+-]\d{4,6}(?!\d)"
    r"|" + re.escape(MONEY_MARK))

_LETTER = re.compile(r"[^\W\d_]")
_ISO_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T[\d:.]+)?$")
_ISO_DURATION = re.compile(r"^-?P(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:[\d.]+S)?)?$")
_GUID = re.compile(r"^\{?[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}?$")


def eligible(text) -> bool:
    """Whether a text from the file becomes a token.

    At least two characters and one letter. A value made only of digits and signs
    stays legible (it is far more often a quantity than a name) and a single letter
    stays legible (S/N flags); both are stated limits.
    """
    if not isinstance(text, str):
        return False
    t = text.strip()
    return len(t) >= 2 and bool(_LETTER.search(t))


def format_legible(text: str) -> bool:
    """Texts the file writes in a machine format: dates, durations, GUIDs."""
    t = text.strip()
    return bool(_ISO_STAMP.match(t) or _ISO_DURATION.match(t) or _GUID.match(t))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def collect_xml(path: str) -> list:
    """Every text of the file that the boundary says becomes a token, with its category.

    Streams the file (a real export runs to tens of megabytes of time-phased data)
    and keeps nothing but the texts.
    """
    import xml.etree.ElementTree as ET
    out, stack = [], []
    for event, el in ET.iterparse(path, events=("start", "end")):
        if event == "start":
            stack.append(_local(el.tag))
            continue
        tag = stack.pop()
        text = el.text
        if text and tag not in LEGIBILITY["legible_tags"] and eligible(text) \
                and not format_legible(text):
            parent = stack[-1] if stack else ""
            if tag == "Name":
                cat = _NAME_BY_PARENT.get(parent, "N")
            else:
                cat = _TAG_CATEGORY.get(tag, "N")
            out.append((cat, text.strip()))
        el.clear()
    return out


def collect_model(model: dict) -> list:
    """Texts as the engine parsed them, in case a parser normalised one differently."""
    out = []
    p = model.get("project") or {}
    for key in ("title", "name"):
        if eligible(p.get(key)):
            out.append(("P", p[key].strip()))
    for t in model.get("tasks") or []:
        if eligible(t.get("name")):
            out.append(("T", t["name"].strip()))
        for v in (t.get("custom") or {}).values():
            if eligible(v):
                out.append(("V", str(v).strip()))
    for c in ((model.get("calendars") or {}).get("in_use") or []):
        if eligible(c.get("name")):
            out.append(("C", c["name"].strip()))
    for f in ((model.get("custom_fields") or {}).get("fields") or []):
        if eligible(f.get("alias")):
            out.append(("A", f["alias"].strip()))
    return out


def collect_profile(profile: dict) -> list:
    out = []
    for value in (profile.get("organisation"), (profile.get("theme") or {}).get("logo_text")):
        if eligible(value):
            out.append(("O", value.strip()))
    return out


def collect_file(path: str) -> list:
    import os
    base = os.path.basename(path)
    stem = os.path.splitext(base)[0]
    return [("F", v) for v in (base, stem) if eligible(v)]


# ---------------------------------------------------------------------------
# Numbers in the report's notation, for money inside a sentence.
# ---------------------------------------------------------------------------
def fnum(v: float, d: int, lang: str) -> str:
    """Same rule as narrative.fnum: thousands grouped, never a negative zero."""
    v = round(float(v), d)
    if v == 0:
        v = 0.0
    s = f"{v:,.{d}f}"
    if lang == "pt":
        s = s.replace(",", " ").replace(".", ",").replace(" ", ".")
    return s


def parse_num(s: str, lang: str):
    """A number written in the report's notation -> (value, decimals shown).

    Strictly the notation of the report's language: "1.234,56" in Portuguese,
    "1,234.56" otherwise. A figure an agent writes in the other notation is read
    wrongly; SKILL.md tells it to write money the way the report does.
    """
    s = s.strip()
    dec, th = (",", ".") if lang == "pt" else (".", ",")
    body = s.replace(th, "")
    if dec in body:
        whole, frac = body.split(dec, 1)
        return float(whole + "." + frac), len(frac)
    return float(body), 0


# ---------------------------------------------------------------------------
# The trie: one regular expression for thousands of names, longest match first.
# ---------------------------------------------------------------------------
def _trie_pattern(words) -> str:
    trie: dict = {}
    for w in words:
        node = trie
        for ch in w:
            node = node.setdefault(ch, {})
        node[""] = True

    def build(node) -> str:
        end = "" in node
        kids = sorted(k for k in node if k)
        if not kids:
            return ""
        # A run of single children with no word ending in between is a literal.
        if len(kids) == 1 and not end:
            ch = kids[0]
            return re.escape(ch) + build(node[ch])
        alts = [re.escape(ch) + build(node[ch]) for ch in kids]
        return "(?:" + "|".join(alts) + ")" + ("?" if end else "")

    return build(trie)


class Codec:
    """One project's codes: the key, the token table, the date origin and k.

    `tokens` maps a real text to its token and is persisted per project, so rev03
    and rev04 of the same schedule share every token, the origin and k, and a
    comparison between them reads the same codes on both sides.
    """

    def __init__(self, key: bytes, origin: date, k: float, tokens: dict | None = None,
                 width: int = WIDTH, lang: str = "en", currency: str = ""):
        if not (k > 1):
            # k > 1 is what makes a rounded coded figure decode to the same rounded
            # real figure: the rounding error shrinks when divided by k.
            raise ValueError("the money factor must be greater than 1")
        self.key = key
        self.origin = origin
        self.k = float(k)
        self.width = width
        self.lang = lang
        self.currency = currency
        self.tokens: dict = dict(tokens or {})          # real -> token
        self.back: dict = {t: r for r, t in self.tokens.items()}   # token -> real
        self._matcher = None
        self._strict = _token_re(width)
        self._lenient = _lenient_token_re(width)
        self.collisions = 0

    # ---- tokens
    def _hash(self, cat: str, value: str, i: int) -> str:
        msg = f"{cat}\x00{value}\x00{i}".encode("utf-8")
        return hmac.new(self.key, msg, hashlib.sha256).hexdigest()[: self.width]

    def add(self, pairs) -> int:
        """Give every new text a token. Returns how many were new.

        Deterministic (HMAC of the text under the project key) and collision-safe:
        a token already taken by another text is never reused; the counter moves on.
        """
        new = 0
        order = {c: i for i, c in enumerate(CATEGORIES)}
        for cat, value in sorted(set(pairs), key=lambda p: (order.get(p[0], 99), p[1])):
            if value in self.tokens:
                continue
            i = 0
            while True:
                tok = f"{cat}{TOKEN_SEP}{self._hash(cat, value, i)}"
                if tok not in self.back:
                    break
                i += 1
                self.collisions += 1
            self.tokens[value] = tok
            self.back[tok] = value
            new += 1
        if new:
            self._matcher = None
        return new

    def _names(self):
        if self._matcher is None:
            words = sorted(self.tokens, key=len, reverse=True)
            if words:
                # No word character on either side, and never inside a {placeholder}
                # of a label, so `{total}` survives a task named "total".
                self._matcher = re.compile(r"(?<![\w{])(?:" + _trie_pattern(words) + r")(?![\w}?|])")
            else:
                self._matcher = re.compile(r"(?!x)x")
        return self._matcher

    # ---- dates
    def _day(self, d: date) -> int:
        return (d - self.origin).days

    def _from_day(self, n: int) -> date:
        return self.origin + timedelta(days=n)

    @staticmethod
    def _signed(prefix: str, n: int) -> str:
        return f"{prefix}{'+' if n >= 0 else '-'}{abs(n):04d}"

    def _month_index(self, y: int, m: int) -> int:
        return (y - self.origin.year) * 12 + (m - self.origin.month)

    def _from_month(self, n: int):
        total = self.origin.year * 12 + (self.origin.month - 1) + n
        return total // 12, total % 12 + 1

    # ---- text
    def encode_text(self, s: str) -> str:
        if not s:
            return s
        # Names first, so a date written inside a name travels inside its token.
        tok = self.tokens.get(s)
        if tok is not None:
            return tok
        s = self._names().sub(lambda m: self.tokens[m.group(0)], s)

        def iso(m):
            try:
                d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return m.group(0)
            return self._signed("D", self._day(d))

        def dmy(m):
            try:
                d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                return m.group(0)
            return self._signed("d", self._day(d))

        def period(m):
            y, mo = int(m.group(1)), int(m.group(2))
            if not (1 <= mo <= 12 and 1800 <= y <= 2300):
                return m.group(0)
            return self._signed("M", self._month_index(y, mo))

        def year(m):
            return self._signed("Y", int(m.group(1)) - self.origin.year)

        s = _ISO_DAY.sub(iso, s)
        s = _DMY.sub(dmy, s)
        s = _PERIOD.sub(period, s)
        s = _YEAR_LABEL.sub(year, s)
        return s

    def decode_text(self, s: str, narrative: bool = False) -> str:
        """Back to the real text. `narrative`: the agent's prose, where a day code is
        written in the report's display form whatever its case, money gets the
        currency symbol, and a token with a dot or hyphen for separator is accepted."""
        if not s:
            return s

        def day(m):
            n = int(m.group(3)) * (1 if m.group(2) == "+" else -1)
            d = self._from_day(n)
            # "d" is the display form by construction; in the agent's prose any day
            # code is shown the way the report shows a day.
            if m.group(1) == "d" or (narrative and self.lang == "pt"):
                return d.strftime("%d/%m/%Y")
            return d.strftime("%Y-%m-%d")

        def month(m):
            n = int(m.group(2)) * (1 if m.group(1) == "+" else -1)
            y, mo = self._from_month(n)
            return f"{y:04d}-{mo:02d}"

        def year(m):
            n = int(m.group(2)) * (1 if m.group(1) == "+" else -1)
            return f"{self.origin.year + n:04d}"

        def money(m):
            coded, dec = parse_num(m.group(1), self.lang)
            real = fnum(coded / self.k, dec, self.lang)
            if narrative and self.currency:
                return f"{self.currency} {real}"
            return real

        s = _CODE_DAY.sub(day, s)
        s = _CODE_MONTH.sub(month, s)
        s = _CODE_YEAR.sub(year, s)
        s = _CODE_MONEY.sub(money, s)
        rx = self._lenient if narrative else self._strict
        s = rx.sub(lambda m: self.back.get(f"{m.group(1)}{TOKEN_SEP}{m.group(2)}", m.group(0)), s)
        return s

    # ---- money
    def scale(self, v):
        if isinstance(v, bool) or v is None:
            return v
        if isinstance(v, int):
            # An integer stays an integer: rounding after scaling by k > 1 loses
            # less than half a unit, which divides back to under half a unit.
            return int(round(v * self.k))
        if isinstance(v, float):
            return v * self.k if math.isfinite(v) else v
        return v

    def unscale(self, c):
        if isinstance(c, bool) or c is None:
            return c
        if isinstance(c, int):
            return int(round(c / self.k))
        if isinstance(c, float):
            if not math.isfinite(c) or c == 0:
                return c / self.k if math.isfinite(c) else c
            x = c / self.k
            # The shortest decimal within a few units in the last place of x: the
            # engine rounds money to two or four places, so this is the figure it
            # wrote, not the float the division left.
            tol = abs(x) * 2.0 ** -48
            for d in range(0, 16):
                r = round(x, d)
                if abs(r - x) <= tol:
                    return r
            return x
        return c

    def encode_money_text(self, number: str) -> str:
        """A money figure already written in a sentence -> the coded figure, marked."""
        v, dec = parse_num(number, self.lang)
        return MONEY_MARK + fnum(v * self.k, dec, self.lang)

    # ---- structures
    def encode_obj(self, o, key=None):
        if isinstance(o, dict):
            return {(self.encode_text(k) if isinstance(k, str) else k): self._enc_value(k, v)
                    for k, v in o.items()}
        if isinstance(o, list):
            return [self.encode_obj(v, key) for v in o]
        if isinstance(o, str):
            return self.encode_text(o)
        return o

    def _enc_value(self, k, v):
        if k in LEGIBILITY["money_keys"] and isinstance(v, (int, float)) and not isinstance(v, bool):
            return self.scale(v)
        if k == "year" and isinstance(v, int) and not isinstance(v, bool):
            return self._signed("Y", v - self.origin.year)
        return self.encode_obj(v, k)

    def decode_obj(self, o):
        if isinstance(o, dict):
            return {(self.decode_text(k) if isinstance(k, str) else k): self._dec_value(k, v)
                    for k, v in o.items()}
        if isinstance(o, list):
            return [self.decode_obj(v) for v in o]
        if isinstance(o, str):
            return self.decode_text(o)
        return o

    def _dec_value(self, k, v):
        if k in LEGIBILITY["money_keys"] and isinstance(v, (int, float)) and not isinstance(v, bool):
            return self.unscale(v)
        if k == "year" and isinstance(v, str):
            m = _CODE_YEAR_WHOLE.fullmatch(v)
            if m:
                return self.origin.year + int(m.group(2)) * (1 if m.group(1) == "+" else -1)
        return self.decode_obj(v)

    # ---- persistence of what decoding needs (never the key)
    def back_table(self) -> dict:
        return {"origin": self.origin.isoformat(), "k": self.k, "width": self.width,
                "lang": self.lang, "currency": self.currency, "tokens": dict(self.back)}

    @classmethod
    def from_back_table(cls, d: dict) -> "Codec":
        tokens = {real: tok for tok, real in (d.get("tokens") or {}).items()}
        return cls(b"", date.fromisoformat(d["origin"]), d["k"], tokens, d.get("width", WIDTH),
                   d.get("lang", "en"), d.get("currency", ""))


# ---------------------------------------------------------------------------
# Money the engine has already written into a sentence. A number in prose carries
# no key saying it is money, so each place that writes one is listed here and
# coded by name. Today there is one: the earned-before-plan reading of the S-curve.
# A new reading that quotes money must be added here; the leak test formats every
# money figure of the real output and looks for it, so a forgotten site fails it.
# ---------------------------------------------------------------------------
def _earned_before_plan(payload: dict, lang: str):
    s = payload.get("scurve") or {}
    periods = s.get("periods") or []
    first = next((p["period"] for p in periods if (p.get("planned") or 0) > 0), None)
    if not first:
        return None
    before = sum((p.get("earned") or 0) for p in periods if p["period"] < first)
    if before > 0 and s.get("bac"):
        return "scurve", fnum(before, 0, lang)
    return None


def _cycle_residual(payload: dict, lang: str):
    """The cycle's residual-term and C5 sentences (0.7.2): the erased earned value of a
    removed activity, and the BAC before, after and its parts. They are written in
    the `movement` and `c5` readings; the figures come from the cycle sidecar."""
    terms = payload.get("residual_terms") or {}
    figures = []
    rem = terms.get("removed_earned") or {}
    figures.append(rem.get("earned_erased"))
    figures += [r.get("earned_erased") for r in rem.get("rows") or []]
    bac = terms.get("bac_change") or {}
    figures += [bac.get("bac_before"), bac.get("bac_after"), bac.get("inserted_cost"),
                bac.get("removed_cost"), abs(bac.get("changed_cost") or 0)]
    gone = (payload.get("past_rewritten") or {}).get("removed_with_progress") or []
    figures += [r.get("earned_erased") for r in gone]
    shown = sorted({fnum(v, 0, lang) for v in figures if v and abs(v) >= 0.5}, key=len, reverse=True)
    return [(section, s) for s in shown for section in ("movement", "c5")]


PROSE_MONEY_SITES = (_earned_before_plan, _cycle_residual)


def mark_prose_money(readings: dict, payload: dict, lang: str, codec: Codec) -> int:
    """Replace each money figure written in a reading by its coded, marked figure.

    `payload` is the real payload the readings were built from (it holds what each
    site needs to know which figure it wrote). Returns how many were replaced.
    """
    if not isinstance(readings, dict):
        return 0
    n = 0
    hits = []
    for site in PROSE_MONEY_SITES:
        hit = site(payload, lang)
        if hit:
            hits += hit if isinstance(hit, list) else [hit]
    for section, shown in hits:
        if section not in readings:
            continue
        rx = re.compile(r"(?<![\d.,])" + re.escape(shown) + r"(?![\d]|[.,]\d)")
        out = []
        for sentence in readings.get(section) or []:
            new, k = rx.subn(lambda _m, s=shown: codec.encode_money_text(s), sentence)
            n += k
            out.append(new)
        readings[section] = out
    return n


def mark_prose_money_everywhere(obj, payload: dict, lang: str, codec: Codec):
    """The same figures, in every string of `obj`: the cycle report repeats the
    residual sentences in its warnings and in each section's reading, not only in
    `readings`. Returns the coded object (strings are immutable)."""
    figures = set()
    for site in PROSE_MONEY_SITES:
        hit = site(payload, lang)
        for one in (hit if isinstance(hit, list) else [hit] if hit else []):
            figures.add(one[1])
    shown = sorted(figures, key=len, reverse=True)
    if not shown:
        return obj
    rxs = [(re.compile(r"(?<![\d.,])" + re.escape(s) + r"(?![\d]|[.,]\d)"), s) for s in shown]

    def walk(o):
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(v) for v in o]
        if isinstance(o, str):
            for rx, s in rxs:
                o = rx.sub(lambda _m, s=s: codec.encode_money_text(s), o)
        return o
    return walk(obj)


def get_path(obj, path):
    for p in path:
        if not isinstance(obj, dict) or p not in obj:
            return None
        obj = obj[p]
    return obj


def withhold(obj: dict, path) -> bool:
    """Empty a withheld series in place, saying so beside it. True if it was there."""
    parent = get_path(obj, path[:-1])
    if isinstance(parent, dict) and path[-1] in parent:
        parent[path[-1]] = []
        parent[path[-1] + "_withheld"] = "secret mode: withheld from the coded output"
        return True
    return False


def restore(decoded: dict, real: dict, path) -> None:
    """Put a withheld series back from the engine's real output."""
    parent = get_path(decoded, path[:-1])
    src = get_path(real, path)
    if isinstance(parent, dict) and path[-1] in parent:
        parent.pop(path[-1] + "_withheld", None)
        if src is not None:
            parent[path[-1]] = src


def find_code_like(obj) -> int:
    """How many strings of a real output already look like a code (see CODE_LIKE)."""
    n = 0
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            stack.extend(o.values())
            stack.extend(k for k in o if isinstance(k, str))
        elif isinstance(o, list):
            stack.extend(o)
        elif isinstance(o, str) and CODE_LIKE.search(o):
            n += 1
    return n
