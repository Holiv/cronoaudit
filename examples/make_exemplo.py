#!/usr/bin/env python3
"""Generate the fictitious road-works example: two MSPDI snapshots of one schedule.

    python3 examples/make_exemplo.py            # writes the two XML files beside this script
    python3 examples/make_exemplo.py --list     # also prints the rev04 schedule as a table

  rodovia-ficticia-rev03.xml   status date 30/09/2026 -- the previous delivery
  rodovia-ficticia-rev04.xml   status date 30/10/2026 -- the current one, a month later

EVERYTHING HERE IS INVENTED. The road (RF-140), the stretch (km 12+000 to km 36+000),
the client, the contractor, the quantities, the unit prices and every date are made
up for the example. No real project, company, contract or place is represented.

How the files are built, so the example stays honest:

* The network is scheduled by a small forward and backward pass over two calendars
  (a five-day project calendar and a six-day earthworks calendar, both with the
  Brazilian national holidays and a rainy-season reserve from December to March).
  Dates, float and the critical flag are therefore consistent with the links.
* The baseline is that same pass with nothing executed. Its cost is distributed in
  time, one block per working day, and adds up to the baseline cost to the cent.
* Each revision is the pass run again with what "really happened" up to its status
  date (PERTURB below): some activities took longer, some started late. An activity
  is complete, in progress or not started according to where the status date falls.
* On top of that sit the PLANTED problems, each one named in PLANTED below and
  listed in the README beside the engine finding that should catch it.

The output is deterministic: no clock, no randomness, no dictionary-order
dependence. Running it twice gives byte-identical files.

Standard library only.
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from xml.sax.saxutils import escape

NS = "http://schemas.microsoft.com/project"
PROJECT_START = date(2026, 3, 2)
STATUS = {"rev03": date(2026, 9, 30), "rev04": date(2026, 10, 30)}
DAY_MIN = 480                      # both calendars work 8-hour days
FIELD_DISC = "188743731"           # Text1, alias DISCIPLINA
FIELD_SEG = "188743734"            # Text2, alias SEGMENTO

PROJECT_NAME = "RF-140 — Duplicação e Restauração — km 12+000 ao km 36+000 (exemplo fictício)"
COMPANY = "Consórcio Fictício Via Exemplar"
CLIENT = "Departamento Fictício de Estradas (DFE)"

SEGMENTS = {
    1: ("Segmento 1 — km 12+000 ao km 18+000", "SEG 1", 1.00),
    2: ("Segmento 2 — km 18+000 ao km 24+000", "SEG 2", 1.10),
    3: ("Segmento 3 — km 24+000 ao km 30+000", "SEG 3", 0.92),
    4: ("Segmento 4 — km 30+000 ao km 36+000", "SEG 4", 1.05),
}


# ---------------------------------------------------------------------------
# Calendars
# ---------------------------------------------------------------------------
HOLIDAYS = [
    (date(2026, 1, 1), "Confraternização Universal"),
    (date(2026, 2, 16), "Carnaval"), (date(2026, 2, 17), "Carnaval"),
    (date(2026, 4, 3), "Sexta-feira Santa"), (date(2026, 4, 21), "Tiradentes"),
    (date(2026, 5, 1), "Dia do Trabalho"), (date(2026, 6, 4), "Corpus Christi"),
    (date(2026, 9, 7), "Independência do Brasil"),
    (date(2026, 10, 12), "Nossa Senhora Aparecida"),
    (date(2026, 11, 2), "Finados"), (date(2026, 11, 20), "Consciência Negra"),
    (date(2026, 12, 24), "Recesso de fim de ano"), (date(2026, 12, 25), "Natal"),
    (date(2026, 12, 31), "Recesso de fim de ano"),
    (date(2027, 1, 1), "Confraternização Universal"),
    (date(2027, 2, 8), "Carnaval"), (date(2027, 2, 9), "Carnaval"),
    (date(2027, 3, 26), "Sexta-feira Santa"), (date(2027, 4, 21), "Tiradentes"),
    (date(2027, 5, 27), "Corpus Christi"), (date(2027, 9, 7), "Independência do Brasil"),
    (date(2027, 10, 12), "Nossa Senhora Aparecida"), (date(2027, 11, 2), "Finados"),
    (date(2027, 11, 15), "Proclamação da República"),
    (date(2027, 12, 24), "Recesso de fim de ano"), (date(2027, 12, 31), "Recesso de fim de ano"),
]
# The calendars are registered for the years the works run in. A reserve entered
# for a year with no activity in it is itself a finding, and is not planted here.
RAIN_MONTHS = [(2026, 12), (2027, 1), (2027, 2), (2027, 3), (2027, 12)]
RAIN_NAME = "Reserva de chuva"


class Cal:
    """A working week plus dated non-working exceptions. Whole days only."""

    def __init__(self, uid: int, name: str, week: tuple, rain_days: int):
        self.uid, self.name, self.week = uid, name, week
        self.exceptions = {}
        for d, label in HOLIDAYS:
            self.exceptions[d] = label
        # The rainy-season reserve: in each month from December to March, a fixed
        # number of otherwise-working days is withdrawn, evenly spaced.
        for y, m in RAIN_MONTHS:
            days, cur = [], date(y, m, 1)
            while cur.month == m:
                if cur.weekday() in self.week and cur not in self.exceptions:
                    days.append(cur)
                cur += timedelta(days=1)
            for i in range(rain_days):
                self.exceptions[days[(i * len(days)) // rain_days + len(days) // (2 * rain_days)]] = RAIN_NAME

    def working(self, d: date) -> bool:
        return d.weekday() in self.week and d not in self.exceptions

    def on_or_after(self, d: date) -> date:
        while not self.working(d):
            d += timedelta(days=1)
        return d

    def on_or_before(self, d: date) -> date:
        while not self.working(d):
            d -= timedelta(days=1)
        return d

    def add(self, d: date, n: int) -> date:
        """n working days after d (before, when negative). d is first snapped to a
        working day in the direction of travel."""
        if n >= 0:
            d = self.on_or_after(d)
            for _ in range(n):
                d = self.on_or_after(d + timedelta(days=1))
        else:
            d = self.on_or_before(d)
            for _ in range(-n):
                d = self.on_or_before(d - timedelta(days=1))
        return d

    def count(self, a: date, b: date) -> int:
        """Working days in [a, b], inclusive. Zero when b is before a."""
        n, cur = 0, a
        while cur <= b:
            if self.working(cur):
                n += 1
            cur += timedelta(days=1)
        return n

    def days_list(self, a: date, b: date) -> list:
        out, cur = [], a
        while cur <= b:
            if self.working(cur):
                out.append(cur)
            cur += timedelta(days=1)
        return out

    def slack(self, f: date, lf: date) -> int:
        """Signed working days from an early finish to a late finish."""
        if lf >= f:
            return self.count(f, lf) - (1 if self.working(f) else 0)
        return -(self.count(lf, f) - (1 if self.working(lf) else 0))


CALS = {
    1: Cal(1, "Padrão da Obra (5 dias)", (0, 1, 2, 3, 4), 5),
    2: Cal(2, "Terraplenagem (6 dias)", (0, 1, 2, 3, 4, 5), 7),
}


# ---------------------------------------------------------------------------
# Resources. Work resources are priced per hour; material resources carry the
# measured quantity of the service and are priced per unit, which is how a unit
# price contract is cost-loaded.
# ---------------------------------------------------------------------------
RES = [
    # uid, key, name, type (1 work, 0 material), label, rate (R$)
    (1, "W_MOB", "Equipe de mobilização e canteiro", 1, None, 1850.0),
    (2, "W_TOPO", "Equipe de topografia", 1, None, 420.0),
    (3, "W_ENG", "Engenharia e projetos", 1, None, 680.0),
    (4, "W_AMB", "Meio ambiente e licenciamento", 1, None, 390.0),
    (5, "W_USINA", "Montagem industrial — usina de asfalto e britagem", 1, None, 9800.0),
    (6, "W_SINP", "Equipe de sinalização de obras", 1, None, 310.0),
    (7, "W_INTERF", "Equipe de remanejamento de interferências", 1, None, 1150.0),
    (8, "W_OAE", "Equipe de OAE — Estruturas Fictícias Beta Ltda.", 1, None, 2900.0),
    (9, "W_ICA", "Equipe de içamento e montagem (guindastes)", 1, None, 14500.0),
    (10, "W_ELE", "Equipe de eletricistas", 1, None, 760.0),
    (11, "W_ADM", "Administração local e desmobilização", 1, None, 1300.0),
    (20, "M_DESM", "Equipe de terraplenagem — desmatamento e limpeza", 0, "m²", 0.85),
    (21, "M_ESC1", "Equipe de terraplenagem — escavação, carga e transporte 1ª cat.", 0, "m³", 14.50),
    (22, "M_ESC3", "Equipe de terraplenagem — escavação 2ª e 3ª cat.", 0, "m³", 48.00),
    (23, "M_ATER", "Equipe de terraplenagem — aterro compactado", 0, "m³", 9.80),
    (24, "M_SUBL", "Regularização e compactação do subleito", 0, "m²", 2.10),
    (25, "M_HIDR", "Hidrossemeadura", 0, "m²", 3.40),
    (26, "M_BTUB", "Bueiro tubular de concreto", 0, "ml", 1450.0),
    (27, "M_CONC", "Concreto estrutural armado", 0, "m³", 2650.0),
    (28, "M_DREN", "Dreno profundo longitudinal", 0, "ml", 185.0),
    (29, "M_SARJ", "Sarjetas e valetas de concreto", 0, "ml", 96.0),
    (30, "M_MFIO", "Meio-fio e descidas d'água", 0, "ml", 78.0),
    (31, "M_SBAS", "Sub-base granular", 0, "m³", 142.0),
    (32, "M_BGS", "Base de brita graduada simples (BGS)", 0, "m³", 198.0),
    (33, "M_IMPR", "Imprimação e pintura de ligação", 0, "m²", 6.90),
    (34, "M_CBUQ", "Usina de asfalto — CBUQ aplicado", 0, "ton", 465.0),
    (35, "M_FRES", "Fresagem de pavimento", 0, "m²", 11.50),
    (36, "M_SINH", "Sinalização horizontal", 0, "m²", 38.0),
    (37, "M_SINV", "Placas e pórticos de sinalização", 0, "un", 720.0),
    (38, "M_DEFE", "Defensas metálicas", 0, "ml", 410.0),
    (39, "M_TACH", "Tachas refletivas", 0, "un", 21.0),
    (40, "M_DUTO", "Dutos e caixas de passagem", 0, "ml", 115.0),
    (41, "M_POST", "Postes e luminárias LED", 0, "un", 6900.0),
    (42, "M_ESTACA", "Estaca escavada de grande diâmetro", 0, "ml", 1380.0),
    (43, "M_VIGA", "Viga pré-moldada protendida", 0, "un", 148000.0),
    (44, "M_GABIAO", "Muro de gabião", 0, "m³", 520.0),
    (45, "M_CERCA", "Cerca de vedação da faixa de domínio", 0, "ml", 64.0),
]
RES_BY_KEY = {r[1]: r for r in RES}


# ---------------------------------------------------------------------------
# What happened, and what was planted.
#
# PERTURB is cumulative reality: `delta` lengthens (or shortens) an activity,
# `delay` starts it late, both in working days of the activity's own calendar.
# rev04 contains everything rev03 contains, plus October. The generator asserts
# that the past of rev03 is unchanged in rev04 -- except where PLANTED says so.
# ---------------------------------------------------------------------------
DELTA_03 = {
    # mobilisation: mostly on time, the asphalt plant a week late
    "mob.proj": -2, "mob.cant": -1, "mob.usina": 5,
    # earthworks crew A (segments 1 and 2)
    "s1.terr.esc1": -2, "s1.terr.ater": 4, "s2.terr.esc1": 3,
    # earthworks crew B (segments 3 and 4)
    "s3.terr.esc1": -1, "s3.terr.ater": 3, "s4.terr.esc3": -2,
    # culverts: segment 1 ran three days over, segment 2 recovered them
    "s1.dren.btub": 3, "s2.dren.btub": -3,
    # the viaduct: design release and the central piles ran long
    "oae.proj": 4, "oae.estc": 5, "oae.este": 1,
}
DELAY_03 = {"s1.dren.dren": 1}

DELTA_04 = dict(DELTA_03, **{
    # October, as executed
    "s1.pav.sbas": 4, "s1.pav.bgs": 8, "s1.pav.impr": 3, "s1.dren.sarj": 2,
    "s2.terr.ater": 12,
    "s3.terr.ater": 6, "s3.terr.subl": 2, "s3.dren.dren": 7,
    "s4.dren.bcel": 3,
    "oae.bloc": 6,          # the pile caps, on the path that ends the project
})
DELAY_04 = dict(DELAY_03)

PERTURB = {
    "rev03": {"delta": DELTA_03, "delay": DELAY_03},
    "rev04": {"delta": DELTA_04, "delay": DELAY_04},
}

PLANTED = {
    # An activity started while its finish-to-start predecessor is still open.
    "out_of_sequence": {"task": "s1.pav.impr", "start": date(2026, 10, 29)},
    # A forecast pushed three weeks by a start-no-earlier-than constraint, nothing executed.
    "replan": {"task": "s2.dren.sarj", "push_days": 15},
    # Planned duration raised on work that has not started.
    "duration": {"task": "oae.lanc", "before": 12, "after": 20},
    # Duration percent complete far ahead of the physical percent.
    "percent_vs_physical": {"task": "s2.terr.ater", "physical_factor": 0.6},
    # An actual finish already reported in rev03 reads three working days earlier in
    # rev04 -- exactly on its baseline date.
    "past_rewritten": {"task": "s1.dren.btub", "shift_days": -3},
    # The baseline of one activity moved between the two deliveries.
    "rebaselined": {"task": "s4.pav.capa", "shift_days": 20},
    # Logic edited between the deliveries.
    "link_removed": ("s4.pav.sbas", "s4.dren.dren"),
    "link_added": ("s3.sin.defe", "s3.dren.mfio", "FS", 0),
    # Scope: one activity only in rev04, one only in rev03.
    "inserted": "s2.terr.gab",
    "removed": "s4.terr.cerca",
    # Open ends: activities left without a successor (in both revisions).
    "no_successor": ["s3.terr.hidr", "s2.sin.tach", "s4.sin.sinv", "fim.jaz"],
}


# ---------------------------------------------------------------------------
# The schedule itself
# ---------------------------------------------------------------------------
class Row:
    def __init__(self, kind, level, key, name, dur=0, preds=None, res=None, qty=None,
                 cal=1, disc=None, seg=None, margin=None):
        self.kind, self.level, self.key, self.name = kind, level, key, name
        self.dur, self.preds, self.res, self.qty = dur, list(preds or []), res, qty
        self.cal, self.disc, self.seg, self.margin = cal, disc, seg, margin
        self.uid = self.id = None
        self.outline = None
        self.children = []


def build_rows(rev: str) -> list:
    rows = []
    ctx = {"disc": None, "seg": None}

    def S(level, key, name):
        rows.append(Row("sum", level, key, name))

    def A(level, key, name, dur, preds, res, qty=None, cal=1):
        norm = [(p, "FS", 0) if isinstance(p, str) else p for p in preds]
        if key[0] == "s" and key[1].isdigit():
            # The same service repeats in every segment; the row name says which,
            # because a report shows a name without its place in the outline.
            name = f"{name} — Seg. {key[1]}"
        rows.append(Row("task", level, key, name, dur, norm, res, qty, cal, ctx["disc"], ctx["seg"]))

    def M(key, name, preds, margin):
        norm = [(p, "FS", 0) if isinstance(p, str) else p for p in preds]
        rows.append(Row("ms", 2, key, name, 0, norm, None, None, 1, "MARCO", "GERAL", margin))

    open_ends = set(PLANTED["no_successor"])

    def feeding(*keys):
        return [k for k in keys if k not in open_ends]

    # ---- 1. Contractual milestones
    S(1, "marcos", "Marcos Contratuais")
    M("ms.os", "Ordem de Serviço (OS) emitida", [], 0)
    M("ms.usina", "Usina de asfalto licenciada e em operação", ["mob.usina"], 15)
    M("ms.terr", "Conclusão da terraplenagem — todos os segmentos", ["s4.terr.subl"], 20)
    for n in (1, 2, 3, 4):
        M(f"ms.s{n}", f"Liberação ao tráfego — {SEGMENTS[n][0]}",
          feeding(f"s{n}.sin.sinv", f"s{n}.sin.defe", f"s{n}.sin.tach", f"s{n}.ilum.ener",
                  f"s{n}.terr.hidr"), 15)
    M("ms.oae", "Conclusão do Viaduto V-01 (km 27+400)", ["oae.prova"], 25)
    M("ms.trp", "Termo de Recebimento Provisório (TRP)", ["fim.desmob"], 30)

    # ---- 2. Mobilisation
    ctx.update(disc="MOBILIZAÇÃO", seg="GERAL")
    S(1, "mob", "Mobilização e Serviços Preliminares")
    A(2, "mob.pes", "Mobilização de pessoal e equipamentos", 15, ["ms.os"], "W_MOB")
    A(2, "mob.cant", "Instalação do canteiro de obras e alojamentos", 25, ["ms.os"], "W_MOB")
    A(2, "mob.lic", "Licenças ambientais e autorização de supressão vegetal", 20, ["ms.os"], "W_AMB")
    A(2, "mob.topo", "Levantamento topográfico e locação do eixo", 20, ["mob.pes"], "W_TOPO")
    A(2, "mob.proj", "Projeto executivo — compatibilização e liberação", 25, ["ms.os"], "W_ENG")
    A(2, "mob.usina", "Instalação da usina de asfalto e da central de britagem", 40, ["mob.cant"], "W_USINA")
    A(2, "mob.sinp", "Sinalização provisória de obras e desvios de tráfego", 10, ["mob.pes"], "W_SINP")
    A(2, "mob.interf", "Remanejamento de interferências (redes de terceiros)", 30,
      ["mob.proj"], "W_INTERF")

    # ---- 3 to 6. The four segments, discipline by discipline
    for n in (1, 2, 3, 4):
        title, seg, f = SEGMENTS[n]
        p = f"s{n}"
        prev = f"s{n - 1}" if n > 1 else None
        # Two earthworks crews and two paving fronts: A works segment 1 then 2,
        # B works segment 3 then 4. Clearing and culverts run 1 to 4 with one crew.
        front_prev = {2: "s1", 4: "s3"}.get(n)
        q = lambda v: float(int(round(v * f)))       # noqa: E731  quantities scale with the segment
        ctx["seg"] = seg
        S(1, p, title)

        ctx["disc"] = "TERRAPLENAGEM"
        S(2, f"{p}.terr", "Terraplenagem")
        A(3, f"{p}.terr.desm", "Desmatamento, destocamento e limpeza", 15,
          ["mob.lic", "mob.sinp", ("mob.topo", "SS", 0)] if n == 1 else [f"{prev}.terr.desm"],
          "M_DESM", q(180000), cal=2)
        A(3, f"{p}.terr.esc1", "Escavação, carga e transporte — material de 1ª categoria", 40,
          [f"{p}.terr.desm"] + ([f"{front_prev}.terr.esc1"] if front_prev else ["mob.interf"]),
          "M_ESC1", q(220000), cal=2)
        A(3, f"{p}.terr.esc3", "Escavação em material de 2ª e 3ª categoria", 25,
          [(f"{p}.terr.esc1", "SS", 10)], "M_ESC3", q(35000), cal=2)
        ater_preds = [f"{p}.terr.esc1", f"{p}.terr.esc3", f"{p}.dren.btub"] + (
            [f"{front_prev}.terr.ater"] if front_prev else [])
        if n in (2, 4):
            ater_preds.append(f"{p}.dren.bcel")
        A(3, f"{p}.terr.ater", "Aterro compactado", 44, ater_preds, "M_ATER", q(190000), cal=2)
        A(3, f"{p}.terr.subl", "Regularização e compactação do subleito", 12,
          [f"{p}.terr.ater"], "M_SUBL", q(96000), cal=2)
        if n == 2 and rev == "rev04":
            # INSERTED in rev04: a retaining wall that was not in the previous delivery.
            A(3, "s2.terr.gab", "Contenção em gabião — talude do km 21+300", 15,
              ["s2.terr.ater"], "M_GABIAO", 1800.0)
        hidr_preds = [f"{p}.terr.ater", f"{p}.pav.acos"] + (
            ["s2.terr.gab"] if (n == 2 and rev == "rev04") else [])
        A(3, f"{p}.terr.hidr", "Proteção vegetal de taludes (hidrossemeadura)", 10,
          hidr_preds, "M_HIDR", q(60000))
        if n == 4 and rev == "rev03":
            # REMOVED in rev04: present only in the previous delivery.
            A(3, "s4.terr.cerca", "Remanejamento de cercas da faixa de domínio", 12,
              ["s4.terr.desm"], "M_CERCA", 7400.0)

        ctx["disc"] = "DRENAGEM"
        S(2, f"{p}.dren", "Drenagem e Obras de Arte Correntes")
        A(3, f"{p}.dren.btub", "Bueiros tubulares de concreto", 25,
          [f"{p}.terr.desm"] + ([f"{prev}.dren.btub"] if prev else []), "M_BTUB", q(480))
        if n in (2, 4):
            A(3, f"{p}.dren.bcel", "Bueiro celular de concreto", 20,
              [f"{p}.dren.btub"], "M_CONC", q(420))
        A(3, f"{p}.dren.dren", "Drenos profundos longitudinais", 15, [f"{p}.terr.ater"], "M_DREN", q(5200))
        A(3, f"{p}.dren.sarj", "Sarjetas e valetas de proteção", 18, [f"{p}.dren.dren"], "M_SARJ", q(11000))
        A(3, f"{p}.dren.mfio", "Meios-fios e descidas d'água", 15,
          [f"{p}.dren.sarj", f"{p}.pav.bind"], "M_MFIO", q(9000))

        ctx["disc"] = "PAVIMENTAÇÃO"
        S(2, f"{p}.pav", "Pavimentação")
        sbas_preds = [f"{p}.terr.subl", f"{p}.dren.dren"] + ([f"{front_prev}.pav.bgs"] if front_prev else [])
        if rev == "rev04" and PLANTED["link_removed"][0] == f"{p}.pav.sbas":
            sbas_preds.remove(PLANTED["link_removed"][1])         # LINK REMOVED in rev04
        A(3, f"{p}.pav.sbas", "Sub-base granular", 18, sbas_preds, "M_SBAS", q(19000))
        A(3, f"{p}.pav.bgs", "Base de brita graduada simples (BGS)", 18,
          [(f"{p}.pav.sbas", "SS", 6)], "M_BGS", q(17000))
        A(3, f"{p}.pav.impr", "Imprimação", 6,
          [f"{p}.pav.bgs", f"{p}.pav.sbas"] + (["ms.usina"] if n == 1 else []), "M_IMPR", q(96000))
        A(3, f"{p}.pav.bind", "CBUQ — camada de ligação (binder)", 15,
          [f"{p}.pav.impr"] + ([f"{front_prev}.pav.capa"] if front_prev else []), "M_CBUQ", q(13500))
        A(3, f"{p}.pav.fres", "Fresagem e reperfilagem da pista existente", 15,
          [f"{p}.pav.bind"], "M_FRES", q(52000))
        A(3, f"{p}.pav.capa", "CBUQ — capa de rolamento (pista nova e existente)", 18,
          [f"{p}.pav.fres", f"{p}.dren.mfio"], "M_CBUQ", q(16000))
        A(3, f"{p}.pav.acos", "Acostamentos e acabamento de bordos", 10, [f"{p}.pav.capa"], "M_CBUQ", q(3000))

        ctx["disc"] = "SINALIZAÇÃO"
        S(2, f"{p}.sin", "Sinalização e Segurança Viária")
        A(3, f"{p}.sin.sinh", "Sinalização horizontal", 8, [f"{p}.pav.capa"], "M_SINH", q(4800))
        A(3, f"{p}.sin.sinv", "Sinalização vertical e pórticos", 10,
          [f"{p}.pav.capa", (f"{p}.sin.sinh", "SS", 0)], "M_SINV", q(260))
        defe_preds = [f"{p}.pav.acos"]
        if n == 3 and rev == "rev04":
            defe_preds.append(PLANTED["link_added"][1:])          # LINK ADDED in rev04
        A(3, f"{p}.sin.defe", "Defensas metálicas e barreiras", 12, defe_preds, "M_DEFE", q(3800))
        A(3, f"{p}.sin.tach", "Tachas e dispositivos auxiliares", 5, [f"{p}.sin.sinh"], "M_TACH", q(6500))

        ctx["disc"] = "ILUMINAÇÃO"
        S(2, f"{p}.ilum", "Iluminação")
        A(3, f"{p}.ilum.dut", "Dutos, caixas de passagem e bases", 12, [f"{p}.dren.mfio"], "M_DUTO", q(2400))
        A(3, f"{p}.ilum.post", "Postes e luminárias LED", 10, [f"{p}.ilum.dut", f"{p}.pav.capa"], "M_POST", q(90))
        A(3, f"{p}.ilum.ener", "Cabeamento, quadros de comando e energização", 8,
          [f"{p}.ilum.post"], "W_ELE")

    # ---- 7. The viaduct
    ctx.update(disc="OAE", seg="SEG 3")
    S(1, "oae", "Obras de Arte Especiais — Viaduto V-01 (km 27+400)")
    S(2, "oae.infra", "Infraestrutura")
    A(3, "oae.sond", "Sondagens complementares e locação dos apoios", 10, ["mob.topo"], "W_TOPO")
    A(3, "oae.proj", "Projeto executivo da OAE — revisão e liberação para execução", 30,
      ["oae.sond", "mob.proj"], "W_ENG")
    A(3, "oae.estc", "Estacas escavadas — apoios centrais (P1 a P3)", 32, ["oae.proj"], "M_ESTACA", 1450.0)
    A(3, "oae.este", "Estacas escavadas — encontros (E1 e E2)", 24, ["oae.estc"], "M_ESTACA", 980.0)
    A(3, "oae.bloc", "Blocos de coroamento", 28, ["oae.este"], "M_CONC", 780.0)
    S(2, "oae.meso", "Mesoestrutura")
    A(3, "oae.pil", "Pilares", 38, ["oae.bloc"], "M_CONC", 640.0)
    A(3, "oae.trav", "Travessas", 25, ["oae.pil"], "M_CONC", 410.0)
    A(3, "oae.enc", "Encontros e alas", 30, [("oae.pil", "SS", 10)], "M_CONC", 720.0)
    A(3, "oae.apar", "Aparelhos de apoio", 6, ["oae.trav", "oae.enc"], "W_OAE")
    S(2, "oae.super", "Superestrutura")
    A(3, "oae.fab", "Fabricação das vigas pré-moldadas protendidas", 40, [("oae.pil", "SS", 0)], "M_VIGA", 20.0)
    dur_lanc = PLANTED["duration"]["after"] if rev == "rev04" else PLANTED["duration"]["before"]
    A(3, "oae.lanc", "Lançamento das vigas pré-moldadas", dur_lanc, ["oae.apar", "oae.fab"], "W_ICA")
    A(3, "oae.plaj", "Pré-lajes e armação do tabuleiro", 28, ["oae.lanc"], "W_OAE")
    A(3, "oae.conc", "Concretagem do tabuleiro", 18, ["oae.plaj"], "M_CONC", 890.0)
    A(3, "oae.trans", "Lajes de transição", 10, ["oae.conc", ("oae.atac", "FF", 5)], "M_CONC", 160.0)
    A(3, "oae.barr", "Barreiras New Jersey e guarda-corpos", 15, ["oae.conc"], "M_CONC", 210.0)
    A(3, "oae.junt", "Juntas de dilatação", 6, ["oae.barr", "oae.trans"], "W_OAE")
    S(2, "oae.acab", "Acabamentos e Acessos")
    A(3, "oae.atac", "Aterros de acesso aos encontros", 25, ["oae.lanc"], "M_ATER", 42000.0, cal=2)
    A(3, "oae.pavt", "Impermeabilização e pavimentação do tabuleiro", 8, ["oae.junt"], "M_CBUQ", 380.0)
    A(3, "oae.sinil", "Sinalização e iluminação do viaduto", 8, ["oae.pavt"], "W_ELE")
    A(3, "oae.prova", "Prova de carga e inspeção final", 5, ["oae.sinil"], "W_ENG")

    # ---- 8. Demobilisation and handover
    ctx.update(disc="DESMOBILIZAÇÃO", seg="GERAL")
    S(1, "fim", "Desmobilização e Entrega")
    A(2, "fim.limp", "Limpeza final e recomposição das áreas de apoio", 10,
      ["ms.s1", "ms.s2", "ms.s3", "ms.s4", "ms.oae"], "W_ADM")
    A(2, "fim.jaz", "Recuperação ambiental de jazidas e caminhos de serviço", 15,
      ["ms.terr"], "W_AMB", cal=2)
    A(2, "fim.asb", "Projeto as built e data book", 25, ["s4.pav.capa", "oae.conc"], "W_ENG")
    A(2, "fim.vist", "Vistoria final com a fiscalização", 5,
      feeding("fim.limp", "fim.jaz", "fim.asb"), "W_ENG")
    A(2, "fim.pend", "Correção de pendências da vistoria", 10, ["fim.vist"], "W_ADM")
    A(2, "fim.desmob", "Desmobilização do canteiro e da usina", 15, ["fim.pend"], "W_MOB")

    # outline numbers, parents
    counters, stack = [0] * 8, []
    for r in rows:
        counters[r.level] += 1
        for lv in range(r.level + 1, 8):
            counters[lv] = 0
        r.outline = ".".join(str(counters[lv]) for lv in range(1, r.level + 1))
        while stack and stack[-1].level >= r.level:
            stack.pop()
        if stack:
            stack[-1].children.append(r)
        r.parent = stack[-1] if stack else None
        stack.append(r)
    return rows


def topo(rows: list) -> list:
    by = {r.key: r for r in rows}
    seen, order = set(), []

    def visit(r):
        if r.key in seen:
            return
        seen.add(r.key)
        for p, _, _ in r.preds:
            visit(by[p])
        order.append(r)

    for r in rows:
        if r.kind != "sum":
            visit(r)
    return order


def cost_of(r: Row, dur: int) -> float:
    if r.kind != "task":
        return 0.0
    rate = RES_BY_KEY[r.res][5]
    return round((r.qty if r.qty is not None else dur * 8.0) * rate, 2)


# ---------------------------------------------------------------------------
# The scheduling pass
# ---------------------------------------------------------------------------
def schedule(rows: list, status: date | None, delta=None, delay=None, force=None, push=None,
             deadlines=None) -> dict:
    """Forward and backward pass. Returns key -> dict of dates and state.

    With no status date nothing is executed: that run is the baseline.
    """
    delta, delay, force, push = delta or {}, delay or {}, force or {}, push or {}
    deadlines = deadlines or {}
    order = topo(rows)
    out = {}
    for r in order:
        cal = CALS[r.cal]
        if r.kind == "ms":
            if not r.preds:
                out[r.key] = {"S": PROJECT_START, "F": PROJECT_START, "dur": 0, "at_start": True}
                continue
            d = PROJECT_START
            for p, _, lag in r.preds:
                d = max(d, cal.add(cal.on_or_after(out[p]["F"]), lag))
            out[r.key] = {"S": d, "F": d, "dur": 0, "at_start": False}
            continue
        dur = r.dur + delta.get(r.key, 0)
        cands = [cal.on_or_after(PROJECT_START)]
        for p, typ, lag in r.preds:
            P = out[p]
            if typ == "FS":
                base = cal.on_or_after(P["F"]) if P.get("at_start") else cal.on_or_after(P["F"] + timedelta(days=1))
                cands.append(cal.add(base, lag))
            elif typ == "SS":
                cands.append(cal.add(cal.on_or_after(P["S"]), lag))
            elif typ == "FF":
                cands.append(cal.add(cal.add(cal.on_or_after(P["F"]), lag), -(dur - 1)))
        s = cal.add(max(cands), delay.get(r.key, 0))
        rec = {"dur": dur}
        if r.key in push:
            s = cal.add(s, push[r.key])
            rec["snet"] = s
        if r.key in force:
            s = force[r.key]
        rec["S"], rec["F"] = s, cal.add(s, dur - 1)
        out[r.key] = rec

    # ---- state at the status date
    for r in order:
        rec = out[r.key]
        cal = CALS[r.cal]
        if status is None:
            rec["state"] = "future"
        elif r.kind == "ms":
            rec["state"] = "done" if rec["F"] <= status else "future"
        elif rec["F"] <= status:
            rec["state"] = "done"
        elif rec["S"] <= status:
            rec["state"] = "wip"
            rec["elapsed"] = cal.count(rec["S"], status)
            rec["pct"] = min(99, max(1, int(round(100.0 * rec["elapsed"] / rec["dur"]))))
        else:
            rec["state"] = "future"

    # ---- backward pass: late dates, total float, critical
    end = max(rec["F"] for rec in out.values())
    succs = {r.key: [] for r in order}
    for r in order:
        for p, typ, lag in r.preds:
            succs[p].append((r, typ, lag))
    for r in reversed(order):
        rec, cal = out[r.key], CALS[r.cal]
        if rec["state"] == "done":
            rec["LF"], rec["LS"], rec["slack"], rec["critical"] = rec["F"], rec["S"], 0, False
            continue
        dur = max(1, rec["dur"])
        cands = []
        for s, typ, lag in succs[r.key]:
            srec, scal = out[s.key], CALS[s.cal]
            if srec["state"] == "done":
                continue
            started = srec["state"] == "wip"
            if typ == "FS":
                if s.kind == "ms":
                    cands.append(cal.on_or_before(scal.add(srec["LF"], -lag)))
                elif started:
                    cands.append(cal.on_or_before(srec["LF"]))
                else:
                    cands.append(cal.on_or_before(scal.add(srec["LS"], -lag) - timedelta(days=1)))
            elif typ == "SS":
                if started or rec["state"] == "wip":
                    cands.append(cal.on_or_before(srec["LF"]))
                else:
                    cands.append(cal.add(cal.on_or_before(scal.add(srec["LS"], -lag)), dur - 1))
            elif typ == "FF":
                cands.append(cal.on_or_before(scal.add(srec["LF"], -lag)))
        if not cands:
            cands.append(cal.on_or_before(end))
        if r.key in deadlines:
            cands.append(cal.on_or_before(deadlines[r.key]))
        rec["LF"] = min(cands)
        rec["LS"] = rec["LF"] if r.kind == "ms" else cal.add(rec["LF"], -(dur - 1))
        rec["slack"] = cal.slack(rec["F"], rec["LF"])
        rec["critical"] = rec["slack"] <= 0
    return out


# ---------------------------------------------------------------------------
# XML
# ---------------------------------------------------------------------------
def ts(d: date, end: bool) -> str:
    return f"{d.isoformat()}T{'17' if end else '08'}:00:00"


def dur_iso(days: float) -> str:
    return f"PT{int(round(days * 8))}H0M0S"


def qty_iso(q: float) -> str:
    h = int(q)
    m = int(round((q - h) * 60))
    return f"PT{h}H{m}M0S"


def cents(v: float) -> int:
    """MSPDI stores money in hundredths of the currency unit."""
    return int(round(v * 100))


def calendars_xml() -> str:
    L = ["  <Calendars>"]
    for cal in CALS.values():
        L += ["    <Calendar>", f"      <UID>{cal.uid}</UID>", f"      <Name>{escape(cal.name)}</Name>",
              "      <IsBaseCalendar>1</IsBaseCalendar>", "      <IsBaselineCalendar>0</IsBaselineCalendar>",
              "      <BaseCalendarUID>-1</BaseCalendarUID>", "      <WeekDays>"]
        for day_type in range(1, 8):                     # MSPDI: 1 = Sunday
            py = (day_type + 5) % 7
            if py in cal.week:
                L += ["        <WeekDay>", f"          <DayType>{day_type}</DayType>",
                      "          <DayWorking>1</DayWorking>", "          <WorkingTimes>",
                      "            <WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>",
                      "            <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>",
                      "          </WorkingTimes>", "        </WeekDay>"]
            else:
                L += ["        <WeekDay>", f"          <DayType>{day_type}</DayType>",
                      "          <DayWorking>0</DayWorking>", "        </WeekDay>"]
        L += ["      </WeekDays>", "      <Exceptions>"]
        for d in sorted(cal.exceptions):
            L += ["        <Exception>", "          <EnteredByOccurrences>0</EnteredByOccurrences>",
                  "          <TimePeriod>", f"            <FromDate>{d.isoformat()}T00:00:00</FromDate>",
                  f"            <ToDate>{d.isoformat()}T23:59:00</ToDate>", "          </TimePeriod>",
                  "          <Occurrences>1</Occurrences>", f"          <Name>{escape(cal.exceptions[d])}</Name>",
                  "          <Type>1</Type>", "          <DayWorking>0</DayWorking>", "        </Exception>"]
        L += ["      </Exceptions>", "    </Calendar>"]
    L.append("  </Calendars>")
    return "\n".join(L)


def tp(kind: int, uid: int, d: date, unit: int, value: str) -> str:
    return (f"    <TimephasedData><Type>{kind}</Type><UID>{uid}</UID>"
            f"<Start>{d.isoformat()}T08:00:00</Start><Finish>{d.isoformat()}T17:00:00</Finish>"
            f"<Unit>{unit}</Unit><Value>{value}</Value></TimephasedData>")


def spread_cents(total: int, n: int) -> list:
    base, rem = divmod(total, n)
    return [base + (1 if i < rem else 0) for i in range(n)]


def build(rev: str, base_rows: list, base_sched: dict) -> dict:
    """Schedule one revision and attach its baseline, deadlines and actuals."""
    status = STATUS[rev]
    rows = build_rows(rev)
    pert = PERTURB[rev]
    force, push = {}, {}
    if rev == "rev04":
        force[PLANTED["out_of_sequence"]["task"]] = PLANTED["out_of_sequence"]["start"]
        push[PLANTED["replan"]["task"]] = PLANTED["replan"]["push_days"]
    by = {r.key: r for r in rows}
    base_by = {r.key: r for r in base_rows}

    # The baseline is the plan with nothing executed; deadlines hang off the
    # baseline date of each milestone.
    baseline, deadlines = {}, {}
    for r in rows:
        if r.kind != "sum" and r.key in base_sched:
            b = base_sched[r.key]
            baseline[r.key] = {"S": b["S"], "F": b["F"], "dur": b["dur"],
                               "cost": cost_of(base_by[r.key], b["dur"])}
            if r.kind == "ms":
                deadlines[r.key] = CALS[1].add(b["F"], r.margin)

    sched = schedule(rows, status, pert["delta"], pert["delay"], force, push, deadlines)

    # An activity that entered after the baseline was saved is baselined at the
    # dates it had on the day it entered.
    for r in rows:
        if r.kind != "sum" and r.key not in baseline:
            s = sched[r.key]
            baseline[r.key] = {"S": s["S"], "F": s["F"], "dur": s["dur"], "cost": cost_of(r, s["dur"])}
    if rev == "rev04":
        k = PLANTED["rebaselined"]["task"]
        cal, b = CALS[by[k].cal], baseline[k]
        ns = cal.add(b["S"], PLANTED["rebaselined"]["shift_days"])
        baseline[k] = {**b, "S": ns, "F": cal.add(ns, b["dur"] - 1)}

    # Reported actuals and percents.
    for r in rows:
        if r.kind == "sum":
            continue
        s = sched[r.key]
        s["AS"] = s["S"] if s["state"] in ("done", "wip") else None
        s["AF"] = s["F"] if s["state"] == "done" else None
        s["true_F"] = s["F"]
        s["pct"] = 100 if s["state"] == "done" else s.get("pct", 0)
        s["phys"] = s["pct"]
        s["elapsed"] = s["dur"] if s["state"] == "done" else s.get("elapsed", 0)
    k = PLANTED["percent_vs_physical"]["task"]
    if sched[k]["state"] == "wip":
        sched[k]["phys"] = int(round(sched[k]["pct"] * PLANTED["percent_vs_physical"]["physical_factor"]))
    if rev == "rev04":
        k = PLANTED["past_rewritten"]["task"]
        cal, s = CALS[by[k].cal], sched[k]
        assert s["state"] == "done", "the rewritten activity must already be complete"
        s["AF"] = s["F"] = s["LF"] = cal.add(s["F"], PLANTED["past_rewritten"]["shift_days"])
        s["dur"] = s["elapsed"] = cal.count(s["S"], s["F"])
    return {"rev": rev, "status": status, "rows": rows, "sched": sched,
            "baseline": baseline, "deadlines": deadlines}


def rollup(r: Row, snap: dict) -> dict:
    """Dates, percent and baseline of a summary row, from its leaves."""
    leaves, stack = [], list(r.children)
    while stack:
        c = stack.pop()
        if c.kind == "sum":
            stack.extend(c.children)
        else:
            leaves.append(c)
    sc, bl = snap["sched"], snap["baseline"]
    recs = [sc[c.key] for c in leaves]
    tasks = [sc[c.key] for c in leaves if c.kind == "task"]
    total = sum(x["dur"] for x in tasks) or 1
    done = sum(x["elapsed"] for x in tasks)
    return {
        "S": min(x["S"] for x in recs), "F": max(x["F"] for x in recs),
        "AS": min((x["AS"] for x in recs if x["AS"]), default=None),
        "AF": max(x["AF"] for x in recs) if all(x["AF"] for x in recs) else None,
        "pct": 100 if all(x["AF"] for x in recs) else min(99, int(100.0 * done / total)),
        "critical": any(x["critical"] for x in recs),
        "bS": min(bl[c.key]["S"] for c in leaves), "bF": max(bl[c.key]["F"] for c in leaves),
        "bcost": sum(bl[c.key]["cost"] for c in leaves),
        "cost": sum(cost_of(c, sc[c.key]["dur"]) for c in leaves),
    }


def task_xml(r: Row, snap: dict, uid_of: dict, assignments: list) -> str:
    sc, bl, status = snap["sched"], snap["baseline"], snap["status"]
    cal = CALS[r.cal]
    L = ["    <Task>", f"      <UID>{r.uid}</UID>", f"      <ID>{r.id}</ID>",
         f"      <Name>{escape(r.name)}</Name>", "      <Active>1</Active>", "      <Manual>0</Manual>",
         "      <Type>0</Type>", "      <IsNull>0</IsNull>",
         "      <CreateDate>2026-02-10T08:00:00</CreateDate>",
         f"      <WBS>{r.outline}</WBS>", f"      <OutlineNumber>{r.outline}</OutlineNumber>",
         f"      <OutlineLevel>{r.level}</OutlineLevel>", "      <Priority>500</Priority>"]

    if r.kind == "sum":
        u = rollup(r, snap)
        days = CALS[1].count(u["S"], u["F"])
        L += [f"      <Start>{ts(u['S'], False)}</Start>", f"      <Finish>{ts(u['F'], True)}</Finish>",
              f"      <Duration>{dur_iso(days)}</Duration>", "      <DurationFormat>7</DurationFormat>",
              "      <EffortDriven>0</EffortDriven>", "      <Estimated>0</Estimated>",
              "      <Milestone>0</Milestone>", "      <Summary>1</Summary>",
              f"      <Critical>{1 if u['critical'] else 0}</Critical>",
              "      <ExternalTask>0</ExternalTask>",
              "      <FixedCostAccrual>3</FixedCostAccrual>",
              f"      <PercentComplete>{u['pct']}</PercentComplete>",
              f"      <Cost>{cents(u['cost'])}</Cost>"]
        if u["AS"]:
            L.append(f"      <ActualStart>{ts(u['AS'], False)}</ActualStart>")
        if u["AF"]:
            L.append(f"      <ActualFinish>{ts(u['AF'], True)}</ActualFinish>")
        L += ["      <ConstraintType>0</ConstraintType>", "      <CalendarUID>-1</CalendarUID>",
              "      <Baseline>", "        <Number>0</Number>",
              f"        <Start>{ts(u['bS'], False)}</Start>", f"        <Finish>{ts(u['bF'], True)}</Finish>",
              f"        <Duration>{dur_iso(CALS[1].count(u['bS'], u['bF']))}</Duration>",
              "        <DurationFormat>7</DurationFormat>",
              f"        <Cost>{cents(u['bcost'])}</Cost>", "      </Baseline>", "    </Task>"]
        return "\n".join(L)

    s, b = sc[r.key], bl[r.key]
    ms = r.kind == "ms"
    at_start = bool(s.get("at_start"))
    start = ts(s["S"], not at_start) if ms else ts(s["S"], False)
    finish = ts(s["F"], not at_start) if ms else ts(s["F"], True)
    bstart = ts(b["S"], not at_start) if ms else ts(b["S"], False)
    bfinish = ts(b["F"], not at_start) if ms else ts(b["F"], True)
    res = RES_BY_KEY[r.res] if r.res else None
    is_work = bool(res and res[3] == 1)
    cost = cost_of(r, s["dur"])
    bcost_c = cents(b["cost"])
    pct, phys = s["pct"], s["phys"]

    L += [f"      <Start>{start}</Start>", f"      <Finish>{finish}</Finish>",
          f"      <Duration>{dur_iso(s['dur'])}</Duration>", "      <DurationFormat>7</DurationFormat>",
          f"      <Work>{dur_iso(s['dur']) if is_work else 'PT0H0M0S'}</Work>",
          "      <EffortDriven>0</EffortDriven>", "      <Estimated>0</Estimated>",
          f"      <Milestone>{1 if ms else 0}</Milestone>", "      <Summary>0</Summary>",
          f"      <Critical>{1 if s['critical'] else 0}</Critical>",
          "      <ExternalTask>0</ExternalTask>",
          f"      <EarlyStart>{start}</EarlyStart>", f"      <EarlyFinish>{finish}</EarlyFinish>",
          f"      <LateStart>{ts(s['LS'], not at_start) if ms else ts(s['LS'], False)}</LateStart>",
          f"      <LateFinish>{ts(s['LF'], not at_start) if ms else ts(s['LF'], True)}</LateFinish>",
          f"      <TotalSlack>{s['slack'] * DAY_MIN * 10}</TotalSlack>",
          "      <FixedCostAccrual>3</FixedCostAccrual>",
          f"      <PercentComplete>{pct}</PercentComplete>",
          f"      <Cost>{cents(cost)}</Cost>"]
    if s["AS"]:
        L.append(f"      <ActualStart>{ts(s['AS'], not at_start) if ms else ts(s['AS'], False)}</ActualStart>")
    if s["AF"]:
        L.append(f"      <ActualFinish>{ts(s['AF'], not at_start) if ms else ts(s['AF'], True)}</ActualFinish>")
    if not ms:
        L += [f"      <ActualDuration>{dur_iso(s['elapsed'])}</ActualDuration>",
              f"      <RemainingDuration>{dur_iso(s['dur'] - s['elapsed'])}</RemainingDuration>"]
    L += [f"      <ConstraintType>{4 if s.get('snet') else 0}</ConstraintType>",
          f"      <CalendarUID>{r.cal if r.cal != 1 else -1}</CalendarUID>"]
    if s.get("snet"):
        L.append(f"      <ConstraintDate>{ts(s['snet'], False)}</ConstraintDate>")
    if r.key in snap["deadlines"]:
        L.append(f"      <Deadline>{ts(snap['deadlines'][r.key], not at_start)}</Deadline>")

    # The planned value to the status date is the baseline phasing itself, added up.
    blocks, bcws = [], 0
    if bcost_c > 0:
        days = cal.days_list(b["S"], b["F"])
        for d, v in zip(days, spread_cents(bcost_c, len(days))):
            blocks.append(tp(10, r.uid, d, 2, str(v)))
            if d <= status:
                bcws += v
    L += [f"      <BCWS>{bcws}</BCWS>", f"      <BCWP>{bcost_c * phys / 100.0:.2f}</BCWP>",
          f"      <PhysicalPercentComplete>{phys}</PhysicalPercentComplete>",
          "      <EarnedValueMethod>1</EarnedValueMethod>"]
    for p, typ, lag in r.preds:
        L += ["      <PredecessorLink>", f"        <PredecessorUID>{uid_of[p]}</PredecessorUID>",
              f"        <Type>{ {'FF': 0, 'FS': 1, 'SF': 2, 'SS': 3}[typ] }</Type>",
              "        <CrossProject>0</CrossProject>",
              f"        <LinkLag>{lag * DAY_MIN * 10}</LinkLag>", "        <LagFormat>7</LagFormat>",
              "      </PredecessorLink>"]
    for fid, val in ((FIELD_DISC, r.disc), (FIELD_SEG, r.seg)):
        L += ["      <ExtendedAttribute>", f"        <FieldID>{fid}</FieldID>",
              f"        <Value>{escape(val)}</Value>", "      </ExtendedAttribute>"]
    L += ["      <Baseline>", "        <Number>0</Number>", f"        <Start>{bstart}</Start>",
          f"        <Finish>{bfinish}</Finish>", f"        <Duration>{dur_iso(b['dur'])}</Duration>",
          "        <DurationFormat>7</DurationFormat>",
          f"        <Work>{dur_iso(b['dur']) if is_work else 'PT0H0M0S'}</Work>",
          f"        <Cost>{bcost_c}</Cost>", "      </Baseline>"]
    L += [x.replace("    <Timephased", "      <Timephased", 1) for x in blocks]

    # Physical percent by day, the way the tool spreads it over the actual span.
    actual_days = cal.days_list(s["AS"], s["AF"] or status) if (s["AS"] and not ms) else []
    if phys > 0 and actual_days:
        per = f"{phys / len(actual_days):.4f}"
        L += [tp(11, r.uid, d, 2, per).replace("    <Timephased", "      <Timephased", 1) for d in actual_days]
    L.append("    </Task>")

    if res:
        planned = r.qty if not is_work else b["dur"] * 8.0
        current = r.qty if not is_work else s["dur"] * 8.0
        executed = round(current * phys / 100.0, 2)
        A = ["    <Assignment>", f"      <UID>{10000 + r.uid}</UID>", f"      <TaskUID>{r.uid}</TaskUID>",
             f"      <ResourceUID>{res[0]}</ResourceUID>",
             f"      <PercentWorkComplete>{phys}</PercentWorkComplete>"]
        if s["AF"]:
            A.append(f"      <ActualFinish>{ts(s['AF'], True)}</ActualFinish>")
        if s["AS"]:
            A.append(f"      <ActualStart>{ts(s['AS'], False)}</ActualStart>")
        A += [f"      <ActualWork>{qty_iso(executed)}</ActualWork>",
              f"      <Cost>{cents(cost)}</Cost>", f"      <Finish>{finish}</Finish>",
              f"      <RemainingWork>{qty_iso(max(0.0, current - executed))}</RemainingWork>",
              f"      <Start>{start}</Start>",
              f"      <Units>{1 if is_work else int(r.qty)}</Units>",
              f"      <Work>{qty_iso(current)}</Work>",
              "      <Baseline>", "        <Number>0</Number>", f"        <Start>{bstart}</Start>",
              f"        <Finish>{bfinish}</Finish>", f"        <Work>{qty_iso(planned)}</Work>",
              f"        <Cost>{bcost_c}</Cost>", "      </Baseline>"]
        if executed > 0 and actual_days:
            each = executed / len(actual_days)
            A += [tp(2, 10000 + r.uid, d, 2, qty_iso(each)).replace("    <Timephased", "      <Timephased", 1)
                  for d in actual_days]
        A.append("    </Assignment>")
        assignments.append("\n".join(A))
    return "\n".join(L)


def document(snap: dict, uid_of: dict) -> str:
    rev, status, rows, sc = snap["rev"], snap["status"], snap["rows"], snap["sched"]
    end = max(sc[r.key]["F"] for r in rows if r.kind != "sum")
    leaves = [r for r in rows if r.kind != "sum"]
    bcost = sum(snap["baseline"][r.key]["cost"] for r in leaves)
    done = sum(sc[r.key]["elapsed"] for r in leaves)
    total = sum(sc[r.key]["dur"] for r in leaves) or 1
    title = f"{PROJECT_NAME} — Rev. {rev[-2:]}"
    head = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<Project xmlns="{NS}">',
        "  <SaveVersion>14</SaveVersion>",
        f"  <Name>rodovia-ficticia-{rev}.xml</Name>",
        f"  <Title>{escape(title)}</Title>",
        f"  <Subject>{escape('Cronograma de exemplo, inteiramente fictício — cliente: ' + CLIENT)}</Subject>",
        f"  <Company>{escape(COMPANY)}</Company>",
        "  <Author>cronoaudit — exemplo fictício</Author>",
        "  <CreationDate>2026-02-10T08:00:00</CreationDate>",
        f"  <LastSaved>{ts(status + timedelta(days=4), True)}</LastSaved>",
        "  <ScheduleFromStart>1</ScheduleFromStart>",
        f"  <StartDate>{ts(PROJECT_START, False)}</StartDate>",
        f"  <FinishDate>{ts(end, True)}</FinishDate>",
        "  <FYStartDate>1</FYStartDate>",
        "  <CriticalSlackLimit>0</CriticalSlackLimit>",
        "  <CurrencyDigits>2</CurrencyDigits>",
        "  <CurrencySymbol>R$</CurrencySymbol>",
        "  <CurrencyCode>BRL</CurrencyCode>",
        "  <CurrencySymbolPosition>2</CurrencySymbolPosition>",
        "  <CalendarUID>1</CalendarUID>",
        "  <DefaultStartTime>08:00:00</DefaultStartTime>",
        "  <DefaultFinishTime>17:00:00</DefaultFinishTime>",
        f"  <MinutesPerDay>{DAY_MIN}</MinutesPerDay>",
        "  <MinutesPerWeek>2400</MinutesPerWeek>",
        "  <DaysPerMonth>20</DaysPerMonth>",
        "  <DefaultTaskType>0</DefaultTaskType>",
        "  <DefaultFixedCostAccrual>3</DefaultFixedCostAccrual>",
        "  <DefaultStandardRate>0</DefaultStandardRate>",
        "  <DefaultOvertimeRate>0</DefaultOvertimeRate>",
        "  <DurationFormat>7</DurationFormat>",
        "  <WorkFormat>2</WorkFormat>",
        "  <EditableActualCosts>0</EditableActualCosts>",
        "  <HonorConstraints>0</HonorConstraints>",
        "  <InsertedProjectsLikeSummary>1</InsertedProjectsLikeSummary>",
        "  <MultipleCriticalPaths>0</MultipleCriticalPaths>",
        "  <NewTasksEffortDriven>0</NewTasksEffortDriven>",
        "  <NewTasksEstimated>0</NewTasksEstimated>",
        "  <SplitsInProgressTasks>0</SplitsInProgressTasks>",
        "  <SpreadActualCost>0</SpreadActualCost>",
        "  <SpreadPercentComplete>0</SpreadPercentComplete>",
        "  <TaskUpdatesResource>1</TaskUpdatesResource>",
        "  <FiscalYearStart>0</FiscalYearStart>",
        "  <WeekStartDay>1</WeekStartDay>",
        "  <MoveCompletedEndsBack>0</MoveCompletedEndsBack>",
        "  <MoveRemainingStartsBack>0</MoveRemainingStartsBack>",
        "  <MoveRemainingStartsForward>0</MoveRemainingStartsForward>",
        "  <MoveCompletedEndsForward>0</MoveCompletedEndsForward>",
        "  <BaselineForEarnedValue>0</BaselineForEarnedValue>",
        "  <AutoAddNewResourcesAndTasks>1</AutoAddNewResourcesAndTasks>",
        f"  <StatusDate>{ts(status, True)}</StatusDate>",
        f"  <CurrentDate>{ts(status + timedelta(days=4), False)}</CurrentDate>",
        "  <NewTasksAreManual>0</NewTasksAreManual>",
        "  <DefaultTaskEVMethod>1</DefaultTaskEVMethod>",
        "  <ExtendedAttributes>",
        f"    <ExtendedAttribute><FieldID>{FIELD_DISC}</FieldID><FieldName>Text1</FieldName>"
        "<Alias>DISCIPLINA</Alias></ExtendedAttribute>",
        f"    <ExtendedAttribute><FieldID>{FIELD_SEG}</FieldID><FieldName>Text2</FieldName>"
        "<Alias>SEGMENTO</Alias></ExtendedAttribute>",
        "  </ExtendedAttributes>",
        calendars_xml(),
        "  <Tasks>",
        # Row zero, the project summary the tool itself writes.
        "    <Task>", "      <UID>0</UID>", "      <ID>0</ID>", f"      <Name>{escape(title)}</Name>",
        "      <Active>1</Active>", "      <Manual>0</Manual>", "      <Type>1</Type>",
        "      <IsNull>0</IsNull>", "      <CreateDate>2026-02-10T08:00:00</CreateDate>",
        "      <WBS>0</WBS>", "      <OutlineNumber>0</OutlineNumber>", "      <OutlineLevel>0</OutlineLevel>",
        "      <Priority>500</Priority>",
        f"      <Start>{ts(PROJECT_START, False)}</Start>", f"      <Finish>{ts(end, True)}</Finish>",
        f"      <Duration>{dur_iso(CALS[1].count(PROJECT_START, end))}</Duration>",
        "      <DurationFormat>7</DurationFormat>", "      <Milestone>0</Milestone>",
        "      <Summary>1</Summary>", "      <Critical>1</Critical>", "      <ExternalTask>0</ExternalTask>",
        f"      <PercentComplete>{int(100.0 * done / total)}</PercentComplete>",
        f"      <ActualStart>{ts(PROJECT_START, False)}</ActualStart>",
        "      <ConstraintType>0</ConstraintType>", "      <CalendarUID>-1</CalendarUID>",
        "      <Baseline>", "        <Number>0</Number>",
        f"        <Cost>{cents(bcost)}</Cost>", "      </Baseline>",
        "    </Task>",
    ]
    assignments = []
    body = [task_xml(r, snap, uid_of, assignments) for r in rows]
    res = ["  </Tasks>", "  <Resources>"]
    for i, (uid, _, name, typ, label, rate) in enumerate(RES, 1):
        res += ["    <Resource>", f"      <UID>{uid}</UID>", f"      <ID>{i}</ID>",
                f"      <Name>{escape(name)}</Name>", f"      <Type>{typ}</Type>", "      <IsNull>0</IsNull>"]
        if label:
            res.append(f"      <MaterialLabel>{escape(label)}</MaterialLabel>")
        res += ["      <MaxUnits>1</MaxUnits>", f"      <StandardRate>{rate:.2f}</StandardRate>",
                f"      <StandardRateFormat>{2 if typ == 1 else 8}</StandardRateFormat>",
                "    </Resource>"]
    res += ["  </Resources>", "  <Assignments>"]
    return "\n".join(head + body + res + assignments + ["  </Assignments>", "</Project>"]) + "\n"


def generate() -> dict:
    """Both revisions, as {file name: xml text}, plus the snapshots for inspection."""
    rows03 = build_rows("rev03")
    base_sched = schedule(rows03, None)
    uid_of = {r.key: i for i, r in enumerate(rows03, 1)}
    snaps = {}
    for rev in ("rev03", "rev04"):
        snap = build(rev, rows03, base_sched)
        for r in snap["rows"]:
            if r.key not in uid_of:            # a row that entered later takes the next free UID
                uid_of[r.key] = max(uid_of.values()) + 1
        for i, r in enumerate(snap["rows"], 1):
            r.id, r.uid = i, uid_of[r.key]
        snaps[rev] = snap

    # The past does not change by itself. Whatever rev03 reported as done or
    # started must read the same in rev04, except where a rewrite was planted.
    p, c = snaps["rev03"]["sched"], snaps["rev04"]["sched"]
    for k, a in p.items():
        if k not in c or a.get("state") is None:
            continue
        if a["state"] in ("done", "wip"):
            assert c[k]["S"] == a["S"], f"{k}: actual start drifted between revisions"
        if a["state"] == "done":
            assert c[k]["true_F"] == a["F"], f"{k}: actual finish drifted between revisions"
    for rev in ("rev03", "rev04"):
        started = {k for k, v in snaps[rev]["sched"].items() if v.get("state") in ("done", "wip")}
        stray = [k for k in PERTURB[rev]["delta"] if k not in started]
        assert not stray, f"{rev}: reality is declared for work that has not started: {stray}"

    files = {f"rodovia-ficticia-{rev}.xml": document(snaps[rev], uid_of) for rev in snaps}
    return {"files": files, "snaps": snaps}


def listing(snap: dict) -> str:
    sc, bl = snap["sched"], snap["baseline"]
    L = []
    for r in snap["rows"]:
        if r.kind == "sum":
            L.append(f"{r.id:>4} {'  ' * r.level}{r.name}")
            continue
        s, b = sc[r.key], bl[r.key]
        L.append(f"{r.id:>4} {r.key:<14} {s['state']:<6} {s['S']} {s['F']} d{s['dur']:<3} "
                 f"bl {b['S']} {b['F']} var {CALS[r.cal].slack(b['F'], s['F']):>4} "
                 f"tf {s['slack']:>4} {'C' if s['critical'] else ' '} {s['pct']:>3}% "
                 f"{b['cost'] / 1e6:7.2f}M")
    return "\n".join(L)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out = generate()
    for name, body in out["files"].items():
        path = os.path.join(here, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        snap = out["snaps"][name[-9:-4]]
        rows = snap["rows"]
        print(f"wrote {name}: {sum(1 for r in rows if r.kind != 'sum')} activities, "
              f"{sum(1 for r in rows if r.kind == 'sum')} summaries, "
              f"{sum(len(r.preds) for r in rows)} links, {len(RES)} resources")
    if "--list" in sys.argv:
        for rev in ("rev03", "rev04"):
            print(f"\n--- {rev} ---")
            print(listing(out["snaps"][rev]))


if __name__ == "__main__":
    main()
