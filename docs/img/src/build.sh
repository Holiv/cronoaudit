#!/usr/bin/env bash
# Rebuild every image the README and the LEIA-ME show, in English and in Portuguese.
#
#   bash docs/img/src/build.sh            # everything: banner, diagram, framed crops, demo GIF
#   bash docs/img/src/build.sh stills     # banner, social preview, diagram and framed crops only
#   bash docs/img/src/build.sh demo       # the demo GIF only
#
# What it does:
#   1. stills.js draws the banner, the social preview and the "how it works" diagram, and
#      puts the brand frame around the report crops kept in crops/<lang>/. The crops are
#      real output of the engine for the FICTITIOUS example; the frame changes no pixel
#      inside them.
#   2. For the demo, the skill and the fictitious example are copied into a throwaway HOME
#      (the layout the installer creates) and the real review.py runs there on rev03 and
#      rev04, free mode. The throwaway HOME is written as "~" in the stored terminal
#      output; nothing else in it is edited. demo.js then opens stage.html in headless
#      Chrome, with the engine's own HTML report live in an iframe, and writes the frames;
#      ffmpeg turns them into a GIF with a two-pass palette.
#
# Output: ../en and ../pt. Work files go to ./build, which is not versioned.
# Needs: python3, node with puppeteer-core (NODE_PATH below), Google Chrome, ffmpeg, and
# network access to Google Fonts (Fraunces, Source Sans 3, Source Code Pro).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
export NODE_PATH="${NODE_PATH:-$ROOT/docs/manual/node_modules}"
FFMPEG="${FFMPEG:-ffmpeg}"
WHAT="${1:-all}"
GIF_W=720; GIF_FPS=10; GIF_COLORS=128
cd "$HERE"

if [[ "$WHAT" == "all" || "$WHAT" == "stills" ]]; then
  node stills.js
  # Each crop must sit inside its frame pixel for pixel. crop-rects.txt says where it was
  # drawn; a band of rows that no red outline touches (200 to 360) is hashed in the framed
  # image and in the crop kept in crops/, and the two must agree.
  while read -r VL NAME X Y W H; do
    A="$("$FFMPEG" -v error -i "crops/$VL/$NAME.png" -vf "crop=$W:160:0:200,format=rgb24" -f md5 -)"
    B="$("$FFMPEG" -v error -i "../$VL/$NAME.png" -vf "crop=$W:160:$X:$((Y + 200)),format=rgb24" -f md5 -)"
    [[ "$A" == "$B" ]] || { echo "crop altered inside its frame: $VL/$NAME" >&2; exit 1; }
  done < build/crop-rects.txt
  echo "crops unchanged inside their frames"
  # Chrome writes large PNGs; write each one again without loss and keep the smaller file.
  for F in ../en/*.png ../pt/*.png; do
    "$FFMPEG" -y -v error -i "$F" -pred none -compression_level 9 build/repack.png
    if [[ "$(wc -c < build/repack.png)" -lt "$(wc -c < "$F")" ]]; then mv build/repack.png "$F"; fi
  done
fi

if [[ "$WHAT" == "all" || "$WHAT" == "demo" ]]; then
  for VL in en pt; do
    B="$HERE/build/$VL"; mkdir -p "$B"
    case "$VL" in en) LOC=en_US.UTF-8 ;; pt) LOC=pt_BR.UTF-8 ;; esac
    # ---- the real engine run, in a throwaway HOME
    TMP="$(cd "$(mktemp -d)" && pwd -P)"
    mkdir -p "$TMP/.claude/skills" "$TMP/cronoaudit-exemplo"
    cp -R "$ROOT/skills/cronoaudit" "$TMP/.claude/skills/cronoaudit"
    cp "$ROOT/examples/rodovia-ficticia-rev03.xml" "$ROOT/examples/rodovia-ficticia-rev04.xml" "$TMP/cronoaudit-exemplo/"
    # The command shown in the demo is this one, typed from ~/cronoaudit-exemplo.
    CMD="python3 ~/.claude/skills/cronoaudit/scripts/review.py rodovia-ficticia-rev03.xml rodovia-ficticia-rev04.xml --free --lang $VL"
    ( cd "$TMP/cronoaudit-exemplo" && HOME="$TMP" LANG="$LOC" LC_ALL="$LOC" CRONOAUDIT_OPEN=0 \
      python3 "$TMP/.claude/skills/cronoaudit/scripts/review.py" \
      rodovia-ficticia-rev03.xml rodovia-ficticia-rev04.xml --free --lang "$VL" ) > "$B/term.raw" 2>&1
    python3 - "$TMP" "$B/term.raw" "$B/term.txt" <<'PY'
import sys
home, src, dst = sys.argv[1:]
open(dst, "w", encoding="utf-8").write(open(src, encoding="utf-8").read().replace(home, "~"))
PY
    rm "$B/term.raw"
    printf '%s\n' "$CMD" > "$B/cmd.txt"
    rm -rf "$B/out"; mkdir -p "$B/out"
    cp "$TMP/cronoaudit-exemplo/"*.html "$TMP/cronoaudit-exemplo/"*.json "$B/out/"
    rm -rf "$TMP"
    # ---- frames, then the GIF (palette from the frames themselves, then applied)
    node demo.js --lang "$VL" --fps "$GIF_FPS" --frames "$B/frames"
    VF="scale=$GIF_W:-1:flags=lanczos"
    "$FFMPEG" -y -v error -framerate "$GIF_FPS" -i "$B/frames/f%04d.png" \
      -vf "$VF,palettegen=max_colors=$GIF_COLORS:stats_mode=diff" "$B/palette.png"
    "$FFMPEG" -y -v error -framerate "$GIF_FPS" -i "$B/frames/f%04d.png" -i "$B/palette.png" \
      -lavfi "$VF[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle" -loop 0 "$HERE/../$VL/demo.gif"
    ls -l "$HERE/../$VL/demo.gif" | awk '{print $5, $NF}'
  done
fi
