#!/usr/bin/env bash
# cronoaudit installer — one command, every agent.
#
#   curl -fsSL https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.sh | bash -s -- --only claude
#
# Installs the skill into the two directories that, between them, every
# Agent Skills client reads:
#   ~/.claude/skills/cronoaudit   Claude Code, OpenCode, Cursor
#   ~/.agents/skills/cronoaudit   Codex, GitHub Copilot, and other Agent Skills clients
#   ~/.copilot/skills/cronoaudit  GitHub Copilot CLI, when it is on the machine (a Copilot
#                                 CLI did not find the skill in ~/.agents, measured)
#
# Then it copies the fictitious example to ~/cronoaudit-exemplo, offers to run it
# (CRONOAUDIT_EXAMPLE=0|1 answers in advance), and says how to use the skill.
#
# Needs: bash, curl or git, Python 3.9+, tar. Nothing is installed globally and
# the installer sends nothing; its only network access is the download itself.
# (An agent that later reads a schedule sends that content to its provider.)
set -euo pipefail

REPO="Holiv/cronoaudit"
REF="${CRONOAUDIT_REF:-main}"
ONLY="all"
SRC=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --only) ONLY="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --from) SRC="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf 'cronoaudit: %s\n' "$*" >&2; exit 1; }
# Portuguese on a Portuguese system, English otherwise.
case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in pt*|PT*) PT=1 ;; *) PT=0 ;; esac
t() { if [[ $PT == 1 ]]; then printf '%s\n' "$1"; else printf '%s\n' "$2"; fi; }

command -v python3 >/dev/null 2>&1 || die "python3 is required (3.9 or later) and was not found"
PYV="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || die "python3 $PYV found; 3.9 or later is required"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [[ -n "$SRC" ]]; then
  # A local checkout: install from it, no download.
  [[ -f "$SRC/skills/cronoaudit/SKILL.md" ]] || die "no skill found under $SRC/skills/cronoaudit"
  SKILL_DIR="$SRC/skills/cronoaudit"
else
  t "Baixando a cronoaudit ($REF)..." "downloading $REPO@$REF ..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/$REF" -o "$WORK/src.tgz" \
      || die "download failed; check the network or install with git clone"
    tar -xzf "$WORK/src.tgz" -C "$WORK"
  elif command -v git >/dev/null 2>&1; then
    git clone --depth 1 --branch "$REF" "https://github.com/$REPO.git" "$WORK/cronoaudit-$REF" >/dev/null 2>&1 \
      || die "git clone failed"
  else
    die "neither curl nor git is available"
  fi
  SKILL_DIR="$(find "$WORK" -maxdepth 3 -type d -path '*/skills/cronoaudit' | head -1)"
  [[ -n "$SKILL_DIR" && -f "$SKILL_DIR/SKILL.md" ]] || die "the download did not contain skills/cronoaudit/SKILL.md"
fi

install_to() {
  local dest="$1"
  mkdir -p "$dest"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --exclude '__pycache__' "$SKILL_DIR/" "$dest/"
  else
    rm -rf "$dest"; mkdir -p "$dest"; cp -R "$SKILL_DIR/." "$dest/"
  fi
  t "instalada em $dest" "installed -> $dest"
}

case "$ONLY" in
  all)    install_to "$HOME/.claude/skills/cronoaudit"; install_to "$HOME/.agents/skills/cronoaudit"
          if [[ -d "$HOME/.copilot" ]] || command -v copilot >/dev/null 2>&1; then
            install_to "$HOME/.copilot/skills/cronoaudit"
          fi ;;
  claude) install_to "$HOME/.claude/skills/cronoaudit" ;;
  agents) install_to "$HOME/.agents/skills/cronoaudit" ;;
  *) die "--only must be all, claude or agents" ;;
esac

