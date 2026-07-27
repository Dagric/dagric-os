#!/bin/sh
# Draw the Dagric login screen without logging out.
#
#   sh branding/sddm/render-login.sh [VARIANT] [WIDTH] [HEIGHT]
#
# VARIANT is one of: full (default), users, caps, failed, nousers, layouts.
# Output lands in out/sddm/, and preview.png for the theme is written by
# "sh branding/sddm/render-login.sh preview".
#
# WHY THIS EXISTS. The login screen is the screen an owner sees more often than
# any other, and the only honest way to review a change to it is to look at it.
# The obvious route — install the ISO, reboot, log out — is a twenty-minute
# round trip for a two-pixel change, so nobody does it, and that is how a login
# screen ends up shipping with a clock that displays seconds.
#
# There are two ways to see this theme and they check different things:
#
#   1. THE REAL GREETER.  sddm-greeter-qt6 --test-mode --theme <dir>
#      This is the truth about whether the theme LOADS: real Theme-API, real
#      QtVersion resolution, real context objects. What it cannot show you is
#      the theme FULL: test mode hands the theme no users, no sessions and no
#      keyboard layouts, and reports that the machine can neither reboot nor
#      power off — so the user switcher, both pickers and both power buttons
#      are all correctly invisible and you learn nothing about them.
#
#   2. THIS SCRIPT.  Loads the same Main.qml under a plain qml6 with the five
#      SDDM context objects (sddm, userModel, sessionModel, keyboard, config)
#      replaced by stubs, so every one of those controls is on screen and can
#      be driven into a particular state. What it does NOT prove is that SDDM
#      will accept the theme — for that, run the real greeter as well.
#
# Neither is a substitute for one real login on real hardware before a release.
#
# Needs: qml6, Xvfb, ImageMagick 7. All three are in the build container.
set -e

REPO=${REPO:-$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)}
THEME=$REPO/config/includes.chroot/usr/share/sddm/themes/dagric
VAR=${1:-full}
W=${2:-1920}
H=${3:-1080}
DISP=${DISP:-:96}

case $VAR in
    preview) VAR=full; W=1920; H=1080; MAKE_PREVIEW=yes ;;
    *)       MAKE_PREVIEW=no ;;
esac

OUTDIR=$REPO/out/sddm
WK=$(mktemp -d "${TMPDIR:-/tmp}/loginrenderXXXXXX")
QMLPID=

# Written out longhand rather than as `kill ${QMLPID:-0}`, because that
# expands to `kill 0` when nothing has been started yet — and `kill 0` signals
# the whole process group, which means the script kills the shell that ran it.
# It does this on the SUCCESS path too, since the trap fires on EXIT. Found the
# hard way: the first run of this script terminated its own caller.
cleanup () {
    if [ -n "$QMLPID" ]; then
        kill "$QMLPID" 2>/dev/null || true
    fi
    pkill -f "Xvfb $DISP" 2>/dev/null || true
    rm -rf "$WK"
}
trap cleanup EXIT INT TERM
mkdir -p "$OUTDIR"

# ---------------------------------------------------------------- the stubs --
# These stand in for the objects the greeter injects into the QML context and
# that exist nowhere else. The property and role names are SDDM's, not ours:
# `name`, `realName`, `icon` and `needsPassword` on the user model, `name` on
# the session model, `shortName`/`longName` on a keyboard layout. Renaming any
# of them here would make the render pass while the real greeter fails.
#
# ListModel is used rather than a plain array because SDDM's models are
# QAbstractItemModels: a delegate that says `required property string realName`
# has to resolve it as a ROLE, and only a real model does that. Getting this
# wrong would mean the stub exercised a code path the greeter never takes.
cat > "$WK/stubs.qml" <<'STUBS'
    // ---- injected by branding/sddm/render-login.sh, never shipped ----
    property var config: stubConfig
    property var sddm: stubSddm
    property var keyboard: stubKeyboard
    property var userModel: stubUsers
    property var sessionModel: stubSessions

    QtObject {
        id: stubConfig
        property string type: "image"
        property string background: "@BG@"
        property string color: "#0a111c"
        property string logo: "@LOGO@"
        property string showlogo: "shown"
        property string showClock: "true"
    }

    QtObject {
        id: stubSddm
        signal loginSucceeded()
        signal loginFailed()
        signal informationMessage(string message)
        property bool canPowerOff: true
        property bool canReboot: true
        property bool canSuspend: true
        property string hostName: "dagric"
        function login(u, p, s) { console.log("stub login:", u, "session", s); stubSddm.loginFailed(); }
        function powerOff() {}
        function reboot() {}
    }

    QtObject { id: stubLayoutA; property string shortName: "us"; property string longName: "English (US)" }
    QtObject { id: stubLayoutB; property string shortName: "gb"; property string longName: "English (UK)" }

    QtObject {
        id: stubKeyboard
        property bool capsLock: false
        property bool numLock: false
        property bool enabled: true
        property int currentLayout: 0
        property var layouts: [stubLayoutA, stubLayoutB]
    }

    ListModel {
        id: stubUsers
        property int lastIndex: 0
        property string lastUser: "dave"
        ListElement {
            name: "dave"; realName: "Dave Richardson"
            icon: "@FACE@"; needsPassword: true
        }
        ListElement {
            name: "guest"; realName: ""
            icon: ""; needsPassword: false
        }
    }

    ListModel {
        id: stubSessions
        property int lastIndex: 0
        ListElement { name: "Plasma (Wayland)" }
        ListElement { name: "Plasma (X11)" }
    }
