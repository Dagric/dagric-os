#!/bin/sh
# Runs INSIDE the build container. Do not run on the host.
#
# The source tree is mounted read-only at /src (Windows filesystems can't
# hold device nodes and hardlinks that live-build creates), so we copy the
# config to the container's own filesystem, build there, and drop the
# finished ISO into /out which maps back to the Windows folder.
#
# EDITION=free (default) or EDITION=pro selects the flavor:
# pro keeps the pro-*.list.chroot package lists; free removes them.
set -e

EDITION="${EDITION:-free}"

# site/repo/ is excluded for the same reason build.sh excludes it: the published
# APT repository is regenerated in place, so rsync can be reading a file that is
# being rewritten underneath it and dies with "file has vanished", killing the
# build before it starts. build.sh gained this exclusion and this script did not,
# so the Docker path kept the bug after the documented fix.
rsync -a --exclude 'out/' --exclude '.git/' --exclude 'site/repo/' /src/ /build/
cd /build
# *.hook.* and not *.hook.chroot: the boot-menu branding is a .hook.BINARY, so
# it was outside this line and depended on the executable bit surviving a
# Windows checkout and an rsync. A binary hook live-build declines to run fails
# in silence — the ISO just comes out with Debian's generic boot menu and no
# accessible ("with screen reader") entry.
chmod +x auto/* config/hooks/normal/*.hook.* 2>/dev/null || true
chmod +x config/includes.chroot/usr/bin/* config/includes.chroot/usr/lib/live/config/* \
         config/includes.chroot/usr/lib/dagric/* 2>/dev/null || true

if [ "$EDITION" != "pro" ]; then
    rm -f config/package-lists/pro-*.list.chroot
    # Pro-only appearance drop-ins are REMOVED from the free image, not just
    # hidden by their EDITION=pro flag — otherwise a free user could unlock
    # the Pro layouts and styles by deleting one line of text. Each one's
    # gallery preview thumbnail goes with it: an orphan thumb is dead weight
    # in a lean free image, and a gallery that lists thumbs would advertise a
    # style the free edition can no longer apply.
    for drop in $(grep -rlx 'EDITION=pro' config/includes.chroot/usr/share/dagric/looks \
        config/includes.chroot/usr/share/dagric/styles 2>/dev/null); do
        base=${drop##*/}
        rm -f "$drop" \
            "config/includes.chroot/usr/share/dagric/appearance/thumbs/${base%.*}.png"
    done
fi
mkdir -p config/includes.chroot/etc
printf '%s\n' "$EDITION" > config/includes.chroot/etc/dagric-edition
export DAGRIC_EDITION="$EDITION"

# Same 8-bit art guard as build.sh — see the comment there for why this reads
# the PNG header directly instead of asking ImageMagick (`identify` reports the
# *effective* depth and calls a 16-bit-header file "8-bit" when its samples
# happen to fit in 8 bits, which is precisely the case that doubles the file
# size and the case we are trying to catch), why it covers every shipped PNG
# rather than only the wallpapers, and why it tests "> 8" rather than "= 8".
deep=
for png in $(find config/includes.chroot -name '*.png' | sort); do
    [ -f "$png" ] || continue
    if [ "$(od -An -tu1 -j24 -N1 "$png" | tr -d ' ')" -gt 8 ]; then
        deep="$deep $png"
    fi
done
if [ -n "$deep" ]; then
    echo "ERROR: wallpapers are not 8-bit — this doubles their size for no" >&2
    echo "visible gain. Re-encode with: mogrify -depth 8 <file>" >&2
    for d in $deep; do echo "  $d" >&2; done
    exit 1
fi

# Same translation-drift gates as build.sh, and skipped the same way when the
# tooling is absent — see the comment there. This container is a live-build
# toolchain, not a translator's workstation, so the skip is the expected path
# here; the catalogues are committed, so a skipped check costs nothing.
if command -v msgfmt >/dev/null 2>&1; then
    sh tools/i18n-build.sh --check
else
    echo "i18n: msgfmt not installed — skipping the catalogue drift check"
fi
if command -v python3 >/dev/null 2>&1; then
    python3 tools/i18n-desktop.py --check
    # build.sh runs this and this script did not, so the Docker path could ship a
    # wizard whose strings had drifted apart with the build log reporting it fully
    # translated. The wizard's English sentences live in one file and are asked
    # for by name in another; nothing else compares the two.
    python3 tools/i18n-wizard.py --check
else
    echo "i18n: python3 not installed — skipping the .desktop drift check"
