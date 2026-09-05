#!/bin/sh
# Build gate for Dagric Rewind.  Everything here is read-only: it can run before
# a 75-minute ISO build without Btrfs, Snapper, a desktop, or root.
set -eu
cd "$(dirname "$0")/.."

WRAPPER=config/includes.chroot/usr/bin/dagric-rewind
HELPER=config/includes.chroot/usr/lib/dagric/rewind-ctl
CORE=config/includes.chroot/usr/lib/dagric/rewind_core.py
QML=config/includes.chroot/usr/share/dagric/rewind/main.qml
DESKTOP=config/includes.chroot/usr/share/applications/dagric-rewind.desktop
POLICY=config/includes.chroot/usr/share/polkit-1/actions/org.dagric.rewind.policy

for file in "$WRAPPER" "$HELPER" "$CORE" "$QML" "$DESKTOP" "$POLICY"; do
    [ -s "$file" ] || { echo "rewind: missing $file" >&2; exit 1; }
done

sh -n "$WRAPPER"
sh -n packages/stage-packages.sh

if command -v python3 >/dev/null 2>&1; then
    python3 test/test-rewind-core.py
    python3 test/test-rewind-controller.py
    python3 - "$HELPER" "$CORE" "$POLICY" <<'PY'
import pathlib, sys, xml.etree.ElementTree as ET
for name in sys.argv[1:3]:
    source = pathlib.Path(name).read_text(encoding="utf-8")
    compile(source, name, "exec")
policy = ET.parse(sys.argv[3]).getroot()
action = policy.find("./action[@id='org.dagric.rewind.manage']")
assert action is not None, "polkit action id is missing"
path = action.find("./annotate[@key='org.freedesktop.policykit.exec.path']")
assert path is not None and path.text == "/usr/lib/dagric/rewind-ctl"
PY
else
    echo "rewind: python3 absent — skipping unit and XML tests"
fi

_staged_dirs=$(sed -n '/^[[:space:]]*for d in .* rewind/{s/^[[:space:]]*for d in \(.*\); do$/\1/p;q;}' packages/stage-packages.sh)
for _required_dir in firstrun appearance manual guide welcome styles looks hwcheck boot family rewind; do
    case " $_staged_dirs " in
        *" $_required_dir "*) ;;
        *) echo "rewind: package staging omits $_required_dir" >&2; exit 1 ;;
    esac
done
# Rewind's policy travels in the general policy loop.  The updater shares the
# same package and policy directory, so checking an old one-file copy command
# would reject the safer packaging rule that keeps every Dagric privileged
# helper's policy alongside its executable.
grep -Fq 'usr/share/polkit-1/actions/"*.policy' packages/stage-packages.sh
grep -Fq 'dagric-rewind' config/hooks/normal/0540-qml-identity.hook.chroot
grep -Fq 'dagric-firstrun dagric-appearance dagric-family dagric-rewind' packages/dagric-tools/DEBIAN/postinst
grep -Fq 'rewind)  dagric-rewind' config/includes.chroot/usr/bin/dagric-hub
grep -Fq 'StartupWMClass=dagric-rewind' "$DESKTOP"
grep -Fq 'mutate_and_refresh start-export' "$WRAPPER"
grep -Fq 'mutate_and_refresh finish-export' "$WRAPPER"
grep -Fq 'btrfs-assistant-launcher' "$WRAPPER"
grep -Fq 'pkexec btrfs-assistant' "$WRAPPER"
grep -Fq 'authorization_cancelled && exit 0' "$WRAPPER"
grep -Fq 'authorization_cancelled || show_error' "$WRAPPER"
grep -Fq '_refresh_status=$?' "$WRAPPER"
grep -Fq 'return "$_refresh_status"' "$WRAPPER"

# btrfs-assistant refuses to run unprivileged.  The Debian desktop launcher is
# the primary handoff because it owns the correct polkit and GUI setup; a raw
# background launch is the exact regression the installed-system test caught.
if grep -Fq '                btrfs-assistant >/dev/null 2>&1 &' "$WRAPPER"; then
    echo "rewind: recovery bypasses btrfs-assistant-launcher" >&2
    exit 1
fi

# A restore command in this helper would bypass the design's most important
# safety boundary. Recovery is intentionally delegated to Btrfs Assistant and
# the bootable snapshot path.
if grep -Eq 'undochange|snapper[^\n]*(rollback|delete)' "$HELPER"; then
    echo "rewind: unsafe live restore/delete operation found in privileged helper" >&2
    exit 1
fi

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$DESKTOP"
fi
QMLLINT=$(command -v qmllint 2>/dev/null || true)
[ -n "$QMLLINT" ] || [ ! -x /usr/lib/qt6/bin/qmllint ] || QMLLINT=/usr/lib/qt6/bin/qmllint
if [ -n "$QMLLINT" ]; then
    "$QMLLINT" "$QML"
fi

echo "rewind: core, privilege boundary, packaging and launcher checks passed"