STUBS

sed -i \
    -e "s|@BG@|$REPO/config/includes.chroot/usr/share/dagric/sddm/background.png|" \
    -e "s|@LOGO@|$REPO/config/includes.chroot/usr/share/dagric/logo/dagric-logo.png|" \
    -e "s|@FACE@|$REPO/config/includes.chroot/usr/share/sddm/faces/default.face.icon|" \
    "$WK/stubs.qml"

# Drive the theme into the state being reviewed. Each of these is a state a real
# owner reaches; none of them is reachable from a screenshot of the idle screen.
case $VAR in
    users)   printf '    Timer { interval: 900; running: true; onTriggered: { userSheet.visible = true; userList.forceActiveFocus(); } }\n' >> "$WK/stubs.qml" ;;
    layouts) printf '    Timer { interval: 900; running: true; onTriggered: { layoutSheet.visible = true; layoutList.forceActiveFocus(); } }\n' >> "$WK/stubs.qml" ;;
    caps)    sed -i 's/property bool capsLock: false/property bool capsLock: true/' "$WK/stubs.qml"
             printf '    Timer { interval: 900; running: true; onTriggered: pw.text = "hunter2" }\n' >> "$WK/stubs.qml" ;;
    failed)  printf '    Timer { interval: 900; running: true; onTriggered: { pw.text = "wrongpass"; root.signIn(); } }\n' >> "$WK/stubs.qml" ;;
    nousers) sed -i '/ListElement {$/,/}$/d' "$WK/stubs.qml" ;;
    full)    : ;;
    *)       echo "unknown variant: $VAR" >&2; exit 2 ;;
esac

# ------------------------------------------------------------ the injection --
# Straight after "id: root", so the stubs are root properties and shadow the
# context properties of the same name. The shipped file is not touched.
awk -v stubs="$WK/stubs.qml" 'BEGIN { done = 0 }
    { print }
    /^    id: root$/ && !done { while ((getline l < stubs) > 0) print l; done = 1 }' \
    "$THEME/Main.qml" > "$WK/Main.qml"

# SDDM resizes the root item to its view; qml6 does the opposite and sizes its
# window to the root item. Rewrite the two placeholder numbers so the render
# comes out at the resolution actually being tested.
sed -i "s/^    width: 1600\$/    width: $W/; s/^    height: 900\$/    height: $H/" "$WK/Main.qml"

# ---------------------------------------------------------------- the render --
pkill -f "Xvfb $DISP" 2>/dev/null || true
sleep 1
Xvfb "$DISP" -screen 0 "${W}x${H}x24" >/dev/null 2>&1 &
sleep 2

DISPLAY=$DISP qml6 "$WK/Main.qml" > "$WK/qml.log" 2>&1 &
QMLPID=$!
sleep 5

SHOT=$OUTDIR/login-$VAR-${W}x${H}.png
DISPLAY=$DISP import -window root "$SHOT"
kill "$QMLPID" 2>/dev/null || true
QMLPID=
sleep 1
pkill -f "Xvfb $DISP" 2>/dev/null || true

# Anything at all in here other than the wayland-plugin grumble is a real
# problem: a QML warning that nobody reads is how a binding quietly stops
# working on one screen size.
echo "--- qml6 output ---"
grep -v 'Could not find the Qt platform plugin "wayland"' "$WK/qml.log" || true
echo "--- wrote $SHOT ---"

if [ "$MAKE_PREVIEW" = yes ]; then
    # Same reproducibility rules as make-login-art.sh: strip the timestamp
    # chunks so a rebuild that changed nothing produces a byte-identical file
    # and does not churn the signed release checksums.
    magick "$SHOT" -resize 1024x576 -strip \
        +set date:create +set date:modify +set date:timestamp \
        -define png:exclude-chunk=date,time -quality 92 "$THEME/preview.png"
    echo "--- wrote $THEME/preview.png ---"
fi
