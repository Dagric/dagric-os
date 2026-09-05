#!/bin/sh
# Run as root on an installed Dagric system. The VM harness puts this script on
# a small writable FAT evidence disk; mount it at /mnt/evidence and the report
# is preserved on that same disk. Usage: installed-audit.sh free|pro [uefi|bios]
set -eu

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
# dpkg-query expands an unqualified Multi-Arch package (for example MangoHud
# on Pro) once per installed architecture. Without a record separator the two
# values become "installedinstalled", making a healthy amd64+i386 pair fail.
has_pkg() { dpkg-query -W -f='${db:Status-Status}\n' "$1" 2>/dev/null | grep -qx installed; }
lacks_pkg() { ! has_pkg "$1"; }
is_disabled() {
    _state=$(systemctl is-enabled "$1" 2>/dev/null || true)
    case "$_state" in disabled|masked|static|indirect|not-found) return 0 ;; *) return 1 ;; esac
}

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
    for unit in docker.service docker.socket usbguard.service usbguard-dbus.service \
                libvirtd.service libvirtd.socket ssh.service ssh.socket; do
        check "$unit does not auto-start" is_disabled "$unit"
    done
else
    for package in wine opensnitch usbguard virt-manager qemu-system-x86 swtpm borgbackup vorta; do
        check "Free excludes Pro package $package" lacks_pkg "$package"
    done
fi

check "APT dependency state is consistent" apt-get check
dpkg_verify=$(dpkg -V dagric-branding dagric-desktop-defaults dagric-security-policy dagric-tools 2>/dev/null || true)
if [ -z "$dpkg_verify" ]; then
    pass "Dagric packages verify with dpkg"
elif [ "$EXPECTED_EDITION" = free ] && \
     [ "$(printf '%s\n' "$dpkg_verify" | wc -l)" -eq 2 ] && \
     printf '%s\n' "$dpkg_verify" | grep -Fq 'missing     /usr/share/applications/dagric-usb-protect.desktop' && \
     printf '%s\n' "$dpkg_verify" | grep -Fq 'missing     /usr/share/applications/dagric-vm.desktop'; then
    # These two entries carry X-Dagric-Edition=pro and are deliberately removed
    # after package installation. dagric-app-names repeats the gate after every
    # update, so their absence is the edition contract rather than corruption.
    pass "Dagric package changes match the two intentional Free launcher removals"
elif [ "$EXPECTED_EDITION" = pro ] && \
     [ "$(printf '%s\n' "$dpkg_verify" | wc -l)" -eq 1 ] && \
     printf '%s\n' "$dpkg_verify" | grep -Fq '/usr/share/sddm/themes/dagric/theme.conf' && \
     grep -qx 'editionBadge=PRO EDITION' /usr/share/sddm/themes/dagric/theme.conf; then
    # dagric-branding is edition-neutral when its .deb is built. The Pro image
    # deliberately writes its login-screen badge after package installation;
    # accept only that one exact file and verify the intended value as well as
    # the dpkg path so unrelated package drift cannot hide behind this rule.
    pass "Dagric package change matches the intentional Pro login badge"
else
    fail "Dagric package verification reported changed files"
    printf '%s\n' "$dpkg_verify" | sed 's/^/       /'
fi
check "no failed system services" sh -c '[ "$(systemctl --failed --no-legend 2>/dev/null | wc -l)" -eq 0 ]'

printf '\ninstalled-audit: %s pass, %s fail, %s skip\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ]
