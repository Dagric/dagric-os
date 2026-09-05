#!/bin/sh
# Run as root on an installed Dagric system. The VM harness puts this script on
# a small writable FAT evidence disk; mount it at /mnt/evidence and the report
# is preserved on that same disk. Usage: installed-audit.sh free|pro [uefi|bios]
set -eu
umask 077
# Keep dpkg's machine-checked verification records deterministic in all five
# desktop locales. This affects only this audit and its child commands.
LC_ALL=C
export LC_ALL

EXPECTED_EDITION=${1:-}
EXPECTED_FIRMWARE=${2:-}
case "$EXPECTED_EDITION" in free|pro) ;; *) echo "usage: $0 free|pro [uefi|bios]" >&2; exit 2 ;; esac
case "$EXPECTED_FIRMWARE" in ''|uefi|bios) ;; *) echo "usage: $0 free|pro [uefi|bios]" >&2; exit 2 ;; esac

# The VM harness mounts its writable host exchange here. Redirect inside the
# script so VNC automation never has to type shell metacharacters such as > or
# 2>&1 through a keyboard-layout translation layer.
if mountpoint -q /mnt/evidence 2>/dev/null; then
    exec > /mnt/evidence/installed-audit.txt 2>&1
fi

PASS=0
FAIL=0
SKIP=0