fi

lb clean
lb config

# SUBSCRIBE THE IMAGE TO ITS OWN UPDATE CHANNEL — see the long note in build.sh.
#
# build.sh got this and container-build.sh did not, so every ISO produced through
# the Docker path shipped with dagric.list pointing at the signed repository and
# with the keyring beside it, while dpkg had no record of a single dagric-*
# package. `apt upgrade` on a machine installed from a CI-built ISO could never
# deliver a fix to the wizard, the manual, the wallpapers or the security
# baseline. The channel was live, signed and reachable, and nothing was
# subscribed to anything in it.
if command -v dpkg-deb >/dev/null 2>&1; then
    rm -rf config/packages.chroot
    mkdir -p config/packages.chroot
    DAGRIC_PKG_STAGE=/build/.pkgstage \
        sh packages/stage-packages.sh /build /build/config/packages.chroot
    rm -rf /build/.pkgstage
    echo "update channel: $(ls -1 config/packages.chroot/*.deb | wc -l) config packages staged for install"

    # And the collision gate that has to travel with the staging, or this script
    # inherits the failure the staging causes: the staged .debs are pinned above
    # the live channel, so when both offer the SAME version with different bytes
    # apt calls it a downgrade and kills the build twenty minutes in. Checking
    # every package, not just dagric-tools, because a gate that catches one in
    # four reads as an all-clear.
    CHANNEL=$(curl -fsS --max-time 15 \
        https://dagric-os.web.app/repo/dists/trixie/main/binary-amd64/Packages 2>/dev/null) \
        || CHANNEL=""
    if [ -z "$CHANNEL" ]; then
        echo "WARNING: could not reach the update channel — the version-collision" >&2
        echo "         check was SKIPPED, not passed." >&2
    else
        COLLIDE=""
        for CTRL in packages/*/DEBIAN/control; do
            [ -f "$CTRL" ] || continue
            PKG=$(sed -n 's/^Package: //p' "$CTRL")
            TREEVER=$(sed -n 's/^Version: //p' "$CTRL")
            [ -n "$PKG" ] && [ -n "$TREEVER" ] || continue
            LIVEVER=$(printf '%s\n' "$CHANNEL" \
                | awk -v p="$PKG" '$0=="Package: "p{f=1} f&&/^Version:/{print $2; exit}')
            [ -n "$LIVEVER" ] || continue
            [ "$LIVEVER" = "$TREEVER" ] && COLLIDE="$COLLIDE    $PKG $TREEVER
"
        done
        if [ -n "$COLLIDE" ]; then
            echo "ERROR: the update channel already publishes these exact versions:" >&2
            printf '%s' "$COLLIDE" >&2
            echo "Bump Version: in each colliding packages/*/DEBIAN/control, then" >&2
            echo "build, then publish. Build first, publish second." >&2
            exit 1
        fi
    fi
else
    echo "WARNING: dpkg-deb not installed — the ISO will not be subscribed to" >&2
    echo "         the Dagric update channel (apt upgrade will deliver nothing)." >&2
fi

lb build

# dd plus a size check, not `cp ... 2>/dev/null`. That line reintroduced exactly
# the failure build.sh was hardened against: cp dying partway across the bridge to
# the Windows folder with "Cannot allocate memory", leaving a TRUNCATED ISO in
# /out with a plausible name and a fresh timestamp. The 2>/dev/null then threw the
# message away, so the only remaining symptom was an image that would not boot —
# and the `||` branch blamed "no ISO produced", which was not what happened.
SRCISO=$(ls -1 ./*.iso 2>/dev/null | head -1)
if [ -z "$SRCISO" ]; then
    echo "BUILD FAILED — no ISO produced. See output above." >&2
    exit 1
fi
NAME=$(basename "$SRCISO")
dd if="$SRCISO" of="/out/$NAME" bs=4M status=none
WANT=$(stat -c%s "$SRCISO")
GOT=$(stat -c%s "/out/$NAME" 2>/dev/null || echo 0)
if [ "$WANT" != "$GOT" ]; then
    echo "ERROR: copy is short — $GOT of $WANT bytes." >&2
    echo "The ISO itself is fine at $SRCISO; only the copy to /out failed." >&2
    rm -f "/out/$NAME"
    exit 1
fi
echo "copied $NAME ($GOT bytes, verified)"
cp -v build.log /out/ 2>/dev/null || true
echo ""
echo "=========================================="
echo "  Dagric OS ($EDITION) ISO is in out/"
echo "=========================================="
