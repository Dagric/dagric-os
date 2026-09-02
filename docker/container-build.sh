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

# Bind every artifact to the exact reviewed source revision that produced it.
# Release builds are stricter: they refuse an unknown revision or a dirty tree,
# because a checksum proves only the ISO bytes, not where those bytes came from.
SOURCE_COMMIT=${DAGRIC_SOURCE_COMMIT:-}
if [ -z "$SOURCE_COMMIT" ] && command -v git >/dev/null 2>&1; then
    SOURCE_COMMIT=$(git -C /src rev-parse HEAD 2>/dev/null || true)
fi
if ! printf '%s\n' "$SOURCE_COMMIT" | grep -Eq '^[0-9a-fA-F]{40}$'; then
    if [ "${DAGRIC_RELEASE_BUILD:-0}" = 1 ]; then
        echo "ERROR: release build has no valid source commit." >&2
        exit 1
    fi
    echo "WARNING: source commit is unknown; this is not a promotable release build." >&2
    SOURCE_COMMIT=
elif [ "${DAGRIC_RELEASE_BUILD:-0}" = 1 ]; then
    [ -d /src/.git ] || { echo "ERROR: release build cannot inspect source cleanliness." >&2; exit 1; }
    if [ -n "$(git -C /src status --porcelain --untracked-files=all)" ]; then
        echo "ERROR: release build source tree is dirty." >&2
        git -C /src status --short >&2
        exit 1
    fi
fi
[ -z "$SOURCE_COMMIT" ] || echo "Source revision: $SOURCE_COMMIT"

# Run repository-level checks before copying the source without .git. The
# action-pin and tracked-secret checks intentionally need the original checkout.
python3 /src/tools/check-source.py

# site/repo/ is excluded for the same reason build.sh excludes it: the published
# APT repository is regenerated in place, so rsync can be reading a file that is
# being rewritten underneath it and dies with "file has vanished", killing the
# build before it starts. build.sh gained this exclusion and this script did not,
# so the Docker path kept the bug after the documented fix.
rsync -a --exclude 'out/' --exclude '.git/' --exclude 'site/repo/' \
    --exclude '%SystemDrive%/' /src/ /build/