# Prove the instrument can fire and can stay silent before anyone trusts it.
# The fictitious example, where a person can find it.
EX_SRC="$(cd "$SKILL_DIR/../.." && pwd)/examples"
EX_DEST="$HOME/cronoaudit-exemplo"
HAVE_EX=0
if [[ -d "$EX_SRC" ]]; then
  for f in "$EX_SRC"/rodovia-ficticia-rev0*.xml "$EX_SRC"/rodovia-ficticia-rev0*.mpp; do
    if [[ -f "$f" ]]; then mkdir -p "$EX_DEST"; cp "$f" "$EX_DEST/"; HAVE_EX=1; fi
  done
  if [[ $HAVE_EX == 1 ]]; then t "exemplo fictício em $EX_DEST" "fictitious example -> $EX_DEST"; fi
fi

t "Conferindo..." "verifying ..."
if python3 "$HOME/.claude/skills/cronoaudit/scripts/test_checks.py" >/dev/null 2>&1 \
   || python3 "$HOME/.agents/skills/cronoaudit/scripts/test_checks.py" >/dev/null 2>&1; then
  t "Autoteste: tudo certo." "self-test passed"
else
  t "O autoteste não rodou aqui (o node é opcional; sem ele, a conferência do desenho do relatório fica de fora)." \
    "self-test could not run here (node is optional; the render check is skipped without it)"
fi

REVIEW="$HOME/.claude/skills/cronoaudit/scripts/review.py"
[[ -f "$REVIEW" ]] || REVIEW="$HOME/.agents/skills/cronoaudit/scripts/review.py"
SHOWN="${REVIEW/#$HOME/~}"

# Offered once: fictitious data, free mode, the report in the browser. Piped from curl,
# the answer is read from the terminal itself.
RUN_EX="${CRONOAUDIT_EXAMPLE:-ask}"
if [[ $HAVE_EX == 1 && "$RUN_EX" == ask ]]; then
  RUN_EX=0
  if { exec 3</dev/tty; } 2>/dev/null; then
    say ""
    if [[ $PT == 1 ]]; then
      printf 'Quer ver um exemplo agora? Ele analisa uma obra fictícia e abre o relatório no navegador. [S/n] '
    else
      printf 'Would you like to see an example now? It analyses a fictitious works and opens the report in your browser. [Y/n] '
    fi
    ans=""
    read -r ans <&3 || true
    exec 3<&-
    case "$ans" in [nN]*) RUN_EX=0 ;; *) RUN_EX=1 ;; esac
  fi
fi
if [[ $HAVE_EX == 1 && "$RUN_EX" == 1 ]]; then
  python3 "$REVIEW" --example || true
fi

VER="$(cat "$SKILL_DIR/VERSION" 2>/dev/null || echo '?')"
say ""
if [[ $PT == 1 ]]; then
  cat <<EOF
Pronto: cronoaudit $VER instalada.

Com um agente de IA (Claude Code, Copilot ou Codex): abra o agente na pasta do cronograma e
peça, por exemplo, "analise o Rev04.xml". Se ele já estava aberto, feche e abra de novo.

Sem agente, num terminal:
    python3 $SHOWN cronograma.xml
O cronograma vem do MS Project: Arquivo > Salvar como > Formato XML.
EOF
  if [[ $HAVE_EX == 1 ]]; then printf 'Para ver o exemplo de novo:\n    python3 %s --example\n' "$SHOWN"; fi
  printf '\nManual e ajuda: https://github.com/%s\n' "$REPO"
else
  cat <<EOF
cronoaudit $VER is installed.

With an AI agent (Claude Code, Copilot or Codex): open the agent in the schedule's folder and
ask, for example, "review Rev04.xml". If it was already open, close it and open it again.

With no agent, in a terminal:
    python3 $SHOWN schedule.xml
The schedule comes from MS Project: File > Save As > XML Format.
EOF
  if [[ $HAVE_EX == 1 ]]; then printf 'To see the example again:\n    python3 %s --example\n' "$SHOWN"; fi
  printf '\nManual and help: https://github.com/%s\n' "$REPO"
fi