pass() { PASS=$((PASS + 1)); printf '[PASS] %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf '[FAIL] %s\n' "$1"; }
skip() { SKIP=$((SKIP + 1)); printf '[SKIP] %s\n' "$1"; }
check() {
    _label=$1
    shift
    if "$@" >/dev/null 2>&1; then pass "$_label"; else fail "$_label"; fi
}
# BEGIN INSTALLED AUDIT HELPERS (also exercised with offline command mocks).
# dpkg-query expands an unqualified Multi-Arch package (for example MangoHud
# on Pro) once per installed architecture. Without a record separator the two
# values become "installedinstalled", making a healthy amd64+i386 pair fail.
has_pkg() {
    _states=$(dpkg-query -W -f='${db:Status-Status}\n' "$1" 2>/dev/null) || return 1
    printf '%s\n' "$_states" | grep -qx installed
}
lacks_pkg() {
    # Query the complete database successfully before claiming absence. A
    # missing package and a broken/unreadable database both make a targeted
    # query fail; negating has_pkg would mistake that error for an exclusion.
    _packages=$(dpkg-query -W -f='${binary:Package}\t${db:Status-Status}\n' 2>/dev/null) || return 1
    [ -n "$_packages" ] || return 1
    printf '%s\n' "$_packages" | awk -v package="$1" '
        NF != 2 || $1 !~ /^[a-z0-9][a-z0-9+.-]*(:[a-z0-9][a-z0-9-]*)?$/ ||
            $2 !~ /^(not-installed|config-files|half-installed|unpacked|half-configured|triggers-awaited|triggers-pending|installed)$/ { invalid = 1 }
        $2 == "installed" && ($1 == package || index($1, package ":") == 1) { found = 1 }
        END { exit found || invalid ? 1 : 0 }'
}
installed_environment() {
    _uid=$(id -u 2>/dev/null) || return 1
    [ "$_uid" = 0 ] || { echo 'Run the installed audit as root.' >&2; return 1; }
    _cmdline=$(cat /proc/cmdline 2>/dev/null) || return 1
    case " $_cmdline " in
        *' boot=live '*|*' boot=casper '*)
            echo 'Refusing installed-system acceptance in a live boot.' >&2; return 1 ;;
    esac
    _root_type=$(findmnt -n -o FSTYPE / 2>/dev/null) || return 1
    case "$_root_type" in
        ''|overlay|aufs|squashfs|tmpfs|ramfs)
            echo "Root type '$_root_type' is not an installed disk filesystem." >&2; return 1 ;;
    esac
    if mountpoint -q /run/live/medium 2>/dev/null || mountpoint -q /lib/live/mount/medium 2>/dev/null; then
        echo 'A live boot medium remains mounted; installed acceptance is refused.' >&2
        return 1
    fi
}
unit_property() { printf '%s\n' "$1" | sed -n "s/^$2=//p"; }
is_disabled() {
    _properties=$(systemctl show --property=LoadState,UnitFileState "$1" 2>/dev/null) || return 1
    [ "$(printf '%s\n' "$_properties" | grep -c '^UnitFileState=')" -eq 1 ] || return 1
    _load=$(unit_property "$_properties" LoadState)
    _state=$(unit_property "$_properties" UnitFileState)
    case "$_load:$_state" in
        loaded:disabled|loaded:static|loaded:indirect|masked:masked|loaded:masked|not-found:) return 0 ;;
        *) return 1 ;;
    esac
}
is_inactive() {
    _properties=$(systemctl show --property=LoadState,ActiveState,SubState "$1" 2>/dev/null) || return 1
    _load=$(unit_property "$_properties" LoadState)
    _active=$(unit_property "$_properties" ActiveState)
    _sub=$(unit_property "$_properties" SubState)
    case "$_load:$_active:$_sub" in
        loaded:inactive:dead|masked:inactive:dead|not-found:inactive:dead) return 0 ;;
        *) return 1 ;;
    esac
}
triggers_inactive() {
    _properties=$(systemctl show --property=LoadState,TriggeredBy "$1" 2>/dev/null) || return 1
    _load=$(unit_property "$_properties" LoadState)
    case "$_load" in loaded|masked|not-found) ;; *) return 1 ;; esac
    # Missing property output is unknown, not an empty list of activators.
    [ "$(printf '%s\n' "$_properties" | grep -c '^TriggeredBy=')" -eq 1 ] || return 1
    _triggers=$(unit_property "$_properties" TriggeredBy)
    for _trigger in $_triggers; do
        is_disabled "$_trigger" && is_inactive "$_trigger" || return 1
    done
}
no_failed_services() {
    _failed=$(systemctl --failed --no-legend --plain --no-pager 2>&1) || return 1
    [ -z "$_failed" ]
}
pro_badge_is_only_change() {
    # Round-trip the one permitted edition substitution against dpkg's
    # original checksum. Merely finding the badge text could hide arbitrary
    # additional edits to the same login-theme file.
    python3 - "$1" "$2" <<'DAGRIC_INSTALLED_BADGE_PY'
import hashlib
from pathlib import Path
import re
import sys

try:
    theme = Path(sys.argv[1]).read_bytes()
    checksums = Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
    badges = [line for line in theme.splitlines(keepends=True) if line.startswith(b"editionBadge=")]
    if badges != [b"editionBadge=PRO EDITION\n"]:
        raise ValueError("unexpected edition badge")
    expected = [match.group(1) for line in checksums
                if (match := re.fullmatch(r"([0-9a-f]{32})[ \t]+usr/share/sddm/themes/dagric/theme\.conf", line))]
    original = theme.replace(b"editionBadge=PRO EDITION\n", b"editionBadge=\n", 1)
    if len(expected) != 1 or hashlib.md5(original, usedforsecurity=False).hexdigest() != expected[0]:
        raise ValueError("theme differs beyond the permitted edition badge")
except (OSError, UnicodeError, ValueError) as exc:
    print("installed-audit: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
DAGRIC_INSTALLED_BADGE_PY
}
audit_package_integrity() {
    for _package in dagric-branding dagric-desktop-defaults dagric-security-policy dagric-tools; do
        if has_pkg "$_package"; then
            pass "required package $_package is installed"
        else
            fail "required package $_package is missing or its state could not be read"
            return 1
        fi
    done
    _verify_status=0
    _verify=$(dpkg -V dagric-branding dagric-desktop-defaults dagric-security-policy dagric-tools 2>&1) || _verify_status=$?
    if [ "$_verify_status" -ne 0 ]; then
        fail "Dagric package verification command failed (status $_verify_status)"
        [ -z "$_verify" ] || printf '%s\n' "$_verify" | sed 's/^/       /'
        return 1
    elif [ -z "$_verify" ]; then
        pass "Dagric packages verify with dpkg"
    elif [ "$EXPECTED_EDITION" = free ] &&
         [ "$(printf '%s\n' "$_verify" | LC_ALL=C sort)" = "$(printf '%s\n' \
             'missing     /usr/share/applications/dagric-usb-protect.desktop' \
             'missing     /usr/share/applications/dagric-vm.desktop' | LC_ALL=C sort)" ]; then
        pass "Dagric package changes match the two intentional Free launcher removals"
    elif [ "$EXPECTED_EDITION" = pro ] &&
         [ "$_verify" = '??5??????   /usr/share/sddm/themes/dagric/theme.conf' ] &&
         pro_badge_is_only_change /usr/share/sddm/themes/dagric/theme.conf /var/lib/dpkg/info/dagric-branding.md5sums; then
        pass "Dagric package change matches only the intentional Pro login badge"
    else
        fail "Dagric package verification reported unexpected changes or diagnostics"
        printf '%s\n' "$_verify" | sed 's/^/       /'
        return 1
    fi
}
# END INSTALLED AUDIT HELPERS.

if installed_environment; then
    pass "root is inspecting an installed disk environment, not a live boot"
else
    fail "installed-system preflight failed; no installed acceptance checks were run"
    printf '\ninstalled-audit: %s pass, %s fail, %s skip\n' "$PASS" "$FAIL" "$SKIP"
    exit 1
fi

actual_edition=$(cat /etc/dagric-edition 2>/dev/null || true)
[ "$actual_edition" = "$EXPECTED_EDITION" ] && pass "edition marker is $EXPECTED_EDITION" || fail "edition marker is '$actual_edition', expected $EXPECTED_EDITION"

rootfs=$(findmnt -n -o FSTYPE / 2>/dev/null || true)
[ "$rootfs" = btrfs ] && pass "root filesystem is Btrfs" || fail "root filesystem is '$rootfs', expected Btrfs"
check "Snapper root configuration exists" test -s /etc/snapper/configs/root
check "Snapper can enumerate snapshots" snapper -c root list
check "snapshot setup completion marker exists" test -f /var/lib/dagric/snapshot-setup-done
snapshot_result=$(systemctl show -p Result --value dagric-snapshot-setup.service 2>/dev/null || true)
[ "$snapshot_result" = success ] && pass "Dagric snapshot setup service succeeded" || fail "Dagric snapshot setup result is '$snapshot_result'"
check "GRUB snapshot refresh service is enabled" systemctl is-enabled --quiet grub-btrfsd.service

if [ -d /sys/firmware/efi ]; then
    firmware=uefi
    check "EFI system partition is mounted" mountpoint -q /boot/efi
    check "signed shim is installed" has_pkg shim-signed
    check "signed GRUB is installed" has_pkg grub-efi-amd64-signed
else
    firmware=bios
    check "BIOS GRUB modules are installed" has_pkg grub-pc-bin
fi
[ -z "$EXPECTED_FIRMWARE" ] || [ "$firmware" = "$EXPECTED_FIRMWARE" ] && pass "firmware mode is $firmware" || fail "firmware mode is $firmware, expected $EXPECTED_FIRMWARE"

check "firewalld is active" systemctl is-active --quiet firewalld.service
check "AppArmor is active" systemctl is-active --quiet apparmor.service
check "unattended upgrades are configured" test -s /etc/apt/apt.conf.d/52dagric-unattended
check "Dagric does not inject Firefox distribution policy" test ! -e /usr/lib/firefox-esr/distribution/policies.json
check "Chromium privacy policy parses" python3 -m json.tool /etc/chromium/policies/managed/10-dagric-privacy.json
check "Rewind privileged helper exists" test -x /usr/lib/dagric/rewind-ctl
check "Rewind policy exists" test -s /usr/share/polkit-1/actions/org.dagric.rewind.policy
check "Dagric Update command exists" test -x /usr/bin/dagric-update
check "Dagric Update safety core exists" test -s /usr/lib/dagric/update_core.py
check "Dagric Update desktop entry exists" test -s /usr/share/applications/dagric-update.desktop
check "Dagric Update privileged policy exists" sh -c 'grep -Fq "org.dagric.update.manage" /usr/share/polkit-1/actions/org.dagric.rewind.policy'
check "Family privileged helper exists" test -x /usr/lib/dagric/family-apply
check "Family policy exists" test -s /usr/share/polkit-1/actions/com.dagric.family.policy
check "Adaptive Pipeline service is installed" test -x /usr/sbin/dagric-pipeline
check "Adaptive Pipeline refresh timer is enabled" systemctl is-enabled --quiet dagric-pipeline.timer
check "Adaptive Pipeline profile passes its privacy and safety audit" dagric-pipeline audit
check "Black Box sampler is installed" test -x /usr/bin/dagric-blackbox
check "Black Box timer is enabled" systemctl is-enabled --quiet dagric-blackbox.timer
check "Black Box sampler succeeds" systemctl start dagric-blackbox.service
check "Black Box state directory is owner-only" sh -c '[ "$(stat -c %a /var/lib/dagric/blackbox)" = 700 ]'
check "Black Box event ring is owner-only" sh -c '[ "$(stat -c %a /var/lib/dagric/blackbox/events.jsonl)" = 600 ]'
check "Black Box status passes its local privacy contract" sh -c 'dagric-blackbox status | python3 -c '\''import json,sys; d=json.load(sys.stdin); assert d["network_upload"] is False; assert d["content_collection"] is False; assert 1 <= d["events"] <= d["maximum_events"]'\'''
check "Life Support read-only assessment succeeds" dagric-life-support
check "service resource budget contract parses" sh -c 'python3 -c '\''import json; p="/usr/share/dagric/budgets/services.json"; d=json.load(open(p)); required={"dagric-blackbox.service","dagric-pipeline.service","dagric-efi-fallback.service","dagric-pdf-queue.service","dagric-snapshot-setup.service"}; assert d.get("schema")==1; assert set(d.get("services",{}))==required; assert all(v.get("network")=="none" for v in d["services"].values())'\'''

blueprint_file=$(mktemp /tmp/dagric-blueprint-audit.XXXXXX.json)
# Export refuses to overwrite an existing path, so remove only the exact empty
# mktemp file before asking Blueprint to create it atomically with mode 0600.
rm -f "$blueprint_file"
if dagric-blueprint export "$blueprint_file" >/dev/null 2>&1 && \
   dagric-blueprint audit "$blueprint_file" >/dev/null 2>&1; then
    pass "Blueprint export passes schema and privacy audit"
else
    fail "Blueprint export passes schema and privacy audit"
fi
if [ -f "$blueprint_file" ] && [ "$(stat -c %a "$blueprint_file")" = 600 ]; then
    pass "Blueprint export is owner-only"
else
    fail "Blueprint export is owner-only"
fi
rm -f "$blueprint_file"
check "Support Mode report passes its privacy audit" dagric-support audit

for command in dagric-hardware-check dagric-migrate dagric-rewind dagric-family \
               dagric-pipeline-launch dagric-blueprint dagric-blackbox \
               dagric-life-support dagric-support dagric-twin dagric-update rsync ntfs-3g orca spd-say flatpak \
               btrfs-assistant snapper smartctl; do
    check "$command is executable" command -v "$command"
done
check "exFAT tools are installed" has_pkg exfatprogs
check "five Dagric translation catalogs are installed" sh -c '[ "$(find /usr/share/locale -path "*/LC_MESSAGES/dagric.mo" -type f | wc -l)" -eq 5 ]'
check "offline manual entry point exists" test -s /usr/share/dagric/manual/index.html
check "Kup backup is installed" has_pkg kup-backup

if [ "$EXPECTED_EDITION" = pro ]; then
    for package in wine wine32 winetricks dxvk-wine32 gamemode mangohud lutris \
                   opensnitch usbguard virt-manager qemu-system-x86 ovmf swtpm \
                   borgbackup vorta openssh-server; do
        check "Pro package $package is installed" has_pkg "$package"
    done
    check "i386 multiarch is enabled" sh -c 'dpkg --print-foreign-architectures | grep -qx i386'
    check "OpenSnitch daemon is active" systemctl is-active --quiet opensnitch.service
    for unit in docker.service docker.socket containerd.service usbguard.service usbguard-dbus.service \
                libvirtd.service libvirtd.socket libvirtd-ro.socket libvirtd-admin.socket \
                ssh.service sshd.service ssh.socket; do
        # Static/indirect state is not proof that no dependency can ever start
        # a unit. Report enablement, present runtime state and known systemd
        # trigger units separately; do not claim to test every D-Bus pathway.
        check "$unit has no direct enablement (or is absent)" is_disabled "$unit"
        check "$unit is inactive (or is absent)" is_inactive "$unit"
        check "$unit has no enabled or active systemd trigger units" triggers_inactive "$unit"
    done
else
    for package in wine opensnitch usbguard virt-manager qemu-system-x86 swtpm borgbackup vorta; do
        check "Free excludes Pro package $package" lacks_pkg "$package"
    done
fi

check "APT dependency state is consistent" apt-get check
audit_package_integrity || : # The helper records its failure; retain the complete report.
check "no failed system services (successful systemd query)" no_failed_services

printf '\nScope: installed software smoke checks only; not physical Secure Boot, hardware, accessibility, multi-user isolation, or release approval.\n'
printf '\ninstalled-audit: %s pass, %s fail, %s skip\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ]