cd /build
# *.hook.* and not *.hook.chroot: the boot-menu branding is a .hook.BINARY, so
# it was outside this line and depended on the executable bit surviving a
# Windows checkout and an rsync. A binary hook live-build declines to run fails
# in silence — the ISO just comes out with Debian's generic boot menu and no
# accessible ("with screen reader") entry.
chmod +x auto/* config/hooks/normal/*.hook.* 2>/dev/null || true
chmod +x config/includes.chroot/usr/bin/* config/includes.chroot/usr/sbin/* \
         config/includes.chroot/usr/lib/live/config/* \
         config/includes.chroot/usr/lib/dagric/* 2>/dev/null || true

# Resolve every package name BEFORE the edition pruning below deletes the Pro
# lists — deliberately, and this position is the whole point.
#
# The first version of this check sat next to `lb config`, which runs after the
# pruning. On a free build the pro-*.list.chroot files were already gone, so it
# validated 164 names and reported "all 164 package names resolve" — a clean
# pass that had never looked at Pro's 66 packages at all. Since CI only builds
# free, that meant the paid edition's package names were never checked by
# anything, which is the half of the product where a broken name costs money.
#
# Here it sees all 230 on every build, free or Pro. A typo in a Pro list now
# fails the free build too, which is correct: it means the tree is broken, and
# the cheapest place to learn that is the build that runs on every push.
sh tools/check-package-names.sh
sh tools/check-rewind.sh
sh tools/check-pipeline.sh

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
    # THE OPENSNITCH CONFIG STAYS ON FREE, AND THIS COMMENT IS THE REASON.
    #
    # It was pruned here on 2026-08-29 as "dead weight": free installs no
    # opensnitch package, so its config looked like clutter that might mislead
    # anyone auditing the image. That argument was made from inside this file
    # without opening the one file in the tree that depends on those paths, and
    # it was wrong.
    #
    # /usr/bin/dagric-upgrade-to-pro — the $39 in-place upgrade, which ships ON
    # THE FREE IMAGE — says so in as many words: "The free image deliberately
    # ships /etc/opensnitchd/ (the tuned config with the pre-answer rules — it
    # exists precisely so an upgraded machine matches the Pro ISO)". That
    # upgrade installs opensnitch with --force-confdef --force-confold, and
    # keeping the old file is not a safety default there, it is THE MECHANISM:
    # the on-disk config is Dagric's, and dpkg keeping it is what gives an
    # upgraded machine the same fourteen pre-answer rules a Pro ISO install has.
    #
    # Delete them and a customer who pays for the upgrade gets upstream's stock
    # config instead — no pre-answer rules, so OpenSnitch begins asking about
    # apt, flatpak, fwupd and the update checker. That is precisely the wall of
    # prompts that once stopped a real install at 42%, and it is documented
    # three files away. A free machine carrying an unused config is not a defect
    # worth paying that for.
    #
    # If this is ever revisited: read dagric-upgrade-to-pro first.
    :
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
# tooling is absent — see the comment there.
#
# This used to say the skip was "the expected path here" because the container
# is a live-build toolchain rather than a translator's workstation, and that a
# skipped check therefore "costs nothing". Both halves were wrong, and together
# they are how a stale catalogue reached main and stayed there: the builder
# image installed no gettext, so this branch was skipped on EVERY CI build of
# both editions, and the .mo files really had drifted two consent strings
# behind po/*.po. The skip cost five languages an English NVIDIA driver prompt
# and an English Variety privacy screen — both of them screens where the owner
# is being asked to agree to something.
#
# docker/Dockerfile now installs gettext, so msgfmt is present and the check is
# the path actually taken. The else branch stays for anyone running this script
# outside the image, but it is no longer the normal case and must not be
# treated as harmless.
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

# THE boot=live GATE, WHICH LIVED ONLY IN build.sh.
#
# tools/check-package-names.sh's header already warns that these two drivers
# have drifted before and that a check living in only one of them "silently does
# not apply to half the builds" — and this is exactly that: build.sh calls the
# loss of this one word something that "must not be silent", while every Docker
# and CI build was never checked at all. Losing boot=live puts opensnitchd into
# the live session, where it can stop a real install at 42% behind a modal
# prompt whose Deny button counts down.
#
# Both flags carry their whole command line in one double-quoted argument on one
# line, and matching the trailing `"` is what keeps --bootappend-live from also
# matching --bootappend-live-failsafe.
for _ba in '--bootappend-live "' '--bootappend-live-failsafe "'; do
    if ! grep -F -- "$_ba" auto/config | grep -q 'boot=live'; then
        echo "ERROR: auto/config's $_ba no longer passes boot=live." >&2
        echo "       The opensnitch drop-in keys off exactly that word, so the" >&2
        echo "       daemon would run during the install and can interrupt it" >&2
        echo "       with a prompt that denies on timeout. Either restore" >&2
        echo "       boot=live or change the Condition in" >&2
        echo "       config/includes.chroot/etc/systemd/system/" >&2
        echo "       opensnitch.service.d/10-dagric-not-in-live.conf to match." >&2
        exit 1
    fi
done
echo "live gate: boot=live present on both boot entries"

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
# THE NAME CARRIES THE EDITION, exactly as build.sh's does. live-build always
# calls its output live-image-amd64.hybrid.iso, so taking the basename handed
# BOTH editions that one name: `.\build.ps1` followed by `.\build.ps1 -Edition
# pro` wrote the same file twice, the free ISO was silently replaced by the Pro
# one, and nothing left in out/ said which edition survived. That is the same
# "plausible name, fresh timestamp, wrong bytes" failure the dd-and-verify block
# above was written to prevent, arriving by a different route.
#
# These exact names are what everything downstream speaks: write-usb.ps1 picks
# the ISO by them, release.yml checks for them, and site/download.html links to
# them. 1.0 is hard-coded on purpose — the product version is "1.0 (Foundation)"
# in os-release and the v1.x tags are release milestones, not version bumps.
case "$EDITION" in
    pro) NAME=dagric-os-pro-1.0-amd64.iso ;;
    *)   NAME=dagric-os-1.0-amd64.iso ;;
esac
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

# RECORD THE CHECKSUM, which build.sh does and this driver did not.
#
# The consequence of the gap is a customer-visible one: a Docker- or CI-built
# ISO left out/SHA256SUMS describing the PREVIOUS image, so a buyer following
# download.html's verify steps gets a MISMATCH — which, as build.sh puts it,
# "reads as a corrupted or tampered download". Same block, same reasoning,
# /out paths.
#
# Deliberately NOT signed here: signing is a release step that needs the key,
# and a build must never quietly emit something that looks signed.
SUMS=/out/SHA256SUMS
[ -f "$SUMS" ] || : > "$SUMS"
grep -v "  ${NAME}\$" "$SUMS" > "$SUMS.tmp" 2>/dev/null || :
( cd /out && sha256sum "$NAME" ) >> "$SUMS.tmp"
LC_ALL=C sort -k2,2 "$SUMS.tmp" -o "$SUMS"
rm -f "$SUMS.tmp"
echo "recorded sha256 for $NAME in out/SHA256SUMS"
if [ -n "$SOURCE_COMMIT" ]; then
    printf '%s\n' "$SOURCE_COMMIT" > "/out/SOURCE_COMMIT-$EDITION"
    echo "recorded source revision in out/SOURCE_COMMIT-$EDITION"
fi
echo "NOTE: out/SHA256SUMS has changed. Before deploying the site, copy it to"
echo "      site/ and RE-SIGN it — site/SHA256SUMS.sig covers the previous"
echo "      contents and will fail gpg --verify until it is regenerated."

cp -v build.log /out/ 2>/dev/null || true
echo ""
echo "=========================================="
echo "  Dagric OS ($EDITION) ISO is in out/"
echo "=========================================="
