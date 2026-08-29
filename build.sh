#!/bin/sh
# Dagric OS — build natively on a Debian machine (needs root).
#   sudo apt install live-build rsync
#   sudo ./build.sh            # free edition
#   sudo ./build.sh pro        # Pro edition
#
# This mirrors docker/container-build.sh: without the edition gating below,
# a native build would include ALL pro-*.list.chroot packages under free
# branding, and leave the includes.chroot helper scripts non-executable.
#
# The build happens in a COPY of the tree, never in place. Building free
# edition used to `rm -f config/package-lists/pro-*.list.chroot` in the source
# directory itself — permanently deleting the Pro lists from the working tree,
# so the next `./build.sh pro` would silently produce a "Pro" ISO with none of
# the Pro packages in it. Copy first; the source tree is now read-only to us.
set -e
cd "$(dirname "$0")"
SRC=$(pwd)

EDITION="${1:-free}"
BUILD="${DAGRIC_BUILD_DIR:-$SRC/../dagric-build-$EDITION}"

command -v rsync >/dev/null 2>&1 || { echo "rsync is required: apt install rsync"; exit 1; }

echo "Building $EDITION edition in: $BUILD"
rm -rf "$BUILD"
mkdir -p "$BUILD"
# site/repo is excluded for two reasons, and the second one bit.
#
# It is 65 MB of .deb that no image build reads — the packages an image needs
# are assembled fresh into config/packages.chroot by stage-packages.sh, from
# the tree AFTER edition gating, so the published copies are the wrong bytes
# anyway.
#
# And it is generated, so it changes under this rsync. Running
# packages/build-repo.sh while a build was copying killed the build outright:
#   file has vanished: ".../pool/main/dagric-tools_1.1.0_all.deb"
#   rsync warning: some files vanished before they could be transferred (24)
# Excluding it means the two can never race again.
rsync -a --exclude 'out/' --exclude '.git/' --exclude 'site/repo/' "$SRC/" "$BUILD/"
cd "$BUILD"

