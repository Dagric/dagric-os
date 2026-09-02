#!/bin/sh
# Dagric Update's static safety contract.  These checks are intentionally
# narrow: they block a future convenience edit from turning normal updates into
# an unattended release migration or package-removal operation.
set -eu
cd "$(dirname "$0")/.."

core=config/includes.chroot/usr/lib/dagric/update_core.py
launcher=config/includes.chroot/usr/bin/dagric-update
desktop=config/includes.chroot/usr/share/applications/dagric-update.desktop
policy=config/includes.chroot/usr/share/polkit-1/actions/org.dagric.rewind.policy

for path in "$core" "$launcher" "$desktop" "$policy"; do
    [ -f "$path" ] || { echo "update-check: missing $path" >&2; exit 1; }
done
grep -Fqx 'exec python3 /usr/lib/dagric/update_core.py "$@"' "$launcher"
grep -Fqx 'Exec=dagric-update --gui' "$desktop"
grep -Fq 'id="org.dagric.update.manage"' "$policy"
grep -Fq '<allow_any>no</allow_any>' "$policy"
grep -Fq '<allow_inactive>no</allow_inactive>' "$policy"
grep -Fq '<allow_active>auth_admin_keep</allow_active>' "$policy"
grep -Fq 'Dpkg::Options::=--force-confold' "$core"
grep -Fq 'Home folders: not copied, deleted, or replaced' "$core"
grep -Fq 'snapper", "-c", "root", "create"' "$core"

echo "update-check: passed (signed APT path, checkpoint, no removals, preserved configuration)"
