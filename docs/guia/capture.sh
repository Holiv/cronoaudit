#!/usr/bin/env bash
# Capture everything the illustrated guide shows as real output.
#
#   NODE_PATH=<path to docs/manual/node_modules> bash docs/guia/capture.sh
#
# It installs cronoaudit from this checkout into a throwaway HOME, runs the engine on
# the fictitious example only, and stores what the terminal printed (capturas/), the
# engine's JSON (dados/) and screenshots of the engine's own HTML report (img/).
# The throwaway HOME is written as "~" in every stored file. Nothing is edited
# otherwise: build.py may cut lines out of a capture, and marks each cut.
#
# The secret run: the engine refuses secret mode when an agent started the process.
# To capture a secret run of the FICTITIOUS EXAMPLE, the agent variables are removed
# from the environment, as the test suite does. Never do this with a real schedule.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
TMP="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf "$TMP"' EXIT
NOAGENT=(env -u CLAUDECODE -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_SESSION_ID)

mkdir -p "$HERE/capturas" "$HERE/img"

for L in pt en; do
  if [[ $L == pt ]]; then LOCALE=pt_BR.UTF-8; YES=s; else LOCALE=en_US.UTF-8; YES=y; fi
  H="$TMP/$L"; mkdir -p "$H"
  EX="$H/cronoaudit-exemplo"
  PY="$H/.claude/skills/cronoaudit/scripts"
  CAP="$HERE/capturas"; DATA="$HERE/dados/$L"; mkdir -p "$DATA"
  export HOME="$H" LANG="$LOCALE" LC_ALL="$LOCALE" CRONOAUDIT_OPEN=0

  # 1. The installer, from this checkout, running the example at the end.
  (cd "$H" && CRONOAUDIT_EXAMPLE=1 bash "$ROOT/install.sh" --from "$ROOT") > "$CAP/install-$L.txt" 2>&1

  # 2. The two revisions compared, free mode.
  (cd "$EX" && python3 "$PY/review.py" rodovia-ficticia-rev03.xml rodovia-ficticia-rev04.xml --free --lang $L) > "$CAP/cycle-$L.txt" 2>&1
  CY="rodovia-ficticia-rev03--to--rodovia-ficticia-rev04-cycle"; RV="rodovia-ficticia-rev04-review"
  cp "$EX/$CY.json" "$DATA/cycle.json"; cp "$EX/$CY-readings.json" "$DATA/cycle-readings.json"
  for part in "" -readings -forecast -forensics -quality -scurve -productivity; do
    cp "$EX/$RV$part.json" "$DATA/review$part.json"
  done
  node "$HERE/shots.js" "$EX/$CY.html" "$HERE/img/cycle-top-$L.png" page 1040 760 1.5
  node "$HERE/shots.js" "$EX/$CY.html" "$HERE/img/cycle-prazo-$L.png" "#c1" 1040 800 1.5
  node "$HERE/shots.js" "$EX/$CY.html" "$HERE/img/cycle-cobrar-$L.png" "#cobrar" 640 1100 1.6

  # 3. The mode question, asked at a (pseudo) terminal and answered yes.
  (cd "$EX" && python3 "$HERE/ptyrun.py" $YES python3 "$PY/review.py" rodovia-ficticia-rev04.xml --lang $L) > "$CAP/question-$L.txt" 2>&1

  # 4. Secret mode asked for from inside an agent session: the engine stops.
  #    Outside an agent, the variable is set here to reproduce that condition.
  (cd "$EX" && CLAUDECODE="${CLAUDECODE:-1}" python3 "$PY/review.py" rodovia-ficticia-rev03.xml rodovia-ficticia-rev04.xml --secret --lang $L) > "$CAP/refuse-$L.txt" 2>&1 || true

  # 5. A secret run of the fictitious example, agent variables removed (see the top).
  (cd "$EX" && "${NOAGENT[@]}" python3 "$PY/review.py" rodovia-ficticia-rev03.xml rodovia-ficticia-rev04.xml --secret --lang $L --workdir "$H/cronoaudit-work") > "$CAP/secret-$L.txt" 2>&1
  WD="$(ls -d "$H"/cronoaudit-work/*/)"; WD="${WD%/}"
  cp "$WD/previous--to--current-cycle-readings.json" "$DATA/coded-cycle-readings.json"
  cp "$WD/current-review-readings.json" "$DATA/coded-review-readings.json"
  (cd "$WD" && ls -A1) > "$CAP/workdir-$L.txt"
  node "$HERE/shots.js" "$WD/previous--to--current-cycle.html" "$HERE/img/coded-cobrar-$L.png" "#cobrar" 640 1100 1.6

  # 6. The way back: four coded sentences of the engine, decoded on this machine,
  #    then the final report.
  python3 - "$DATA/coded-cycle-readings.json" > "$CAP/coded-answer-$L.txt" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
r = d["readings"]
for line in (r["c1"][3], r["c5"][2], r["c1"][2], d["demands"][3]["text"]):
    print(line)
PY
  (cd "$WD" && "${NOAGENT[@]}" python3 "$PY/secret_decode.py" text "$WD" < "$CAP/coded-answer-$L.txt") > "$CAP/decoded-answer-$L.txt" 2>&1
  (cd "$WD" && "${NOAGENT[@]}" python3 "$PY/secret_decode.py" finish --no-open) > "$CAP/finish-$L.txt" 2>&1

  # The throwaway HOME becomes "~" everywhere.
  python3 - "$H" "$CAP" "$DATA" $L <<'PY'
import glob, os, sys
home, cap, data, lang = sys.argv[1:5]
files = glob.glob(os.path.join(cap, f"*-{lang}.txt")) + glob.glob(os.path.join(data, "*.json"))
for path in files:
    text = open(path, encoding="utf-8").read()
    for form in (home, home.replace("/private", "", 1)):
        text = text.replace(form, "~")
    open(path, "w", encoding="utf-8").write(text)
PY
done
echo "captured: $HERE/capturas, $HERE/dados, $HERE/img"