# *.hook.* and not *.hook.chroot: the boot-menu branding is a .hook.BINARY and
# was outside this line, so it depended entirely on the executable bit
# surviving the checkout. On a Windows clone that bit is synthesised by the
# drvfs mount rather than stored, and a binary hook live-build declines to run
# fails silently — the ISO simply comes out with Debian's generic boot menu and
# no accessible entry.
chmod +x auto/* config/hooks/normal/*.hook.* 2>/dev/null || true
chmod +x config/includes.chroot/usr/bin/* \
         config/includes.chroot/usr/lib/live/config/* \
         config/includes.chroot/usr/lib/dagric/* 2>/dev/null || true

# Resolve every package name BEFORE the edition pruning below deletes the Pro
# lists. See the long note at the same point in docker/container-build.sh: put
# after the pruning, this validates only the free edition's 164 names and
# reports a clean pass having never looked at Pro's 66.
sh tools/check-package-names.sh

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
    # OpenSnitch's configuration must not ship on an edition that has no
    # OpenSnitch. The free image carried /etc/opensnitchd/default-config.json,
    # fourteen Dagric rule files and the /etc/skel UI preference — while free
    # installs no opensnitch package and has no opensnitchd binary at all.
    # Nothing malfunctioned; it is dead weight in an image whose whole pitch is
    # being leaner, and it misleads in the one direction that matters: somebody
    # auditing the free edition finds a firewall's config and its rules and
    # reasonably concludes the firewall is there.
    rm -rf config/includes.chroot/etc/opensnitchd \
           config/includes.chroot/etc/skel/.config/opensnitch \
           config/includes.chroot/etc/systemd/system/opensnitch.service.d \
           config/includes.chroot/usr/lib/live/config/2020-dagric-opensnitch-live
fi
mkdir -p config/includes.chroot/etc
printf '%s\n' "$EDITION" > config/includes.chroot/etc/dagric-edition
export DAGRIC_EDITION="$EDITION"

# Refuse to ship 16-bit wallpapers. Every pack now comes out of
# branding/wallpaper/make-wallpapers.sh, which writes -depth 8 -- the six wave-1
# packs that used to have no generator were fitted and folded into it. So the
# generator is no longer the risk; a hand-edited or re-exported PNG is. This
# gate is what proves one never sneaks back in, and it is the only thing
# standing between us and a repeat of the 43 MB regression, where six packs were
# written as 16-bit RGBA and nobody noticed until the ISO was measured.
#
# Read the depth out of the PNG header directly (byte 24, right after IHDR's
# width and height) rather than shelling out to ImageMagick: the build host is
# a live-build chroot toolchain and is not required to have `identify`, and a
# check that silently no-ops when its dependency is missing is worse than none.
#
# Every shipped PNG is checked, not just the wallpapers. The wallpapers were
# where the regression happened, but they are not the only 4K art in the image:
# usr/share/dagric/sddm/background.png is 3840x2160 and comes out of its own
# generator (branding/sddm/make-login-art.sh), so it can regress exactly the
# same way and used to sit outside this gate entirely.
#
# The test is "greater than 8", not "equal to 8". 16-bit is the thing that
# doubles the file for no visible gain; a palette PNG with a depth of 1, 2 or 4
# is SMALLER, and several of the icons and avatars here are one pngquant pass
# away from being exactly that. An equality test would reject a file for being
# too cheap, which is the opposite of what this gate is for.
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

# Translation drift. The .mo catalogues and the localised .desktop keys are
# COMMITTED build products (see tools/i18n-build.sh for why), so the failure
# this catches is somebody editing an English string and forgetting to
# recompile: the catalogue still loads, still says the old thing, and the only
# symptom is a language that quietly goes stale. Both checks are read-only and
# exit non-zero on drift.
#
# SKIPPED rather than fatal when the tooling is absent. gettext and python3 are
# build-HOST packages that the image does not need and the live-build container
# is not required to carry; the catalogues are committed, so a host without
# them still produces a fully translated ISO. Making this a hard requirement
# would break the build for a check, which is the wrong trade — but it is
# announced, because a gate that skips in silence is a gate nobody trusts.
if command -v msgfmt >/dev/null 2>&1; then
    sh tools/i18n-build.sh --check
else
    echo "i18n: msgfmt not installed — skipping the catalogue drift check"
fi
if command -v python3 >/dev/null 2>&1; then
    python3 tools/i18n-desktop.py --check
    # The setup wizard's English sentences live in one file and are asked for by
    # name in another, and nothing compared the two — so 18 shipped strings were
    # never displayed while about fifty displayed strings were never shipped, and
    # the build log reported a fully translated wizard the whole time. See the
    # header of tools/i18n-wizard.py.
    python3 tools/i18n-wizard.py --check
else
    echo "i18n: python3 not installed — skipping the .desktop drift check"
fi

# THE ONE WORD THAT KEEPS AN INSTALL FROM BEING INTERRUPTED.
#
# config/includes.chroot/etc/systemd/system/opensnitch.service.d/
# 10-dagric-not-in-live.conf carries ConditionKernelCommandLine=!boot=live, and
# that is the whole mechanism keeping the OpenSnitch daemon out of the live
# session — where Calamares runs apt out of /tmp and a real Pro install stopped
# at 42% on a prompt whose Deny button was counting down.
#
# A condition that names a kernel argument the image does not pass is not an
# error anywhere. systemd evaluates it, finds boot=live absent, starts the
# daemon, and the install-time prompt comes back with nothing in any log to
# say why. Editing --bootappend-live is a completely reasonable thing for
# someone to do; losing this along with it must not be silent.
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

# SUBSCRIBE THE IMAGE TO ITS OWN UPDATE CHANNEL.
#
# config/includes.chroot/etc/apt/sources.list.d/dagric.list points every
# installed machine at the signed repository, and the keyring beside it is
# shipped — but none of that delivers anything, because the four dagric-*
# packages only ever existed in site/repo. Their CONTENTS reached the ISO
# through includes.chroot, so dpkg had no record of dagric-tools at all and
# `apt upgrade` on a sold machine could never offer a fix to the wizard, the
# manual, the wallpapers or the security baseline. The channel was live, signed,
# reachable — and nothing was subscribed to a single package in it.
#
# Building the .debs here, from the tree that is about to become the image, and
# handing them to live-build as local packages is what registers them. They are
# installed before config/includes.chroot is copied in (see the ordering note in
# stage-packages.sh), so the tree remains the source of truth for what ships and
# the packages exist to be RECORDED, at a version the channel can supersede.
#
# Free and Pro each build their own, after the edition gating above — so the
# free image never records a package built from the Pro tree.
#
# Skipped, loudly, when dpkg-deb is missing: a build host without it can still
# produce a correct ISO, it just produces one that cannot be updated in place.
if command -v dpkg-deb >/dev/null 2>&1; then
    rm -rf config/packages.chroot
    mkdir -p config/packages.chroot
    DAGRIC_PKG_STAGE="$BUILD/.pkgstage" \
        sh packages/stage-packages.sh "$BUILD" "$BUILD/config/packages.chroot"
    rm -rf "$BUILD/.pkgstage"
    echo "update channel: $(ls -1 config/packages.chroot/*.deb | wc -l) config packages staged for install"

    # Fail NOW if the tree's version is not ahead of what the channel publishes.
    #
    # Both sources are visible to apt during the build: the staged .debs at
    # file:/packages, pinned 1001, and the live channel from dagric.list. When
    # they offer the SAME version, the bytes still differ — a Pro build stages
    # packages assembled after edition gating, and the published copies came
    # from a different tree — so apt is asked to swap one 1.1.1 for a different
    # 1.1.1 under a pin above 1000, and calls that a downgrade:
    #
    #     The following packages will be DOWNGRADED: dagric-branding ...
    #     E: Packages were downgraded and -y was used without --allow-downgrades.
    #
    # That killed two builds twenty minutes in, and bumping the version "fixed"
    # it only until the same version was published — at which point the next
    # build failed identically. The order is what matters: BUMP, BUILD, THEN
    # PUBLISH. This turns forgetting it into a five-second error that says so.
    # EVERY package, not just dagric-tools. This gate used to read one control
    # file out of four, so a tree that bumped dagric-tools and forgot the other
    # three passed the check in five seconds and then died twenty minutes later
    # on whichever one still collided. A gate that catches a quarter of the cases
    # is worse than none, because it reads as an all-clear.
    CHANNEL=$(curl -fsS --max-time 15 \
        https://dagric-os.web.app/repo/dists/trixie/main/binary-amd64/Packages 2>/dev/null) \
        || CHANNEL=""
    if [ -z "$CHANNEL" ]; then
        # Say so out loud. Silence here is indistinguishable from "checked, all
        # clear", and a gate that fails open without a word is how the twenty
        # minute build death gets reintroduced by somebody on a flaky connection.
        echo "WARNING: could not reach the update channel — the version-collision" >&2
        echo "         check was SKIPPED, not passed. If this build dies on" >&2
        echo "         'Packages were DOWNGRADED' in about twenty minutes, that" >&2
        echo "         is why, and the fix is to bump packages/*/DEBIAN/control." >&2
    else
        COLLIDE=""
        for CTRL in packages/*/DEBIAN/control; do
            [ -f "$CTRL" ] || continue
            PKG=$(sed -n 's/^Package: //p' "$CTRL")
            TREEVER=$(sed -n 's/^Version: //p' "$CTRL")
            [ -n "$PKG" ] && [ -n "$TREEVER" ] || continue
            # Exact line match, so dagric-tools cannot be matched by a future
            # dagric-tools-something.
            LIVEVER=$(printf '%s\n' "$CHANNEL" \
                | awk -v p="$PKG" '$0=="Package: "p{f=1} f&&/^Version:/{print $2; exit}')
            [ -n "$LIVEVER" ] || continue
            if [ "$LIVEVER" = "$TREEVER" ]; then
                COLLIDE="$COLLIDE    $PKG $TREEVER
"
            fi
        done
        if [ -n "$COLLIDE" ]; then
            echo "ERROR: the update channel already publishes these exact versions," >&2
            echo "and this tree builds them again with different contents:" >&2
            printf '%s' "$COLLIDE" >&2
            echo "apt will refuse the build as a downgrade about twenty minutes from now." >&2
            echo >&2
            echo "Bump Version: in each colliding packages/*/DEBIAN/control, then build," >&2
            echo "then publish. Build first, publish second — never the other way round." >&2
            exit 1
        fi
        echo "update channel: checked all four packages, no version collisions"
    fi
