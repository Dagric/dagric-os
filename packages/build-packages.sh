#!/bin/sh
# Dagric OS — SUPERSEDED. This script must not run. Use packages/stage-packages.sh.
#
# repo.ps1 called this alongside make-repo.sh. Both of those were replaced with
# refusals; this one was missed, and it is the more dangerous of the three
# because it still runs to completion and its output looks correct.
#
# It read Version: from the same packages/*/DEBIAN/control files the real
# builder reads, so its .debs carried the CURRENT version string and nothing
# downstream could tell them apart. What they actually contained:
#
#   * NO dagric-tools AT ALL — three build_pkg calls where stage-packages.sh has
#     four. The wizard, the manual, the guide, the helpers and every
#     /usr/bin/dagric-* simply do not exist in its output.
#   * dagric-branding with ONE wallpaper pack (`cp -r .../wallpapers/Dagric`, an
#     exact directory name) against the 34 the tree ships, no
#     usr/share/sddm/themes/dagric, no usr/share/dagric/sddm or splash, and no
#     plasma/look-and-feel/org.dagric.splash.
#   * dagric-desktop-defaults with 3 of the 9 files the package declares as
#     conffiles, and nothing under /etc/xdg at all.
#
# dpkg removes what a new version no longer owns, so an owner who took that
# "upgrade" would lose 33 wallpaper packs, the SDDM theme, the Plasma splash,
# the default-browser declaration and the Konsole profile — silently, from a
# correctly signed update, and build-repo.sh could not catch it because its
# index/pool count check only compares the index to whatever was staged.
#
# It also skips every guard stage-packages.sh grew: the conffiles cross-check in
# both directions, normalise_modes (this is the build that shipped 0755
# kdeglobals), and the shebang-keyed chmod that keeps the /usr/lib/dagric
# programs executable across an upgrade.
#
# The live path is packages/stage-packages.sh, called by build.sh for the ISO
# and by packages/build-repo.sh for the channel, so the two are assembled from
# one source.
echo "build-packages.sh is superseded and will not run." >&2
echo >&2
echo "It builds only 3 of the 4 packages — dagric-tools is missing entirely —" >&2
echo "at the current version number, from an outdated file list. Publishing its" >&2
echo "output would strip files from every installed machine." >&2
echo >&2
echo "Use instead:  sh packages/stage-packages.sh REPO_ROOT OUTPUT_DIR" >&2
echo "         or:  sh packages/build-repo.sh" >&2
exit 1
