#!/usr/bin/env bash
# One-way sync: this repository is canonical, every destination is derived.
# Edit under skill/, then run this. Never edit an installed copy -- a fix made
# downstream is erased by the next sync, and nobody sees it happen.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"

sync_to() {
  mkdir -p "$1"
  rsync -a --delete --exclude '__pycache__' "$here/skills/cronoaudit/" "$1/"
  echo "installed -> $1"
}

# Where Claude Code loads it from.
sync_to "$HOME/.claude/skills/cronoaudit"

# Optional extra destinations, one absolute path per line, in .local-targets.
# That file is gitignored: local paths are not the repository's business, and a
# public repository must not carry anybody's folder structure.
if [[ -f "$here/.local-targets" ]]; then
  while IFS= read -r dest; do
    [[ -z "$dest" || "$dest" == \#* ]] && continue
    sync_to "${dest/#\~/$HOME}"
  done < "$here/.local-targets"
fi
