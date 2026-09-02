#!/bin/sh
# Render the deterministic Rewind fixture under Xvfb for visual review.
set -eu
cd "$(dirname "$0")/.."
OUT=${1:-out/rewind-ui-preview.png}
QML=${QML:-/usr/bin/qml6}
mkdir -p "$(dirname "$OUT")"

command -v xvfb-run >/dev/null 2>&1 || { echo "xvfb-run is required" >&2; exit 1; }
command -v import >/dev/null 2>&1 || { echo "ImageMagick import is required" >&2; exit 1; }
[ -x "$QML" ] || { echo "qml6 is required" >&2; exit 1; }

ABS_CATALOG=$(readlink -f test/rewind-catalog.json)
ABS_QML=$(readlink -f config/includes.chroot/usr/share/dagric/rewind/main.qml)
ABS_OUT=$(readlink -m "$OUT")
case "$ABS_OUT" in
    *.png) ABS_DETAIL=${ABS_OUT%.png}-detail.png ;;
    *) ABS_DETAIL=$ABS_OUT-detail.png ;;
esac
export ABS_CATALOG ABS_QML ABS_OUT ABS_DETAIL QML

xvfb-run -a -s '-screen 0 1280x800x24' sh -c '
    QT_QUICK_CONTROLS_STYLE=Basic QML_XHR_ALLOW_FILE_READ=1 \
      "$QML" "$ABS_QML" -- "--catalog=$ABS_CATALOG" "--reduced-motion=true" \
      >/tmp/dagric-rewind-qml.log 2>&1 &
    qml_pid=$!
    sleep 3
    import -window root "$ABS_OUT"
    if command -v xdotool >/dev/null 2>&1; then
        xdotool mousemove 680 660 click --repeat 10 5 2>/dev/null || true
        sleep 1
        import -window root "$ABS_DETAIL"
    fi
    kill "$qml_pid" 2>/dev/null || true
    wait "$qml_pid" 2>/dev/null || true
'
echo "rewind preview: $ABS_OUT"
[ ! -f "$ABS_DETAIL" ] || echo "rewind detail:  $ABS_DETAIL"
