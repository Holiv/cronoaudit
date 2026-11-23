"""A .mpp in, an XML out, through the MS Project installed on this computer.

The person, or the agent working for them, should be able to say "analyse
Rev04.mpp" without knowing that the engine reads XML. On Windows with Project
installed, export_mpp.ps1 does what a person would do by hand (File > Save As >
XML) and this module hands the XML to the engine. Elsewhere, or without Project,
it says what to do instead, in plain words.

The XML goes to a temporary folder named after nothing but a random token, under
the file's own stem so the report keeps the name the person recognises, and the
caller deletes the folder when the run ends. Nothing of the schedule is printed
here: in secret mode the screen must stay free of names, and a path can be one.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PS1 = os.path.join(HERE, "export_mpp.ps1")
TIMEOUT_S = 600
ACTIVE = ":open-in-project:"

MESSAGES = {
    "en": {
        "not_windows": "{name}: a .mpp file can only be exported by MS Project, which runs on Windows. "
                       "Open it in Project and use File > Save As > XML Format, then pass the .xml.",
        "no_project": "MS Project was not found on this computer, so the .mpp cannot be exported here. "
                      "Ask for the XML export of the schedule (in Project: File > Save As > XML Format).",
        "project_not_running": "MS Project is not open. Open the schedule in Project, or pass the .mpp file.",
        "nothing_open": "MS Project is open, but no schedule is. Open the schedule, or pass the .mpp file.",
        "never_saved": "The schedule open in Project was never saved to disk. Save it, then try again.",
        "already_xml": "The schedule open in Project is already an XML file. Pass that file directly.",
        "unsaved_note": "Note: {name} is open in Project with unsaved changes (Project marks a file so "
                        "just by opening it). The analysis read the file as saved on disk.",
        "open_failed": "MS Project did not open the file. Open it in Project once to see what it asks.",
        "export_failed": "MS Project could not export the file ({detail}). Export it by hand: "
                         "File > Save As > XML Format.",
        "export_empty": "MS Project wrote an empty XML. Export it by hand: File > Save As > XML Format.",
        "timeout": "MS Project did not answer in {s} seconds. It may be waiting on a question on the "
                   "screen; answer it, or export by hand: File > Save As > XML Format.",
        "not_found": "{name}: no such file.",
        "no_output": "The export gave no answer. Export by hand: File > Save As > XML Format.",
    },
    "pt": {
        "not_windows": "{name}: um arquivo .mpp só pode ser exportado pelo MS Project, que roda no Windows. "
                       "Abra no Project e use Arquivo > Salvar como > Formato XML, depois passe o .xml.",
        "no_project": "O MS Project não foi encontrado neste computador, então o .mpp não pode ser exportado "
                      "aqui. Peça a exportação em XML do cronograma (no Project: Arquivo > Salvar como > Formato XML).",
        "project_not_running": "O MS Project não está aberto. Abra o cronograma no Project, ou passe o arquivo .mpp.",
        "nothing_open": "O MS Project está aberto, mas sem cronograma. Abra o cronograma, ou passe o arquivo .mpp.",
        "never_saved": "O cronograma aberto no Project nunca foi salvo em disco. Salve e tente de novo.",
        "already_xml": "O cronograma aberto no Project já é um XML. Passe esse arquivo direto.",
        "unsaved_note": "Aviso: {name} está aberto no Project com alterações não salvas (o Project marca "
                        "o arquivo assim só por abrir). A análise leu o arquivo como está salvo em disco.",
        "open_failed": "O MS Project não abriu o arquivo. Abra uma vez no Project para ver o que ele pergunta.",
        "export_failed": "O MS Project não conseguiu exportar o arquivo ({detail}). Exporte à mão: "
                         "Arquivo > Salvar como > Formato XML.",
        "export_empty": "O MS Project gravou um XML vazio. Exporte à mão: Arquivo > Salvar como > Formato XML.",
        "timeout": "O MS Project não respondeu em {s} segundos. Pode estar esperando uma resposta na tela; "
                   "responda, ou exporte à mão: Arquivo > Salvar como > Formato XML.",
        "not_found": "{name}: arquivo não encontrado.",
        "no_output": "A exportação não respondeu. Exporte à mão: Arquivo > Salvar como > Formato XML.",
    },
}


class ExportError(Exception):
    pass


def needs_export(path: str) -> bool:
    return path == ACTIVE or os.path.splitext(path)[1].lower() == ".mpp"


def _say(code: str, lang: str, **kw) -> str:
    t = MESSAGES.get(lang, MESSAGES["en"])
    return t.get(code, t["no_output"]).format(**kw)


def export(path: str, tmpdir: str, lang: str = "en") -> tuple:
    """Export one .mpp (or the project open in Project, for ACTIVE) to XML in tmpdir.

    Returns (xml_path, source_path, note or ""). Raises ExportError with a sentence
    for a person.
    """
    name = ({"pt": "o cronograma aberto no Project"}.get(lang, "the schedule open in Project")
            if path == ACTIVE else os.path.basename(path))
    if os.name != "nt":
        raise ExportError(_say("not_windows", lang, name=name))
    if path != ACTIVE and not os.path.exists(path):
        raise ExportError(_say("not_found", lang, name=name))
    stem = os.path.splitext(name)[0] if path != ACTIVE else "schedule"
    out = os.path.join(tmpdir, stem + ".xml")
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1, "-Out", out]
    cmd += ["-Active"] if path == ACTIVE else ["-Path", os.path.abspath(path)]
    try:
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise ExportError(_say("timeout", lang, s=TIMEOUT_S))
    except OSError:
        raise ExportError(_say("no_project", lang))
    line = next((ln for ln in reversed((r.stdout or "").splitlines()) if ln.strip().startswith("{")), "")
    try:
        res = json.loads(line)
    except ValueError:
        raise ExportError(_say("no_output", lang))
    if not res.get("ok"):
        raise ExportError(_say(res.get("code") or "no_output", lang, detail=res.get("detail") or "?",
                               name=name, s=TIMEOUT_S))
    source = res.get("source") or path
    if path == ACTIVE:
        # Named after the schedule the person sees, so the report is too.
        named = os.path.join(tmpdir, os.path.splitext(os.path.basename(source))[0] + ".xml")
        if named != out:
            os.replace(out, named)
            out = named
    note = _say("unsaved_note", lang, name=os.path.basename(source)) if res.get("unsaved") else ""
    return out, source, note


def prepare(files: list, lang: str = "en"):
    """The engine's inputs with every .mpp exported. Returns (xml_files, origin_files,
    tmpdir or None, notes). The caller removes tmpdir with cleanup().

    Off Windows a .mpp is left alone: the optional reader, or the help that says
    how to export, takes it from there in review.load()."""
    if not any(needs_export(f) for f in files) or (os.name != "nt" and ACTIVE not in files):
        return files, [os.path.abspath(f) for f in files], None, []
    tmpdir = tempfile.mkdtemp(prefix="cronoaudit-export-")
    xml_files, origins, notes = [], [], []
    try:
        for i, f in enumerate(files):
            if needs_export(f):
                sub = os.path.join(tmpdir, str(i))
                os.makedirs(sub)
                x, src, note = export(f, sub, lang)
                if note:
                    notes.append(note)
                xml_files.append(x)
                origins.append(os.path.abspath(src))
            else:
                xml_files.append(f)
                origins.append(os.path.abspath(f))
    except Exception:
        cleanup(tmpdir)
        raise
    return xml_files, origins, tmpdir, notes


def cleanup(tmpdir) -> None:
    if tmpdir:
        shutil.rmtree(tmpdir, ignore_errors=True)
