#!/bin/sh
# Audit the already-built Free and Pro ISOs without modifying either image.
# Run as root on Linux/WSL because reading one file from each squashfs requires
# a loop mount. Usage: sudo sh tools/check-artifacts.sh [out/week-audit]
#
# `--pipeline-only` is a deliberately narrower developer-candidate inspection:
# it validates both immutable images, their checksums, package split, signed
# EFI, Adaptive Pipeline and Foundations payloads, but does not claim boot
# evidence exists.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
pipeline_only=0
if [ "${1:-}" = --pipeline-only ]; then
    pipeline_only=1
    shift
fi
BASE=${1:-"$ROOT/out/week-audit"}
case "$BASE" in /*) ;; *) BASE="$ROOT/$BASE" ;; esac

FREE="$BASE/free/dagric-os-1.0-amd64.iso"
PRO="$BASE/pro/dagric-os-pro-1.0-amd64.iso"
[ "$(id -u)" -eq 0 ] || { echo "artifact-check: run as root" >&2; exit 1; }
for file in "$FREE" "$PRO"; do
    [ -f "$file" ] || { echo "artifact-check: missing $file" >&2; exit 1; }
done
for command in sha256sum xorriso unsquashfs mount umount python3 git; do
    command -v "$command" >/dev/null 2>&1 || { echo "artifact-check: missing $command" >&2; exit 1; }
done

tmp=$(mktemp -d)
free_mnt="$tmp/free"
pro_mnt="$tmp/pro"
mkdir "$free_mnt" "$pro_mnt"
mounted_free=0
mounted_pro=0
cleanup() {
    [ "$mounted_pro" -eq 0 ] || umount "$pro_mnt" 2>/dev/null || true
    [ "$mounted_free" -eq 0 ] || umount "$free_mnt" 2>/dev/null || true
    rm -rf "$tmp"
}
trap cleanup EXIT HUP INT TERM

if [ -f "$BASE/SHA256SUMS" ]; then
    (cd "$BASE" && sha256sum -c SHA256SUMS)
elif [ "$pipeline_only" -eq 1 ] && [ -f "$BASE/free/SHA256SUMS" ] && [ -f "$BASE/pro/SHA256SUMS" ]; then
    (cd "$BASE/free" && sha256sum -c SHA256SUMS)
    (cd "$BASE/pro" && sha256sum -c SHA256SUMS)
else
    echo "artifact-check: missing combined $BASE/SHA256SUMS" >&2
    exit 1
fi

# Checksums identify artifact bytes; these files identify the reviewed source
# that produced them. Both editions must come from the same exact commit.
for edition in free pro; do
    provenance="$BASE/SOURCE_COMMIT-$edition"
    [ -f "$provenance" ] || { echo "artifact-check: missing $provenance" >&2; exit 1; }
    commit=$(tr -d '\r\n' < "$provenance")
    printf '%s\n' "$commit" | grep -Eq '^[0-9a-fA-F]{40}$' || {
        echo "artifact-check: invalid source revision in $provenance" >&2
        exit 1
    }
    if [ "$edition" = free ]; then
        source_commit=$commit
    elif [ "$commit" != "$source_commit" ]; then
        echo "artifact-check: Free and Pro were built from different source revisions" >&2
        exit 1
    fi
done
echo "artifact-check: source revision $source_commit"
mount -o loop,ro "$FREE" "$free_mnt"
mounted_free=1
mount -o loop,ro "$PRO" "$pro_mnt"
mounted_pro=1

require_package() {
    manifest=$1
    package=$2
    grep -Eq "^${package}(:[^[:space:]]+)?[[:space:]]" "$manifest" || {
        echo "artifact-check: $manifest lacks $package" >&2
        exit 1
    }
}

reject_package() {
    manifest=$1
    package=$2
    if grep -Eq "^${package}(:[^[:space:]]+)?[[:space:]]" "$manifest"; then
        echo "artifact-check: Free artifact unexpectedly contains Pro package $package" >&2
        exit 1
    fi
}

free_manifest="$free_mnt/live/filesystem.packages"
pro_manifest="$pro_mnt/live/filesystem.packages"
for package in calamares grub-pc-bin grub-efi-amd64-signed shim-signed mokutil \
               orca speech-dispatcher-espeak-ng firewalld apparmor snapper \
               btrfs-assistant kup-backup ntfs-3g exfatprogs; do
    require_package "$free_manifest" "$package"
    require_package "$pro_manifest" "$package"
done

for package in wine wine32 winetricks dxvk-wine32 gamemode mangohud lutris \
               opensnitch usbguard virt-manager qemu-system-x86 ovmf swtpm \
               borgbackup vorta; do
    require_package "$pro_manifest" "$package"
    reject_package "$free_manifest" "$package"
done

free_edition=$(unsquashfs -cat "$free_mnt/live/filesystem.squashfs" etc/dagric-edition 2>/dev/null)
pro_edition=$(unsquashfs -cat "$pro_mnt/live/filesystem.squashfs" etc/dagric-edition 2>/dev/null)
[ "$free_edition" = free ] || { echo "artifact-check: Free marker is '$free_edition'" >&2; exit 1; }
[ "$pro_edition" = pro ] || { echo "artifact-check: Pro marker is '$pro_edition'" >&2; exit 1; }

# The adaptive profile compiler is deliberately service-only: there must be no
# desktop entry, but both editions must contain its audited command, launch
# wrapper and refresh timer.  Inspect the immutable squashfs rather than
# trusting source files or a package staging directory.
require_pipeline() {
    image=$1
    listing=$(unsquashfs -ll "$image" 2>/dev/null)
    for path in \
        squashfs-root/usr/sbin/dagric-pipeline \
        squashfs-root/usr/bin/dagric-pipeline-launch \
        squashfs-root/usr/lib/dagric/pipeline.py \
        squashfs-root/usr/lib/dagric/private_files.py \
        squashfs-root/etc/systemd/system/dagric-pipeline.service \
        squashfs-root/etc/systemd/system/dagric-pipeline.timer \
        squashfs-root/etc/systemd/system/timers.target.wants/dagric-pipeline.timer; do
        printf '%s\\n' "$listing" | grep -Fq " $path" || {
            echo "artifact-check: adaptive pipeline missing $path" >&2
            exit 1
        }
    done
    unsquashfs -cat "$image" etc/systemd/system/dagric-pipeline.service 2>/dev/null \
        | grep -Fq 'ProtectSystem=strict' || {
            echo "artifact-check: adaptive pipeline service is not hardened" >&2
            exit 1
        }
    unsquashfs -cat "$image" etc/systemd/system/dagric-pipeline.timer 2>/dev/null \
        | grep -Fq 'OnUnitActiveSec=6h' || {
            echo "artifact-check: adaptive pipeline refresh interval is absent" >&2
            exit 1
        }
    if printf '%s\\n' "$listing" | grep -Fq 'squashfs-root/usr/share/applications/dagric-pipeline.desktop'; then
        echo "artifact-check: adaptive pipeline unexpectedly has a desktop entry" >&2
        exit 1
    fi
}
require_pipeline "$free_mnt/live/filesystem.squashfs"
require_pipeline "$pro_mnt/live/filesystem.squashfs"

# Blueprint, Black Box and Life Support are the privacy/safety foundations for
# a hardware-specific Dagric pipeline.  Verify the actual compressed payload,
# enablement links and resource limits in both immutable images.  Source-only
# checks would miss a hook that forgot to copy or enable one of these pieces.
require_foundations() {
    image=$1
    listing=$(unsquashfs -ll "$image" 2>/dev/null)
    for path in \
        squashfs-root/usr/bin/dagric-blueprint \
        squashfs-root/usr/bin/dagric-blackbox \
        squashfs-root/usr/bin/dagric-life-support \
        squashfs-root/usr/bin/dagric-support \
        squashfs-root/usr/bin/dagric-update \
        squashfs-root/usr/lib/dagric/foundations.py \
        squashfs-root/usr/lib/dagric/update_core.py \
        squashfs-root/etc/systemd/system/dagric-blackbox.service \
        squashfs-root/etc/systemd/system/dagric-blackbox.timer \
        squashfs-root/etc/systemd/system/timers.target.wants/dagric-blackbox.timer \
        squashfs-root/usr/share/dagric/budgets/services.json \
        squashfs-root/usr/share/applications/dagric-blueprint.desktop \
        squashfs-root/usr/share/applications/dagric-update.desktop \
        squashfs-root/usr/share/polkit-1/actions/org.dagric.rewind.policy \
        squashfs-root/usr/share/applications/dagric-life-support.desktop; do
        printf '%s\n' "$listing" | grep -Fq " $path" || {
            echo "artifact-check: Dagric Foundations missing $path" >&2
            exit 1
        }
    done
    service=$(unsquashfs -cat "$image" etc/systemd/system/dagric-blackbox.service 2>/dev/null)
    for setting in ProtectSystem=strict ProtectHome=yes NoNewPrivileges=yes \
                   ReadWritePaths=/var/lib/dagric/blackbox MemoryMax=64M \
                   CPUQuota=5% IOSchedulingClass=idle UMask=0077; do
        printf '%s\n' "$service" | grep -Fqx "$setting" || {
            echo "artifact-check: Black Box service lacks $setting" >&2
            exit 1
        }
    done
    timer=$(unsquashfs -cat "$image" etc/systemd/system/dagric-blackbox.timer 2>/dev/null)
    for setting in OnBootSec=5m OnUnitActiveSec=5m Persistent=false; do
        printf '%s\n' "$timer" | grep -Fqx "$setting" || {
            echo "artifact-check: Black Box timer lacks $setting" >&2
            exit 1
        }
    done
    unsquashfs -cat "$image" usr/share/dagric/budgets/services.json 2>/dev/null \
        | python3 -c 'import json,sys; d=json.load(sys.stdin); required={"dagric-blackbox.service","dagric-pipeline.service","dagric-efi-fallback.service","dagric-pdf-queue.service","dagric-snapshot-setup.service"}; assert d.get("schema")==1; assert set(d.get("services",{}))==required; assert all(v.get("network")=="none" and v.get("decision") in {"provisional","measured"} for v in d["services"].values())' || {
            echo "artifact-check: service budget contract is invalid" >&2
            exit 1
        }
}
require_foundations "$free_mnt/live/filesystem.squashfs"
require_foundations "$pro_mnt/live/filesystem.squashfs"

# Static payload evidence only: do not execute image code or infer that a
# physical account/connection test passed. The eight reviewed security files
# must match the commit recorded for these artifacts (allowing CRLF cleanup).
require_security_payload() {
    python3 - "$1" "$2" "$ROOT" "$source_commit" <<'DAGRIC_SECURITY_ARTIFACT_PY'
import ast
import json
from pathlib import PurePosixPath
import posixpath
import subprocess
import sys

SOURCE_FILES = {
    'usr/bin/opensnitch-ui': 'config/includes.chroot/usr/bin/opensnitch-ui',
    'usr/lib/dagric/private_files.py': 'config/includes.chroot/usr/lib/dagric/private_files.py',
    'usr/lib/dagric/pipeline.py': 'config/includes.chroot/usr/lib/dagric/pipeline.py',
    'usr/lib/dagric/twin.py': 'config/includes.chroot/usr/lib/dagric/twin.py',
    'usr/bin/dagric-restore-assistant': 'config/includes.chroot/usr/bin/dagric-restore-assistant',
    'var/lib/dpkg/info/dagric-tools.preinst': 'packages/dagric-tools/DEBIAN/preinst',
    'var/lib/dpkg/info/dagric-tools.postinst': 'packages/dagric-tools/DEBIAN/postinst',
    'var/lib/dpkg/info/dagric-tools.postrm': 'packages/dagric-tools/DEBIAN/postrm',
}
ENDPOINT = 'unix:///run/dagric-opensnitch/osui.sock'
DROPIN = 'usr/lib/systemd/system/opensnitch.service.d/20-dagric-control-socket.conf'


def parse_listing(text):
    entries = {}
    for line in text.splitlines():
        if ' squashfs-root/' not in line:
            continue
        metadata, tail = line.split(' squashfs-root/', 1)
        path, _, target = tail.partition(' -> ')
        columns = metadata.split()
        entries[path] = (columns[0], columns[1], target)
    return entries


def audit_security_payload(read, listing, edition, expected_sources):
    def require(condition, reason):
        if not condition:
            raise ValueError(reason)

    def regular(path, executable=False):
        require(path in listing, 'missing exact payload path: ' + path)
        mode, owner, _ = listing[path]
        require(mode.startswith('-') and owner == 'root/root', 'unsafe payload owner/type: ' + path)
        require(mode[5] != 'w' and mode[8] != 'w', 'writable security payload: ' + path)
        if executable:
            require(mode[3] in 'xs', 'nonexecutable launcher: ' + path)

    package_files = set(read('var/lib/dpkg/info/dagric-tools.list').decode().splitlines())
    for path in SOURCE_FILES:
        regular(path, path == 'usr/bin/opensnitch-ui' or '/dagric-tools.' in path)
        require(read(path).replace(b'\r\n', b'\n') == expected_sources[path].replace(b'\r\n', b'\n'),
                'security payload differs from recorded source commit: ' + path)
        if not path.startswith('var/lib/dpkg/info/'):
            require('/' + path in package_files, 'security payload is not owned by dagric-tools: ' + path)

    for path in (DROPIN, 'usr/lib/tmpfiles.d/dagric-opensnitch.conf'):
        regular(path)
        require('/' + path in package_files, 'unpackaged OpenSnitch wiring: ' + path)
    require('etc/systemd/system/opensnitch.service.d/20-dagric-control-socket.conf' not in listing,
            'managed drop-in is incorrectly preserved under /etc')
    require(ENDPOINT == json.loads(read('etc/opensnitchd/default-config.json'))['Server']['Address'],
            'daemon JSON does not use the protected endpoint')
    tmpfiles = read('usr/lib/tmpfiles.d/dagric-opensnitch.conf').decode().splitlines()
    require('d /run/dagric-opensnitch 02770 root sudo -' in tmpfiles,
            'missing root:sudo 02770 boot directory contract')
    unit = read(DROPIN).decode().splitlines()
    for directive in (
        'ExecStartPre=/usr/bin/systemd-tmpfiles --create /usr/lib/tmpfiles.d/dagric-opensnitch.conf',
        'ExecStartPre=/usr/bin/opensnitch-ui --check-directory',
        'ExecStartPre=/usr/bin/opensnitch-ui --migrate-config',
        'ExecStart=',
        'ExecStart=/usr/bin/opensnitchd -rules-path /etc/opensnitchd/rules -ui-socket ' + ENDPOINT,
    ):
        require(directive in unit, 'missing managed daemon directive: ' + directive)
    records = read('var/lib/dpkg/diversions').decode().splitlines()
    require(len(records) % 3 == 0, 'invalid dpkg diversion records')
    matches = [records[i:i + 3] for i in range(0, len(records), 3) if records[i] == '/usr/bin/opensnitch-ui']
    require(matches == [['/usr/bin/opensnitch-ui', '/usr/lib/dagric/opensnitch-ui-upstream', 'dagric-tools']],
            'missing or conflicting installed OpenSnitch diversion')
    helper = ast.parse(read('usr/lib/dagric/private_files.py'))
    require(any(isinstance(node, ast.FunctionDef) and node.name == 'write_private_text' for node in helper.body),
            'missing private state writer API')
    for path in ('usr/lib/dagric/pipeline.py', 'usr/lib/dagric/twin.py', 'usr/bin/dagric-restore-assistant'):
        module = ast.parse(read(path))
        require(any(isinstance(node, ast.ImportFrom) and node.module == 'private_files' and
                    any(alias.name == 'write_private_text' for alias in node.names) for node in ast.walk(module)),
                'private state writer is not wired into: ' + path)

    # The Free artifact carries the guard for later upgrades, not the Pro UI.
    vendor = 'usr/lib/dagric/opensnitch-ui-upstream'
    if edition == 'pro' or vendor in listing:
        regular(vendor, executable=True)
        require(b'--socket' in read(vendor), 'vendor UI lacks the required socket option')
        desktop = 'usr/share/applications/opensnitch_ui.desktop'
        allowed_exec = {'Exec=opensnitch-ui', 'Exec=opensnitch-ui --background'}
        require(any(line in allowed_exec for line in read(desktop).decode().splitlines()),
                'vendor menu bypasses the managed launcher')
        autostart = 'etc/xdg/autostart/opensnitch_ui.desktop'
        require(autostart in listing, 'missing vendor autostart route')
        if listing[autostart][0].startswith('l'):
            target = listing[autostart][2]
            resolved = posixpath.normpath(posixpath.join('/' + str(PurePosixPath(autostart).parent), target))
            require(resolved == '/' + desktop, 'autostart symlink bypasses the managed launcher')
        else:
            require(any(line in allowed_exec for line in read(autostart).decode().splitlines()),
                    'vendor autostart bypasses the managed launcher')
    if edition == 'pro':
        blocked_defaults = {'docker.service', 'docker.socket', 'containerd.service', 'ssh.service', 'sshd.service', 'ssh.socket'}
        for path in listing:
            if path.startswith(('etc/systemd/system/', 'usr/lib/systemd/system/', 'lib/systemd/system/')):
                require(not (('/' in path and PurePosixPath(path).name in blocked_defaults) and
                             ('.wants/' in path or '.requires/' in path)),
                        'Pro ships an unexpected enabled service dependency: ' + path)


if __name__ == '__main__':
    image, edition, root, commit = sys.argv[1:]
    try:
        def read(path):
            return subprocess.check_output(['unsquashfs', '-cat', image, path], stderr=subprocess.PIPE)
        expected = {path: subprocess.check_output(['git', '-C', root, 'show', commit + ':' + source], stderr=subprocess.PIPE)
                    for path, source in SOURCE_FILES.items()}
        listing = parse_listing(subprocess.check_output(['unsquashfs', '-ll', image], stderr=subprocess.PIPE).decode())
        audit_security_payload(read, listing, edition, expected)
    except (ValueError, KeyError, SyntaxError, IndexError, subprocess.CalledProcessError) as exc:
        print('artifact-check: security payload failed for ' + edition + ': ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
    print('artifact-check: ' + edition + ' security payload/source wiring passed (not runtime or physical approval)')
DAGRIC_SECURITY_ARTIFACT_PY
}
require_security_payload "$free_mnt/live/filesystem.squashfs" free
require_security_payload "$pro_mnt/live/filesystem.squashfs" pro

sh "$ROOT/tools/check-secureboot.sh" "$FREE"
sh "$ROOT/tools/check-secureboot.sh" "$PRO"

if [ "$pipeline_only" -eq 0 ]; then
    evidence="$BASE/boot-evidence"
    for run in \
        "$evidence/free/boot-test/dagric-os-1.0-amd64-bios" \
        "$evidence/free/boot-test/dagric-os-1.0-amd64-uefi" \
        "$evidence/free/boot-test/dagric-os-1.0-amd64-secureboot" \
        "$evidence/pro/boot-test/dagric-os-pro-1.0-amd64-uefi"; do
        [ -s "$run/qemu.log" ] || { echo "artifact-check: missing boot log $run/qemu.log" >&2; exit 1; }
        frames=$(find "$run" -name 't*.png' -type f -size +10k | wc -l)
        [ "$frames" -ge 3 ] || { echo "artifact-check: insufficient non-empty frames in $run" >&2; exit 1; }
    done
fi

free_size=$(stat -c %s "$FREE")
pro_size=$(stat -c %s "$PRO")
[ "$free_size" -gt 1500000000 ] || { echo "artifact-check: Free ISO is implausibly small" >&2; exit 1; }
[ "$pro_size" -gt "$free_size" ] || { echo "artifact-check: Pro ISO is not larger than Free" >&2; exit 1; }

if [ "$pipeline_only" -eq 1 ]; then
    echo "artifact-check: candidate passed (checksums, edition split, package manifests, signed EFI, adaptive pipeline, Foundations and static security payloads)"
else
    echo "artifact-check: passed (checksums, edition split, package manifests, signed EFI, adaptive pipeline, Foundations, static security payloads and four boot evidence sets)"
fi