else
    echo "WARNING: dpkg-deb not installed — the ISO will not be subscribed to" >&2
    echo "         the Dagric update channel (apt upgrade will deliver nothing)." >&2
fi

lb build

mkdir -p "$SRC/out"
case "$EDITION" in
    pro) NAME=dagric-os-pro-1.0-amd64.iso ;;
    *)   NAME=dagric-os-1.0-amd64.iso ;;
esac
# dd, not cp, and then check the size — because the destination is usually a
# Windows drive seen through WSL's 9p bridge, and cp fails there on a file this
# large:
#     cp: error writing '.../dagric-os-pro-1.0-amd64.iso': Cannot allocate memory
# It failed at 1.1 GB of a 3.8 GB image and still exited before the verify, so
# out/ was left holding a TRUNCATED ISO with a plausible name and a fresh
# timestamp. That is the worst possible failure mode for a build: the artefact
# looks finished, and the only way to find out otherwise is for somebody to
# flash it and watch it not boot.
#
# dd with an explicit block size writes in bounded chunks instead of letting cp
# choose a mapping strategy 9p cannot satisfy. The size comparison afterwards is
# the part that actually matters — any copy method can be interrupted, and a
# build must not report success over a short file.
SRCISO=$(ls -1 ./*.iso 2>/dev/null | head -1)
[ -n "$SRCISO" ] || { echo "no ISO produced" >&2; exit 1; }
mkdir -p "$SRC/out"
dd if="$SRCISO" of="$SRC/out/$NAME" bs=4M status=none

WANT=$(stat -c%s "$SRCISO")
GOT=$(stat -c%s "$SRC/out/$NAME" 2>/dev/null || echo 0)
if [ "$WANT" != "$GOT" ]; then
    echo "ERROR: copy is short — $GOT of $WANT bytes." >&2
    echo "The ISO itself is fine at $SRCISO; only the copy failed." >&2
    rm -f "$SRC/out/$NAME"
    exit 1
fi
echo "copied $NAME ($GOT bytes, verified)"

# Record the checksum beside the ISO, on every single build.
#
# Nothing did this, and the result was THREE published copies of the checksum
# carrying TWO different values: site/download.html and site/index.html each held
# a hand-transcribed pair, site/SHA256SUMS held another, and neither matched the
# ISO actually sitting in out/. The cause is structural — NAME is a fixed
# filename, so every rebuild overwrites the same path with different bytes while
# the recorded sums stay where they were. A buyer who followed the verify steps
# the download page insists they not skip got a MISMATCH, which reads as a
# corrupted or tampered download rather than as a stale web page.
#
# The two inline copies are gone from the site. This keeps the one that is left
# honest. Deliberately NOT signed here: signing is a release step that needs the
# key, and a build must never quietly emit something that looks signed.
SUMS="$SRC/out/SHA256SUMS"
[ -f "$SUMS" ] || : > "$SUMS"
grep -v "  ${NAME}\$" "$SUMS" > "$SUMS.tmp" 2>/dev/null || :
( cd "$SRC/out" && sha256sum "$NAME" ) >> "$SUMS.tmp"
LC_ALL=C sort -k2,2 "$SUMS.tmp" -o "$SUMS"
rm -f "$SUMS.tmp"
echo "recorded sha256 for $NAME in out/SHA256SUMS"
echo
echo "NOTE: out/SHA256SUMS has changed. Before deploying the site, copy it to"
echo "      site/ and RE-SIGN it — site/SHA256SUMS.sig covers the previous"
echo "      contents and will fail gpg --verify until it is regenerated."
echo "Done ($EDITION edition) — ISO is at out/$NAME"
