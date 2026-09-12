#!/usr/bin/env bash
# One-way sync: this repository is canonical, ~/.claude/skills is derived.
# Edit under skill/, then run this. Never edit the installed copy — a fix made
# downstream is erased by the next sync, and nobody sees it happen.
set -euo pipefail
DEST="$HOME/.claude/skills/schedule-integrity"
mkdir -p "$DEST"
rsync -a --delete "$(dirname "$0")/skill/" "$DEST/"
echo "installed -> $DEST"
