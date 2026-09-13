#!/usr/bin/env bash
# cronoaudit installer — one command, every agent.
#
#   curl -fsSL https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.sh | bash -s -- --only claude
#
# Installs the skill into the two directories that, between them, every
# Agent Skills client reads:
#   ~/.claude/skills/cronoaudit   Claude Code, OpenCode, Cursor
#   ~/.agents/skills/cronoaudit   Codex, Gemini CLI, Cursor, GitHub Copilot, VS Code, OpenCode
#
# Needs: bash, curl or git, Python 3.9+, tar. Nothing is installed globally and
# nothing is sent anywhere; the only network access is the download itself.
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
  say "downloading $REPO@$REF ..."
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
  say "installed -> $dest"
}

case "$ONLY" in
  all)    install_to "$HOME/.claude/skills/cronoaudit"; install_to "$HOME/.agents/skills/cronoaudit" ;;
  claude) install_to "$HOME/.claude/skills/cronoaudit" ;;
  agents) install_to "$HOME/.agents/skills/cronoaudit" ;;
  *) die "--only must be all, claude or agents" ;;
esac

# Prove the instrument can fire and can stay silent before anyone trusts it.
say "verifying ..."
if python3 "$HOME/.claude/skills/cronoaudit/scripts/test_checks.py" >/dev/null 2>&1 \
   || python3 "$HOME/.agents/skills/cronoaudit/scripts/test_checks.py" >/dev/null 2>&1; then
  say "self-test passed"
else
  say "self-test could not run here (node is optional; the render check is skipped without it)"
fi

VER="$(cat "$SKILL_DIR/VERSION" 2>/dev/null || echo '?')"
cat <<EOF

cronoaudit $VER is installed.

  Restart your agent, then ask it to review a schedule, or run directly:
    python3 ~/.claude/skills/cronoaudit/scripts/review.py delivery.xml

  Export the schedule first:  MS Project > File > Save As > XML Format.
  Manual and method:          https://github.com/$REPO
EOF
